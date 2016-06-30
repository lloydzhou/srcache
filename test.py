#!/usr/bin/env python
# coding=utf-8
import sys
import logging
from tornado.ioloop import IOLoop
from tosredis import StaleRedisCache


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    cache = StaleRedisCache(expire=10, stale=10, max_time_delay=0, time_delay=0)
    # using callback to auto create cache.
    print cache.get('foo', lambda x: "hello %s" % x, 'world')
    IOLoop.current().add_timeout(IOLoop.current().time() + 2, lambda: IOLoop.current().stop())
    IOLoop.instance().start()

