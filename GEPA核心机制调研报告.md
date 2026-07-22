# GEPA (Gradient-free Evolutionary Prompt Adaptation) 核心机制调研报告

> 基于DSPy官方文档、GEPA论文(arXiv:2507.19457, ICLR 2026 Oral)及源码分析的完整调研

---

## 一、GEPA 核心算法流程

### 1.1 全称与定位

**GEPA = Genetic-Pareto**（论文全称：Gradient-free Evolutionary Prompt Adaptation），是DSPy的**反射式指令优化器**。核心思想：利用自然语言反馈（而非标量梯度）驱动Prompt进化。

论文关键结论：
- 比GRPO平均高6%，最高高20%，使用少35倍rollout
- 比MIPROv2高10%+（如AIME-2025 +12%准确率）
- ICLR 2026 Oral

### 1.2 核心算法伪代码

```
function GEPA_OPTIMIZE(student, trainset, valset, metric, reflection_lm, budget):
    population = [student]  # 初始候选种群
    frontier = compute_pareto_frontier(population, valset, metric)
    
    while metric_calls < budget:
        # Step 1: 从Pareto前沿随机采样一个候选
        parent = sample_from_pareto_frontier(frontier)
        
        # Step 2: 选择要优化的predictor（round-robin/all/自定义）
        target_predictor = select_component(parent)
        
        # Step 3: 在trainset上执行，收集低分样本
        traces = execute(parent, trainset)
        failing_examples = filter(traces, score < perfect_score)
        minibatch = sample(failing_examples, size=reflection_minibatch_size)
        
        # Step 4: 反射——用reflection_lm分析失败原因并提出新指令
        feedback = metric(gold, pred, pred_name=target_predictor, pred_trace=sub_trace)
        new_instruction = reflection_lm.reflect(
            current_instruction=parent.predictors[target_predictor].instruction,
            failing_traces=minibatch,
            feedback=feedback  # 关键：自然语言反馈
        )
        
        # Step 5: 创建变异体
        child = mutate(parent, target_predictor, new_instruction)
        
        # Step 6: 在valset上评估变异体
        child_scores = evaluate(child, valset, metric)
        
        # Step 7: 更新种群和Pareto前沿
        population.append(child)
        frontier = update_pareto_frontier(frontier, child, child_scores)
        
        # Step 8（可选）: 合并——组合不同候选的优势
        if use_merge:
            merged = merge_complementary_candidates(frontier)
            evaluate_and_update(merged)
    
    # 返回聚合分数最高的候选
    return best_by_aggregate_score(frontier)
```

### 1.3 三大核心机制

| 机制 | 描述 | 关键参数 |
|------|------|---------|
| **反射式Prompt变异** | 用reflection_lm分析失败trace + feedback，提出新指令 | `reflection_lm`, `reflection_minibatch_size=3` |
| **自然语言反馈通道** | metric返回`Prediction(score, feedback)`而非纯float | `pred_name`, `pred_trace` |
| **Pareto前沿采样** | 从per-example Pareto前沿随机采样，而非贪心选最佳 | `candidate_selection_strategy="pareto"` |

### 1.4 预算配置

| auto模式 | 候选数 | 预估metric调用(2-pred/100-example) | 适用场景 |
|----------|--------|--------------------------------------|---------|
| `light` | 6 | ~1330 | 快速实验 |
| `medium` | 12 | ~1740 | 平衡优化 |
| `heavy` | 18 | ~2045 | 充分优化 |

也可直接设置 `max_full_evals`（全量评估次数）或 `max_metric_calls`（硬性上限）。

---

## 二、反射式Prompt进化（Reflection-based Prompt Evolution）

### 2.1 反射流程详解

