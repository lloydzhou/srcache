#!/usr/bin/env python
# coding=utf-8
import os
import sys
import redis
from binascii import crc32
import json
from tornado.ioloop import IOLoop
import logging


class StaleRedisCache(object):

    redis_pool = None

    def __init__(self, hosts=[('localhost', 6379, 0)], duration=600, stale=100):
        self.duration = duration
        self.redis_pool = self.redis_pool or [redis.Redis(connection_pool=redis.ConnectionPool(host=h, port=p, db=d), socket_timeout=0.5) for h,p,d in hosts]
        self.stale = stale

    def _get_redis(self, key=None):
        if not key:
            return self.redis_pool[0]
        idx = crc32(key) % len(self.redis_pool)
        return self.redis_pool[idx]

    def get(self, key, callback=None, *args, **kwargs):
        r = self._get_redis(key)
        res = r.pipeline().ttl(key).get(key).execute()
        # may catch exception.
        v = json.loads(res[1]) if res[0] and res[1] else None
        logging.info("get redis cache for %s, and ttl is: %d" % (key, res[0] or -1))

        if not res[0] or res[0] < self.stale and callback:
            logging.info("auto  create new cache for %s" % (key))
            # define inline callback to create new cache.
            def func():
                value = callback and callback(*args, **kwargs)
                logging.info("auto set value for key %s" % key)
                r.pipeline().set(key, json.dumps(value)).expire(key, int(kwargs.get('duration', self.duration)) + self.stale).execute()
                return value
            # create new cache in blocking modal, if cache not exists.
            if not res[0]:
                return func()

            # create new cache in non blocking modal, and return stale data.
            IOLoop.current().add_timeout(IOLoop.current().time(), func)

        return v

    def set(self, key, value, duration=60):
        self._get_redis(key).pipeline().set(key, json.dumps(value)).expire(key, int(duration or self.duration) + int(self.stale)).execute()

    def delete(self, key):
        self._get_redis(key).delete(key)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    cache = StaleRedisCache(duration=10, stale=10)
    # using callback to auto create cache.
    print cache.get('foo', lambda x: "hello %s" % x, 'world')
    IOLoop.current().add_timeout(IOLoop.current().time() + 3, lambda: IOLoop.current().stop())
    IOLoop.instance().start()

