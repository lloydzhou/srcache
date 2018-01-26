# StaleRedisCache
python redis cache library, can using stale data, and create new cache async  
using tornado.ioloop to make async task.

## Synopsis

### using decorator

    @stalecache()
    def get_data(name):
        return "hello %s" % name

    print(get_data('world'))
    IOLoop.current().add_timeout(IOLoop.current().time() + 2, lambda: IOLoop.current().stop())
    IOLoop.instance().start()


## Test

run command "python3 test.py" to test this library.

#### first time create new cache in blocking modal


    INFO:root:get redis cache for foo, and ttl is: -1
    INFO:root:auto  create new cache for foo
    INFO:root:auto set value for key foo
    hello world

#### Hit cache, just return cached data


    INFO:root:get redis cache for foo, and ttl is: 16
    hello world

#### Cache in stale modal, auto create new cache in non blocking modal


    INFO:root:get redis cache for foo, and ttl is: 6
    INFO:root:auto  create new cache for foo
    hello world
    INFO:root:auto set value for key foo