```
                         ┌─────────────────────────┐
                         │   Step 1: 执行student     │
                         │   在trainset上跑推理       │
                         └──────────┬──────────────┘
                                    │
                         ┌──────────▼──────────────┐
                         │   Step 2: 收集失败trace    │
                         │   过滤掉perfect_score样本  │
                         │   采样minibatch(默认3条)   │
                         └──────────┬──────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │   Step 3: 双重metric调用         │
                    │   (a) 模块级: metric(gold,pred)  │
                    │       → aggregate score          │
                    │   (b) 预测器级:                   │
                    │       metric(gold,pred,           │
                    │         pred_name="predictor_x",  │
                    │         pred_trace=sub_trace)     │
                    │       → per-predictor feedback     │
                    └───────────────┬───────────────┘
                                    │
                         ┌──────────▼──────────────┐
                         │  Step 4: reflection_lm反思  │
                         │  输入:                       │
                         │  - 当前predictor的指令        │
                         │  - 失败的trace + feedback     │
                         │  输出:                       │
                         │  - 新的指令文本               │
                         └──────────┬──────────────┘
                                    │
                         ┌──────────▼──────────────┐
                         │  Step 5: 变异 + 评估        │
                         │  将新指令注入child候选       │
                         │  在valset上全量评估          │
                         └──────────┬──────────────┘
                                    │
                         ┌──────────▼──────────────┐
                         │  Step 6: 更新Pareto前沿    │
                         │  保留per-example最优候选    │
                         └─────────────────────────┘
```

### 2.2 Feedback Metric的实现规范

```python
def gepa_feedback_metric(
    gold: Example,
    pred: Prediction,
    trace=None,
    pred_name=None,      # GEPA注入：当前优化的predictor名称
    pred_trace=None,     # GEPA注入：该predictor的子trace
) -> Prediction:         # 注意：返回dspy.Prediction，不是float！
    
    # 模块级评分
    module_score = compute_score(gold, pred)
    
    # 如果GEPA请求per-predictor反馈
    if pred_name is not None and pred_trace is not None:
        predictor_score = compute_predictor_score(pred_name, pred_trace)
        feedback = generate_natural_language_feedback(pred_name, pred_trace)
        return dspy.Prediction(score=predictor_score, feedback=feedback)
    
    # 模块级返回
    feedback = explain_why_score(module_score, gold, pred)
    return dspy.Prediction(score=module_score, feedback=feedback)
```

### 2.3 反射Prompt的关键模式

reflection_lm收到的输入包含：
1. **当前指令**：被优化predictor的signature.instructions
2. **失败样本**：minibatch_size个低分trace（默认3个）
3. **自然语言反馈**：metric返回的feedback文本
4. **输出约束**：生成新的指令文本

核心设计原则：
- **反射是提议机制，不是评估机制** → 用强模型(GPT-5)反思，用弱模型(gpt-4o-mini)执行
- **skip_perfect_score=True** → 反射只看失败样本，不看成功样本
- **round-robin轮转** → 每轮只优化一个predictor，避免互相干扰

---

## 三、MIPROv2优化器工作原理（与GEPA的对比）

### 3.1 MIPROv2核心机制

MIPROv2 = **M**ulti-prompt **I**nstruction **PRO**posal v2，是**贝叶斯优化驱动的指令+demo联合搜索**。

```
MIPROv2工作流:
1. Bootstrap阶段: 用BootstrapFewShot收集成功的demo traces
2. 提议阶段: prompt_model为每个predictor生成多条候选指令
3. 搜索阶段: 贝叶斯优化在(instruction, demo_set)联合空间中搜索
4. 评估阶段: 在valset上评估每个候选组合
5. 返回: 最高分的program
```

### 3.2 关键差异对比

| 维度 | GEPA | MIPROv2 |
|------|------|---------|
| **优化目标** | 仅指令(instructions) | 指令 + demos联合 |
| **搜索策略** | 进化式(Pareto前沿采样) | 贝叶斯优化 |
| **反馈机制** | 自然语言feedback→反射 | 纯标量score→黑盒 |
| **提议机制** | reflection_lm基于失败trace反思 | prompt_model批量生成候选 |
| **种群管理** | Pareto前沿 + 合并 | 候选池 + 贝叶斯采集 |
| **metric要求** | `Prediction(score, feedback)` | 普通float/bool |
| **每轮变异** | 精准：1个predictor的1条指令 | 广泛：多个predictor的多条候选 |
| **收敛速度** | 少量rollout即可大幅提升 | 需要更多评估轮次 |
| **适用场景** | 有丰富反馈的任务 | 指令+demo都需要调 |
| **最佳实践** | 强reflection_lm + 反馈metric | 有预算时联合优化 |

### 3.3 何时选择哪个

- **选GEPA**：metric能提供自然语言反馈、指令是瓶颈、想要少量rollout快速提升
- **选MIPROv2**：demos也需要优化、metric只能返回标量、预算充足
- **选BetterTogether**：两者都需要优化时，先GEPA再BootstrapFinetune

