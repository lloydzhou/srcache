#!/usr/bin/env python
# coding=utf-8
import sys
import redis
from binascii import crc32
import json
from tornado.ioloop import IOLoop
import logging
import functools
import pickle
import random


class RedisDB(object):

    redis_pool = None

    def __init__(self, hosts=[('localhost', 6379, 0)]):
        self.redis_pool = self.redis_pool or [redis.Redis(connection_pool=redis.ConnectionPool(
            host=h, port=p, db=d), socket_timeout=0.5) for h, p, d in hosts]

    def client(self, key=None):
        # key not set, will return first connection in pool.
        # so the first server mast be the master redis server
        if not key:
            return self.redis_pool[0]
        idx = crc32(key) % len(self.redis_pool)
        return self.redis_pool[idx]


def stale_redis_cache(redisdb=None, key=None, prifix=None, attr_key=None, attr_prifix=None,
               expire=600, stale=3600, time_lock=1, time_delay=1, max_time_delay=10):
    if not redisdb:
        redisdb = RedisDB()
    def _(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            name = key or (attr_key and getattr(self, attr_key))
            if not name:
                _prifix = prifix or (attr_prifix and getattr(self, attr_prifix)) or method.__name__
                name = "%s:%08x" % (_prifix, crc32(pickle.dumps(args) + pickle.dumps(kwargs)) & 0xffffffff)
            res = redisdb.client(name).pipeline().ttl(name).get(name).execute()
            v = pickle.loads(res[1]) if res[0] > 0 and res[1] else None
            if res[0] <= 0 or res[0] < stale:

                def func():
                    value = method(self, *args, **kwargs)
                    logging.info("update cache: %s", name)
                    redisdb.client().pipeline().set(
                        name, pickle.dumps(value)
                    ).expire(name, expire + stale).execute()
                    return value

                # create new cache in blocking modal, if cache not exists.
                if res[0] <= 0:
                    return func()

                # create new cache in non blocking modal, and return stale data.
                # set expire to get a "lock", and delay to run the task
                real_time_delay = max_time_delay > time_delay and random.randrange(time_delay, max_time_delay) or 0
                redisdb.client().expire(name, expire + real_time_delay + time_lock)
                IOLoop.current().add_timeout(IOLoop.current().time() + real_time_delay, func)

            return v
        return wrapper
    return _


class StaleRedisCache(object):

    def __init__(self, hosts=[('localhost', 6379, 0)], **kwargs):
        self.config = kwargs
        self.config['redisdb'] = RedisDB(hosts=hosts)

    def get(self, key, callback=None, *args, **kwargs):

        ckwargs = self.config
        ckwargs['key'] = key
        @stale_redis_cache(**ckwargs)
        def get_data(*args, **kwargs):
            return callback(*args, **kwargs)

        return get_data(*args, **kwargs)


