# 开源项目调研报告

## 1. OpenTelemetry Python SDK (opentelemetry-python)

### 核心 API 签名

```python
# TracerProvider — 全局tracer工厂
class TracerProvider(ABC):
    def get_tracer(self, instrumenting_module_name: str,
                   instrumenting_library_version: Optional[str] = None,
                   schema_url: Optional[str] = None,
                   attributes: Optional[Mapping] = None) -> Tracer

# Tracer — 创建Span的入口
class Tracer(ABC):
    def start_span(self, name: str, context: Optional[Context] = None,
                   kind: SpanKind = SpanKind.INTERNAL,
                   attributes: Optional[Mapping] = None,
                   links: Optional[Sequence[Link]] = None,
                   start_time: Optional[int] = None) -> Span

    def start_as_current_span(self, name: str, ...) -> Iterator[Span]  # 上下文管理器

# Span — 单个操作
class Span(ABC):
    def set_attribute(self, key: str, value: Any) -> None
    def add_event(self, name: str, attributes: Optional[Mapping] = None) -> None
    def set_status(self, status: Status, description: Optional[str] = None) -> None
    def record_exception(self, exception: Exception, attributes: Optional[Mapping] = None) -> None
    def end(self, end_time: Optional[int] = None) -> None
    def get_span_context(self) -> SpanContext

# SpanContext — 不可变span标识
class SpanContext(NamedTuple):
    trace_id: int       # 16字节 → 32字符hex
    span_id: int        # 8字节 → 16字符hex
    is_remote: bool
    trace_flags: TraceFlags  # 0x01=sampled
    trace_state: TraceState

# 全局函数
def get_tracer(name: str, version: Optional[str] = None) -> Tracer
def set_tracer_provider(provider: TracerProvider) -> None
def get_tracer_provider() -> TracerProvider
def get_current_span(context: Optional[Context] = None) -> Span
def format_trace_id(trace_id: int) -> str  # → 32字符hex
def format_span_id(span_id: int) -> str    # → 16字符hex
```

### 关键设计模式

| 模式 | 说明 |
|------|------|
| **API/SDK分离** | `opentelemetry-api`(零依赖) vs `opentelemetry-sdk`(完整实现)，API包只含ABC和NoOp实现 |
| **NonRecordingSpan** | 无SDK时自动降级为no-op span，仅传播context不记录数据 |
| **Context Propagation** | W3C Trace Context标准，`traceparent`/`tracestate` header传播 |
| **Provider注册** | 全局单例`set_tracer_provider()`，只允许设置一次 |
| **SpanKind枚举** | INTERNAL/SERVER/CLIENT/PRODUCER/CONSUMER |

### 零依赖兼容OTel的轻量tracing最小实现

```python
import uuid, time, contextvars
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

_current_span = contextvars.ContextVar('span', default=None)

@dataclass
class SpanContext:
    trace_id: str  # 32-char hex
    span_id: str   # 16-char hex

@dataclass
class LightSpan:
    name: str
    context: SpanContext
    parent: Optional['LightSpan'] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    start_time_ns: int = field(default_factory=lambda: time.time_ns())
    end_time_ns: Optional[int] = None
    status: str = "UNSET"
    events: list = field(default_factory=list)

    def set_attribute(self, key, value): self.attributes[key] = value
    def set_status(self, status): self.status = status
    def end(self): self.end_time_ns = time.time_ns()

def _gen_id(n_bytes): return uuid.uuid4().hex[:n_bytes*2]

def start_span(name: str, attributes: Optional[Dict] = None) -> LightSpan:
    parent = _current_span.get()
    trace_id = parent.context.trace_id if parent else _gen_id(16)
    span = LightSpan(name=name, context=SpanContext(trace_id, _gen_id(8)),
                     parent=parent, attributes=attributes or {})
    _current_span.set(span)
    return span

# 用法
span = start_span("llm.call", {"gen_ai.system": "openai", "gen_ai.request.model": "gpt-4"})
span.set_attribute("gen_ai.response.finish_reason", "stop")
span.end()
# 输出OTel JSON格式可对接华为云AOM/APM
```

---

## 2. Traceloop/OpenLLMetry (7.3k⭐)

### 核心 API 签名

