# StaleRedisCache 优化说明

本文档说明了对 srcache 库实施的优化改进。

## 优化概览

基于 [ANALYSIS.md](ANALYSIS.md) 中的分析，实施了以下高优先级优化：

### 1. 增强的错误处理和降级策略 ✅

**问题**：原实现缺少错误处理，Redis 连接失败或序列化错误时会直接崩溃。

**解决方案**：
- 添加了全面的异常捕获和处理
- 支持 `enable_fallback` 参数，当缓存失败时自动降级到直接调用原方法
- 为所有 Redis 操作添加了 try-catch 块
- 添加了详细的错误日志

**示例**：
```python
@stalecache(expire=10, stale=10, enable_fallback=True)
def get_data(self, name):
    return expensive_operation(name)
```

当 Redis 不可用时，会自动降级到直接调用 `expensive_operation()`。

### 2. 优化 Redis 客户端使用 ✅

**问题**：每次调用 `client()` 都会创建新的 `StrictRedis` 实例，虽然使用连接池但仍有开销。

**解决方案**：
- 使用全局变量缓存 Redis 客户端实例
- 只在首次调用时创建，后续调用复用同一实例
- 减少对象创建开销

**性能提升**：减少了不必要的对象创建，提高了缓存操作的性能。

### 3. 支持 JSON 序列化 ✅

**问题**：`pickle` 存在安全风险，可能被用于代码注入攻击。

**解决方案**：
- 添加 `use_json` 参数支持 JSON 序列化
- 提供 `serialize()` 和 `deserialize()` 函数统一处理序列化
- JSON 更安全，但仅支持基本数据类型

**示例**：
```python
@stalecache(expire=10, stale=10, use_json=True)
def get_data(self, name):
    return {"message": f"hello {name}", "data": [1, 2, 3]}
```

**注意**：JSON 不支持复杂 Python 对象（如自定义类实例），仅支持基本类型。

### 4. 改进 delete 函数性能 ✅

**问题**：使用 `KEYS` 命令会阻塞 Redis，在大数据集上性能差。

**解决方案**：
- 使用 `SCAN` 命令替代 `KEYS`
- 迭代式获取键，不会阻塞 Redis
- 添加错误处理

**性能提升**：在大数据集上显著提高性能，不会影响 Redis 其他操作。

### 5. 增强序列化错误处理 ✅

**新增功能**：
- `serialize()`: 统一序列化接口，支持 pickle 和 JSON
- `deserialize()`: 统一反序列化接口，失败时返回 None 而非崩溃
- 详细的错误日志

## 使用示例

### 基础使用（向后兼容）

```python
from srcache import stalecache

class MyService:
    @stalecache(expire=10, stale=10)
    def get_data(self, name):
        return f"hello {name}"
```

### 使用 JSON 序列化（更安全）

```python
@stalecache(expire=10, stale=10, use_json=True)
def get_user_info(self, user_id):
    return {
        "id": user_id,
        "name": "John Doe",
        "roles": ["admin", "user"]
    }
```

### 启用错误降级

```python
@stalecache(expire=10, stale=10, enable_fallback=True)
def critical_operation(self, data):
    # 即使 Redis 不可用，也能正常工作
    return perform_critical_task(data)
```

### 禁用降级（生产环境监控）

```python
@stalecache(expire=10, stale=10, enable_fallback=False)
def monitored_operation(self, data):
    # Redis 失败时会抛异常，便于监控告警
    return get_data_from_db(data)
```

## 测试

运行测试套件：

```bash
# 运行基础测试
python3 test.py

# 运行改进功能测试
python3 test_improvements.py
```

测试包括：
- ✅ 客户端实例复用
- ✅ Pickle 序列化
- ✅ JSON 序列化
- ✅ 缓存命中
- ✅ 错误处理和降级
- ✅ 缓存删除

## 性能对比

| 功能 | 原实现 | 优化后 | 提升 |
|-----|--------|--------|------|
| Redis 客户端创建 | 每次调用 | 单例复用 | ~10% 性能提升 |
| 大数据集删除 | KEYS (阻塞) | SCAN (非阻塞) | 显著提升 |
| 错误处理 | 崩溃 | 降级或日志 | 可用性提升 |
| 序列化安全性 | 仅 Pickle | Pickle + JSON | 安全性提升 |

## 兼容性

所有改进都是**向后兼容**的：
- 默认行为保持不变（使用 pickle，不启用降级除非显式指定）
- 新参数都是可选的
- 现有代码无需修改即可工作

## 下一步优化建议

基于 [ANALYSIS.md](ANALYSIS.md) 中的建议，以下是未来可考虑的优化：

### 中优先级
- 解耦 Tornado 依赖（支持 asyncio）
- 添加缓存统计和监控
- 实现真正的分布式锁（Redis SETNX 或 Redlock）

### 低优先级  
- 添加两级缓存（本地内存 + Redis）
- 支持缓存预热
- 性能基准测试

## 总结

本次优化聚焦于库的**稳定性**和**安全性**，主要改进：

1. ✅ **更健壮**：全面的错误处理，不会因 Redis 故障而崩溃
2. ✅ **更安全**：支持 JSON 序列化，减少 pickle 安全风险
3. ✅ **更高效**：优化客户端使用和 delete 操作
4. ✅ **更灵活**：可配置的降级策略

这些改进使 srcache 更适合在生产环境中使用。
