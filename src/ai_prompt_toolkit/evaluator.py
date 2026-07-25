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
            return 8.0 if self._has_pattern(r"你(?:是|作为|扮演)", r"you\s+are", r"role[:：]") else 2.0
        elif dim_id == "D02":
            return 8.0 if self._has_pattern(r"请|帮我|要求|must|should|need") else 3.0
        elif dim_id == "D03":
            return 9.0 if self._has_pattern(r"输出(?:格式|为)|JSON|Markdown|format|output\s+as") else 2.0
        elif dim_id == "D04":
            count = self._count_pattern(r"不要|不可|禁止|must\s+not|do\s+not|never|限制")
            return min(10.0, 3.0 + count * 1.5)
        elif dim_id == "D05":
            return min(10.0, 3.0 + length / 200.0)
        elif dim_id == "D06":
            ambiguous = self._count_pattern(r"可能|大概|也许|maybe|perhaps|possibly|差不多")
            return max(1.0, 10.0 - ambiguous * 2.0)
        elif dim_id == "D07":
            has_positive = self._has_pattern(r"要|必须|需要|should|must")
            has_negative = self._has_pattern(r"不要|禁止|must\s+not|never")
            if has_positive and has_negative:
                return 10.0
            return 5.0
        elif dim_id == "D08":
            headers = self._count_pattern(r"^#+\s", r"^\d+\.\s", r"^-\s")
            return min(10.0, 2.0 + headers * 1.0)
        elif dim_id == "D09":
            return 8.0 if self._has_pattern(r"version|版本|v\d+") else 2.0
        elif dim_id == "D10":
            return min(10.0, 3.0 + (1.0 if length < 2000 else 0.0) + (2.0 if self._has_pattern(r"---") else 0.0))
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
            has_escape = self._has_pattern(r"转义|escape|sanitize|校验")
            has_user_input = self._has_pattern(r"\{\{.*?user.*?\}\}", r"\$\{")
            if has_user_input and has_escape:
                return 8.0
            if has_user_input:
                return 3.0
            return 7.0
        elif dim_id == "D12":
            sensitive = self._count_pattern(r"api[_-]?key|password|secret|token")
            return max(1.0, 10.0 - sensitive * 3.0)
        elif dim_id == "D13":
            broad = self._has_pattern(r"任何|任意|anything|everything")
            return 3.0 if broad else 8.0
        elif dim_id == "D14":
            return 7.0 if self._has_pattern(r"验证|校验|validate|check") else 3.0
        elif dim_id == "D15":
            return 7.0 if self._has_pattern(r"过滤|filter|排除|exclude") else 4.0
        elif dim_id == "D16":
            return 8.0 if self._has_pattern(r"审计|audit|日志|log") else 2.0
        elif dim_id == "D17":
            return 8.0 if self._has_pattern(r"如果.*失败|回退|fallback|otherwise") else 3.0
        elif dim_id == "D18":
            return 7.0 if self._has_pattern(r"隔离|isolate|sandbox|沙箱") else 4.0
        elif dim_id == "D19":
            return 7.0 if self._has_pattern(r"合规|compliance|GDPR|隐私") else 4.0
        elif dim_id == "D20":
            return 8.0 if self._has_pattern(r"脱敏|mask|redact|匿名") else 3.0
        return 5.0

    def _eval_performance(self, dim_id: str, length: int) -> float:
        if dim_id == "D21":
            if length < 500:
                return 9.0
            if length < 2000:
                return 6.0
            return 3.0
        elif dim_id == "D22":
            has_concise = self._has_pattern(r"简洁|简短|不超过|精简|concise|brief")
            has_no_redundancy = self._count_pattern(r"等等|之类的|可能|大概|应该|尽量") < 3
            score = 4.0
            if length < 1000:
                score += 2.0
            if has_concise:
                score += 2.0
            if has_no_redundancy:
                score += 1.0
            return min(10.0, score)
        elif dim_id == "D23":
            return 7.0 if self._has_pattern(r"---", r"version") else 4.0
        elif dim_id == "D24":
            return 6.0 if self._has_pattern(r"批量|batch|循环|loop") else 4.0
        elif dim_id == "D25":
            has_stateless = self._has_pattern(r"无状态|stateless|幂等|idempotent")
            no_global_var = self._count_pattern(r"全局|global|共享变量") == 0
            score = 5.0
            if has_stateless:
                score += 3.0
            if no_global_var:
                score += 2.0
            return min(10.0, score)
        elif dim_id == "D26":
            has_structure = self._count_pattern(r"^#+\s") >= 2
            has_sequential = self._has_pattern(r"首先|然后|接着|最后|第一步|step")
            score = 4.0
            if has_structure:
                score += 3.0
            if has_sequential:
                score += 2.0
            return min(10.0, score)
        elif dim_id == "D27":
            return 8.0 if length < 800 else 5.0
        elif dim_id == "D28":
            return 7.0 if self._has_pattern(r"{{#if", r"model") else 5.0
        elif dim_id == "D29":
            return 6.0 if length < 500 else 4.0
        elif dim_id == "D30":
            has_idempotent = self._has_pattern(r"幂等|idempotent|无状态|stateless")
            has_same_result = self._has_pattern(r"相同结果|same result|一致|consistent")
            score = 5.0
            if has_idempotent:
                score += 3.0
            if has_same_result:
                score += 2.0
            return min(10.0, score)
        return 5.0

    def _eval_quality(self, dim_id: str) -> float:
        if dim_id == "D31":
            return 8.0 if self._has_pattern(r"示例|example|如：|如下|e\.g\.") else 3.0
        elif dim_id == "D32":
            return 8.0 if self._has_pattern(r"一步步|逐步|step\s+by\s+step|CoT|推理链") else 3.0
        elif dim_id == "D33":
            return 7.0 if self._has_pattern(r"如果.*失败|错误|异常|error|exception") else 3.0
        elif dim_id == "D34":
            return 7.0 if self._has_pattern(r"边界|极限|最大|最小|boundary|edge") else 3.0
        elif dim_id == "D35":
            return 8.0 if self._has_pattern(r"中文|英文|English|language|语言") else 4.0
        elif dim_id == "D36":
            return 6.0 if self._has_pattern(r"文化|习惯|地区|region") else 3.0
        elif dim_id == "D37":
            return 7.0 if self._has_pattern(r"原因|理由|为什么|why|reason") else 4.0
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
            return 7.0 if self._has_pattern(r"请|帮我") else 4.0
        return 5.0

    def _eval_toolchain(self, dim_id: str) -> float:
        if dim_id == "D41":
            has_import = self._has_pattern(r"import|from|require|依赖")
            has_api_ref = self._has_pattern(r"API|SDK|\.py|\.ts|\.js|\.go")
            score = 4.0
            if has_import:
                score += 3.0
            if has_api_ref:
                score += 3.0
            return min(10.0, score)
        elif dim_id == "D42":
            has_endpoint = self._has_pattern(r"https?://|endpoint|API|api_key|url")
            has_provider = self._has_pattern(r"provider|openai|claude|qwen|pangu|deepseek")
            score = 3.0
            if has_endpoint:
                score += 3.0
            if has_provider:
                score += 4.0
            return min(10.0, score)
        elif dim_id == "D43":
            return 7.0 if self._has_pattern(r"依赖|require|import") else 4.0
        elif dim_id == "D44":
            return 8.0 if self._has_pattern(r"ENV|environment|环境变量") else 4.0
        elif dim_id == "D45":
            return 7.0 if self._has_pattern(r"version|版本|v\d") else 3.0
        elif dim_id == "D46":
            has_gate = self._has_pattern(r"quality.?gate|门禁|lint|score|评分")
            has_ci = self._has_pattern(r"CI|github|workflow|pipeline")
            score = 4.0
            if has_gate:
                score += 3.0
            if has_ci:
                score += 3.0
            return min(10.0, score)
        elif dim_id == "D47":
            has_scan = self._has_pattern(r"scan|安全扫描|injection|注入|PII|脱敏")
            has_compliance = self._has_pattern(r"合规|OWASP|compliance|GDPR")
            score = 3.0
            if has_scan:
                score += 4.0
            if has_compliance:
                score += 3.0
            return min(10.0, score)
        elif dim_id == "D48":
            return 7.0 if self._has_pattern(r"{{#if", r"{{/if}}") else 5.0
        elif dim_id == "D49":
            has_test_ref = self._has_pattern(r"测试|test|assert|验证|pytest|jest")
            has_dataset = self._has_pattern(r"dataset|数据集|用例|test.?case")
            score = 3.0
            if has_test_ref:
                score += 4.0
            if has_dataset:
                score += 3.0
            return min(10.0, score)
        elif dim_id == "D50":
            return 7.0 if self._has_pattern(r"---", r"```") else 3.0
        elif dim_id == "D51":
            has_ci = self._has_pattern(r"CI|CD|github|workflow|pipeline|jenkins")
            has_auto = self._has_pattern(r"自动|automat|hook|trigger|trigger")
            score = 3.0
            if has_ci:
                score += 4.0
            if has_auto:
                score += 3.0
            return min(10.0, score)
        elif dim_id == "D52":
            has_monitor = self._has_pattern(r"监控|monitor|日志|log|metric|指标")
            has_alert = self._has_pattern(r"告警|alert|阈值|threshold|通知")
            score = 3.0
            if has_monitor:
                score += 4.0
            if has_alert:
                score += 3.0
            return min(10.0, score)
        elif dim_id == "D53":
            return 8.0 if self._has_pattern(r"lint_score|lint") else 3.0
        elif dim_id == "D54":
            return 8.0 if self._has_pattern(r"i18n_status|locale|translation") else 3.0
        elif dim_id == "D55":
            return 8.0 if self._has_pattern(r"provider|api_key|PROMPT_CLI_REAL_API") else 3.0
        elif dim_id == "D56":
            return 7.0 if self._has_pattern(r"compile|scan|lint|ab-test|redteam|serve") else 3.0
        elif dim_id == "D57":
            return 7.0 if self._has_pattern(r"playground|/api/compile|WebSocket") else 3.0
        elif dim_id == "D58":
            return 7.0 if self._has_pattern(r"github|workflows|quality-gate|CI") else 3.0
        elif dim_id == "D59":
            return 8.0 if self._has_pattern(r"template_type|knowledge|prompt") else 4.0
        elif dim_id == "D60":
            return 8.0 if self._has_pattern(r"market_status|i18n_status|lint_score") else 3.0
        elif dim_id == "D61":
            return 7.0 if self._has_pattern(r"vscode|extension|CodeActions") else 3.0
        elif dim_id == "D62":
            return 7.0 if self._has_pattern(r"init|onboarding|引导") else 3.0
        return 5.0

    def _eval_fairness(self, dim_id: str) -> float:
        if dim_id == "D63":
            bias_count = self._count_pattern(
                r"他/她|he/she|(?:男|女)(?:士|生|工|程序员|工程师|经理|CEO)",
                r"(?:必须|只能|不可以)(?:男|女|年轻|年长)",
            )
            if bias_count > 0:
                return max(2.0, 5.0 - bias_count * 1.0)
            neutral = self._has_pattern(r"所有人|不论性别|inclusive|diverse|平等")
            return 9.0 if neutral else 7.0
        elif dim_id == "D64":
            offense = self._count_pattern(
                r"(?:所谓|那些)(?:人|国家|文化)",
                r"foreigner|alien|exotic",
            )
            if offense > 0:
                return max(2.0, 4.0 - offense * 1.0)
            inclusive = self._has_pattern(r"多文化|跨文化|文化敏感|inclusive|culturally")
            return 9.0 if inclusive else 7.0
        elif dim_id == "D65":
            a11y = self._has_pattern(r"无障碍|accessible|alt|screen.reader|屏幕阅读器|语音")
            if a11y:
                return 9.0
            return 6.0
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
    """获取全部62个维度定义。"""
    return list(_DIMENSIONS)


def get_dimensions_by_category(category: str) -> list[dict[str, Any]]:
    """按类别获取维度。"""
    return [d for d in _DIMENSIONS if d["category"] == category]
