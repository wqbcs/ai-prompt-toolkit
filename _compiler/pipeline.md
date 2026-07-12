# 编译管线设计 (Pipeline)

> 模块路径: `_compiler/pipeline`
> 版本: v1.0
> 依赖: `lexer.md`, `ast.md`, `evaluator.md`, `renderer.md`, `cache.md`

---

## 1. 概述

编译管线(Pipeline)是条件编译运行时引擎的顶层编排模块，串联词法分析→语法解析→条件求值→渲染输出四个阶段，并提供配置加载、缓存集成、编译报告生成和统一错误处理。

### 端到端数据流

```
原始模板 + CompilationContext
         │
         ▼
  ┌─────────────────────────────────────────────────┐
  │                  Pipeline.compile()               │
  │                                                   │
  │  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐
  │  │  Lexer  │──→│ Parser  │──→│ Evaluator│──→│Renderer │
  │  │tokenize │   │  parse  │   │ evaluate │   │ render  │
  │  └─────────┘   └─────────┘   └──────────┘   └─────────┘
  │       │             │             │              │
  │   List[Token]   ProgramNode  EvaluatedNodes  RenderResult
  │                                                   │
  │  ┌─────────┐                                      │
  │  │  Cache  │←─── 命中时跳过上述4阶段 ──────────────┤
  │  └─────────┘                                      │
  └─────────────────────────────────────────────────┘
         │
         ▼
  RenderResult (output + CompileReport)
```

---

## 2. 类型定义

### 2.1 PipelineConfig

```python
from dataclasses import dataclass, field

@dataclass
class PipelineConfig:
    lexer: LexerConfig = field(default_factory=LexerConfig)
    parser: ParserConfig = field(default_factory=ParserConfig)
    evaluator: EvaluatorConfig = field(default_factory=EvaluatorConfig)
    renderer: RendererConfig = field(default_factory=RendererConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    enable_cache: bool = True
    source_id: str = "<template>"
```

### 2.2 CompileOptions

```python
@dataclass
class CompileOptions:
    """单次编译的可选覆盖配置"""
    override_context: CompilationContext | None = None
    skip_cache: bool = False              # 跳过缓存
    dry_run: bool = False                 # 仅解析不求值/渲染
    fallback_strategy: FallbackStrategy | None = None  # 覆盖回退策略
```

### 2.3 PipelineError

```python
class PipelineError(Exception):
    """管线统一错误，包装各阶段异常"""

    def __init__(
        self,
        stage: str,           # 出错阶段: "lexer" / "parser" / "evaluator" / "renderer"
        inner: Exception,     # 原始异常
        source_id: str = "",
    ):
        self.stage = stage
        self.inner = inner
        self.source_id = source_id
        super().__init__(
            f"[PipelineError] {source_id} @ {stage} — {inner}"
        )
```

---

## 3. Pipeline 类设计

### 3.1 类签名

```python
class Pipeline:
    def __init__(self, config: PipelineConfig | None = None) -> None: ...
    def compile(
        self,
        source: str,
        context: CompilationContext,
        options: CompileOptions | None = None,
    ) -> RenderResult: ...
    def compile_batch(
        self,
        sources: list[tuple[str, CompilationContext]],
        options: CompileOptions | None = None,
    ) -> list[RenderResult]: ...
    def _stage_lex(self, source: str) -> list[Token]: ...
    def _stage_parse(self, tokens: list[Token]) -> ProgramNode: ...
    def _stage_evaluate(
        self,
        ast: ProgramNode,
        context: CompilationContext,
    ) -> tuple[list[EvaluatedNode], EvaluationReport]: ...
    def _stage_render(
        self,
        evaluated: list[EvaluatedNode],
        eval_report: EvaluationReport,
        cache_hit: bool,
    ) -> RenderResult: ...
```

### 3.2 内部组件

```python
class Pipeline:
    _config: PipelineConfig
    _lexer: Lexer
    _parser: Parser
    _evaluator: Evaluator
    _renderer: Renderer
    _cache: CompileCache
```

---

## 4. 配置加载

### 4.1 从 config.yaml 加载

```python
import yaml

def load_config(config_path: str = "_compiler/config.yaml") -> PipelineConfig:
    """
    从 YAML 配置文件加载管线配置

    映射关系:
      max_nesting_depth      → parser.max_nesting_depth
      cache_ttl_seconds      → cache.ttl_seconds
      cache_max_size         → cache.max_size
      fallback_strategy.*    → renderer.fallback_strategy
    """
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return PipelineConfig(
        parser=ParserConfig(max_nesting_depth=raw.get("max_nesting_depth", 3)),
        cache=CacheConfig(
            ttl_seconds=float(raw.get("cache_ttl_seconds", 3600)),
            max_size=raw.get("cache_max_size", 1000),
        ),
        renderer=RendererConfig(
            fallback_strategy=_map_fallback(raw.get("fallback_strategy", {})),
        ),
    )
```

