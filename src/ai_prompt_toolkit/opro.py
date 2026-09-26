"""OPRO元Prompt优化器 — 参考Google DeepMind OPRO

核心特性:
- LLM-as-Optimizer: LLM本身作为Prompt优化器
- 元Prompt: 包含历史指令+准确率, LLM据此生成新指令
- 迭代优化: 每轮从top-k候选中采样, 生成新候选
- 收敛检测: 连续N轮无改进则停止

参考: OPRO (Google DeepMind, 2023)
- Optimization by PROmpting
- GSM8K提升8%, Big-Bench Hard提升50%
- 核心思想: 元Prompt = 任务描述 + 历史最优解 + 得分 → LLM生成新解

注意: 本实现不依赖LLM API调用, 使用规则化元Prompt+评估驱动
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class OPROCandidate:
    instruction: str = ""
    score: float = 0.0
    generation: int = 0
    parent: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction_length": len(self.instruction),
            "score": round(self.score, 2),
            "generation": self.generation,
        }


@dataclass
class OPROConfig:
    max_generations: int = 8
    population_size: int = 5
    top_k: int = 3
    convergence_rounds: int = 3
    mutation_strategies: list[str] = field(
        default_factory=lambda: [
            "rephrase",
            "elaborate",
            "simplify",
            "restructure",
            "specialize",
        ]
    )
    seed: int = 42


@dataclass
class OPROResult:
    initial_instruction: str = ""
    best_instruction: str = ""
    initial_score: float = 0.0
    best_score: float = 0.0
    improvement: float = 0.0
    generations: int = 0
    converged: bool = False
    candidates_explored: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_score": round(self.initial_score, 2),
            "best_score": round(self.best_score, 2),
            "improvement": round(self.improvement, 2),
            "generations": self.generations,
            "converged": self.converged,
            "candidates_explored": self.candidates_explored,
            "elapsed_ms": round(self.elapsed_ms, 0),
        }


class OPROOptimizer:
    def __init__(self, config: OPROConfig | None = None) -> None:
        self.config = config or OPROConfig()
        self._rng = random.Random(self.config.seed)

    def optimize(
        self,
        instruction: str,
        eval_fn: Callable[[str], float] | None = None,
    ) -> OPROResult:
        start_time = time.time()

        if eval_fn is None:
            eval_fn = _opro_default_eval_fn

        initial_score = eval_fn(instruction)

        population: list[OPROCandidate] = [
            OPROCandidate(instruction=instruction, score=initial_score, generation=0),
        ]

        result = OPROResult(
            initial_instruction=instruction,
            initial_score=initial_score,
        )

        no_improvement_count = 0
        best_score = initial_score

        for gen in range(1, self.config.max_generations + 1):
            top_k = sorted(population, key=lambda c: c.score, reverse=True)[: self.config.top_k]

            meta_prompt = self._build_meta_prompt(top_k, instruction)

            new_candidates = self._generate_candidates(meta_prompt, top_k, gen, eval_fn)

            population.extend(new_candidates)
            population = sorted(population, key=lambda c: c.score, reverse=True)[: self.config.population_size * 3]

            gen_best = population[0].score

            result.history.append(
                {
                    "generation": gen,
                    "best_score": round(gen_best, 2),
                    "new_candidates": len(new_candidates),
                    "population_size": len(population),
                }
            )

            if gen_best > best_score:
                best_score = gen_best
                no_improvement_count = 0
            else:
                no_improvement_count += 1

            if no_improvement_count >= self.config.convergence_rounds:
                result.converged = True
                break

        best = max(population, key=lambda c: c.score)

        result.best_instruction = best.instruction
        result.best_score = best.score
        result.improvement = best.score - initial_score
        result.generations = len(result.history)
        result.candidates_explored = sum(h["new_candidates"] for h in result.history) + 1
        result.elapsed_ms = (time.time() - start_time) * 1000

        return result

    def _build_meta_prompt(self, top_k: list[OPROCandidate], original: str) -> str:
        lines = [
            "## Prompt优化任务",
            "",
            "原始指令:",
            f"```\n{original}\n```",
            "",
            "## 历史最优候选指令 (按得分排序):",
            "",
        ]
        for i, cand in enumerate(top_k, 1):
            lines.append(f"### 候选{i} (得分: {cand.score:.1f}/100)")
            lines.append(f"```\n{cand.instruction}\n```")
            lines.append("")

        lines.extend(
            [
                "## 任务要求",
                "基于以上历史候选指令及其得分，生成一条新的优化指令。",
                "新指令应该:",
                "1. 继承高分候选的优点",
                "2. 改进低分候选的不足",
                "3. 尝试新的表达方式和结构",
            ]
        )

        return "\n".join(lines)

    def _generate_candidates(
        self,
        meta_prompt: str,
        top_k: list[OPROCandidate],
        generation: int,
        eval_fn: Callable[[str], float],
    ) -> list[OPROCandidate]:
        candidates: list[OPROCandidate] = []

        for strategy in self.config.mutation_strategies:
            parent = top_k[self._rng.randint(0, len(top_k) - 1)]
            new_instruction = self._mutate(parent.instruction, strategy)
            score = eval_fn(new_instruction)

            candidates.append(
                OPROCandidate(
                    instruction=new_instruction,
                    score=score,
                    generation=generation,
                    parent=parent.instruction[:50],
                )
            )

        return candidates

    def _mutate(self, instruction: str, strategy: str) -> str:
        if strategy == "rephrase":
            return _mutate_rephrase(instruction, self._rng)
        elif strategy == "elaborate":
            return _mutate_elaborate(instruction, self._rng)
        elif strategy == "simplify":
            return _mutate_simplify(instruction, self._rng)
        elif strategy == "restructure":
            return _mutate_restructure(instruction, self._rng)
        elif strategy == "specialize":
            return _mutate_specialize(instruction, self._rng)
        return instruction


def _mutate_rephrase(text: str, rng: random.Random) -> str:
    rephrasings = {
        "你是一个": "作为",
        "请": "务必",
        "必须": "确保",
        "注意": "重要提示",
        "不要": "禁止",
        "如果": "当",
        "输出": "返回",
        "分析": "深入分析",
    }
    result = text
    for old, new in rephrasings.items():
        if old in result and rng.random() > 0.5:
            result = result.replace(old, new, 1)
            break
    return result


def _mutate_elaborate(text: str, rng: random.Random) -> str:
    elaborations = [
        "\n\n请确保你的回答具有以下特质：准确性、完整性、清晰性。",
        "\n\n执行标准：专业级输出，符合行业最佳实践。",
        "\n\n质量控制：自我检查输出是否符合所有要求，如有不符请修正。",
        "\n\n注意事项：在关键决策点进行推理验证，确保逻辑一致性。",
    ]
    return text + rng.choice(elaborations)


def _mutate_simplify(text: str, rng: random.Random) -> str:
    sentences = text.split("。")
    if len(sentences) > 5:
        keep = rng.randint(3, len(sentences) - 1)
        selected = sentences[:keep]
        return "。".join(selected)
    return text


def _mutate_restructure(text: str, rng: random.Random) -> str:
    parts = text.split("\n\n")
    if len(parts) > 2:
        rng.shuffle(parts)
        return "\n\n".join(parts)
    return text


def _mutate_specialize(text: str, rng: random.Random) -> str:
    specializations = [
        ("专业", "在【专业场景】中"),
        ("任务", "针对具体业务任务"),
        ("回答", "提供结构化专业回答"),
        ("帮助", "以专家身份协助"),
    ]
    for old, new in specializations:
        if old in text and rng.random() > 0.5:
            return text.replace(old, new, 1)
    return text


def _opro_default_eval_fn(text: str) -> float:
    try:
        from ai_prompt_toolkit.linter.linter import PromptLinter

        linter = PromptLinter()
        result = linter.lint("opro-optimize", text)
        return result.score
    except Exception:
        from ai_prompt_toolkit.textgrad import _default_eval_fn

        return _default_eval_fn(text)


def opro_optimize(
    instruction: str,
    *,
    max_generations: int = 8,
    population_size: int = 5,
    top_k: int = 3,
    convergence_rounds: int = 3,
    eval_fn: Callable[[str], float] | None = None,
) -> OPROResult:
    config = OPROConfig(
        max_generations=max_generations,
        population_size=population_size,
        top_k=top_k,
        convergence_rounds=convergence_rounds,
    )
    optimizer = OPROOptimizer(config)
    return optimizer.optimize(instruction, eval_fn=eval_fn)