---

## 四、BootstrapFewShot的采样策略

### 4.1 核心流程

```
BootstrapFewShot.compile(student, trainset, teacher=None):
    
    # 1. 初始化teacher
    if teacher is None:
        teacher = student.deepcopy()
    if teacher未编译 and max_labeled_demos > 0:
        LabeledFewShot(k=max_labeled_demos).compile(teacher, trainset)
    
    # 2. 遍历trainset
    for example in trainset:
        for round in range(max_rounds):
            # 关键：移除当前example防止泄露
            strip_example_from_demos(teacher, example)
            
            # 强制温度=1.0打破缓存
            lm_copy = copy_lm(temperature=1.0, rollout_id=round)
            
            # Teacher执行推理
            prediction = teacher(example)
            
            # Metric评估
            if metric(example, prediction, trace):
                # 3. 提取通过trace中的demo
                for predictor_invocation in trace:
                    demo = Example(
                        augmented=True,
                        **inputs,
                        **outputs
                    )
                    store_demo(predictor_name, demo)
                break  # 通过则不再重试
    
    # 4. 分配demos给每个predictor
    for predictor in predictors:
        predictor.demos = (
            bootstrapped_demos[:max_bootstrapped_demos] +   # 前4个：带trace验证
            raw_labeled_examples[:remaining_slots]           # 补充：原始标注
        )[:max_labeled_demos]  # 总共不超过16个
```

### 4.2 采样策略层次

| 策略 | 类 | 描述 | LM调用 |
|------|---|------|--------|
| **随机采样** | `LabeledFewShot` | 从trainset随机/顺序取k条 | 0次 |
| **Metric过滤** | `BootstrapFewShot` | Teacher执行→metric评分→通过才保留 | 1-N次/样本 |
| **多轮重试** | `BootstrapFewShot(max_rounds=N)` | 同一样本多次temperature=1.0重试 | N次/样本 |
| **随机搜索** | `BootstrapRS` | 运行N次BootstrapFewShot(不同seed)，取最优 | N×基础 |
| **KNN推理时** | `KNNFewShot` | 每次推理时动态选k近邻demos | 每次推理1次mini-compile |

### 4.3 Demo分配的关键参数

- `max_bootstrapped_demos=4`：经过trace验证的高质量demo数量上限
- `max_labeled_demos=16`：总demo数量上限（包含原始标注）
- 泄露防护：正在bootstrap的example会从teacher的demos中临时移除

---

## 五、Signature编译和Assertion约束机制

### 5.1 Signature编译流程

```
Signature定义 → Adapter编译 → LM Messages → LM Response → 解析回类型化值

详细流程:
1. Signature类定义
   class MySignature(dspy.Signature):
       """指令文本（会被GEPA优化覆盖）"""
       question: str = InputField(desc="用户问题")
       answer: str = OutputField(desc="回答")
       
2. Adapter.format() 编译
   ├─ format_system_message(signature)  → 系统消息
   │   ├─ format_field_description()    → 字段描述+类型+约束
   │   ├─ format_field_structure()      → [[ ## field ## ]] 标记格式说明
   │   └─ format_task_description()     → signature.instructions
   ├─ format_demos(signature, demos)    → 每个demo转为user/assistant对
   └─ format_user_message_content()     → 当前输入

3. LM调用 → 原始输出

4. Adapter.parse() 解析
   ├─ ChatAdapter: 正则匹配 [[ ## field ## ]] value
   ├─ JSONAdapter: json_repair.loads → 按key提取
   ├─ XMLAdapter: 正则匹配 <field>value</field>
   └─ parse_value(value, annotation) → 类型强制转换
       ├─ str: 直接通过
       ├─ Enum/Literal: 匹配允许值
       ├─ 其他: json_repair.loads → ast.literal_eval → raw string
       └─ Pydantic TypeAdapter验证
```

### 5.2 Adapter体系

| Adapter | 输出格式 | 适用场景 | 解析方式 |
|---------|---------|---------|---------|
| `ChatAdapter` | `[[ ## field ## ]] value` | 通用默认 | 正则+JSON fallback |
| `JSONAdapter` | JSON对象 | 支持结构化输出的模型 | json_repair |
| `XMLAdapter` | `<field>value</field>` | XML偏好模型 | 正则 |
| `TwoStepAdapter` | 第1步自由文本→第2步提取 | 推理模型(o1/o3) | 两阶段 |

