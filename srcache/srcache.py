#!/usr/bin/env python
# coding=utf-8

import random
import functools
import logging
import pickle
import json
from inspect import iscoroutinefunction

import redis
from binascii import crc32
from tornado.ioloop import IOLoop
from tornado.options import options


redispool = redis.ConnectionPool(
    host=options.REDIS_HOST,
    port=options.REDIS_PORT,
    db=options.REDIS_DB
)

# Reuse Redis client instance for better performance
_redis_client = None


def client():
    """Get or create Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.StrictRedis(connection_pool=redispool)
    return _redis_client


def gen_prefix(obj, method):
    return '.'.join([obj.__module__, obj.__class__.__name__, method.__name__])


def serialize(data, use_json=False):
    """Serialize data with error handling."""
    try:
        if use_json:
            return json.dumps(data).encode('utf-8')
        else:
            return pickle.dumps(data)
    except (pickle.PicklingError, TypeError, json.JSONEncodeError) as e:
        logging.error("Serialization error: %s", e)
        raise


def deserialize(data, use_json=False):
    """Deserialize data with error handling."""
    if not data:
        return None
    try:
        if use_json:
            return json.loads(data.decode('utf-8'))
        else:
            return pickle.loads(data)
    except (pickle.UnpicklingError, ValueError, json.JSONDecodeError) as e:
        logging.warning("Deserialization error: %s", e)
        return None


def stalecache(key=None, prefix=None, attr_key=None, attr_prefix=None,
               expire=600, stale=3600, time_lock=1, time_delay=1, max_time_delay=10,
               use_json=False, enable_fallback=True):
    """
    Stale cache decorator with error handling.
    
    Args:
        key: Fixed cache key
        prefix: Cache key prefix
        attr_key: Attribute name to get key from
        attr_prefix: Attribute name to get prefix from
        expire: Cache expiration time in seconds
        stale: Stale period in seconds (total TTL = expire + stale)
        time_lock: Lock time in seconds to prevent concurrent updates
        time_delay: Minimum delay before async update
        max_time_delay: Maximum delay before async update
        use_json: Use JSON serialization instead of pickle (safer but limited types)
        enable_fallback: Fall back to calling original method if cache fails
    """
    def _(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if kwargs.get('skip_cache'):
                return method(self, *args, **kwargs)

            # Generate cache key
            name = key or kwargs.get('key', None) or (attr_key and getattr(self, attr_key, None))
            if not name:
                _prefix = prefix or (attr_prefix and getattr(self, attr_prefix, None)) or gen_prefix(self, method)
                try:
                    name = "%s:%u" % (_prefix, crc32(serialize(args, use_json) + serialize(kwargs, use_json)))
                except Exception as e:
                    logging.error("Failed to generate cache key: %s", e)
                    if enable_fallback:
                        return method(self, *args, **kwargs)
                    raise

            # Try to get cached value
            try:
                res = client().pipeline().ttl(name).get(name).execute()
                v = deserialize(res[1], use_json) if res[0] > 0 and res[1] else None
            except redis.RedisError as e:
                logging.error("Redis error when getting cache: %s", e)
                if enable_fallback:
                    return method(self, *args, **kwargs)
                raise
            except Exception as e:
                logging.error("Unexpected error when getting cache: %s", e)
                if enable_fallback:
                    return method(self, *args, **kwargs)
                raise

            if res[0] <= 0 or res[0] < stale:

                def func():
                    try:
                        value = method(self, *args, **kwargs)
                        logging.debug("update cache: %s", name)
                        client().pipeline().set(
                            name, serialize(value, use_json)
                        ).expire(name, expire + stale).execute()
                        return value
                    except redis.RedisError as e:
                        logging.error("Redis error when updating cache: %s", e)
                        # Return the computed value even if cache update fails
                        return value if 'value' in locals() else method(self, *args, **kwargs)
                    except Exception as e:
                        logging.error("Error updating cache: %s", e)
                        raise

                # create new cache in blocking modal, if cache not exists.
                if res[0] <= 0:
                    return func()

                # create new cache in non blocking modal, and return stale data.
                # set expire to get a "lock", and delay to run the task
                try:
                    real_time_delay = random.randrange(time_delay, max_time_delay)
                    client().expire(name, stale + real_time_delay + time_lock)
                    IOLoop.current().add_timeout(IOLoop.current().time() + real_time_delay, func)
                except Exception as e:
                    logging.error("Error scheduling async cache update: %s", e)

            return v

        @functools.wraps(method)
        async def async_wrapper(self, *args, **kwargs):
            if kwargs.get('skip_cache'):
                return await method(self, *args, **kwargs)

            # Generate cache key
            name = key or kwargs.get('key', None) or (attr_key and getattr(self, attr_key, None))
            if not name:
                _prefix = prefix or (attr_prefix and getattr(self, attr_prefix, None)) or gen_prefix(self, method)
                try:
                    name = "%s:%u" % (_prefix, crc32(serialize(args, use_json) + serialize(kwargs, use_json)))
                except Exception as e:
                    logging.error("Failed to generate cache key: %s", e)
                    if enable_fallback:
                        return await method(self, *args, **kwargs)
                    raise

            # Try to get cached value
            try:
                res = client().pipeline().ttl(name).get(name).execute()
                v = deserialize(res[1], use_json) if res[0] > 0 and res[1] else None
            except redis.RedisError as e:
                logging.error("Redis error when getting cache: %s", e)
                if enable_fallback:
                    return await method(self, *args, **kwargs)
                raise
            except Exception as e:
                logging.error("Unexpected error when getting cache: %s", e)
                if enable_fallback:
                    return await method(self, *args, **kwargs)
                raise

            if res[0] <= 0 or res[0] < stale:

                async def func():
                    try:
                        value = await method(self, *args, **kwargs)
                        logging.debug("update cache: %s", name)
                        client().pipeline().set(
                            name, serialize(value, use_json)
                        ).expire(name, expire + stale).execute()
                        return value
                    except redis.RedisError as e:
                        logging.error("Redis error when updating cache: %s", e)
                        # Return the computed value even if cache update fails
                        return value if 'value' in locals() else await method(self, *args, **kwargs)
                    except Exception as e:
                        logging.error("Error updating cache: %s", e)
                        raise

                # create new cache in blocking modal, if cache not exists.
                if res[0] <= 0:
                    return await func()

                # create new cache in non blocking modal, and return stale data.
                # set expire to get a "lock", and delay to run the task
                try:
                    real_time_delay = random.randrange(time_delay, max_time_delay)
                    client().expire(name, stale + real_time_delay + time_lock)
                    IOLoop.current().add_timeout(IOLoop.current().time() + real_time_delay, func)
                except Exception as e:
                    logging.error("Error scheduling async cache update: %s", e)

            return v

        return async_wrapper if iscoroutinefunction(method) else wrapper
    return _


def delete(key=None, prefix=None, attr_key=None, attr_prefix=None, target=None, stale=3600):
    """
    Delete cache decorator with improved performance.
    
    Uses SCAN instead of KEYS for better performance with large datasets.
    """
    def _(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            value = method(self, *args, **kwargs)
            
            try:
                c = client()

                # delete by key
                name = key or kwargs.get('key', None) or (attr_key and getattr(self, attr_key, None))
                if name:
                    c.expire(name, stale)

                # delete by prefix
                _prefix = prefix or (attr_prefix and getattr(self, attr_prefix, None))\
                    or (target and hasattr(self, target) and gen_prefix(self, getattr(self, target)))
                if _prefix:
                    # Use SCAN instead of KEYS for better performance
                    pattern = "{}*".format(_prefix)
                    cursor = 0
                    while True:
                        cursor, keys = c.scan(cursor=cursor, match=pattern, count=100)
                        if keys:
                            for cache_key in keys:
                                c.expire(cache_key, stale)
                        if cursor == 0:
                            break
            except redis.RedisError as e:
                logging.error("Redis error when deleting cache: %s", e)
            except Exception as e:
                logging.error("Error deleting cache: %s", e)

            return value
        return wrapper
    return _

