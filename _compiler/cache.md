# LRU 缓存设计 (Cache)

> 模块路径: `_compiler/cache`
> 版本: v1.0
> 依赖: 无外部依赖

---

## 1. 概述

编译缓存模块基于 LRU (Least Recently Used) 策略缓存编译结果，避免对相同模板+上下文的重复编译。缓存键由模板内容与编译上下文联合计算 SHA256 哈希生成。

### 数据流

```
编译请求 (source + context)
         │
         ▼
  Cache.get(cache_key)
         │
    ┌────┴─────┐
    │ 命中?     │
    ├ YES ──────┤→ 返回缓存的 RenderResult, cache_hit=True
    │ NO        │
    └───────────┘
         │
         ▼
  执行完整编译管线
         │
         ▼
  Cache.put(cache_key, result)
         │
         ▼
  返回 RenderResult, cache_hit=False
```

---

## 2. 类型定义

### 2.1 CacheEntry

```python
from dataclasses import dataclass
import time

@dataclass
class CacheEntry:
    key: str                      # SHA256 哈希键
    value: "RenderResult"         # 缓存的编译结果
    created_at: float             # 创建时间戳 (time.time())
    ttl: float                    # 生存时间 (秒)
    hit_count: int = 0            # 命中次数
    last_accessed: float = 0.0    # 最后访问时间

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at
```

### 2.2 缓存统计

```python
@dataclass
class CacheStats:
    total_entries: int            # 当前缓存条目数
    total_hits: int               # 总命中次数
    total_misses: int             # 总未命中次数
    evictions: int                # 淘汰次数
    hit_rate: float               # 命中率 = hits / (hits + misses)
    avg_hit_time_ms: float        # 平均命中延迟
    memory_usage_bytes: int       # 预估内存占用
```

### 2.3 缓存配置

```python
@dataclass
class CacheConfig:
    max_size: int = 1000          # 最大缓存条目数 (与 config.yaml 一致)
    ttl_seconds: float = 3600.0   # 默认TTL (与 config.yaml 一致)
    enable_stats: bool = True     # 是否启用统计
    shard_count: int = 16         # 分片数 (并发优化)
```

---

## 3. 缓存键计算

### 3.1 键生成算法

```python
import hashlib

def compute_cache_key(
    source: str,
    context: CompilationContext,
) -> str:
    """
    计算缓存键: SHA256(source + context_canonical)

    步骤:
      1. 序列化 context 为规范形式 (排序键值对)
      2. 拼接 source + canonical_context
      3. 计算 SHA256 哈希
      4. 返回十六进制字符串 (前16字符)
    """
    canonical = json.dumps(
        {
            "model": context.model,
            "language": context.language,
            "industry": context.industry,
            "extras": dict(sorted(context.extras.items())),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    raw = source + "|" + canonical
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
```

### 3.2 键碰撞概率

| 键空间 | 碰撞概率 (1000条目) |
|--------|-------------------|
| SHA256[:16] (64 bit) | ≈ 2.7×10⁻⁸ |
| SHA256[:32] (128 bit) | ≈ 0 |

> 默认使用16字符前缀，对1000条目级缓存碰撞可忽略。碰撞时后验证 source+context 完全匹配。

---

## 4. CompileCache 类设计

### 4.1 类签名

```python
from collections import OrderedDict
from threading import Lock

class CompileCache:
    def __init__(self, config: CacheConfig | None = None) -> None: ...
    def get(self, key: str) -> "RenderResult | None": ...
    def put(self, key: str, value: "RenderResult", ttl: float | None = None) -> None: ...
    def invalidate(self, key: str) -> bool: ...
    def invalidate_all(self) -> None: ...
    def get_stats(self) -> CacheStats: ...
    def _evict_lru(self) -> None: ...
    def _cleanup_expired(self) -> int: ...
```

### 4.2 内部结构

```python
class CompileCache:
    _config: CacheConfig
    _entries: OrderedDict[str, CacheEntry]  # 有序字典, 维护LRU顺序
    _lock: Lock                              # 线程安全锁
    _stats: _InternalStats                   # 内部统计计数器
```

---

## 5. 核心算法

### 5.1 get 流程

```
输入: key (缓存键)

1. 获取锁
2. 若 key 不在 _entries → stats.misses++, 返回 None
3. entry = _entries[key]
4. 若 entry.is_expired → 删除, stats.misses++, 返回 None
5. 将 key 移到 OrderedDict 末尾 (标记为最近使用)
6. entry.hit_count++
7. entry.last_accessed = time.time()
8. stats.hits++
9. 返回 entry.value
```

### 5.2 put 流程