```python
# 装饰器模式
@workflow(name="pipeline")      # 等价于 OTel SpanKind=INTERNAL 的根span
@task(name="step")              # 等价于 OTel SpanKind=INTERNAL 的子span

# 语义约定 (Semantic Conventions) — gen_ai.* 命名空间
# 关键attributes:
"gen_ai.system"              # "openai" | "anthropic" | ...
"gen_ai.request.model"       # "gpt-4"
"gen_ai.request.max_tokens"  # 4096
"gen_ai.request.temperature" # 0.7
"gen_ai.response.finish_reason"  # "stop"
"gen_ai.usage.input_tokens"  # 100
"gen_ai.usage.output_tokens" # 50
"gen_ai.prompt"              # 原始prompt文本
"gen_ai.completion"          # 模型输出
"gen_ai.tool.name"           # 工具调用名
"gen_ai.tool.call.id"        # 工具调用ID
```

### 关键设计模式

| 模式 | 说明 |
|------|------|
| **@workflow/@task装饰器** | 声明式标注，自动创建嵌套span，零侵入 |
| **gen_ai.*语义约定** | 遵循OTel GenAI Semantic Conventions规范，标准化LLM可观测性属性 |
| **自动instrumentation** | 对OpenAI/Anthropic等SDK的monkey-patch，无需改代码 |
| **SpanProcessor链** | 支持多exporter同时输出(OTLP→Langfuse/Jaeger/华为云) |
| **向量数据库trace** | 特殊处理embedding/retrieval span |

### 最小实现示例

```python
import functools
from typing import Optional, Callable

def workflow(name: Optional[str] = None):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            span_name = name or fn.__name__
            span = start_span(span_name, {"traceloop.workflow.name": span_name})
            try:
                result = fn(*args, **kwargs)
                span.set_status("OK")
                return result
            except Exception as e:
                span.set_status("ERROR")
                span.set_attribute("error.message", str(e))
                raise
            finally:
                span.end()
        return wrapper
    return decorator

@workflow(name="rag_pipeline")
def rag_query(question: str) -> str:
    return llm_call(retrieval(question))

@workflow(name="llm_step")
def llm_call(ctx: str) -> str:
    return "answer"
```

---

## 3. Promptfoo (23.5k⭐)

### 核心 API 签名 (YAML声明式配置)

```yaml
# promptfooconfig.yaml 核心结构
providers:                    # LLM API配置
  - openai:gpt-4
  - id: openai:gpt-4o
    config:
      temperature: 0

prompts:                      # Prompt模板
  - prompt1.txt
  - raw: "Summarize: {{text}}"
    label: "summarize-v2"

tests:                        # 测试用例
  - description: "test case"
    vars:                     # 模板变量
      text: "Hello world"
    assert:                   # 断言列表
      - type: contains        # 断言类型: contains/icontains/equals/regex/similar/llm-rubric/json-schema/python/javascript
        value: "expected"
        threshold: 0.8        # 相似度阈值(用于similar)
        weight: 1             # 权重
        metric: "accuracy"    # 命名指标(聚合用)
    options:
      transform: 'output.answer'  # 输出变换
      transformVars: 'file://transform.py:fn'  # 输入变换

# 新特性: Extension Hooks (生命周期钩子)
extensions:
  - file://hooks.py:extension_hook
# beforeAll / afterAll / beforeEach / afterEach

# 新特性: OpenTelemetry Tracing
tracing:
  enabled: true

# 新特性: Test Generator (动态生成测试)
tests:
  path: file://generator.py:generate_tests
  config: { count: 100 }

# 新特性: Derived Metrics (派生指标)
derivedMetrics:
  - name: "composite_score"
    value: "accuracy * 0.7 + fluency * 0.3"
```

### 关键设计模式

| 模式 | 说明 |
|------|------|
| **YAML声明式配置** | 零代码定义评估流水线，支持`file://`外部引用 |
| **Assertion系统** | 40+内置断言类型，支持`not-`前缀取反，权重/阈值/指标聚合 |
| **Transform Pipeline** | `transformResponse` → `options.transform` → `assertion.transform` 三级变换 |
| **Scenario矩阵** | 组合providers × prompts × tests自动生成笛卡尔积评估 |
| **Nunjucks模板** | 变量插值`{{var}}`，过滤器`{{var | filter}}`，支持自定义filter |
| **OTel Tracing** | 评估过程自带trace，`TraceData`结构含`traceId/spans` |
| **Extension Hooks** | 生命周期钩子(beforeAll/afterAll/beforeEach/afterEach) |

### 最小实现示例

