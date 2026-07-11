# Token优化策略v2

> 版本：v16.0.0 | 从L0-L3压缩到动态优化

---

## 1. 压缩层级(v1回顾+v2增强)

| 层级 | 名称 | 描述 | 压缩率 | 信息损失 |
|------|------|------|--------|---------|
| L0 | 原文 | 完整无压缩 | 0% | 无 |
| L1 | 精简 | 去除冗余+合并相似 | 20-30% | 极小 |
| L2 | 压缩 | 缩写+引用+模板化 | 40-60% | 可控 |
| L3 | 极致 | 最小表达+运行时展开 | 60-80% | 需验证 |

## 2. v2新增策略

### 2.1 动态压缩(Dynamic Compression)

根据模型能力和场景复杂度动态选择压缩层级：

```python
class DynamicCompressor:
    def select_level(self, model_capability, scenario_complexity, token_budget):
        """
        动态选择最优压缩层级
        - 高能力模型 + 低复杂度 + 宽预算 → L0/L1
        - 低能力模型 + 高复杂度 + 紧预算 → L2/L3
        """
        if token_budget == "unlimited":
            return CompressionLevel.L0
        if model_capability.score > 0.8 and scenario_complexity < 0.5:
            return CompressionLevel.L1
        if model_capability.score > 0.5 and scenario_complexity < 0.7:
            return CompressionLevel.L2
        return CompressionLevel.L3
```

### 2.2 智能缓存(Smart Cache)

| 缓存类型 | 键 | 值 | TTL | 命中条件 |
|---------|-----|-----|-----|---------|
| 场景缓存 | hash(scenario+model+params) | 编译后场景 | 1小时 | 参数不变 |
| 片段缓存 | hash(fragment) | 编译后片段 | 24小时 | 片段不变 |
| Schema缓存 | hash(schema) | 验证器 | 永久 | Schema不变 |
| 翻译缓存 | hash(text+target_lang) | 翻译结果 | 7天 | 源文本不变 |

```python
class SmartCache:
    def get_or_compute(self, key, compute_fn, ttl):
        cached = self.cache.get(key)
        if cached and not cached.is_expired():
            self.stats.hit()
            return cached.value
        value = compute_fn()
        self.cache.set(key, value, ttl)
        self.stats.miss()
        return value
```

### 2.3 增量渲染(Incremental Rendering)

对于长输出场景，分块渲染+流式输出：

```python
class IncrementalRenderer:
    def render(self, scenario, context):
        """
        将场景分解为可增量渲染的块：
        1. 头部块(不变): 立即渲染+缓存
        2. 上下文块(低频变): 检测变化+条件渲染
        3. 动态块(高频变): 每次渲染
        """
        header = self.render_header(scenario)  # 缓存
        context = self.render_context(scenario, context, incremental=True)
        dynamic = self.render_dynamic(scenario, context)
        return header + context + dynamic
```

### 2.4 预计算(Pre-computation)

在空闲时预计算高频场景的编译结果：

```python
class PreComputer:
    def precompute(self):
        """
        策略：
        1. 统计场景使用频率(访问日志)
        2. 对Top-20场景预编译
        3. 对Top-10场景×Top-5模型预缓存
        4. 对高频片段预渲染
        """
        top_scenarios = self.usage_stats.top_scenarios(n=20)
        for scenario in top_scenarios:
            compiled = self.compiler.compile(scenario)
            self.cache.set(f"compiled:{scenario.id}", compiled, ttl="1h")
            
            top_models = self.usage_stats.top_models(scenario, n=5)
            for model in top_models:
                rendered = self.renderer.render(compiled, model)
                self.cache.set(f"rendered:{scenario.id}:{model}", rendered, ttl="30min")
```

## 3. 冷启动优化

### 3.1 懒加载(Lazy Loading)

```python
class LazyLoader:
    """
    按需加载而非全量加载：
    - 核心: 立即加载(PromptEngine, ScenarioLoader)
    - 扩展: 首次使用时加载(Combinator, Validator)
    - 行业: 按需加载(IndustryPlugin)
    - i18n: 按语言加载(LocaleData)
    """
    _loaded = {}
    
    def load(self, module_name):
        if module_name not in self._loaded:
            self._loaded[module_name] = importlib.import_module(module_name)
        return self._loaded[module_name]
```

### 3.2 预编译(Pre-compilation)

```yaml
precompile:
  scenarios: 
    - S01_需求分析
    - S04_代码审查
    - S08_安全审计
  models:
    - gpt-4-turbo
    - qwen-max
    - deepseek-v3
  output: ".cache/precompiled/"
```

### 3.3 缓存预热(Cache Warmup)

```python
async def warmup(self):
    """
    启动时并行预热：
    1. 加载Top-20场景到内存
    2. 预编译高频场景
    3. 预加载当前语言包
    4. 预连接模型API端点
    """
    await asyncio.gather(
        self._warm_top_scenarios(),
        self._precompile_frequent(),
        self._load_current_locale(),
        self._preconnect_model_apis()
    )
```

## 4. 优化效果总结

| 优化 | 冷启动 | 重复执行 | 长输出 | Token节省 |
|------|--------|---------|--------|----------|
| 动态压缩 | - | 20-40% | 30-50% | 20-80% |
| 智能缓存 | - | 80-95% | - | 80-95% |
| 增量渲染 | - | - | 40-60% | 40-60% |
| 预计算 | 50-70% | 30-50% | - | - |
| 懒加载 | 40-60% | - | - | - |
| 预编译 | 30-50% | 20-30% | - | - |
| 缓存预热 | 60-80% | - | - | - |
| **综合** | **80-90%** | **85-97%** | **60-80%** | **50-90%** |
