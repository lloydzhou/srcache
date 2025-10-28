# StaleRedisCache
python redis cache library, can using stale data, and create new cache async  
using tornado.ioloop to make async task.

## Recent Improvements

This library has been recently improved with the following enhancements:

- ✅ **Error Handling**: Comprehensive error handling with optional fallback to direct method calls
- ✅ **JSON Serialization**: Safer alternative to pickle with `use_json=True` parameter
- ✅ **Performance**: Optimized Redis client reuse and SCAN-based deletion
- ✅ **Robustness**: Better error recovery and detailed logging

See [IMPROVEMENTS.md](IMPROVEMENTS.md) for detailed documentation and [ANALYSIS.md](ANALYSIS.md) for library analysis.

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

### Advanced usage with new features

    class A:
        # Use JSON serialization (safer, but limited to JSON-compatible types)
        @stalecache(expire=10, stale=10, use_json=True)
        def get_user_data(self, user_id):
            return {"id": user_id, "name": "John", "roles": ["admin"]}
        
        # Enable fallback to direct call if Redis fails
        @stalecache(expire=10, stale=10, enable_fallback=True)
        def critical_data(self, id):
            return fetch_from_database(id)


## Test

run command "python3 test.py" to test this library.

run command "python3 test_improvements.py" to test new features.

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