### 4.2 Fallback 映射

```python
def _map_fallback(raw: dict) -> FallbackStrategy:
    mapping = {
        "passthrough": FallbackStrategy.PASSTHROUGH,
        "empty_string": FallbackStrategy.EMPTY,
        "abort": FallbackStrategy.SKIP,
        "truncate_at_limit": FallbackStrategy.SKIP,
    }
    on_error = raw.get("on_compile_error", "empty_string")
    return mapping.get(on_error, FallbackStrategy.EMPTY)
```

---

## 5. 核心编译流程

### 5.1 compile 流程

```
输入: source, context, options

1. 加载配置 (PipelineConfig)
2. 构造 CompilationContext (options.override_context 优先)
3. 若 enable_cache 且非 skip_cache:
   a. cache_key = compute_cache_key(source, context)
   b. cached = cache.get(cache_key)
   c. 若命中 → 返回 cached (设置 cache_hit=True)
4. 记录开始时间 t_start
5. Stage 1 - Lexer:
   a. try: tokens = _stage_lex(source)
   b. except LexerError → 包装为 PipelineError("lexer", e)
6. Stage 2 - Parser:
   a. try: ast = _stage_parse(tokens)
   b. except ParserError → 包装为 PipelineError("parser", e)
7. 若 dry_run → 返回仅含 AST 的部分结果
8. Stage 3 - Evaluator:
   a. try: (evaluated, eval_report) = _stage_evaluate(ast, context)
   b. except Exception → 包装为 PipelineError("evaluator", e)
9. Stage 4 - Renderer:
   a. try: result = _stage_render(evaluated, eval_report, cache_hit=False)
   b. except RendererError → 包装为 PipelineError("renderer", e)
10. 计算 compilation_time_ms
11. 若 enable_cache → cache.put(cache_key, result)
12. 返回 result
```

### 5.2 compile_batch 流程

```
输入: sources: List[(source, context)], options

1. results = []
2. for (source, context) in sources:
   a. try: result = compile(source, context, options)
   b. except PipelineError → 记录, result = _make_error_result(e)
   c. results.append(result)
3. 返回 results
```

---

## 6. 编译报告生成

### 6.1 报告构建流程

```
EvaluationReport + 渲染统计
         │
         ▼
  _build_compile_report()
         │
    ┌────┴─────────────────┐
    │ 字段映射              │
    ├──────────────────────┤
    │ timestamp             │← datetime.now().isoformat()
    │ template_id           │← source_id
    │ status                │← _determine_status(eval_report)
    │ details               │
    │   activated_branches  │← eval_report.activated_branches
    │   ignored_branches    │← eval_report.ignored_branches
    │   uncovered_conditions│← eval_report.uncovered_conditions
    │   compilation_time_ms │← 计时器
    │   cache_hit           │← cache.get() 结果
    │ warnings              │← eval_report.warnings
    └──────────────────────┘
         │
         ▼
  CompileReport (符合 compile_report.schema.json)
```

### 6.2 状态判定

```python
def _determine_status(eval_report: EvaluationReport, has_error: bool) -> str:
    if has_error:
        return "failed"
    if eval_report.uncovered_conditions:
        return "partial"
    if eval_report.ignored_branches:
        return "partial"
    return "success"
```

### 6.3 schema 验证

```python
def validate_report(report: CompileReport) -> bool:
    """
    验证报告是否符合 _schemas/compile_report.schema.json

    使用 jsonschema 库验证:
      - timestamp 格式
      - template_id 模式
      - status 枚举值
      - required 字段完整性
    """
    import jsonschema
    with open("_schemas/compile_report.schema.json") as f:
        schema = json.load(f)
    jsonschema.validate(instance=dataclasses.asdict(report), schema=schema)
    return True
```

---

## 7. 错误处理流程

### 7.1 错误传播链

```
LexerError ──────────────→ PipelineError(stage="lexer")
ParserError ─────────────→ PipelineError(stage="parser")
EvaluatorError ──────────→ PipelineError(stage="evaluator")
RendererError ───────────→ PipelineError(stage="renderer")
CacheError ──────────────→ 降级处理 (跳过缓存, 继续编译)
```

### 7.2 错误处理策略

| 阶段 | 错误类型 | 处理方式 |
|------|---------|---------|
| Lexer | 语法错误 | 抛出 PipelineError, status=`failed` |
| Lexer | 源文本超限 | 抛出 PipelineError, status=`blocked` |
| Parser | 嵌套超限 | 截断 + 警告, status=`partial` |
| Parser | 未闭合标签 | 抛出 PipelineError, status=`failed` |
| Evaluator | 维度缺失 | 警告 + 回退值, status=`partial` |
| Evaluator | 矛盾条件 | 警告, status=`partial` |
| Renderer | 输出超限 | 截断 + 警告, status=`failed` |
| Renderer | 无匹配分支 | 执行回退策略, status=`partial` |
| Cache | 缓存异常 | 降级: 跳过缓存, status 不受影响 |

