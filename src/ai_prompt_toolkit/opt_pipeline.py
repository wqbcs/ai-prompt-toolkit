"""统一优化管线Pipeline — 参考AdalFlow Trainer+Agent Lightning LightningStore

核心特性:
- OptPipeline: 统一优化管线, 串联/并联多种优化器
- PipelineStage: 管线阶段(优化器+配置+条件)
- 串联模式: lint-fix → tgd → gepa → opro (逐级优化)
- 并联模式: tgd/opro/gepa 同时运行, 取最优
- 条件门控: 上一阶段达到阈值才进入下一阶段
- 结果融合: 多优化器结果合并取最优

参考:
- AdalFlow Trainer: 统一训练循环 + 多策略组合
- Agent Lightning: 框架无关设计 + LightningStore中央存储
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class PipelineStage:
    name: str = ""
    optimizer: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    condition: str = ""
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "optimizer": self.optimizer,
            "config": self.config,
            "condition": self.condition,
            "enabled": self.enabled,
        }


@dataclass
class PipelineResult:
    initial_text: str = ""
    final_text: str = ""
    initial_score: float = 0.0
    final_score: float = 0.0
    improvement: float = 0.0
    stages_completed: int = 0
    total_stages: int = 0
    stage_results: list[dict[str, Any]] = field(default_factory=list)
    best_optimizer: str = ""
    mode: str = "sequential"
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_score": round(self.initial_score, 2),
            "final_score": round(self.final_score, 2),
            "improvement": round(self.improvement, 2),
            "stages_completed": self.stages_completed,
            "total_stages": self.total_stages,
            "best_optimizer": self.best_optimizer,
            "mode": self.mode,
            "elapsed_ms": round(self.elapsed_ms, 0),
        }


@dataclass
class PipelineConfig:
    mode: str = "sequential"
    score_threshold: float = 90.0
    max_stages: int = 10
    fail_fast: bool = False
    eval_fn: Callable[[str], float] | None = None


class OptPipeline:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self._stages: list[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> None:
        self._stages.append(stage)

    def clear_stages(self) -> None:
        self._stages = []

    @property
    def stages(self) -> list[PipelineStage]:
        return self._stages

    def run(self, prompt: str) -> PipelineResult:
        start_time = time.time()
        eval_fn = self.config.eval_fn or _pipeline_default_eval

        result = PipelineResult(
            initial_text=prompt,
            initial_score=eval_fn(prompt),
            total_stages=len(self._stages),
            mode=self.config.mode,
        )

        enabled_stages = [s for s in self._stages if s.enabled]

        if self.config.mode == "sequential":
            current_text = prompt
            current_score = result.initial_score

            for _i, stage in enumerate(enabled_stages):
                if self.config.fail_fast and current_score >= self.config.score_threshold:
                    logger.info("Score threshold reached, skipping remaining stages")
                    break

                if stage.condition and not self._evaluate_condition(stage.condition, current_score):
                    logger.info("Condition not met, skipping stage %s", stage.name)
                    continue

                stage_result = self._run_stage(stage, current_text, eval_fn)
                result.stage_results.append(stage_result)
                result.stages_completed += 1

                if stage_result.get("score", 0) > current_score:
                    current_text = stage_result.get("text", current_text)
                    current_score = stage_result["score"]

        elif self.config.mode == "parallel":
            best_text = prompt
            best_score = result.initial_score

            for stage in enabled_stages:
                stage_result = self._run_stage(stage, prompt, eval_fn)
                result.stage_results.append(stage_result)
                result.stages_completed += 1

                if stage_result.get("score", 0) > best_score:
                    best_text = stage_result.get("text", best_text)
                    best_score = stage_result["score"]
                    result.best_optimizer = stage.name

            current_text = best_text
            current_score = best_score

        result.final_text = current_text
        result.final_score = current_score
        result.improvement = current_score - result.initial_score
        result.elapsed_ms = (time.time() - start_time) * 1000

        if not result.best_optimizer and result.stage_results:
            best_stage = max(result.stage_results, key=lambda s: s.get("score", 0))
            result.best_optimizer = best_stage.get("name", "")

        return result

    def _run_stage(
        self,
        stage: PipelineStage,
        text: str,
        eval_fn: Callable[[str], float],
    ) -> dict[str, Any]:
        stage_result: dict[str, Any] = {
            "name": stage.name,
            "optimizer": stage.optimizer,
            "score": eval_fn(text),
        }

        try:
            if stage.optimizer == "tgd":
                from ai_prompt_toolkit.textgrad import TGDConfig, TGDOptimizer

                config = TGDConfig(
                    max_iterations=stage.config.get("max_iterations", 5),
                    momentum=stage.config.get("momentum", 0.9),
                )
                optimizer = TGDOptimizer(config)
                tgd_result = optimizer.optimize(text, eval_fn=eval_fn)
                stage_result["text"] = tgd_result.optimized_text
                stage_result["score"] = tgd_result.final_score
                stage_result["iterations"] = tgd_result.iterations

            elif stage.optimizer == "opro":
                from ai_prompt_toolkit.opro import OPROConfig, OPROOptimizer

                # R197: 改名防config/optimizer与TGD分支同名复用(mypy沿用首次推断)
                opro_config = OPROConfig(
                    max_generations=stage.config.get("max_generations", 3),
                    population_size=stage.config.get("population_size", 3),
                )
                opro_optimizer = OPROOptimizer(opro_config)
                opro_result = opro_optimizer.optimize(text, eval_fn=eval_fn)
                stage_result["text"] = opro_result.best_instruction
                stage_result["score"] = opro_result.best_score
                stage_result["candidates_explored"] = opro_result.candidates_explored

            elif stage.optimizer == "gepa":
                from ai_prompt_toolkit.gepa import gepa_optimize

                custom_metric = stage.config.get("custom_metric")
                gepa_result = gepa_optimize(
                    text,
                    auto="light",
                    custom_metric=custom_metric,
                )
                # R198: GEPAResult无best_prompt — 真实字段best_instructions为dict,
                # 取main键(gepa模块约定: best_instructions.get("main", text))
                stage_result["text"] = gepa_result.best_instructions.get("main", text)
                stage_result["score"] = gepa_result.best_score * 100
                stage_result["candidates"] = gepa_result.candidates_explored

            elif stage.optimizer == "lint-fix":
                from ai_prompt_toolkit.linter.fixer import Fixer  # R198: 真实类名 Fixer
                from ai_prompt_toolkit.linter.linter import PromptLinter

                linter = PromptLinter()
                lint_result = linter.lint("pipeline", text)
                fixer = Fixer()
                # R198: Fixer.fix真实返回tuple[str, list[FixResult]], 无fix_count属性
                fixed_text, fix_results = fixer.fix(text, lint_result.findings)
                stage_result["text"] = fixed_text
                stage_result["score"] = eval_fn(fixed_text)
                stage_result["fixes_applied"] = len(fix_results)

            elif stage.optimizer == "strategy":
                from ai_prompt_toolkit.prompt_optimizer import optimize_prompt

                opt_result = optimize_prompt(text)
                stage_result["text"] = opt_result.optimized_text
                stage_result["score"] = opt_result.final_score
                stage_result["steps"] = opt_result.iterations

        except Exception as e:
            logger.exception("Stage %s failed", stage.name)
            stage_result["error"] = str(e)
            stage_result["text"] = text

        return stage_result

    def _evaluate_condition(self, condition: str, current_score: float) -> bool:
        if condition == "score_below_threshold":
            return current_score < self.config.score_threshold
        elif condition == "always":
            return True
        elif condition.startswith("score_below_"):
            try:
                threshold = float(condition.split("_")[-1])
                return current_score < threshold
            except ValueError:
                return True
        return True


def create_default_pipeline(mode: str = "sequential") -> OptPipeline:
    pipeline = OptPipeline(PipelineConfig(mode=mode))
    pipeline.add_stage(
        PipelineStage(
            name="lint-fix",
            optimizer="lint-fix",
            condition="always",
        )
    )
    pipeline.add_stage(
        PipelineStage(
            name="tgd",
            optimizer="tgd",
            config={"max_iterations": 5},
            condition="score_below_threshold",
        )
    )
    pipeline.add_stage(
        PipelineStage(
            name="opro",
            optimizer="opro",
            config={"max_generations": 3, "population_size": 3},
            condition="score_below_95",
        )
    )
    return pipeline


def _pipeline_default_eval(text: str) -> float:
    try:
        from ai_prompt_toolkit.linter.linter import PromptLinter

        linter = PromptLinter()
        result = linter.lint("pipeline", text)
        return result.score
    except Exception:
        from ai_prompt_toolkit.textgrad import _default_eval_fn

        return _default_eval_fn(text)


def pipeline_optimize(
    prompt: str,
    *,
    mode: str = "sequential",
    stages: list[dict[str, Any]] | None = None,
    score_threshold: float = 90.0,
    eval_fn: Callable[[str], float] | None = None,
) -> PipelineResult:
    config = PipelineConfig(mode=mode, score_threshold=score_threshold, eval_fn=eval_fn)
    pipeline = OptPipeline(config)

    if stages:
        for s in stages:
            pipeline.add_stage(
                PipelineStage(
                    name=s.get("name", ""),
                    optimizer=s.get("optimizer", "tgd"),
                    config=s.get("config", {}),
                    condition=s.get("condition", ""),
                    enabled=s.get("enabled", True),
                )
            )
    else:
        pipeline = create_default_pipeline(mode)
        pipeline.config = config

    return pipeline.run(prompt)
