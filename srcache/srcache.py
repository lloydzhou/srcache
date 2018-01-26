#!/usr/bin/env python
# coding=utf-8

import redis

from tornado.options import options
import pickle
import functools
import logging
import random
from binascii import crc32
from tornado.ioloop import IOLoop


redispool = redis.ConnectionPool(
    host=options.REDIS_HOST,
    port=options.REDIS_PORT,
    db=options.REDIS_DB
)


def client():
    return redis.StrictRedis(connection_pool=redispool)


def stalecache(key=None, prifix=None, attr_key=None, attr_prifix=None,
               expire=600, stale=3600, time_lock=1, time_delay=1, max_time_delay=10):
    def _(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if kwargs.get('skip_cache'):
                return method(self, *args, **kwargs)
            name = key or kwargs.get('key', None) or (attr_key and getattr(self, attr_key))
            if not name:
                _prifix = prifix or (attr_prifix and getattr(self, attr_prifix))\
                    or '.'.join([self.__module__, self.__class__.__name__, method.__name__])
                name = "%s:%u" % (_prifix, crc32(pickle.dumps(args) + pickle.dumps(kwargs)))
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
                client().expire(name, expire + real_time_delay + time_lock)
                IOLoop.current().add_timeout(IOLoop.current().time() + real_time_delay, func)

            return v
        return wrapper
    return _