### 7.3 错误恢复流程

```
PipelineError
     │
     ▼
  1. 记录错误到 CompileReport.warnings
  2. 根据错误阶段确定 status
  3. 尝试生成部分编译结果 (若可能)
  4. 返回带错误标记的 RenderResult
```

---

## 8. 完整使用示例

### 8.1 基础编译

```python
from _compiler.pipeline import Pipeline
from _compiler.evaluator import CompilationContext

pipeline = Pipeline()

source = """
你是一个{{#if model=="gpt-4o"}}高级推理{{else if model=="claude-3"}}深度分析{{else}}通用{{/if}}助手。
{{#if language=="python"}}请使用Python代码示例。{{/if}}
"""

context = CompilationContext(
    model="gpt-4o",
    language="python",
    industry="tech",
)

result = pipeline.compile(source, context)

print(result.output)
# 输出:
# 你是一个高级推理助手。
# 请使用Python代码示例。

print(result.report.status)      # "success"
print(result.report.details.cache_hit)  # False
```

### 8.2 带缓存的编译

```python
from _compiler.pipeline import Pipeline, PipelineConfig
from _compiler.cache import CacheConfig

config = PipelineConfig(
    cache=CacheConfig(max_size=500, ttl_seconds=1800),
    enable_cache=True,
)
pipeline = Pipeline(config)

# 第一次编译 (未命中)
result1 = pipeline.compile(source, context)
assert result1.report.details.cache_hit == False

# 第二次编译 (命中)
result2 = pipeline.compile(source, context)
assert result2.report.details.cache_hit == True
```

### 8.3 批量编译

```python
sources = [
    (source1, ctx1),
    (source2, ctx2),
    (source3, ctx3),
]

results = pipeline.compile_batch(sources)

for i, result in enumerate(results):
    print(f"模板{i}: status={result.report.status}, len={len(result.output)}")
```

### 8.4 自定义配置

```python
config = PipelineConfig(
    parser=ParserConfig(max_nesting_depth=5),
    renderer=RendererConfig(
        fallback_strategy=FallbackStrategy.WARN,
        trim_whitespace=False,
    ),
    evaluator=EvaluatorConfig(strict_mode=True),
)
pipeline = Pipeline(config)
```

### 8.5 Dry Run 模式

```python
options = CompileOptions(dry_run=True)
result = pipeline.compile(source, context, options)
# 仅执行 Lexer + Parser, 不求值不渲染
# 可用于模板语法校验
```

### 8.6 错误处理

```python
from _compiler.pipeline import Pipeline, PipelineError

pipeline = Pipeline()

try:
    result = pipeline.compile(bad_source, context)
except PipelineError as e:
    print(f"编译失败: 阶段={e.stage}, 原因={e.inner}")
    # 编译失败: 阶段=lexer, 原因=LexerError(...)
```

---

## 9. 模块依赖图

```
pipeline.py
├── lexer.py       (Lexer, LexerConfig, Token, TokenKind)
├── ast.py         (Parser, ParserConfig, ProgramNode, Condition, ...)
├── evaluator.py   (Evaluator, EvaluatorConfig, CompilationContext, ...)
├── renderer.py    (Renderer, RendererConfig, RenderResult, CompileReport)
└── cache.py       (CompileCache, CacheConfig, compute_cache_key)
```

### 初始化顺序

```python
Pipeline.__init__():
    1. self._lexer = Lexer(config.lexer)
    2. self._parser = Parser(config.parser)
    3. self._evaluator = Evaluator(config.evaluator)
    4. self._renderer = Renderer(config.renderer)
    5. self._cache = CompileCache(config.cache)
```

---

## 10. 性能目标

| 指标 | 目标值 |
|------|--------|
| 端到端编译延迟 (1KB模板, 缓存未命中) | < 5ms |
| 端到端编译延迟 (1KB模板, 缓存命中) | < 10ms |
| 批量编译吞吐 (100模板) | < 500ms |
| 内存峰值 (单次编译) | < 1MB |
| 缓存命中率 | ≥ 80% |

---

## 11. 与外部接口

```
外部调用者
     │
     ▼
Pipeline.compile(source, context) → RenderResult
     │                                │
     │                                ├── output: str (编译输出)
     │                                └── report: CompileReport
     │                                        │
     │                                        ├── 符合 compile_report.schema.json
     │                                        └── 可序列化为 JSON
     │
     ▼
Pipeline.compile_batch(sources) → List[RenderResult]
```

所有输出均通过 `RenderResult` 封装，确保调用者无需关心内部阶段细节。CompileReport 严格遵循 `_schemas/compile_report.schema.json`，可直接持久化或传输。
