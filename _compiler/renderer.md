# 渲染器设计 (Renderer)

> 模块路径: `_compiler/renderer`
> 版本: v1.0
> 依赖: `evaluator.md` (求值后的 AST)

---

## 1. 概述

渲染器接收求值后的 AST，通过深度优先遍历收集激活分支的文本，生成最终编译输出。是编译管线的最终阶段。

### 数据流

```
List[EvaluatedNode] + EvaluationReport
         │
         ▼
  Renderer.render()
         │
    ┌────┴─────────┐
    │ 深度优先遍历    │
    ├──────────────┤
    │ TextNode → 输出文本
    │ EvaluatedConditional →
    │   找到 active_index 分支
    │   递归遍历其 children
    │   无匹配 → 执行回退策略
    └──────────────┘
         │
         ▼
  RenderResult (output + report)
```

---

## 2. 类型定义

### 2.1 回退策略

```python
from enum import Enum

class FallbackStrategy(Enum):
    EMPTY = "empty"       # 输出空字符串
    SKIP = "skip"         # 跳过该节点 (不输出任何内容)
    WARN = "warn"         # 输出空字符串 + 记录警告
    PASSTHROUGH = "passthrough"  # 输出原始模板文本 (调试用)
```

### 2.2 渲染结果

```python
from dataclasses import dataclass, field

@dataclass
class RenderResult:
    output: str                           # 最终编译输出文本
    report: CompileReport                 # 编译报告

@dataclass
class CompileReport:
    timestamp: str                        # ISO 8601 时间戳
    template_id: str                      # 模板标识
    status: str                           # success / partial / failed / blocked
    details: CompileDetails
    warnings: list[str]

@dataclass
class CompileDetails:
    activated_branches: list[str]         # 激活分支列表
    ignored_branches: list[str]           # 忽略分支列表
    uncovered_conditions: list[str]       # 未覆盖条件列表
    compilation_time_ms: float            # 编译耗时
    cache_hit: bool                       # 是否命中缓存
```

> CompileReport 结构严格遵循 `_schemas/compile_report.schema.json` 定义。

---

## 3. Renderer 类设计

### 3.1 类签名

```python
class Renderer:
    def __init__(self, config: RendererConfig | None = None) -> None: ...
    def render(
        self,
        evaluated_nodes: list[EvaluatedNode],
        eval_report: EvaluationReport,
        source_id: str = "<template>",
    ) -> RenderResult: ...
    def _render_node(
        self,
        node: EvaluatedNode,
        builder: list[str],
    ) -> None: ...
    def _render_conditional(
        self,
        node: EvaluatedConditional,
        builder: list[str],
    ) -> None: ...
    def _apply_fallback(
        self,
        node: EvaluatedConditional,
        builder: list[str],
    ) -> None: ...
    def _build_report(
        self,
        eval_report: EvaluationReport,
        source_id: str,
        elapsed_ms: float,
        cache_hit: bool,
    ) -> CompileReport: ...
```

### 3.2 配置

```python
@dataclass
class RendererConfig:
    fallback_strategy: FallbackStrategy = FallbackStrategy.EMPTY
    trim_whitespace: bool = True          # 是否裁剪分支首尾空白
    max_output_size: int = 10_000_000     # 最大输出大小 (10MB)
    include_metadata: bool = False        # 是否在输出中嵌入元数据注释
```

### 3.3 配置映射 (config.yaml)

```yaml
# config.yaml → RendererConfig 映射
fallback_strategy:
  on_compile_error: passthrough    → FallbackStrategy.PASSTHROUGH
  on_missing_variable: empty_string → FallbackStrategy.EMPTY
  on_circular_reference: abort     → 抛出 RendererError
  on_depth_exceeded: truncate_at_limit → FallbackStrategy.SKIP
```

---

## 4. 核心算法

### 4.1 render 流程

```
输入: evaluated_nodes, eval_report, source_id

1. 记录开始时间 t_start
2. builder: list[str] = []
3. 遍历 evaluated_nodes:
   a. _render_node(node, builder)
4. output = "".join(builder)
5. 校验 len(output) ≤ max_output_size
6. 若 trim_whitespace → 裁剪首尾空白
7. 计算 elapsed_ms
8. 构建 CompileReport (映射 eval_report → report)
9. 返回 RenderResult(output, report)
```

### 4.2 _render_node (深度优先)

```
输入: node, builder

1. 若 node 是 TextNode:
   a. builder.append(node.value)
   b. return
2. 若 node 是 EvaluatedConditional:
   a. 调用 _render_conditional(node, builder)
```

### 4.3 _render_conditional