```python
# 核心Assertion评估逻辑
from typing import Any, List, Dict
import re

class Assertion:
    def __init__(self, type: str, value: Any = None, threshold: float = None, weight: float = 1.0):
        self.type, self.value, self.threshold, self.weight = type, value, threshold, weight

    def evaluate(self, output: str) -> float:
        if self.type == "contains":    return 1.0 if self.value in output else 0.0
        if self.type == "regex":       return 1.0 if re.search(self.value, output) else 0.0
        if self.type == "equals":      return 1.0 if output.strip() == self.value else 0.0
        if self.type == "icontains":   return 1.0 if self.value.lower() in output.lower() else 0.0
        return 0.0

def evaluate_test(output: str, assertions: List[Assertion]) -> Dict:
    total_weight, total_score = 0, 0
    for a in assertions:
        total_weight += a.weight
        total_score += a.evaluate(output) * a.weight
    return {"pass": total_score / total_weight >= 0.5, "score": total_score / total_weight}

# YAML式声明: tests: [{vars: {q: "2+2"}, assert: [{type: "equals", value: "4"}]}]
```

---

## 4. Langfuse (31.6k⭐)

### 核心 API 签名

```python
# 客户端初始化
from langfuse import get_client, observe, propagate_attributes
langfuse = get_client()  # 自动读取LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST

# 方式1: @observe装饰器 (最常用)
@observe(name="my_pipeline", as_type="generation")  # as_type: "span"|"generation"|"tool"
def my_llm_call(prompt: str) -> str:
    return "response"

# 方式2: Context Manager (自动嵌套)
with langfuse.start_as_current_observation(
    as_type="span", name="pipeline",
    input={"query": "hello"}, metadata={"env": "prod"}
) as root_span:
    with langfuse.start_as_current_observation(
        as_type="generation", name="llm", model="gpt-4"
    ) as gen:
        gen.update(output="answer", usage_details={"input_tokens": 10, "output_tokens": 5})
    root_span.update(output={"result": "done"})

# 方式3: Manual Observation (手动生命周期)
span = langfuse.start_observation(name="bg-task", as_type="span")
span.update(input="data")
span.end()  # 必须手动调用

# 属性传播
with propagate_attributes(user_id="u1", session_id="s1", version="1.0"):
    pass  # 自动传播到所有子observation

# 更新当前span
langfuse.update_current_span(metadata={"step": "done"})
langfuse.update_current_generation(output="result")

# Trace ID管理
langfuse.create_trace_id(seed="external_id")     # 确定性trace ID
langfuse.get_current_trace_id()
langfuse.get_current_observation_id()

# 跨服务传播 (W3C Trace Context)
with langfuse.start_as_current_observation(as_type="span", name="api", trace_context={
    "trace_id": "abc123...", "parent_span_id": "def456..."
}):
    pass

# 刷新/关闭
langfuse.flush()
langfuse.shutdown()
```

### 关键设计模式

| 模式 | 说明 |
|------|------|
| **OTel原生集成** | 底层完全基于OTel Span，trace_id/span_id遵循W3C标准 |
| **@observe装饰器** | 自动捕获input/output/timing/errors，`capture_input/output`可关闭 |
| **三种Observation类型** | span(通用)、generation(LLM调用)、tool(工具调用) |
| **start_as_current_observation** | 自动context propagation，嵌套自动建立父子关系 |
| **propagate_attributes** | 一次设置userId/sessionId/version，自动向下传播 |
| **确定性Trace ID** | `create_trace_id(seed=)` 基于seed生成，方便关联外部系统 |
| **trace_context参数** | 接入已有W3C trace，实现跨服务分布式追踪 |

### Prompt管理设计

```
Prompt对象:
  - name: str              # prompt名称
  - version: int           # 版本号(自动递增)
  - prompt: str            # 模板文本
  - config: Dict           # 模型参数(temperature, max_tokens等)
  - labels: List[str]      # 标签("production", "staging")

API:
  langfuse.get_prompt(name, version=None, label="production")
  langfuse.create_prompt(name, prompt, config={})
  
模板语法: Mustache风格 {{variable}}
```

### 最小实现示例

```python
from langfuse import observe, get_client

@observe(as_type="generation", name="chat")
def chat(user_msg: str, system_prompt: str = "You are helpful.") -> str:
    return f"Echo: {user_msg}"

@observe(as_type="span", name="pipeline")
def pipeline(question: str):
    prompt = get_client().get_prompt("chat-template", label="production")
    result = chat(question, system_prompt=prompt.prompt)
    return result

pipeline("What is OTel?")
```

