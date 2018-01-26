#!/usr/bin/env python
# coding=utf-8
import sys
import logging
from tornado.ioloop import IOLoop
from tornado.options import define

define('REDIS_HOST', default="localhost")
define('REDIS_PORT', default=6379)
define('REDIS_DB', default=1)

from srcache import stalecache


class Test:
    @stalecache(expire=10, stale=10)
    def get_data(self, name):
        return "hello %s" % name


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    t = Test()
    print(t.get_data('world'))
    IOLoop.current().add_timeout(IOLoop.current().time() + 2, lambda: IOLoop.current().stop())
    IOLoop.instance().start()