### 5.3 Assertion约束机制

DSPy的约束机制通过两层实现：

**Layer 1: Signature类型约束**
```python
class MySig(dspy.Signature):
    answer: int = OutputField(ge=0, le=100)  # Pydantic约束
    category: Literal["A", "B", "C"] = OutputField()  # 枚举约束
```
→ Adapter在format时将约束写入prompt，parse时用TypeAdapter验证

**Layer 2: dspy.Assert / dspy.Suggest 运行时约束**
```python
with dspy.context(assertions=True):
    result = module(**inputs)
    # 在module的forward中：
    dspy.Assert(
        condition=len(result.answer) > 0,
        msg="Answer cannot be empty"
    )
    dspy.Suggest(  # 软约束，失败时重试而非终止
        condition="reasoning" in result.__dict__,
        msg="Please include reasoning"
    )
```

**Layer 3: metric反馈约束（GEPA独有）**
```python
# GEPA通过feedback机制实现软约束
def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    if not is_valid(pred):
        return dspy.Prediction(
            score=0.0,
            feedback=f"Output violates constraint: {explain_violation(pred)}"
        )
    return dspy.Prediction(score=1.0, feedback=None)
```
→ feedback被反射LM读取，从而在后续迭代中学习遵守约束

---

## 六、GEPA核心思想移植方案

### 6.1 架构设计（不依赖DSPy的Python Prompt工具包）