---

## 5. Jinja2 SandboxedEnvironment

### 核心 API 签名

```python
from jinja2.sandbox import SandboxedEnvironment, ImmutableSandboxedEnvironment

# 安全沙箱环境
env = SandboxedEnvironment(
    autoescape=True,                    # 自动HTML转义
    undefined=StrictUndefined,          # 未定义变量报错(非静默)
    variable_start_string='{{',         # 变量插值语法
    variable_end_string='}}',
    block_start_string='{%',
    block_end_string='%}',
)

# 不可变沙箱(最安全)
env = ImmutableSandboxedEnvironment(autoescape=True)

# 模板渲染
template = env.from_string("Hello {{ name | default('World') }}!")
result = template.render(name="OTel")  # "Hello OTel!"
result = template.render()             # "Hello World!" (默认值)

# 变量插值 + 默认值 + 类型校验
template = env.from_string("""
{%- set expected_types = {"age": "number", "name": "string"} -%}
Hello {{ name | default('Anonymous') }}!
Age: {{ age | default(0) }}.
{% if age is number and age > 0 %}Valid{% else %}Invalid{% endif %}
""")

# 安全策略控制
env.policies['urlize.rel'] = 'noopener noreferrer'  # 链接安全
env.policies['truncate.leeway'] = 5                   # 截断容差

# 自定义过滤器
def sanitize(value): return re.sub(r'[<>&]', '', str(value))
env.filters['sanitize'] = sanitize
```

### 关键设计模式

| 模式 | 说明 |
|------|------|
| **SandboxedEnvironment** | 禁止不安全属性访问(`__class__`/`__subclasses__`等)，防模板注入 |
| **ImmutableSandboxedEnvironment** | 最严格：禁止修改常量/内建，防止沙箱逃逸 |
| **autoescape** | HTML自动转义，防XSS |
| **StrictUndefined** | 未定义变量抛异常(非静默空字符串)，防信息泄露 |
| **default过滤器** | `{{ var | default('fallback') }}` 安全默认值 |
| **policies** | 运行时安全策略配置字典 |
| **finalize回调** | 所有输出经过finalize函数处理，可做全局清洗 |

### 防注入最小实现

```python
from jinja2.sandbox import ImmutableSandboxedEnvironment
import re

env = ImmutableSandboxedEnvironment(autoescape=True, undefined=StrictUndefined)

def safe_render(template_str: str, variables: dict) -> str:
    # 1. 禁止模板注入：沙箱阻止{{ config.__class__ }}等
    # 2. 自动转义：HTML特殊字符自动escape
    # 3. 严格未定义：{{ undefined_var }} → 异常
    tpl = env.from_string(template_str)
    return tpl.render(**variables)

# 攻击尝试全部被拦截:
safe_render("{{ ''.__class__.__mro__ }}", {})           # SecurityError!
safe_render("{{ config }}", {})                          # UndefinedError!
safe_render("Hello {{ name | default('World') }}", {})   # "Hello World" ✓
```

---

## 6. python-jsonschema

### 核心 API 签名

```python
import jsonschema
from jsonschema import Draft202012Validator, validate

# 快速验证
validate(instance={"name": "test"}, schema={
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"]
})
# 无异常=合法；ValidationError=数据不合法；SchemaError=schema不合法

# Validator对象(推荐：复用schema)
validator = Draft202012Validator(schema={"type": "object", ...})
validator.validate(instance)            # 抛异常
validator.is_valid(instance)            # 返回bool
errors = list(validator.iter_errors(instance))  # 懒加载所有错误

# 自定义类型检查器
from jsonschema import validators
CustomValidator = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("date", lambda c, i: isinstance(i, str)))

# Format验证(需pip install jsonschema[format])
Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)

# 自定义format检查器
from jsonschema import FormatChecker
checker = FormatChecker()
@checker.checks("prompt-var", raises=ValueError)
def check_prompt_var(value):
    if '{{' in value: raise ValueError("未插值的模板变量")
    return True
```

### 关键设计模式

| 模式 | 说明 |
|------|------|
| **Draft202012Validator** | 最新JSON Schema规范实现 |
| **validate()快捷函数** | 单次验证，自动检测$schema选validator |
| **iter_errors()** | 懒加载所有校验错误，支持复杂schema批量检查 |
| **TypeChecker** | 不可变映射，`redefine()`返回新实例(函数式) |
| **FormatChecker** | 可扩展的format验证框架，`@checks`装饰器注册 |
| **evolve()** | 基于当前validator创建新实例(不同schema相同配置) |