```
输入: key, value, ttl

1. 获取锁
2. 若 key 已存在 → 更新 entry, 移到末尾, 返回
3. 若 len(_entries) >= max_size → _evict_lru()
4. 创建 CacheEntry(key, value, created_at, ttl)
5. _entries[key] = entry (自动插入末尾)
6. stats.puts++
```

### 5.3 LRU 淘汰

```
输入: 无

1. 若 _entries 为空 → 返回
2. 清理过期条目: _cleanup_expired()
3. 若仍超过容量 → 删除最旧的条目 (OrderedDict 首项)
4. stats.evictions++
5. 重复步骤3直到 len(_entries) < max_size
```

### 5.4 过期清理

```
输入: 无

1. 遍历 _entries
2. 收集所有 is_expired 的键
3. 批量删除
4. 返回清理数量
```

---

## 6. 缓存集成点

### 6.1 编译管线集成

```python
def compile_with_cache(
    source: str,
    context: CompilationContext,
    cache: CompileCache,
    pipeline: "Pipeline",
) -> RenderResult:
    """带缓存的编译入口"""
    cache_key = compute_cache_key(source, context)

    cached = cache.get(cache_key)
    if cached is not None:
        cached.report.details.cache_hit = True
        return cached

    result = pipeline.compile(source, context)
    result.report.details.cache_hit = False
    cache.put(cache_key, result)
    return result
```

### 6.2 缓存失效触发

| 事件 | 失效范围 |
|------|---------|
| 模板更新 | invalidate(template_key) |
| 上下文维度变更 | 自动 (键包含上下文) |
| 配置变更 | invalidate_all() |
| 手动刷新 | invalidate(key) / invalidate_all() |

---

## 7. 示例

### 7.1 缓存命中

```python
cache = CompileCache(CacheConfig(max_size=100, ttl_seconds=3600))

# 第一次编译
result1 = compile_with_cache(source, ctx, cache, pipeline)
assert result1.report.details.cache_hit == False

# 第二次相同编译 (命中)
result2 = compile_with_cache(source, ctx, cache, pipeline)
assert result2.report.details.cache_hit == True
```

### 7.2 LRU 淘汰

```python
cache = CompileCache(CacheConfig(max_size=3))

cache.put("key_a", result_a)  # [A]
cache.put("key_b", result_b)  # [A, B]
cache.put("key_c", result_c)  # [A, B, C]
cache.get("key_a")            # [B, C, A] (A被访问, 移到末尾)
cache.put("key_d", result_d)  # [C, A, D] (B最久未使用, 被淘汰)
```

### 7.3 TTL 过期

```python
cache = CompileCache(CacheConfig(ttl_seconds=0.1))

cache.put("key", result)
time.sleep(0.2)
assert cache.get("key") is None  # 已过期
```

### 7.4 统计信息

```python
stats = cache.get_stats()
# CacheStats(
#     total_entries=50,
#     total_hits=820,
#     total_misses=180,
#     evictions=12,
#     hit_rate=0.82,
#     avg_hit_time_ms=2.3,
#     memory_usage_bytes=204800
# )
```

---

## 8. 并发安全

### 8.1 线程安全设计

- 所有公开方法使用 `threading.Lock` 保护
- `OrderedDict` 操作在锁内完成
- 统计计数器使用原子操作

### 8.2 分片优化 (可选)

```python
class ShardedCompileCache:
    """
    分片缓存: 将键空间均匀分散到 N 个独立 CompileCache
    减少锁竞争，提升并发性能

    分片选择: hash(key) % shard_count
    """
    def __init__(self, config: CacheConfig) -> None:
        self._shards = [
            CompileCache(config) for _ in range(config.shard_count)
        ]

    def _get_shard(self, key: str) -> CompileCache:
        return self._shards[hash(key) % len(self._shards)]
```

---

## 9. 性能目标

| 指标 | 目标值 | 测量方式 |
|------|--------|---------|
| 命中率 | ≥ 80% | hits / (hits + misses) |
| 命中延迟 | < 10ms | 从 get() 调用到返回结果 |
| 未命中延迟 | < 1ms | get() 未命中时的开销 |
| 淘汰开销 | < 0.1ms | 单次 LRU 淘汰 |
| 内存占用 | < 100MB | max_size=1000 时的峰值 |
| 并发吞吐 | ≥ 10000 ops/s | 分片模式下 8 线程 |

---

## 10. 与编译管线接口

```
Pipeline.compile() 调用链:

  source + context
       │
       ▼
  compute_cache_key() → cache.get()
       │                    │
       │              ┌─────┴─────┐
       │              │ 命中      │ 未命中
       │              ▼           ▼
       │         返回缓存结果   Lexer→Parser→Evaluator→Renderer
       │                            │
       │                            ▼
       │                      cache.put() → 返回结果
```

cache_hit 字段最终写入 CompileReport.details.cache_hit，符合 compile_report.schema.json。
