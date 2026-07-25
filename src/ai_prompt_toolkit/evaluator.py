"""80维度评估框架——D01-D80维度定义、evaluate_template()函数、EvaluationReport数据类。"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity

_LOW_SCORE_THRESHOLD = 4.0
_VERY_LOW_SCORE_THRESHOLD = 2.0


_DIMENSIONS: list[dict[str, Any]] = [
    {"id": "D01", "name": "角色清晰度", "category": "structure", "weight": 1.0, "description": "Prompt是否定义了明确的角色"},
    {"id": "D02", "name": "目标明确性", "category": "structure", "weight": 1.0, "description": "Prompt是否表达了清晰的目标"},
    {"id": "D03", "name": "输出格式规范", "category": "structure", "weight": 0.8, "description": "Prompt是否指定了输出格式"},
    {"id": "D04", "name": "约束完备性", "category": "structure", "weight": 0.9, "description": "Prompt是否包含充分的约束条件"},
    {"id": "D05", "name": "上下文充分性", "category": "structure", "weight": 1.0, "description": "Prompt是否提供了足够的上下文"},
    {"id": "D06", "name": "指令无歧义性", "category": "structure", "weight": 1.0, "description": "Prompt指令是否无歧义"},
    {"id": "D07", "name": "逻辑一致性", "category": "structure", "weight": 1.0, "description": "Prompt内部逻辑是否自洽"},
    {"id": "D08", "name": "结构层次性", "category": "structure", "weight": 0.7, "description": "Prompt是否有清晰的结构层次"},
    {"id": "D09", "name": "版本兼容性", "category": "structure", "weight": 0.5, "description": "Prompt是否声明了版本和兼容性"},
    {"id": "D10", "name": "可维护性", "category": "structure", "weight": 0.6, "description": "Prompt是否易于维护和更新"},
    {"id": "D11", "name": "注入防御", "category": "security", "weight": 1.0, "description": "Prompt是否防御了注入攻击"},
    {"id": "D12", "name": "敏感信息保护", "category": "security", "weight": 1.0, "description": "Prompt是否保护了敏感信息"},
    {"id": "D13", "name": "权限最小化", "category": "security", "weight": 0.9, "description": "Prompt是否遵循最小权限原则"},
    {"id": "D14", "name": "输入验证", "category": "security", "weight": 0.9, "description": "Prompt是否验证了用户输入"},
    {"id": "D15", "name": "输出过滤", "category": "security", "weight": 0.8, "description": "Prompt是否过滤了危险输出"},
    {"id": "D16", "name": "审计追踪", "category": "security", "weight": 0.6, "description": "Prompt是否支持审计追踪"},
    {"id": "D17", "name": "回退策略", "category": "security", "weight": 0.7, "description": "Prompt是否定义了回退策略"},
    {"id": "D18", "name": "隔离性", "category": "security", "weight": 0.8, "description": "Prompt是否实现了上下文隔离"},
    {"id": "D19", "name": "合规性", "category": "security", "weight": 0.7, "description": "Prompt是否符合合规要求"},
    {"id": "D20", "name": "数据脱敏", "category": "security", "weight": 0.8, "description": "Prompt是否对数据进行了脱敏"},
    {"id": "D21", "name": "Token效率", "category": "performance", "weight": 0.8, "description": "Prompt的Token使用效率"},
    {"id": "D22", "name": "响应延迟优化", "category": "performance", "weight": 0.7, "description": "Prompt是否优化了响应延迟"},
    {"id": "D23", "name": "缓存友好性", "category": "performance", "weight": 0.6, "description": "Prompt是否适合缓存复用"},
    {"id": "D24", "name": "批处理兼容性", "category": "performance", "weight": 0.5, "description": "Prompt是否支持批处理"},
    {"id": "D25", "name": "并行安全性", "category": "performance", "weight": 0.6, "description": "Prompt在并行调用下是否安全"},
    {"id": "D26", "name": "流式输出适配", "category": "performance", "weight": 0.5, "description": "Prompt是否适配流式输出"},
    {"id": "D27", "name": "成本效率", "category": "performance", "weight": 0.7, "description": "Prompt的API调用成本效率"},
    {"id": "D28", "name": "模型兼容广度", "category": "performance", "weight": 0.6, "description": "Prompt在多种模型上的兼容性"},
    {"id": "D29", "name": "降级适配性", "category": "performance", "weight": 0.5, "description": "Prompt在低配模型上的表现"},
    {"id": "D30", "name": "重试幂等性", "category": "performance", "weight": 0.6, "description": "Prompt重试调用是否幂等"},
    {"id": "D31", "name": "示例质量", "category": "quality", "weight": 0.9, "description": "Prompt的Few-shot示例质量"},
    {"id": "D32", "name": "推理链引导", "category": "quality", "weight": 0.8, "description": "Prompt是否引导了推理链"},
    {"id": "D33", "name": "错误处理完整性", "category": "quality", "weight": 0.7, "description": "Prompt的错误处理是否完整"},
    {"id": "D34", "name": "边界条件覆盖", "category": "quality", "weight": 0.8, "description": "Prompt是否覆盖了边界条件"},
    {"id": "D35", "name": "多语言支持", "category": "quality", "weight": 0.5, "description": "Prompt是否支持多语言"},
    {"id": "D36", "name": "文化适配性", "category": "quality", "weight": 0.4, "description": "Prompt是否适配不同文化背景"},
    {"id": "D37", "name": "可解释性", "category": "quality", "weight": 0.7, "description": "Prompt的决策过程是否可解释"},
    {"id": "D38", "name": "鲁棒性", "category": "quality", "weight": 0.8, "description": "Prompt在异常输入下的鲁棒性"},
    {"id": "D39", "name": "一致性", "category": "quality", "weight": 0.9, "description": "Prompt多次调用输出的一致性"},
    {"id": "D40", "name": "用户意图匹配", "category": "quality", "weight": 1.0, "description": "Prompt输出是否匹配用户意图"},
    {"id": "D41", "name": "工具链可运行性", "category": "toolchain", "weight": 1.0, "description": "Prompt引用的工具链是否可运行"},
    {"id": "D42", "name": "API可达性", "category": "toolchain", "weight": 0.9, "description": "Prompt依赖的API是否可达"},
    {"id": "D43", "name": "依赖完整性", "category": "toolchain", "weight": 0.8, "description": "Prompt的依赖是否完整声明"},
    {"id": "D44", "name": "环境变量引用", "category": "toolchain", "weight": 0.7, "description": "Prompt是否正确引用环境变量"},
    {"id": "D45", "name": "版本锁定", "category": "toolchain", "weight": 0.6, "description": "Prompt依赖是否有版本锁定"},
    {"id": "D46", "name": "Lint合规", "category": "toolchain", "weight": 0.9, "description": "Prompt是否通过了Lint质量门禁"},
    {"id": "D47", "name": "安全扫描通过", "category": "toolchain", "weight": 1.0, "description": "Prompt是否通过了安全扫描"},
    {"id": "D48", "name": "编译无误", "category": "toolchain", "weight": 0.9, "description": "Prompt条件编译是否无错误"},
    {"id": "D49", "name": "测试覆盖", "category": "toolchain", "weight": 0.7, "description": "Prompt是否有测试覆盖"},
    {"id": "D50", "name": "文档完备", "category": "toolchain", "weight": 0.5, "description": "Prompt是否有完备文档"},
    {"id": "D51", "name": "CI/CD集成", "category": "toolchain", "weight": 0.6, "description": "Prompt是否集成CI/CD流程"},
    {"id": "D52", "name": "监控就绪", "category": "toolchain", "weight": 0.5, "description": "Prompt是否具备监控能力"},
    {"id": "D53", "name": "Lint前置质量", "category": "toolchain", "weight": 0.9, "description": "Prompt是否经过Lint检查并达到质量门禁"},
    {"id": "D54", "name": "国际化完备度", "category": "toolchain", "weight": 0.7, "description": "Prompt是否具备多语言翻译和i18n支持"},
    {"id": "D55", "name": "真实API调用能力", "category": "toolchain", "weight": 1.0, "description": "Provider是否能真实调用LLM API并获取响应"},
    {"id": "D56", "name": "CLI完备度", "category": "toolchain", "weight": 0.9, "description": "CLI子命令是否端到端可用(非骨架echo)"},
    {"id": "D57", "name": "Playground可用性", "category": "toolchain", "weight": 0.8, "description": "条件编译Playground Web UI是否可交互使用"},
    {"id": "D58", "name": "CI/CD集成度", "category": "toolchain", "weight": 0.7, "description": "是否集成CI/CD流水线质量门禁"},
    {"id": "D59", "name": "模板类型感知", "category": "toolchain", "weight": 0.8, "description": "Linter是否区分知识型/提示词型模板并调整规则"},
    {"id": "D60", "name": "Front Matter v3合规", "category": "toolchain", "weight": 0.9, "description": "模板是否使用v3 Schema(i18n_status/market_status/lint_score)"},
    {"id": "D61", "name": "VS Code扩展集成", "category": "toolchain", "weight": 0.7, "description": "是否提供VS Code Lint扩展实现编辑器内实时检查"},
    {"id": "D62", "name": "新用户引导可用性", "category": "toolchain", "weight": 0.6, "description": "是否提供3步引导(init命令)帮助新用户快速上手"},
    {"id": "D63", "name": "偏见公平性", "category": "fairness", "weight": 1.0, "description": "Prompt是否避免性别/种族/年龄等偏见表述"},
    {"id": "D64", "name": "文化包容性", "category": "fairness", "weight": 0.9, "description": "Prompt是否尊重多元文化背景，避免文化冒犯"},
    {"id": "D65", "name": "可访问性", "category": "fairness", "weight": 0.8, "description": "Prompt输出是否考虑残障用户可访问性需求"},
    {"id": "D66", "name": "思维链质量", "category": "quality", "weight": 0.8, "description": "Prompt推理链/CoT指令的质量和清晰度"},
    {"id": "D67", "name": "工具调用准确性", "category": "quality", "weight": 0.9, "description": "Prompt工具/函数调用声明的准确性和完整性"},
    {"id": "D68", "name": "多轮对话连贯性", "category": "quality", "weight": 0.8, "description": "Prompt多轮对话场景的上下文连贯性设计"},
    {"id": "D69", "name": "RAG检索相关性", "category": "quality", "weight": 0.8, "description": "RAG场景Prompt的检索增强声明和引用规范"},
    {"id": "D70", "name": "知识时效性", "category": "quality", "weight": 0.7, "description": "Prompt是否声明知识截止日期和时效性约束"},
    {"id": "D71", "name": "情感智能度", "category": "quality", "weight": 0.6, "description": "Prompt是否具备情感感知和共情能力设计"},
    {"id": "D72", "name": "伦理对齐度", "category": "fairness", "weight": 1.0, "description": "Prompt是否符合AI伦理准则，避免有害输出"},
    {"id": "D73", "name": "公平性偏见检测", "category": "fairness", "weight": 1.0, "description": "Prompt是否检测并缓解输出中的公平性偏见"},
    {"id": "D74", "name": "隐私合规度", "category": "security", "weight": 1.0, "description": "Prompt是否满足数据隐私法规(GDPR/PIPL)要求"},
    {"id": "D75", "name": "可审计性", "category": "security", "weight": 0.8, "description": "Prompt是否支持决策过程审计和结果追溯"},
    {"id": "D76", "name": "鲁棒性评分", "category": "quality", "weight": 0.9, "description": "Prompt在对抗性输入下的鲁棒性和稳定性"},
    {"id": "D77", "name": "可维护性评分", "category": "structure", "weight": 0.7, "description": "Prompt的模块化程度和版本管理能力"},
    {"id": "D78", "name": "国际化完备度", "category": "toolchain", "weight": 0.7, "description": "Prompt的国际化/本地化支持完备度"},
    {"id": "D79", "name": "盘古模型适配度", "category": "toolchain", "weight": 0.9, "description": "Prompt对华为云盘古大模型的适配和优化程度"},
    {"id": "D80", "name": "鸿蒙场景贴合度", "category": "toolchain", "weight": 1.0, "description": "Prompt对鸿蒙HarmonyOS NEXT场景的专业贴合度"},
]


@dataclass
class DimensionScore:
    dimension_id: str
    name: str
    category: str
    weight: float
    score: float
    max_score: float = 10.0
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized(self) -> float:
        return self.score / self.max_score if self.max_score > 0 else 0.0

    @property
    def weighted_score(self) -> float:
        return self.normalized * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "name": self.name,
            "category": self.category,
            "weight": self.weight,
            "score": self.score,
            "max_score": self.max_score,
            "normalized": round(self.normalized, 4),
            "weighted_score": round(self.weighted_score, 4),
            "details": self.details,
        }


@dataclass
class EvaluationReport:
    template_id: str
    scores: list[DimensionScore] = field(default_factory=list)
    overall_score: float = 0.0
    max_possible_score: float = 0.0
    percentage: float = 0.0
    category_scores: dict[str, float] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    evaluation_time_ms: float = 0.0
    dimension_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "overall_score": round(self.overall_score, 4),
            "max_possible_score": round(self.max_possible_score, 4),
            "percentage": round(self.percentage, 2),
            "category_scores": {k: round(v, 4) for k, v in self.category_scores.items()},
            "scores": [s.to_dict() for s in self.scores],
            "findings": [f.to_dict() for f in self.findings],
            "evaluation_time_ms": round(self.evaluation_time_ms, 2),
            "dimension_count": self.dimension_count,
        }


class _DimensionEvaluator:
    def __init__(self, text: str) -> None:
        self._text = text
        self._stats_cache: dict[str, Any] | None = None

    def _has_pattern(self, *patterns: str) -> bool:
        for p in patterns:
            if re.search(p, self._text, re.IGNORECASE):
                return True
        return False

    def _text_length(self) -> int:
        return len(self._text)

    def _count_pattern(self, *patterns: str) -> int:
        total = 0
        for p in patterns:
            total += len(re.findall(p, self._text, re.IGNORECASE | re.MULTILINE))
        return total

    def _compute_stats(self) -> dict[str, Any]:
        if self._stats_cache is not None:
            return self._stats_cache
        import unicodedata
        from collections import Counter
        from difflib import SequenceMatcher
        text = self._text
        words_zh = [c for c in text if '\u4e00' <= c <= '\u9fff']
        words_en = re.findall(r'[a-zA-Z]+', text)
        total_words = len(words_zh) + len(words_en)
        unique_zh = len(set(words_zh))
        unique_en = len(set(w.lower() for w in words_en))
        ttr = (unique_zh + unique_en) / max(total_words, 1)
        sentences = re.split(r'[。！？.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sent_lengths = [len(s) for s in sentences]
        avg_sent_len = sum(sent_lengths) / max(len(sent_lengths), 1)
        sent_len_var = 0.0
        if len(sent_lengths) > 1:
            mean = avg_sent_len
            sent_len_var = sum((l - mean) ** 2 for l in sent_lengths) / len(sent_lengths)
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        para_count = len(paragraphs)
        has_structure = sum(1 for p in paragraphs if re.match(r'^#{1,6}\s', p) or re.match(r'^-{3,}', p))
        bigrams = []
        for sent in sentences:
            chars = [c for c in sent if '\u4e00' <= c <= '\u9fff']
            for i in range(len(chars) - 1):
                bigrams.append(chars[i] + chars[i + 1])
        bigram_counter = Counter(bigrams)
        repeated_bigrams = sum(1 for bg, cnt in bigram_counter.items() if cnt > 2)
        similarities = []
        if len(paragraphs) >= 2:
            for i in range(min(len(paragraphs) - 1, 5)):
                ratio = SequenceMatcher(None, paragraphs[i], paragraphs[i + 1]).ratio()
                similarities.append(ratio)
        avg_similarity = sum(similarities) / max(len(similarities), 1)
        has_variables = bool(re.search(r'\{\{.*?\}\}', text))
        has_conditions = bool(re.search(r'\{%\s*if', text))
        has_few_shot = text.count('```') >= 2 or self._count_pattern(r'例[如子]', r'example', r'for\s+instance') >= 2
        role_sections = len(re.findall(r'(?:^|\n)\s*(?:system|user|assistant|角色|任务|约束|输出)[：:]\s*', text, re.IGNORECASE))
        self._stats_cache = {
            "total_chars": len(text),
            "total_words": total_words,
            "ttr": ttr,
            "sentence_count": len(sentences),
            "avg_sent_len": avg_sent_len,
            "sent_len_var": sent_len_var,
            "para_count": para_count,
            "structured_para_count": has_structure,
            "repeated_bigrams": repeated_bigrams,
            "avg_para_similarity": avg_similarity,
            "has_variables": has_variables,
            "has_conditions": has_conditions,
            "has_few_shot": has_few_shot,
            "role_sections": role_sections,
        }
        return self._stats_cache

    def _stat(self, key: str) -> Any:
        return self._compute_stats().get(key, 0)

    def evaluate(self, dim: dict[str, Any]) -> DimensionScore:
        dim_id = dim["id"]
        category = dim["category"]
        score = self._compute_score(dim_id, category)
        return DimensionScore(
            dimension_id=dim_id,
            name=dim["name"],
            category=category,
            weight=dim["weight"],
            score=score,
        )

    def _compute_score(self, dim_id: str, category: str) -> float:
        text = self._text
        length = self._text_length()

        if dim_id == "D01":
            score = 2.0
            if self._has_pattern(r"你(?:是|作为|扮演)", r"you\s+are", r"role[:：]"):
                score += 4.0
            if self._stat("role_sections") >= 2:
                score += 2.0
            if self._stat("role_sections") >= 4:
                score += 1.0
            if self._has_pattern(r"作为.{1,20}专家", r"你是.{1,20}助手", r"act\s+as", r"expert|specialist|professional"):
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D02":
            score = 2.0
            instr_count = self._count_pattern(r"请|帮我|要求|must|should|need|务必|确保|禁止|不要|不可")
            score += min(instr_count * 1.0, 4.0)
            if self._stat("avg_sent_len") > 10:
                score += 2.0
            if self._stat("role_sections") >= 2:
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D03":
            score = 2.0
            if self._has_pattern(r"输出(?:格式|为)|JSON|Markdown|format|output\s+as"):
                score += 4.0
            if self._has_pattern(r"列表|分点|要点|bullet|numbered|步骤"):
                score += 2.0
            if self._has_pattern(r"格式要求|输出规范|output\s+spec|output\s+format"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D04":
            count = self._count_pattern(r"不要|不可|禁止|must\s+not|do\s+not|never|限制|不得|严禁")
            return min(10.0, 3.0 + count * 1.5)
        elif dim_id == "D05":
            score = 2.0
            score += min(length / 200.0, 4.0)
            ttr = self._stat("ttr")
            if ttr > 0.5:
                score += 2.0
            elif ttr > 0.3:
                score += 1.0
            if self._stat("para_count") >= 3:
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D06":
            ambiguous = self._count_pattern(r"可能|大概|也许|maybe|perhaps|possibly|差不多|尽量|尽量|适当|酌情")
            base = max(1.0, 10.0 - ambiguous * 2.0)
            if self._has_pattern(r"务必|确保|必须|严格|exactly|precisely"):
                base = min(base + 1.5, 10.0)
            return base
        elif dim_id == "D07":
            score = 3.0
            has_positive = self._has_pattern(r"要|必须|需要|should|must|务必")
            has_negative = self._has_pattern(r"不要|禁止|must\s+not|never|不可|不得")
            if has_positive:
                score += 2.0
            if has_negative:
                score += 2.0
            if has_positive and has_negative:
                score += 2.0
            if self._stat("sent_len_var") > 100:
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D08":
            score = 2.0
            headers = self._count_pattern(r"^#+\s", r"^\d+\.\s", r"^-\s")
            score += min(headers * 0.8, 3.0)
            sp = self._stat("structured_para_count")
            if sp >= 3:
                score += 2.0
            elif sp >= 1:
                score += 1.0
            if self._stat("para_count") >= 3:
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D09":
            score = 2.0
            if self._has_pattern(r"version|版本|v\d+"):
                score += 4.0
            if self._has_pattern(r"更新|修订|迭代|changelog|变更日志"):
                score += 2.0
            if self._stat("has_conditions"):
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D10":
            score = 3.0
            if length < 2000:
                score += 1.0
            if self._has_pattern(r"---"):
                score += 1.5
            if self._stat("ttr") < 0.2:
                score -= 1.5
            repeated = self._stat("repeated_bigrams")
            if repeated > 10:
                score -= 1.0
            if self._stat("avg_para_similarity") > 0.8:
                score -= 1.0
            return max(1.0, min(score, 10.0))
        elif dim_id in ("D11", "D12", "D13", "D14", "D15", "D16", "D17", "D18", "D19", "D20"):
            return self._eval_security(dim_id)
        elif dim_id in ("D21", "D22", "D23", "D24", "D25", "D26", "D27", "D28", "D29", "D30"):
            return self._eval_performance(dim_id, length)
        elif dim_id in ("D31", "D32", "D33", "D34", "D35", "D36", "D37", "D38", "D39", "D40"):
            return self._eval_quality(dim_id)
        elif dim_id in ("D41", "D42", "D43", "D44", "D45", "D46", "D47", "D48", "D49", "D50", "D51", "D52"):
            return self._eval_toolchain(dim_id)
        elif dim_id in ("D63", "D64", "D65"):
            return self._eval_fairness(dim_id)
        elif dim_id in ("D66", "D67", "D68", "D69", "D70", "D71", "D76"):
            return self._eval_advanced_quality(dim_id)
        elif dim_id in ("D72", "D73"):
            return self._eval_advanced_fairness(dim_id)
        elif dim_id in ("D74", "D75"):
            return self._eval_advanced_security(dim_id)
        elif dim_id == "D77":
            return self._eval_advanced_structure(dim_id)
        elif dim_id in ("D78", "D79", "D80"):
            return self._eval_advanced_toolchain(dim_id)
        return 5.0

    def _eval_security(self, dim_id: str) -> float:
        if dim_id == "D11":
            score = 3.0
            has_escape = self._has_pattern(r"转义|escape|sanitize|校验|清洗|purify")
            has_user_input = self._has_pattern(r"\{\{.*?user.*?\}\}", r"\$\{", r"用户输入|user.?input")
            if has_user_input and has_escape:
                score += 5.0
            elif has_user_input:
                score += 0.0
            elif has_escape:
                score += 3.0
            else:
                score += 2.0
            if self._has_pattern(r"注入检测|injection.?detect|防护|protect"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D12":
            sensitive = self._count_pattern(r"api[_-]?key|password|secret|token|AK|SK|密钥|凭证")
            score = max(1.0, 10.0 - sensitive * 2.5)
            if self._has_pattern(r"环境变量|env|密钥管理|KMS|DEW"):
                score = min(score + 2.0, 10.0)
            return score
        elif dim_id == "D13":
            score = 3.0
            broad = self._has_pattern(r"任何|任意|anything|everything|所有.*权限|完全.*控制")
            if not broad:
                score += 4.0
            if self._has_pattern(r"最小权限|least.?privilege|仅限|restricted"):
                score += 3.0
            return min(score, 10.0)
        elif dim_id == "D14":
            score = 2.0
            if self._has_pattern(r"验证|校验|validate|check|确认|verify"):
                score += 4.0
            if self._has_pattern(r"输入验证|input.?valid|类型检查|type.?check"):
                score += 2.0
            if self._has_pattern(r"白名单|allowlist|whitelist|范围.*限制"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D15":
            score = 2.0
            if self._has_pattern(r"过滤|filter|排除|exclude|屏蔽|block"):
                score += 4.0
            if self._has_pattern(r"敏感词|sensitive.?word|内容审核|content.?moderat"):
                score += 2.0
            if self._has_pattern(r"黑名单|blacklist|denylist"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D16":
            score = 2.0
            if self._has_pattern(r"审计|audit|日志|log|记录|record"):
                score += 4.0
            if self._has_pattern(r"操作日志|access.?log|变更.*记录|change.?log"):
                score += 2.0
            if self._has_pattern(r"不可篡改|immutable|签名|signature"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D17":
            score = 2.0
            if self._has_pattern(r"如果.*失败|回退|fallback|otherwise|异常处理"):
                score += 4.0
            if self._has_pattern(r"重试|retry|降级|degrade|容错|fault.?tolerant"):
                score += 2.0
            if self._has_pattern(r"超时|timeout|熔断|circuit.?break"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D18":
            score = 2.0
            if self._has_pattern(r"隔离|isolate|sandbox|沙箱|安全边界"):
                score += 4.0
            if self._has_pattern(r"权限.*分离|separation.*duty|最小.*权限"):
                score += 2.0
            if self._has_pattern(r"容器|container|命名空间|namespace"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D19":
            score = 2.0
            if self._has_pattern(r"合规|compliance|GDPR|隐私|PIPL|等保"):
                score += 4.0
            if self._has_pattern(r"数据安全法|个人信息保护|数据出境|跨境"):
                score += 2.0
            if self._has_pattern(r"审计.*报告|合规.*检查|compliance.*check"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D20":
            score = 2.0
            if self._has_pattern(r"脱敏|mask|redact|匿名|anonymiz"):
                score += 4.0
            if self._has_pattern(r"假名化|pseudonymiz|去标识|de.?identif"):
                score += 2.0
            if self._has_pattern(r"差分隐私|differential.?privacy|K.?匿名"):
                score += 2.0
            return min(score, 10.0)
        return 5.0

    def _eval_performance(self, dim_id: str, length: int) -> float:
        if dim_id == "D21":
            score = 3.0
            if length < 500:
                score += 4.0
            elif length < 2000:
                score += 2.0
            if self._stat("has_variables"):
                score += 2.0
            if self._has_pattern(r"精简|token.*效率|efficient|优化.*长度"):
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D22":
            score = 3.0
            if length < 1000:
                score += 2.0
            has_concise = self._has_pattern(r"简洁|简短|不超过|精简|concise|brief")
            if has_concise:
                score += 2.0
            repeated = self._stat("repeated_bigrams")
            if repeated < 5:
                score += 1.5
            elif repeated > 15:
                score -= 1.0
            redundant_words = self._count_pattern(r"等等|之类的|可能|大概|应该|尽量")
            if redundant_words < 3:
                score += 1.5
            return max(1.0, min(score, 10.0))
        elif dim_id == "D23":
            score = 2.0
            if self._has_pattern(r"---", r"version"):
                score += 3.0
            if self._stat("has_conditions"):
                score += 3.0
            if self._stat("has_variables"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D24":
            score = 3.0
            if self._has_pattern(r"批量|batch|循环|loop|并行|parallel"):
                score += 4.0
            if self._has_pattern(r"异步|async|并发|concurrent|队列|queue"):
                score += 3.0
            return min(score, 10.0)
        elif dim_id == "D25":
            score = 4.0
            has_stateless = self._has_pattern(r"无状态|stateless|幂等|idempotent")
            no_global_var = self._count_pattern(r"全局|global|共享变量") == 0
            if has_stateless:
                score += 3.0
            if no_global_var:
                score += 2.0
            if self._has_pattern(r"缓存|cache|LRU|TTL"):
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D26":
            score = 3.0
            has_structure = self._count_pattern(r"^#+\s") >= 2
            has_sequential = self._has_pattern(r"首先|然后|接着|最后|第一步|step")
            if has_structure:
                score += 3.0
            if has_sequential:
                score += 2.0
            if self._stat("para_count") >= 3:
                score += 1.0
            if self._stat("avg_para_similarity") < 0.5:
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D27":
            score = 2.0
            if length < 800:
                score += 4.0
            elif length < 1500:
                score += 2.0
            if self._has_pattern(r"压缩|compress|摘要|summary|精简"):
                score += 2.0
            if self._stat("ttr") > 0.4:
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D28":
            score = 3.0
            if self._has_pattern(r"\{\{#if", r"model", r"条件编译", r"compile"):
                score += 4.0
            if self._stat("has_conditions"):
                score += 3.0
            return min(score, 10.0)
        elif dim_id == "D29":
            score = 2.0
            if length < 500:
                score += 4.0
            elif length < 1000:
                score += 2.0
            if self._has_pattern(r"流式|stream|增量|incremental|SSE"):
                score += 3.0
            return min(score, 10.0)
        elif dim_id == "D30":
            score = 4.0
            has_idempotent = self._has_pattern(r"幂等|idempotent|无状态|stateless")
            has_same_result = self._has_pattern(r"相同结果|same result|一致|consistent")
            if has_idempotent:
                score += 3.0
            if has_same_result:
                score += 2.0
            if self._has_pattern(r"temperature.*0|确定性|deterministic"):
                score += 1.0
            return min(score, 10.0)
        return 5.0

    def _eval_quality(self, dim_id: str) -> float:
        if dim_id == "D31":
            score = 3.0
            if self._has_pattern(r"示例|example|如：|如下|e\.g\."):
                score += 3.0
            if self._stat("has_few_shot"):
                score += 3.0
            if self._count_pattern(r"```") >= 2:
                score += 1.0
            return min(score, 10.0)
        elif dim_id == "D32":
            score = 3.0
            if self._has_pattern(r"一步步|逐步|step\s+by\s+step|CoT|推理链|思考过程|chain.of.thought"):
                score += 4.0
            if self._has_pattern(r"先.*再.*然后|首先.*其次.*最后|1\..*2\..*3\."):
                score += 3.0
            return min(score, 10.0)
        elif dim_id == "D33":
            score = 2.0
            if self._has_pattern(r"如果.*失败|错误|异常|error|exception|失败时"):
                score += 4.0
            if self._has_pattern(r"重试|retry|回退|fallback|降级|备选"):
                score += 2.0
            if self._has_pattern(r"超时|timeout|中断|interrupt"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D34":
            score = 2.0
            if self._has_pattern(r"边界|极限|最大|最小|boundary|edge|极端"):
                score += 4.0
            if self._has_pattern(r"空值|null|none|缺失|missing|空字符串"):
                score += 2.0
            if self._has_pattern(r"超长|overflow|超出范围|超出.*限制"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D35":
            score = 3.0
            zh_chars = sum(1 for c in self._text if '\u4e00' <= c <= '\u9fff')
            en_chars = len(re.findall(r'[a-zA-Z]', self._text))
            if zh_chars > 0 and en_chars > 0:
                score += 4.0
            elif zh_chars > 0 or en_chars > 0:
                score += 2.0
            if self._has_pattern(r"中文|英文|English|language|语言|locale|i18n"):
                score += 3.0
            return min(score, 10.0)
        elif dim_id == "D36":
            score = 2.0
            if self._has_pattern(r"文化|习惯|地区|region|本地化|文化差异"):
                score += 4.0
            if self._has_pattern(r"避免.*歧视|尊重.*差异|文化敏感|inclusive|diversity"):
                score += 4.0
            return min(score, 10.0)
        elif dim_id == "D37":
            score = 3.0
            if self._has_pattern(r"原因|理由|为什么|why|reason|解释"):
                score += 4.0
            if self._has_pattern(r"因为.*所以|due\s+to|because|therefore|因果"):
                score += 3.0
            return min(score, 10.0)
        elif dim_id == "D38":
            has_error_handling = self._has_pattern(r"错误|异常|失败|error|exception|fallback")
            has_boundary = self._has_pattern(r"边界|极限|最大|最小|超|超出|boundary")
            has_default = self._has_pattern(r"默认|default|否则|otherwise|回退")
            score = 3.0
            if has_error_handling:
                score += 3.0
            if has_boundary:
                score += 2.0
            if has_default:
                score += 2.0
            return min(10.0, score)
        elif dim_id == "D39":
            has_deterministic = self._has_pattern(r"确定|固定|一致|相同|deterministic|consistent")
            no_random = self._count_pattern(r"随机|random|可能|也许|任意") < 2
            has_temperature = self._has_pattern(r"temperature|温度|确定性")
            score = 4.0
            if has_deterministic:
                score += 2.0
            if no_random:
                score += 2.0
            if has_temperature:
                score += 2.0
            return min(10.0, score)
        elif dim_id == "D40":
            score = 2.0
            politeness = self._count_pattern(r"请|帮我|麻烦|能否|would|could|please")
            score += min(politeness * 1.0, 4.0)
            if self._has_pattern(r"谢谢|感谢|thank"):
                score += 2.0
            if self._stat("avg_sent_len") > 5:
                score += 2.0
            return min(score, 10.0)
        return 5.0

    def _eval_toolchain(self, dim_id: str) -> float:
        if dim_id == "D41":
            score = 2.0
            if self._has_pattern(r"import|from|require|依赖|SDK"):
                score += 3.0
            if self._has_pattern(r"API|\.py|\.ts|\.js|\.go|\.dart"):
                score += 3.0
            if self._has_pattern(r"包管理|package.?manage|pip|npm|pub"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D42":
            score = 2.0
            if self._has_pattern(r"https?://|endpoint|API|api_key|url|服务地址"):
                score += 3.0
            if self._has_pattern(r"provider|openai|claude|qwen|pangu|deepseek|模型"):
                score += 3.0
            if self._has_pattern(r"认证|auth|AK|SK|token|凭证"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D43":
            score = 2.0
            if self._has_pattern(r"依赖|require|import|第三方"):
                score += 4.0
            if self._has_pattern(r"版本.*锁定|pin|lock|freeze|固定版本"):
                score += 2.0
            if self._has_pattern(r"安全.*审计|audit|漏洞|CVE|vulnerability"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D44":
            score = 2.0
            if self._has_pattern(r"ENV|environment|环境变量|\$\{.*\}"):
                score += 4.0
            if self._has_pattern(r"配置文件|config|\.env|setting|TOML|YAML"):
                score += 2.0
            if self._stat("has_variables"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D45":
            score = 2.0
            if self._has_pattern(r"version|版本|v\d"):
                score += 4.0
            if self._has_pattern(r"变更.*日志|changelog|release.*note"):
                score += 2.0
            if self._has_pattern(r"语义版本|semver|兼容.*性"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D46":
            score = 2.0
            if self._has_pattern(r"quality.?gate|门禁|lint|score|评分"):
                score += 3.0
            if self._has_pattern(r"CI|github|workflow|pipeline"):
                score += 3.0
            if self._has_pattern(r"PASS|WARN|FAIL|阈值|threshold"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D47":
            score = 2.0
            if self._has_pattern(r"scan|安全扫描|injection|注入|PII|脱敏"):
                score += 4.0
            if self._has_pattern(r"合规|OWASP|compliance|GDPR"):
                score += 2.0
            if self._has_pattern(r"红队|redteam|probe|对抗"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D48":
            score = 2.0
            if self._stat("has_conditions"):
                score += 4.0
            if self._has_pattern(r"\{\{#if", r"\{\{/if\}\}"):
                score += 2.0
            if self._has_pattern(r"条件.*编译|compile|model"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D49":
            score = 2.0
            if self._has_pattern(r"测试|test|assert|验证|pytest|jest"):
                score += 3.0
            if self._has_pattern(r"dataset|数据集|用例|test.?case"):
                score += 3.0
            if self._has_pattern(r"覆盖.*率|coverage|边界.*测试|edge.?case"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D50":
            score = 2.0
            if self._has_pattern(r"---", r"```"):
                score += 4.0
            if self._stat("has_variables"):
                score += 2.0
            if self._has_pattern(r"front.?matter|元数据|metadata"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D51":
            score = 2.0
            if self._has_pattern(r"CI|CD|github|workflow|pipeline|jenkins"):
                score += 4.0
            if self._has_pattern(r"自动|automat|hook|trigger"):
                score += 2.0
            if self._has_pattern(r"SARIF|code.?scanning|质量.*报告"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D52":
            score = 2.0
            if self._has_pattern(r"监控|monitor|日志|log|metric|指标"):
                score += 4.0
            if self._has_pattern(r"告警|alert|阈值|threshold|通知"):
                score += 2.0
            if self._has_pattern(r"dashboard|仪表盘|grafana|prometheus"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D53":
            score = 2.0
            if self._has_pattern(r"lint_score|lint|代码质量"):
                score += 4.0
            if self._has_pattern(r"P\d{3}|规则|rule|check"):
                score += 2.0
            if self._has_pattern(r"自动修复|auto.?fix|fixer"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D54":
            score = 2.0
            if self._has_pattern(r"i18n|locale|translation|国际化|多语言"):
                score += 4.0
            if self._has_pattern(r"术语.*表|glossary|翻译.*一致"):
                score += 2.0
            if self._has_pattern(r"回退|fallback|默认.*语言"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D55":
            score = 2.0
            if self._has_pattern(r"provider|api_key|PROMPT_CLI_REAL_API|模型.*调用"):
                score += 4.0
            if self._has_pattern(r"重试|retry|超时|timeout|降级"):
                score += 2.0
            if self._has_pattern(r"负载均衡|load.?balanc|路由|routing"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D56":
            score = 2.0
            if self._has_pattern(r"compile|scan|lint|ab-test|redteam|serve"):
                score += 4.0
            if self._has_pattern(r"prompt-cli|CLI|命令行"):
                score += 2.0
            if self._has_pattern(r"MCP|JSON.?RPC|工具.*调用"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D57":
            score = 2.0
            if self._has_pattern(r"playground|/api/compile|WebSocket|交互"):
                score += 4.0
            if self._has_pattern(r"实时|real.?time|预览|preview"):
                score += 2.0
            if self._has_pattern(r"浏览器|browser|UI|可视化"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D58":
            score = 2.0
            if self._has_pattern(r"github|workflows|quality-gate|CI"):
                score += 4.0
            if self._has_pattern(r"SARIF|codeql|security.*scan"):
                score += 2.0
            if self._has_pattern(r"merge.*request|pull.*request|branch"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D59":
            score = 2.0
            if self._has_pattern(r"template_type|knowledge|prompt|模板"):
                score += 4.0
            if self._has_pattern(r"分类|category|标签|tag"):
                score += 2.0
            if self._has_pattern(r"版本.*管理|version.*manage|发布|publish"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D60":
            score = 2.0
            if self._has_pattern(r"market_status|i18n_status|lint_score|评分"):
                score += 4.0
            if self._has_pattern(r"趋势|trend|历史|history|对比"):
                score += 2.0
            if self._has_pattern(r"dashboard|面板|统计|statistic"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D61":
            score = 2.0
            if self._has_pattern(r"vscode|extension|CodeActions|插件"):
                score += 4.0
            if self._has_pattern(r"LSP|language.*server|诊断|diagnostic"):
                score += 2.0
            if self._has_pattern(r"语法高亮|syntax.*highlight|自动补全|autocomplete"):
                score += 2.0
            return min(score, 10.0)
        elif dim_id == "D62":
            score = 2.0
            if self._has_pattern(r"init|onboarding|引导|wizard|快速开始"):
                score += 4.0
            if self._has_pattern(r"doctor|健康.*检查|配置.*验证"):
                score += 2.0
            if self._has_pattern(r"示例|example|demo|教程|tutorial"):
                score += 2.0
            return min(score, 10.0)
        return 5.0

    def _eval_fairness(self, dim_id: str) -> float:
        if dim_id == "D63":
            score = 5.0
            bias_count = self._count_pattern(
                r"他/她|he/she|(?:男|女)(?:士|生|工|程序员|工程师|经理|CEO)",
                r"(?:必须|只能|不可以)(?:男|女|年轻|年长)",
                r"男人们|女人们|boys.*don.*t|girls.*can.*t",
                r"(?:只会|只会|天生)(?:男|女|黑|白)",
            )
            if bias_count > 0:
                score -= min(bias_count * 1.5, 4.0)
            neutral = self._has_pattern(r"所有人|不论性别|inclusive|diverse|平等|每个人|无论性别")
            if neutral:
                score += 3.0
            if self._has_pattern(r"避免.*偏见|避免.*歧视|bias.?free|non.?discriminat"):
                score += 2.0
            return max(1.0, min(score, 10.0))
        elif dim_id == "D64":
            score = 5.0
            offense = self._count_pattern(
                r"(?:所谓|那些)(?:人|国家|文化)",
                r"foreigner|alien|exotic",
                r"(?:低等|劣等|野蛮)(?:文化|种族|国家)",
                r"underdeveloped|third.?world|primitive",
            )
            if offense > 0:
                score -= min(offense * 1.5, 4.0)
            inclusive = self._has_pattern(r"多文化|跨文化|文化敏感|inclusive|culturally|尊重.*差异")
            if inclusive:
                score += 3.0
            if self._has_pattern(r"不同.*背景|多元|diversity|各.*文化"):
                score += 2.0
            return max(1.0, min(score, 10.0))
        elif dim_id == "D65":
            score = 3.0
            a11y = self._has_pattern(r"无障碍|accessible|alt|screen.reader|屏幕阅读器|语音")
            if a11y:
                score += 4.0
            if self._has_pattern(r"色盲|高对比|contrast|color.?blind|大字体|large.?text"):
                score += 2.0
            if self._has_pattern(r"aria|WCAG|readable|键盘.*导航|keyboard.*nav"):
                score += 1.0
            return min(score, 10.0)
        return 5.0

    def _eval_advanced_quality(self, dim_id: str) -> float:
        if dim_id == "D66":
            has_cot = self._has_pattern(r"逐步|step.?by.?step|推理链|chain.?of.?thought|思考过程|思维链|CoT")
            has_reasoning = self._has_pattern(r"推理|分析|判断|reasoning|analyze|逻辑|推断")
            if has_cot:
                return 9.0
            if has_reasoning:
                return 4.0
            return 7.0
        elif dim_id == "D67":
            has_tool_decl = self._has_pattern(r"工具|函数调用|function.?call|tool.?call|API|插件|plugin")
            has_tool_spec = self._has_pattern(r"参数|返回值|类型|格式|parameter|return.?type|schema")
            if has_tool_decl and has_tool_spec:
                return 9.0
            if has_tool_decl:
                return 5.0
            return 8.0
        elif dim_id == "D68":
            has_dialog = self._has_pattern(r"对话|聊天|多轮|conversation|chat|multi.?turn|会话")
            has_state = self._has_pattern(r"上下文|记忆|状态|context|memory|state|会话.*一致|session.*consistent")
            if has_dialog and has_state:
                return 9.0
            if has_dialog:
                return 4.0
            return 8.0
        elif dim_id == "D69":
            has_rag = self._has_pattern(r"上下文|检索|知识库|RAG|rag|检索增强|向量|embedding|context")
            has_rag_spec = self._has_pattern(r"引用|来源|置信度|citation|source|confidence|信息不足")
            if has_rag and has_rag_spec:
                return 9.0
            if has_rag:
                return 4.0
            return 8.0
        elif dim_id == "D70":
            has_cutoff = self._has_pattern(r"截止|cutoff|cut.?off|知识.*日期|训练.*日期|时效|timeliness|更新.*日期")
            if has_cutoff:
                return 9.0
            return 5.0
        elif dim_id == "D71":
            has_empathy = self._has_pattern(r"共情|理解|empathy|关心|情感|感受|温和|语气|tone")
            if has_empathy:
                return 9.0
            return 6.0
        elif dim_id == "D76":
            has_defense = self._has_pattern(r"注入.*防御|injection.*defense|校验|validate|sanitize|异常.*处理|鲁棒|robust")
            if has_defense:
                return 9.0
            has_adversarial = self._has_pattern(r"攻击|对抗|adversarial|red.?team|注入|inject")
            if has_adversarial:
                return 5.0
            return 7.0
        return 5.0

    def _eval_advanced_fairness(self, dim_id: str) -> float:
        if dim_id == "D72":
            has_ethics = self._has_pattern(r"伦理|道德|ethics|moral|有害|harmful|安全|safety|负责任|responsible")
            has_harm_decl = self._has_pattern(r"禁止.*有害|不得.*歧视|避免.*偏见|no.?harm|do.?no.?harm|公平|equitable")
            if has_ethics and has_harm_decl:
                return 9.0
            if has_ethics:
                return 6.0
            return 5.0
        elif dim_id == "D73":
            bias_count = self._count_pattern(
                r"显然|毋庸置疑|绝对|obviously|undoubtedly|absolutely",
                r"必须.*认为|一定.*正确|理所当然",
            )
            has_mitigation = self._has_pattern(r"客观|中立|多角度|objective|neutral|balanced|公平|equitable")
            if bias_count > 0 and not has_mitigation:
                return max(2.0, 4.0 - bias_count)
            if has_mitigation:
                return 9.0
            return 7.0
        return 5.0

    def _eval_advanced_security(self, dim_id: str) -> float:
        if dim_id == "D74":
            score = 3.0
            privacy_patterns = [
                (r"隐私|GDPR|gdpr|PIPL|个人信息|个人数据|privacy|data.?protection", 1.5),
                (r"合规|脱敏|匿名|consent|同意|最小.*收集|不.*存储|不.*传输", 1.5),
                (r"加密|encrypt|AES|RSA|TLS|SSL|KMS|密钥管理", 1.0),
                (r"数据分类|分级|sensitivity|classification|敏感.*级别", 1.0),
                (r"跨境|cross.?border|数据出境|transfer.*abroad|本地化|localization", 1.0),
                (r"被遗忘权|right.?to.?be.?forgotten|数据删除|data.?deletion|撤回.*同意", 1.0),
                (r"DPIA|隐私影响评估|PIA|privacy.?impact|data.?protection.?impact", 1.0),
                (r"数据最小化|data.?minimization|必要.*收集|purpose.?limitation", 1.0),
            ]
            for pattern, weight in privacy_patterns:
                if self._has_pattern(pattern):
                    score += weight
            return min(score, 10.0)
        elif dim_id == "D75":
            score = 3.0
            audit_patterns = [
                (r"审计|audit|追溯|trace|日志|log", 1.5),
                (r"决策.*依据|reasoning.?process|explain|可解释|interpretability", 1.5),
                (r"版本|version|变更|changelog|diff|历史", 1.0),
                (r"签名|signature|哈希|hash|不可篡改|immutable|tamper.?proof", 1.0),
                (r"SIEM|安全.*事件|event.*management|告警|alert|通知|notification", 1.0),
                (r"保留.*期限|retention.*period|归档|archive|销毁|destroy", 1.0),
                (r"链路.*追踪|tracing|span|trace.?id|correlation.?id", 1.0),
            ]
            for pattern, weight in audit_patterns:
                if self._has_pattern(pattern):
                    score += weight
            return min(score, 10.0)
        return 5.0

    def _eval_advanced_structure(self, dim_id: str) -> float:
        if dim_id == "D77":
            score = 3.0
            structure_patterns = [
                (r"---|模块|##|section|组件|component|变量|variable", 1.5),
                (r"版本|version|v\d|变更|changelog", 1.0),
                (r"输入|input|输出|output|接口|interface|API|参数|parameter", 1.0),
                (r"配置|config|环境|environment|profile|setting", 1.0),
                (r"测试|test|验证|verify|校验|validate|assert", 1.0),
                (r"错误处理|error.?handling|异常|exception|fallback|降级|degrade", 1.0),
                (r"依赖|dependency|import|require|引用|reference", 0.5),
                (r"文档|doc|注释|comment|说明|readme|README", 0.5),
            ]
            sections = self._text.count("##") + self._text.count("---") + self._text.count("===")
            if sections >= 5:
                score += 1.0
            elif sections >= 3:
                score += 0.5
            for pattern, weight in structure_patterns:
                if self._has_pattern(pattern):
                    score += weight
            return min(score, 10.0)
        return 5.0

    def _eval_advanced_toolchain(self, dim_id: str) -> float:
        if dim_id == "D78":
            has_i18n = self._has_pattern(r"i18n|国际化|多语言|locale|翻译|translate|lang|语言")
            has_glossary = self._has_pattern(r"术语|glossary|术语表|翻译.*一致性|translation.*consistency")
            if has_i18n and has_glossary:
                return 9.0
            if has_i18n:
                return 6.0
            return 5.0
        elif dim_id == "D79":
            has_pangu = self._has_pattern(r"盘古|Pangu|pangu|华为云.*模型|MaaS|ModelArts|昇腾|Ascend")
            has_pangu_spec = self._has_pattern(r"盘古.*格式|Pangu.*format|MaaS.*API|system.*role|Function.?Calling|安全护栏")
            if has_pangu and has_pangu_spec:
                return 9.0
            if has_pangu:
                return 5.0
            return 7.0
        elif dim_id == "D80":
            has_harmony = self._has_pattern(r"鸿蒙|HarmonyOS|harmonyos|ArkTS|arkts|Stage模型|Ability|OHOS|元服务")
            has_harmony_spec = self._has_pattern(r"ArkTS.*严格|onCreate|onDestroy|ohos\.permission|断点|响应式|沙箱|DataShare|FormExtension|HTTPS|ohos\.net")
            if has_harmony and has_harmony_spec:
                return 9.0
            if has_harmony:
                return 5.0
            return 7.0
        return 5.0


def evaluate_template(
    template_id: str,
    text: str,
    *,
    dimensions: list[str] | None = None,
    categories: list[str] | None = None,
) -> EvaluationReport:
    """80维度模板评估函数。

    Args:
        template_id: 模板标识。
        text: 模板文本。
        dimensions: 指定评估的维度ID列表（None=全部），ID格式为"D01"-"D80"。
                    也接受"D1"-"D9"格式（自动补零为"D01"-"D09"）。
        categories: 指定评估的维度类别（None=全部）。

    Returns:
        EvaluationReport 评估报告。
    """
    start = time.perf_counter()

    dims = list(_DIMENSIONS)
    if dimensions:
        normalized = set()
        for d in dimensions:
            if d.startswith("D") and len(d) == 2 and d[1].isdigit():
                normalized.add(f"D0{d[1]}")
            else:
                normalized.add(d)
        dims = [d for d in dims if d["id"] in normalized]
    if categories:
        cat_set = set(categories)
        dims = [d for d in dims if d["category"] in cat_set]

    evaluator = _DimensionEvaluator(text)
    scores = [evaluator.evaluate(d) for d in dims]

    overall = sum(s.weighted_score for s in scores)
    max_possible = sum(d["weight"] for d in dims)
    percentage = (overall / max_possible * 100) if max_possible > 0 else 0.0

    category_scores: dict[str, float] = {}
    category_weights: dict[str, float] = {}
    for s in scores:
        category_scores[s.category] = category_scores.get(s.category, 0.0) + s.weighted_score
        category_weights[s.category] = category_weights.get(s.category, 0.0) + s.weight
    for cat in category_scores:
        if category_weights[cat] > 0:
            category_scores[cat] = category_scores[cat] / category_weights[cat] * 10.0

    findings: list[Finding] = []
    for s in scores:
        if s.score < _LOW_SCORE_THRESHOLD:
            findings.append(
                Finding(
                    rule_id=f"EVAL-{s.dimension_id}",
                    severity=Severity.HIGH if s.score < _VERY_LOW_SCORE_THRESHOLD else Severity.MEDIUM,
                    description=f"维度 {s.name}({s.dimension_id}) 评分偏低: {s.score}/{s.max_score}",
                    remediation=f"建议优化 {s.name} 相关内容",
                )
            )

    elapsed = (time.perf_counter() - start) * 1000

    return EvaluationReport(
        template_id=template_id,
        scores=scores,
        overall_score=overall,
        max_possible_score=max_possible,
        percentage=round(percentage, 2),
        category_scores=category_scores,
        findings=findings,
        evaluation_time_ms=elapsed,
        dimension_count=len(scores),
    )


def get_all_dimensions() -> list[dict[str, Any]]:
    """获取全部80个维度定义。"""
    return list(_DIMENSIONS)


def get_dimensions_by_category(category: str) -> list[dict[str, Any]]:
    """按类别获取维度。"""
    return [d for d in _DIMENSIONS if d["category"] == category]