```python
"""
gepa_lite: 轻量级GEPA实现
核心依赖: 仅需openai/anthropic SDK + pydantic
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
import copy, random, json

# ═══════════════════════════════════════
# 核心数据结构
# ═══════════════════════════════════════

@dataclass
class ScoreWithFeedback:
    score: float
    feedback: Optional[str] = None

@dataclass
class Trace:
    predictor_name: str
    instruction: str
    inputs: dict
    outputs: dict
    score: float = 0.0
    feedback: Optional[str] = None

@dataclass
class Candidate:
    id: int
    instructions: dict[str, str]  # predictor_name → instruction
    parent_id: Optional[int] = None
    per_example_scores: dict[int, float] = field(default_factory=dict)
    aggregate_score: float = 0.0

# ═══════════════════════════════════════
# 反射式提议器
# ═══════════════════════════════════════

class ReflectiveProposer:
    """用reflection_lm分析失败trace并提出新指令"""
    
    def __init__(self, reflection_lm: Callable):
        self.reflection_lm = reflection_lm
    
    def propose(
        self,
        current_instruction: str,
        failing_traces: list[Trace],
        predictor_name: str,
    ) -> str:
        # 构建反射prompt
        reflection_prompt = self._build_reflection_prompt(
            current_instruction, failing_traces, predictor_name
        )
        # 调用reflection LM
        new_instruction = self.reflection_lm(reflection_prompt)
        return new_instruction
    
    def _build_reflection_prompt(self, current_instruction, traces, predictor_name):
        examples_text = ""
        for t in traces:
            examples_text += f"""
---
Input: {json.dumps(t.inputs, ensure_ascii=False)}
Output: {json.dumps(t.outputs, ensure_ascii=False)}
Score: {t.score}
Feedback: {t.feedback or "No specific feedback provided."}
---"""
        
        return f"""You are a prompt optimization expert. Analyze the following failing examples and propose an improved instruction.

## Current instruction for `{predictor_name}`:
{current_instruction}

## Failing examples:
{examples_text}

## Task:
Based on the patterns of failure and the feedback provided, write an improved instruction that addresses these issues. The instruction should be specific, actionable, and directly address the failure modes observed.

Output ONLY the new instruction text, no explanation."""

# ═══════════════════════════════════════
# Pareto前沿管理
# ═══════════════════════════════════════

class ParetoFrontier:
    """管理per-example Pareto前沿"""
    
    def __init__(self):
        self.candidates: dict[int, Candidate] = {}
        self.per_example_best: dict[int, set[int]] = {}  # example_id → {candidate_ids}
    
    def update(self, candidate: Candidate):
        self.candidates[candidate.id] = candidate
        for ex_id, score in candidate.per_example_scores.items():
            if ex_id not in self.per_example_best:
                self.per_example_best[ex_id] = {candidate.id}
            else:
                current_best_ids = self.per_example_best[ex_id]
                current_best_score = max(
                    self.candidates[cid].per_example_scores.get(ex_id, 0)
                    for cid in current_best_ids
                )
                if score > current_best_score:
                    self.per_example_best[ex_id] = {candidate.id}
                elif score == current_best_score:
                    current_best_ids.add(candidate.id)
    
    def sample_parent(self) -> Candidate:
        """从Pareto前沿随机采样一个候选作为父本"""
        pareto_ids = set()
        for ids in self.per_example_best.values():
            pareto_ids.update(ids)
        parent_id = random.choice(list(pareto_ids))
        return self.candidates[parent_id]
    
    def best_candidate(self) -> Candidate:
        """返回聚合分数最高的候选"""
        return max(self.candidates.values(), key=lambda c: c.aggregate_score)

# ═══════════════════════════════════════
# 合并策略
# ═══════════════════════════════════════

class MergeStrategy:
    """组合不同候选的优势指令"""
    
    def merge(
        self,
        parent_a: Candidate,
        parent_b: Candidate,
        predictor_names: list[str],
    ) -> dict[str, str]:
        merged = {}
        for name in predictor_names:
            # 取分数更高的候选的指令
            score_a = parent_a.aggregate_score
            score_b = parent_b.aggregate_score
            merged[name] = parent_a.instructions[name] if score_a >= score_b else parent_b.instructions[name]
        return merged

# ═══════════════════════════════════════
# 组件选择器
# ═══════════════════════════════════════

class RoundRobinSelector:
    """轮转选择predictor进行优化"""
    
    def __init__(self, predictor_names: list[str]):
        self.names = predictor_names
        self.idx = 0
    
    def select(self) -> str:
        name = self.names[self.idx % len(self.names)]
        self.idx += 1
        return name

# ═══════════════════════════════════════
# 核心优化器
# ═══════════════════════════════════════

class GEPAOptimizer:
    """
    轻量级GEPA优化器
    不依赖DSPy，可独立集成到任何Python Prompt工具包中
    """
    
    def __init__(
        self,
        metric: Callable,
        execute_fn: Callable,
        reflection_lm: Callable,
        predictor_names: list[str],
        auto: str = "light",
        reflection_minibatch_size: int = 3,
        skip_perfect_score: bool = True,
        use_merge: bool = True,
        max_merge_invocations: int = 5,
        perfect_score: float = 1.0,
        failure_score: float = 0.0,
        seed: int = 0,
    ):
        self.metric = metric
        self.execute_fn = execute_fn
        self.reflection_lm = reflection_lm
        self.predictor_names = predictor_names
        self.reflection_minibatch_size = reflection_minibatch_size
        self.skip_perfect_score = skip_perfect_score
        self.use_merge = use_merge
        self.max_merge_invocations = max_merge_invocations
        self.perfect_score = perfect_score
        self.failure_score = failure_score
        self.seed = seed
        
        # 内部组件
        self.proposer = ReflectiveProposer(reflection_lm)
        self.frontier = ParetoFrontier()
        self.component_selector = RoundRobinSelector(predictor_names)
        self.merger = MergeStrategy()
        self.rng = random.Random(seed)
        
        # 预算
        budget_map = {"light": 6, "medium": 12, "heavy": 18}
        self.num_candidates = budget_map.get(auto, 6)
    
    def optimize(
        self,
        initial_instructions: dict[str, str],
        trainset: list[dict],
        valset: Optional[list[dict]] = None,
    ) -> dict[str, str]:
        """
        执行GEPA优化循环
        
        Args:
            initial_instructions: {predictor_name: initial_instruction}
            trainset: 训练集，每个元素包含inputs和expected
            valset: 验证集，默认使用trainset
            
        Returns:
            优化后的 {predictor_name: optimized_instruction}
        """
        valset = valset or trainset
        candidate_counter = 0
        merge_count = 0
        
        # 初始候选
        seed = Candidate(
            id=candidate_counter,
            instructions=copy.deepcopy(initial_instructions),
        )
        self._evaluate_candidate(seed, valset)
        self.frontier.update(seed)
        candidate_counter += 1
        
        iteration = 0
        while candidate_counter < self.num_candidates + 10:
            iteration += 1
            
            # 1. 从Pareto前沿采样父本
            parent = self.frontier.sample_parent()
            
            # 2. 选择要优化的predictor
            target_predictor = self.component_selector.select()
            
            # 3. 在trainset上执行，收集失败trace
            traces = self._execute_and_trace(
                parent.instructions, trainset, target_predictor
            )
            
            # 4. 过滤+采样失败样本
            failing = [
                t for t in traces
                if not self.skip_perfect_score or t.score < self.perfect_score
            ]
            if not failing:
                # 所有样本都满分，跳过本轮
                continue
            
            minibatch = self.rng.sample(
                failing, min(self.reflection_minibatch_size, len(failing))
            )
            
            # 5. 反射：提出新指令
            new_instruction = self.proposer.propose(
                current_instruction=parent.instructions[target_predictor],
                failing_traces=minibatch,
                predictor_name=target_predictor,
            )
            
            # 6. 创建变异体
            child_instructions = copy.deepcopy(parent.instructions)
            child_instructions[target_predictor] = new_instruction
            
            child = Candidate(
                id=candidate_counter,
                instructions=child_instructions,
                parent_id=parent.id,
            )
            
            # 7. 评估
            self._evaluate_candidate(child, valset)
            self.frontier.update(child)
            candidate_counter += 1
            
            # 8. 合并（可选）
            if self.use_merge and merge_count < self.max_merge_invocations:
                merged_instructions = self._try_merge(child)
                if merged_instructions:
                    merged = Candidate(
                        id=candidate_counter,
                        instructions=merged_instructions,
                    )
                    self._evaluate_candidate(merged, valset)
                    self.frontier.update(merged)
                    candidate_counter += 1
                    merge_count += 1
        
        # 返回最优候选
        best = self.frontier.best_candidate()
        return best.instructions
    
    def _execute_and_trace(
        self,
        instructions: dict[str, str],
        dataset: list[dict],
        target_predictor: str,
    ) -> list[Trace]:
        """执行program并收集per-predictor trace"""
        traces = []
        for example in dataset:
            try:
                outputs = self.execute_fn(instructions, example["inputs"])
                
                # 调用metric获取score + feedback
                result = self.metric(
                    gold=example,
                    pred=outputs,
                    pred_name=target_predictor,
                    pred_trace=outputs.get("__trace__", {}),
                )
                
                if isinstance(result, ScoreWithFeedback):
                    score, feedback = result.score, result.feedback
                else:
                    score, feedback = float(result), None
                
                traces.append(Trace(
                    predictor_name=target_predictor,
                    instruction=instructions[target_predictor],
                    inputs=example["inputs"],
                    outputs=outputs,
                    score=score,
                    feedback=feedback,
                ))
            except Exception:
                traces.append(Trace(
                    predictor_name=target_predictor,
                    instruction=instructions[target_predictor],
                    inputs=example["inputs"],
                    outputs={},
                    score=self.failure_score,
                    feedback="Execution failed with exception.",
                ))
        return traces
    
    def _evaluate_candidate(self, candidate: Candidate, valset: list[dict]):
        """在valset上全量评估候选"""
        total_score = 0.0
        for i, example in enumerate(valset):
            try:
                outputs = self.execute_fn(candidate.instructions, example["inputs"])
                result = self.metric(gold=example, pred=outputs)
                if isinstance(result, ScoreWithFeedback):
                    score = result.score
                else:
                    score = float(result)
            except Exception:
                score = self.failure_score
            
            candidate.per_example_scores[i] = score
            total_score += score
        
        candidate.aggregate_score = total_score / len(valset) if valset else 0.0
    
    def _try_merge(self, candidate: Candidate) -> Optional[dict[str, str]]:
        """尝试与另一个Pareto候选合并"""
        pareto_ids = set()
        for ids in self.frontier.per_example_best.values():
            pareto_ids.update(ids)
        pareto_ids.discard(candidate.id)
        
        if not pareto_ids:
            return None
        
        other_id = self.rng.choice(list(pareto_ids))
        other = self.frontier.candidates[other_id]
        
        # 检查是否有互补性（各自在不同example上领先）
        a_wins = sum(
            1 for ex_id in candidate.per_example_scores
            if candidate.per_example_scores.get(ex_id, 0) > other.per_example_scores.get(ex_id, 0)
        )
        b_wins = sum(
            1 for ex_id in other.per_example_scores
            if other.per_example_scores.get(ex_id, 0) > candidate.per_example_scores.get(ex_id, 0)
        )
        
        if a_wins > 0 and b_wins > 0:
            return self.merger.merge(candidate, other, self.predictor_names)
        return None
```

