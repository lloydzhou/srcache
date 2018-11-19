#!/usr/bin/env python
# coding=utf-8

import random
import functools
import logging
import pickle
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


def client():
    return redis.StrictRedis(connection_pool=redispool)


def gen_prefix(obj, method):
    return '.'.join([obj.__module__, obj.__class__.__name__, method.__name__])


def stalecache(key=None, prefix=None, attr_key=None, attr_prefix=None,
               expire=600, stale=3600, time_lock=1, time_delay=1, max_time_delay=10):
    def _(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if kwargs.get('skip_cache'):
                return method(self, *args, **kwargs)

            name = key or kwargs.get('key', None) or (attr_key and getattr(self, attr_key))
            if not name:
                _prefix = prefix or (attr_prefix and getattr(self, attr_prefix)) or gen_prefix(self, method)
                name = "%s:%u" % (_prefix, crc32(pickle.dumps(args) + pickle.dumps(kwargs)))
            res = client().pipeline().ttl(name).get(name).execute()
            v = pickle.loads(res[1]) if res[0] > 0 and res[1] else None
            if res[0] <= 0 or res[0] < stale:

                def func():
                    value = method(self, *args, **kwargs)
                    logging.debug("update cache: %s", name)
                    client().pipeline().set(
                        name, pickle.dumps(value)
                    ).expire(name, expire + stale).execute()
                    return value

                # create new cache in blocking modal, if cache not exists.
                if res[0] <= 0:
                    return func()

                # create new cache in non blocking modal, and return stale data.
                # set expire to get a "lock", and delay to run the task
                real_time_delay = random.randrange(time_delay, max_time_delay)
                client().expire(name, stale + real_time_delay + time_lock)
                IOLoop.current().add_timeout(IOLoop.current().time() + real_time_delay, func)

            return v

        @functools.wraps(method)
        async def async_wrapper(self, *args, **kwargs):
            if kwargs.get('skip_cache'):
                return await method(self, *args, **kwargs)

            name = key or kwargs.get('key', None) or (attr_key and getattr(self, attr_key))
            if not name:
                _prefix = prefix or (attr_prefix and getattr(self, attr_prefix)) or gen_prefix(self, method)
                name = "%s:%u" % (_prefix, crc32(pickle.dumps(args) + pickle.dumps(kwargs)))
            res = client().pipeline().ttl(name).get(name).execute()
            v = pickle.loads(res[1]) if res[0] > 0 and res[1] else None
            if res[0] <= 0 or res[0] < stale:

                async def func():
                    value = await method(self, *args, **kwargs)
                    logging.debug("update cache: %s", name)
                    client().pipeline().set(
                        name, pickle.dumps(value)
                    ).expire(name, expire + stale).execute()
                    return value

                # create new cache in blocking modal, if cache not exists.
                if res[0] <= 0:
                    return await func()

                # create new cache in non blocking modal, and return stale data.
                # set expire to get a "lock", and delay to run the task
                real_time_delay = random.randrange(time_delay, max_time_delay)
                client().expire(name, stale + real_time_delay + time_lock)
                IOLoop.current().add_timeout(IOLoop.current().time() + real_time_delay, func)

            return v

        return async_wrapper if iscoroutinefunction(method) else wrapper
    return _


def delete(key=None, prefix=None, attr_key=None, attr_prefix=None, target=None, stale=3600):
    def _(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            value = method(self, *args, **kwargs)
            c = client()

            # delete by key
            name = key or kwargs.get('key', None) or (attr_key and getattr(self, attr_key))
            if name:
                c.expire(name, stale)

            # delete by prefix
            _prefix = prefix or (attr_prefix and getattr(self, attr_prefix))\
                or (target and hasattr(self, target) and gen_prefix(self, getattr(self, target)))
            if _prefix:
                for name in c.keys(pattern="{}*".format(_prefix)):
                    c.expire(name, stale)

            return value
        return wrapper
    return _

