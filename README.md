# StaleRedisCache
python redis cache library, can using stale data, and create new cache async  
using tornado.ioloop to make async task.

## Synopsis

### using decorator

    class A:
        @stalecache(expire=10, stale=10)
        def get_data(self, name):
            return "hello %s" % name
    
    if __name__ == '__main__':
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        a = A()
        print(a.get_data('world'))
        IOLoop.current().add_timeout(IOLoop.current().time() + 2, lambda: IOLoop.current().stop())
        IOLoop.instance().start()


## Test

run command "python3 test.py" to test this library.

#### first time create new cache in blocking modal


    DEBUG:root:get cache in blocking modal: __main__.Test.get_data:3101872214
    DEBUG:root:update cache: __main__.Test.get_data:3101872214
    hello world

#### Hit cache, just return cached data


    DEBUG:root:get cache: __main__.Test.get_data:3101872214
    hello world

#### Cache in stale modal, auto create new cache in non blocking modal


    DEBUG:root:get cache: __main__.Test.get_data:3101872214
    hello world
    DEBUG:root:update cache: __main__.Test.get_data:3101872214