### 6.2 集成使用示例

```python
import openai

# 1. 定义LM调用函数
def call_lm(prompt: str, system: str = "") -> str:
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=1.0,
        max_tokens=4000,
    )
    return resp.choices[0].message.content

# 2. 定义feedback metric
def my_metric(gold, pred, pred_name=None, pred_trace=None):
    is_correct = pred["answer"].strip().lower() == gold["expected"].strip().lower()
    if not is_correct:
        feedback = f"Expected: {gold['expected']}, Got: {pred['answer']}. The answer is incorrect."
    else:
        feedback = None
    return ScoreWithFeedback(score=1.0 if is_correct else 0.0, feedback=feedback)

# 3. 定义执行函数
def execute_fn(instructions: dict, inputs: dict) -> dict:
    prompt = f"""{instructions['answer_predictor']}

Question: {inputs['question']}"""
    answer = call_lm(prompt)
    return {"answer": answer}

# 4. 运行GEPA优化
optimizer = GEPAOptimizer(
    metric=my_metric,
    execute_fn=execute_fn,
    reflection_lm=call_lm,
    predictor_names=["answer_predictor"],
    auto="light",
    reflection_minibatch_size=3,
)

optimized = optimizer.optimize(
    initial_instructions={"answer_predictor": "Answer the following question accurately."},
    trainset=[
        {"inputs": {"question": "What is 2+2?"}, "expected": "4"},
        {"inputs": {"question": "Capital of France?"}, "expected": "Paris"},
        # ... more examples
    ],
)

print(f"Optimized instruction: {optimized['answer_predictor']}")
```