```
输入: EvaluatedConditional, builder

1. 若 active_index >= 0:
   a. active_branch = node.branches[active_index]
   b. 递归遍历 active_branch.branch.children:
      - TextNode → builder.append(text)
      - ConditionalNode → 递归 _render_conditional()
2. 若 active_index == -1 (无匹配分支):
   a. 调用 _apply_fallback(node, builder)
```

### 4.4 _apply_fallback

```
输入: EvaluatedConditional (无匹配), builder

根据 fallback_strategy:
  EMPTY      → builder.append("")
  SKIP       → 不追加任何内容
  WARN       → builder.append("") + 记录警告
  PASSTHROUGH → 追加原始模板文本 (调试模式)
```

### 4.5 遍历顺序图

```
EvaluatedConditional
├── if_branch (ACTIVE) ★
│   └── children:
│       ├── TextNode("A")       → 输出 "A"
│       └── ConditionalNode      → 递归
│           ├── if_branch (INACTIVE)
│           └── else_branch (ACTIVE) ★
│               └── TextNode("B") → 输出 "B"
├── else_if_branch (INACTIVE)
└── else_branch (INACTIVE)

最终输出: "AB"
```

---

## 5. CompileReport 构建

### 5.1 报告字段映射

| CompileReport 字段 | 来源 |
|-------------------|------|
| timestamp | `datetime.now().isoformat()` |
| template_id | source_id 参数 |
| status | 求值结果决定 (见下表) |
| details.activated_branches | eval_report.activated_branches |
| details.ignored_branches | eval_report.ignored_branches |
| details.uncovered_conditions | eval_report.uncovered_conditions |
| details.compilation_time_ms | 计时器测量 |
| details.cache_hit | 缓存模块传入 |
| warnings | eval_report.warnings + 渲染警告 |

### 5.2 状态判定

| 条件 | status |
|------|--------|
| 所有条件分支均有匹配 | `success` |
| 存在未匹配分支但无警告 | `partial` |
| 存在未覆盖条件或回退触发 | `failed` |
| 编译过程被中断 (循环引用/深度超限) | `blocked` |

---

## 6. 示例

### 6.1 简单渲染

**输入:**
```
EvaluatedNode列表:
  TextNode("你是一个")
  EvaluatedConditional(active_index=0):
    if_branch(ACTIVE): [TextNode("高级推理")]
  TextNode("助手。")
```

**输出:**
```
你是一个高级推理助手。
```

**报告:**
```json
{
  "timestamp": "2026-07-12T10:00:00",
  "template_id": "<template>",
  "status": "success",
  "details": {
    "activated_branches": ["model==gpt-4o"],
    "ignored_branches": [],
    "uncovered_conditions": [],
    "compilation_time_ms": 0.12,
    "cache_hit": false
  },
  "warnings": []
}
```

### 6.2 无匹配 + 回退

**输入:**
```
EvaluatedConditional(active_index=-1):
  if_branch(INACTIVE): [TextNode("推理模式")]
  else_branch(INACTIVE)
```

**回退策略: EMPTY**
```
输出: "" (空字符串)
状态: "partial"
警告: ["条件分支无匹配: model==gpt-4o, 已执行回退策略: empty"]
```

### 6.3 嵌套渲染

**输入:**
```
EvaluatedConditional(active_index=0):
  if_branch(ACTIVE):
    TextNode("GPT-4o专属")
    EvaluatedConditional(active_index=0):
      if_branch(ACTIVE): [TextNode("Python模式")]
```

**输出:**
```
GPT-4o专属Python模式
```

---

## 7. 边界情况

| 场景 | 行为 |
|------|------|
| 空节点列表 | 输出 `""`，status=`success` |
| 纯文本 (无条件) | 直接输出文本 |
| 嵌套3层全部激活 | 递归输出所有文本 |
| 输出超过 max_output_size | 抛出 RendererError |
| 循环引用 (理论上不可能) | 抛出 RendererError, status=`blocked` |

---

## 8. 性能目标

| 指标 | 目标值 |
|------|--------|
| 渲染吞吐 | ≥ 20MB/s |
| 单模板延迟 (1KB, 10条件) | < 0.5ms |
| 内存峰值 | O(d), d=最大嵌套深度 |
| 报告生成开销 | < 渲染总时间的 3% |

---

## 9. 与上下游模块接口

```
上游: Evaluator.evaluate() → (List[EvaluatedNode], EvaluationReport) → Renderer.render()
下游: Renderer.render() → RenderResult → 最终输出 / 缓存写入
```

RenderResult.report 严格符合 `_schemas/compile_report.schema.json`，可直接序列化输出。
