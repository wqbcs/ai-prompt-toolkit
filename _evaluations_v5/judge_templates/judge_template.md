# LLM-as-Judge评估脚本模板

> **版本**：v1.0.0
> **日期**：2026-05-29
> **迭代**：C11-迭代51
> **适用**：八维度自动化评估

---

## 一、Judge模板设计原则

1. 每个维度独立Judge Prompt，避免维度间干扰
2. 3次采样取中位数，减少位置偏差和随机性
3. 交叉评估：不同模型Judge同一输出
4. 反转测试：交换A/B顺序验证位置偏差
5. 基线锚定：先评估已知质量样本，校准评分尺度

---

## 二、八维度Judge Prompt模板

### 2.1 结构完整性Judge

```python
STRUCTURE_JUDGE_PROMPT = """
你是一名提示词工程专家，请评估以下场景模板的结构完整性。

【评估标准】
- 0-5分：仅有任务列表，无结构化要素
- 6-10分：有部分要素(2-3个)，缺显式5要素标注
- 11-14分：有4个要素，缺1个
- 15-17分：有5要素，但部分内容过简(<3项)
- 18-20分：5要素完整，每要素充实(≥3项)且格式规范

【五要素清单】
1. 场景描述：1-2句话说明场景用途
2. 输入要素：必需输入+可选输入
3. 输出格式：结构化格式+示例
4. 检查清单：至少8项
5. 验收标准：可量化的通过条件

【待评估场景模板】
{scenario_content}

请按以下格式输出评估结果：
```json
{{
  "score": 0,
  "five_elements_status": {{
    "description": {{"present": true, "quality": "good|partial|missing"}},
    "input": {{"present": true, "quality": "good|partial|missing"}},
    "output": {{"present": true, "quality": "good|partial|missing"}},
    "checklist": {{"present": true, "item_count": 0, "quality": "good|partial|missing"}},
    "acceptance": {{"present": true, "quality": "good|partial|missing"}}
  }},
  "improvement_suggestions": []
}}
```
"""
```

### 2.2 约束完备性Judge

```python
CONSTRAINT_JUDGE_PROMPT = """
你是一名系统架构师，请评估以下文档的约束条件完备性。

【评估标准】
- 0-5分：无约束或仅1条泛泛约束
- 6-10分：有2-3条约束，仅覆盖1-2个维度
- 11-14分：有4-6条约束，覆盖2-3个维度
- 15-17分：覆盖3个维度，第4维度仅隐含
- 18-20分：覆盖技术/业务/安全/性能4维度，每维度≥2条显式约束

【四维度检查】
1. 技术约束：技术栈/框架版本/兼容性/架构限制
2. 业务约束：业务规则/数据范围/用户规模/SLA
3. 安全约束：认证/授权/加密/审计/合规
4. 性能约束：延迟/吞吐/资源限制/容量上限

【待评估文档】
{document_content}

请输出JSON格式的评估结果，包含score/constraint_dimensions_status/improvement_suggestions。
"""
```

### 2.3 输出格式精确性Judge

```python
OUTPUT_FORMAT_JUDGE_PROMPT = """
你是一名API设计专家，请评估以下场景模板的输出格式精确性。

【评估标准】
- 0-5分：仅"输出XXX"文本，无格式约束
- 6-10分：有格式提及(如"表格形式")，无模板/示例
- 11-14分：有格式模板，缺示例
- 15-17分：有格式模板+示例，部分场景缺失
- 18-20分：所有场景有模板+完整示例，含必含要素+禁止项

【检查项】
1. 是否指定了输出格式(JSON/YAML/Markdown)?
2. 是否提供了格式模板/Schema?
3. 是否提供了完整输出示例?
4. 是否标注了必含要素和禁止项?
5. 示例是否可解析(JSON/YAML合法)?

【待评估场景模板】
{scenario_content}

请输出JSON格式的评估结果。
"""
```

### 2.4 推理模式适配性Judge

```python
REASONING_JUDGE_PROMPT = """
你是一名AI提示词工程师，请评估以下场景模板的推理模式适配性。

【评估标准】
- 0-5分：无任何推理模式标注
- 6-10分：有适配标注，但无CoT/Few-shot
- 11-14分：有CoT指令或Few-shot，仅1-2场景
- 15-17分：有CoT+Few-shot，覆盖≥50%复杂场景
- 18-20分：多种推理模式(CoT+Few-shot+自纠错+ReAct)覆盖≥80%

【推理模式检查】
1. CoT(思维链)：是否有逐步推理指令?
2. Few-shot：是否有格式示例(3-5个)?
3. Self-Correction：是否有自纠错循环?
4. ReAct：是否有Thought→Action→Observation循环?
5. PoT(Program-of-Thoughts)：是否有可执行验证指令?
6. Active-Prompt：是否有不确定性评估?

【待评估场景模板】
{scenario_content}

请输出JSON格式的评估结果。
"""
```

### 2.5 行业垂直化覆盖度Judge

```python
INDUSTRY_JUDGE_PROMPT = """
你是一名行业解决方案专家，请评估以下提示词体系的行业垂直化覆盖度。

【评估标准】
- 0-2分：无行业适配
- 2-4分：1-2个行业初步适配
- 4-6分：3个行业适配，含checklist+合规
- 6-8分：4-5个行业适配，含完整3件套(checklist+glossary+compliance)
- 8-10分：5+行业适配，含行业工作流+行业专用监控

【检查项】
1. 行业覆盖数量(金融/医疗/电商/SaaS/游戏/...)
2. 每行业是否有专项检查清单?
3. 每行业是否有术语表?
4. 每行业是否有合规要求?
5. 是否有行业专用工作流?
6. 行业与通用提示词是否集成?

【待评估体系内容】
{system_content}

请输出JSON格式的评估结果。
"""
```

### 2.6 前沿技术适配度Judge

```python
FRONTIER_JUDGE_PROMPT = """
你是一名AI技术研究专家，请评估以下提示词体系的前沿技术适配度。

【评估标准】
- 0-2分：无前沿技术适配
- 2-4分：1-2种前沿技术初步适配
- 4-6分：3种前沿技术适配(PoT/Active-Prompt/Agent-First)
- 6-8分：4+种前沿技术适配，含具体指令
- 8-10分：5+种前沿技术，含模型适配+评估数据

【前沿技术检查】
1. PoT(Program-of-Thoughts)
2. Active-Prompt(不确定性驱动)
3. Agent-First(多Agent协作)
4. 结构化输出强制
5. Prompt Chaining(链式提示)
6. APE(Automatic Prompt Engineer)

【待评估体系内容】
{system_content}

请输出JSON格式的评估结果。
"""
```

---

## 三、评估脚本执行流程

```python
import json
from typing import Dict, List

def run_llm_judge(
    model: str,
    judge_prompt: str,
    content: str,
    samples: int = 3
) -> Dict:
    scores = []
    for i in range(samples):
        response = llm_call(
            model=model,
            prompt=judge_prompt.format(scenario_content=content),
            temperature=0.1
        )
        result = json.loads(response)
        scores.append(result["score"])
    return {
        "median_score": median(scores),
        "all_scores": scores,
        "std": stdev(scores)
    }

def cross_evaluation(
    models: List[str],
    judge_prompt: str,
    content: str
) -> Dict:
    results = {}
    for model in models:
        results[model] = run_llm_judge(model, judge_prompt, content)
    return {
        "cross_eval_results": results,
        "agreement_rate": calculate_agreement(results)
    }
```

---

*本文件为C11批次迭代51产出，LLM-as-Judge评估脚本模板。*