### 6.3 关键移植要点

| GEPA核心概念 | 移植实现 | 注意事项 |
|-------------|---------|---------|
| **反射式变异** | `ReflectiveProposer` | 反射prompt必须包含：当前指令+失败trace+feedback |
| **自然语言反馈** | `ScoreWithFeedback` | metric必须返回feedback，否则退化为标量搜索 |
| **Pareto前沿** | `ParetoFrontier` | 采样从前沿而非贪心，是GEPA vs COPRO的核心差异 |
| **轮转选择** | `RoundRobinSelector` | 多predictor时避免同时变异导致不稳定 |
| **合并策略** | `MergeStrategy` | 检测互补性后合并，发现单一反射无法发现的组合 |
| **skip_perfect** | 过滤满分样本 | 反射只看失败，避免"修复"已工作的行为 |
| **双LM架构** | task_model + reflection_lm | 弱模型执行+强模型反思=成本最优 |

### 6.4 进阶优化方向

1. **检查点恢复**：将frontier状态序列化到磁盘，支持中断恢复
2. **自适应minibatch**：根据失败样本多样性动态调整reflection_minibatch_size
3. **多模态支持**：扩展Trace以支持image/audio内容
4. **分布式评估**：valset评估可并行化
5. **早停机制**：当连续N轮无Pareto改进时提前终止
6. **日志系统**：记录每轮变异的指令diff和分数变化，便于事后分析

---

## 附录：参考资源

| 资源 | 链接 |
|------|------|
| GEPA论文 | arXiv:2507.19457 (ICLR 2026 Oral) |
| GEPA独立库 | https://github.com/gepa-ai/gepa |
| DSPy主仓库 | https://github.com/stanfordnlp/dspy |
| DSPy官方文档-GEPA入门 | https://dspy.ai/getting-started/gepa-optimization/ |
| DSPy官方文档-GEPA深入 | https://dspy.ai/diving-deeper/gepa-in-depth/ |
| DSPy官方文档-优化器选择 | https://dspy.ai/diving-deeper/choosing-an-optimizer/ |
| DSPy官方文档-BootstrapFewShot | https://dspy.ai/diving-deeper/bootstrap-fewshot-family/ |
| DSPy官方文档-Adapter机制 | https://dspy.ai/diving-deeper/adapters/ |
| Shopify案例 | 使用GEPA后成本降低75x，可靠性提升2x |
| Dropbox案例 | 使用DSPy优化后准确率翻倍，标注成本降低10-100x |
