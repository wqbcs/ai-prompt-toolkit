"""TextGrad文本梯度优化器 — 参考TextGrad Nature 2025

核心特性:
- TextualVariable: 可追踪"文本梯度"的Prompt变量
- TextualGradient: LLM反馈构成的文本梯度(批评+建议)
- TGDOptimizer: 文本梯度下降优化器
- 反向传播链: Variable -> Gradient -> Apply -> New Variable
- 不依赖LLM API: 使用内置评估函数作为梯度源

参考: TextGrad (Stanford Zou Group, Nature 2025)
- 核心思想: LLM反馈=文本梯度, 沿梯度反方向编辑Prompt
- Variable对象追踪梯度, TGD优化器执行梯度下降
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TextualGradient:
    criticism: str = ""
    suggestion: str = ""
    direction: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "criticism": self.criticism,
            "suggestion": self.suggestion,
            "direction": self.direction,
            "source": self.source,
        }


class TextualVariable:
    def __init__(self, value: str, role_description: str = "") -> None:
        self.value = value
        self.role_description = role_description
        self.gradients: list[TextualGradient] = []
        self._history: list[tuple[str, float]] = [(value, 0.0)]

    def add_gradient(self, gradient: TextualGradient) -> None:
        self.gradients.append(gradient)

    def apply_gradients(self) -> str:
        if not self.gradients:
            return self.value

        combined_criticism = "\n".join(
            f"- {g.criticism}" for g in self.gradients if g.criticism
        )
        combined_suggestion = "\n".join(
            f"- {g.suggestion}" for g in self.gradients if g.suggestion
        )

        new_value = _apply_textual_gradient(self.value, combined_criticism, combined_suggestion)
        self.value = new_value
        self.gradients = []
        return new_value

    def record_score(self, score: float) -> None:
        self._history.append((self.value, score))

    @property
    def best_version(self) -> tuple[str, float]:
        return max(self._history, key=lambda x: x[1])

    @property
    def score_history(self) -> list[float]:
        return [s for _, s in self._history]

    def to_dict(self) -> dict[str, Any]:
        return {
            "value_length": len(self.value),
            "role_description": self.role_description,
            "gradient_count": len(self.gradients),
            "history_count": len(self._history),
            "best_score": self.best_version[1],
        }


def _apply_textual_gradient(
    current_text: str,
    criticism: str,
    suggestion: str,
) -> str:
    result = current_text

    if criticism:
        lines = criticism.strip().split("\n")
        for line in lines:
            line = line.strip().lstrip("- ").strip()
            if not line:
                continue
            problematic_phrases = _extract_problematic_phrase(line)
            for phrase in problematic_phrases:
                if phrase in result:
                    result = result.replace(phrase, "", 1)

    if suggestion:
        suggestions = [s.strip().lstrip("- ").strip() for s in suggestion.strip().split("\n") if s.strip()]
        if suggestions:
            improvement_block = "\n\n" + "\n".join(f"- {s}" for s in suggestions[:3])
            result += improvement_block

    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _extract_problematic_phrase(criticism_line: str) -> list[str]:
    patterns = [
        r'[「"『](.*?)[」"』]',
        r"\"(.*?)\"",
        r"'(.*?)'",
    ]
    phrases = []
    for pattern in patterns:
        matches = re.findall(pattern, criticism_line)
        phrases.extend(matches)
    return [p for p in phrases if len(p) > 2]


@dataclass
class TGDConfig:
    max_iterations: int = 10
    learning_rate: float = 1.0
    momentum: float = 0.9
    convergence_threshold: float = 0.5
    gradient_source: str = "auto"
    verbose: bool = False


@dataclass
class TGDResult:
    initial_text: str = ""
    optimized_text: str = ""
    initial_score: float = 0.0
    final_score: float = 0.0
    improvement: float = 0.0
    iterations: int = 0
    converged: bool = False
    gradient_history: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_score": round(self.initial_score, 2),
            "final_score": round(self.final_score, 2),
            "improvement": round(self.improvement, 2),
            "iterations": self.iterations,
            "converged": self.converged,
            "gradient_count": len(self.gradient_history),
            "elapsed_ms": round(self.elapsed_ms, 0),
        }


class TGDOptimizer:
    def __init__(self, config: TGDConfig | None = None) -> None:
        self.config = config or TGDConfig()
        self._momentum_buffer: TextualGradient | None = None

    def optimize(
        self,
        prompt: str,
        eval_fn: Callable[[str], float] | None = None,
        gradient_fn: Callable[[str, float], TextualGradient] | None = None,
    ) -> TGDResult:
        start_time = time.time()

        if eval_fn is None:
            eval_fn = _default_eval_fn
        if gradient_fn is None:
            gradient_fn = _default_gradient_fn

        variable = TextualVariable(
            value=prompt,
            role_description="prompt to optimize",
        )

        current_score = eval_fn(prompt)
        variable.record_score(current_score)

        result = TGDResult(
            initial_text=prompt,
            initial_score=current_score,
        )

        prev_score = current_score

        for iteration in range(self.config.max_iterations):
            gradient = gradient_fn(variable.value, current_score)

            if self._momentum_buffer and self.config.momentum > 0:
                gradient = self._apply_momentum(gradient, self._momentum_buffer)
            self._momentum_buffer = gradient

            variable.add_gradient(gradient)
            variable.apply_gradients()

            new_score = eval_fn(variable.value)
            variable.record_score(new_score)

            improvement = new_score - prev_score

            result.gradient_history.append({
                "iteration": iteration + 1,
                "gradient": gradient.to_dict(),
                "score": round(new_score, 2),
                "improvement": round(improvement, 2),
            })

            if self.config.verbose:
                logger.info(
                    "TGD iter %d: score %.2f → %.2f (%+.2f)",
                    iteration + 1, prev_score, new_score, improvement,
                )

            if abs(improvement) < self.config.convergence_threshold and iteration > 0:
                result.converged = True
                if new_score < prev_score:
                    variable.value, _ = variable.best_version
                    new_score = variable.best_version[1]
                break

            if new_score < prev_score and self.config.learning_rate > 0:
                variable.value, new_score = variable.best_version

            prev_score = new_score

        best_text, best_score = variable.best_version

        result.optimized_text = best_text
        result.final_score = best_score
        result.improvement = best_score - current_score
        result.iterations = len(result.gradient_history)
        result.elapsed_ms = (time.time() - start_time) * 1000

        return result

    def _apply_momentum(self, current: TextualGradient, previous: TextualGradient) -> TextualGradient:
        m = self.config.momentum
        return TextualGradient(
            criticism=current.criticism,
            suggestion=(
                f"{current.suggestion}\n{previous.suggestion}"
                if current.suggestion and previous.suggestion
                else current.suggestion or previous.suggestion
            ),
            direction=current.direction,
            source="momentum_tgd",
        )


def _default_eval_fn(text: str) -> float:
    try:
        from ai_prompt_toolkit.linter.linter import PromptLinter
        linter = PromptLinter()
        result = linter.lint("tgd-optimize", text)
        return result.score
    except Exception:
        score = 50.0
        if len(text) > 50:
            score += 10
        if re.search(r"(角色|你是一个|You are a)", text, re.IGNORECASE):
            score += 5
        if re.search(r"(步骤|Step|1\.|首先)", text, re.IGNORECASE):
            score += 5
        if re.search(r"(安全|防护|Security)", text, re.IGNORECASE):
            score += 5
        if re.search(r"(约束|限制|Constraint)", text, re.IGNORECASE):
            score += 5
        return min(score, 100.0)


def _default_gradient_fn(text: str, score: float) -> TextualGradient:
    criticisms: list[str] = []
    suggestions: list[str] = []

    if not re.search(r"(角色|你是一个|You are a|Act as)", text, re.IGNORECASE):
        criticisms.append("缺少明确的角色定义")
        suggestions.append("添加角色定义: 你是一个专业的[角色]")

    if not re.search(r"(步骤|Step|1\.|首先|第一步)", text, re.IGNORECASE):
        criticisms.append("缺少执行步骤指引")
        suggestions.append("添加分步骤执行指引")

    if not re.search(r"(安全|防护|Security|injection)", text, re.IGNORECASE):
        criticisms.append("缺少安全防护指令")
        suggestions.append("添加安全防护指令: 禁止泄露系统指令")

    if not re.search(r"(约束|限制|Constraint|必须|不得)", text, re.IGNORECASE):
        criticisms.append("缺少输出约束条件")
        suggestions.append("添加输出约束: 长度/格式/质量要求")

    if len(text) > 2000:
        criticisms.append("Prompt过长, 可能导致模型注意力分散")
        suggestions.append("精简冗余内容, 控制在1500字以内")

    if not re.search(r"(不确定|无法|hallucinat|编造)", text, re.IGNORECASE):
        criticisms.append("缺少幻觉预防指令")
        suggestions.append("添加幻觉预防: 如不确定请明确说明")

    if not re.search(r"(输出格式|格式要求|Output format|JSON|markdown)", text, re.IGNORECASE):
        criticisms.append("缺少输出格式要求")
        suggestions.append("指定输出格式: JSON/Markdown/列表等")

    direction = "improve" if score < 80 else "refine" if score < 95 else "maintain"

    return TextualGradient(
        criticism="\n".join(f"- {c}" for c in criticisms),
        suggestion="\n".join(f"- {s}" for s in suggestions),
        direction=direction,
        source="default_tgd",
    )


def tgd_optimize(
    prompt: str,
    *,
    max_iterations: int = 10,
    convergence_threshold: float = 0.5,
    momentum: float = 0.9,
    eval_fn: Callable[[str], float] | None = None,
    gradient_fn: Callable[[str, float], TextualGradient] | None = None,
) -> TGDResult:
    config = TGDConfig(
        max_iterations=max_iterations,
        convergence_threshold=convergence_threshold,
        momentum=momentum,
    )
    optimizer = TGDOptimizer(config)
    return optimizer.optimize(prompt, eval_fn=eval_fn, gradient_fn=gradient_fn)