### Prompt变量校验最小实现

```python
from jsonschema import Draft202012Validator

PROMPT_VAR_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "system_prompt": {"type": "string", "minLength": 1, "maxLength": 4000},
        "temperature":   {"type": "number", "minimum": 0, "maximum": 2},
        "max_tokens":    {"type": "integer", "minimum": 1, "maximum": 32000},
        "model":         {"type": "string", "enum": ["gpt-4", "gpt-4o", "claude-3"]},
        "variables": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "minProperties": 1
        }
    },
    "required": ["system_prompt", "model"]
}

validator = Draft202012Validator(PROMPT_VAR_SCHEMA)

def validate_prompt_config(config: dict):
    errors = list(validator.iter_errors(config))
    return [{"path": ".".join(str(p) for p in e.path), "msg": e.message} for e in errors]
```

---

## 综合分析：核心关注点

### 1. 零依赖兼容OTel格式的轻量tracing

**核心思路**: 复制OTel API层的ABC接口，自实现最小RecordingSpan

```
opentelemetry-api (≈0依赖)
    ├── TracerProvider(ABC) → 自实现LightTracerProvider
    ├── Tracer(ABC)         → 自实现LightTracer
    ├── Span(ABC)           → 自实现LightSpan (RecordingSpan简化版)
    ├── SpanContext          → 自实现 (trace_id: 32hex, span_id: 16hex)
    └── NonRecordingSpan    → 直接复用 (context propagation only)

关键约束:
  - trace_id: 16字节 → 32字符小写hex
  - span_id: 8字节 → 16字符小写hex
  - W3C traceparent: {version}-{trace_id}-{span_id}-{trace_flags}
  - 时间戳: nanosecond精度 (time.time_ns())
  - 属性值类型: str/bool/int/float/Sequence[str|bool|int|float]
```

**华为云AOM/APM对接格式**:
- OTLP/gRPC 或 OTLP/HTTP 协议
- endpoint: `https://AOM_ENDPOINT/v1/traces`
- Header: `x-auth-token` / 鉴权信息
- Span JSON结构需包含: `traceId`, `spanId`, `parentSpanId`, `name`, `kind`, `startTimeUnixNano`, `endTimeUnixNano`, `attributes`, `status`
- 资源属性: `service.name`, `service.version`, `telemetry.sdk.name` 等

### 2. Prompt模板变量系统安全实现

**三层防护架构**:

```
Layer 1: Jinja2 ImmutableSandboxedEnvironment
  ├── 禁止: __class__, __subclasses__, __globals__ 等属性访问
  ├── autoescape=True: HTML特殊字符自动转义
  └── StrictUndefined: 未定义变量抛异常

Layer 2: JSON Schema校验
  ├── 变量类型约束: string/number/integer/boolean
  ├── 值域约束: minLength/maxLength/minimum/maximum/enum/pattern
  ├── 结构约束: required/additionalProperties/dependencies
  └── 自定义format: prompt-var(检查未插值变量)/safe-string

Layer 3: 输出清洗(finish回调)
  ├── env.finalize = sanitize_output  # 全局输出清洗
  ├── 自定义filter: {{ var | sanitize | truncate(1000) }}
  └── 正则黑名单: 移除<script>, javascript:, data: 等危险内容
```

### 3. 华为云AOM/APM Trace数据格式

```json
{
  "resourceSpans": [{
    "resource": {
      "attributes": [
        {"key": "service.name", "value": {"stringValue": "prompt-service"}},
        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
        {"key": "telemetry.sdk.name", "value": {"stringValue": "opentelemetry"}}
      ]
    },
    "scopeSpans": [{
      "scope": {"name": "prompt-tracing"},
      "spans": [{
        "traceId": "abc123...32chars",
        "spanId": "def456...16chars",
        "parentSpanId": "ghi789...16chars",
        "name": "llm.call",
        "kind": 1,
        "startTimeUnixNano": "1700000000000000000",
        "endTimeUnixNano": "1700000001000000000",
        "attributes": [
          {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
          {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4"}},
          {"key": "gen_ai.usage.input_tokens", "value": {"intValue": "100"}},
          {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "50"}}
        ],
        "status": {"code": 1}
      }]
    }]
  }]
}
```
