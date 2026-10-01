"""
Prompt Engine SDK - Python Implementation
Version: v1.0.0-beta | Date: 2026-05-29

核心模块：PromptEngine, ScenarioLoader, Evaluator, Combinator
"""

from __future__ import annotations

import json
import re
import hashlib
import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, validator


class ConstraintLevel(str, Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    XML = "xml"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Constraint:
    rule: str
    level: ConstraintLevel = ConstraintLevel.ERROR
    message: str = ""
    checker: Optional[Callable[[Any], bool]] = None

    def validate(self, value: Any) -> tuple[bool, str]:
        if self.checker:
            result = self.checker(value)
            return (result, "" if result else self.message)
        return (True, "")


class ConstraintSet:
    def __init__(self):
        self._constraints: list[Constraint] = []

    def add(self, constraint: Constraint) -> "ConstraintSet":
        self._constraints.append(constraint)
        return self

    def add_rule(self, rule: str, level: ConstraintLevel = ConstraintLevel.ERROR,
                 message: str = "", checker: Optional[Callable] = None) -> "ConstraintSet":
        self._constraints.append(Constraint(rule, level, message, checker))
        return self

    def validate(self, value: Any) -> list[tuple[ConstraintLevel, str]]:
        violations = []
        for c in self._constraints:
            ok, msg = c.validate(value)
            if not ok:
                violations.append((c.level, msg or c.rule))
        return violations

    def has_errors(self, value: Any) -> bool:
        return any(level == ConstraintLevel.ERROR for level, _ in self.validate(value))


class ScenarioVariable(BaseModel):
    name: str
    type: str = "string"
    required: bool = True
    default: Optional[Any] = None
    description: str = ""
    constraints: list[dict] = Field(default_factory=list)

    @validator("name")
    def name_must_be_valid(cls, v):
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError(f"Invalid variable name: {v}")
        return v


class ScenarioDefinition(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    category: str = "general"
    template: str
    variables: list[ScenarioVariable] = Field(default_factory=list)
    output_format: OutputFormat = OutputFormat.MARKDOWN
    output_schema: Optional[dict] = None
    constraints: list[dict] = Field(default_factory=list)
    examples: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    def resolve_template(self, bindings: dict[str, Any]) -> str:
        result = self.template
        for var in self.variables:
            value = bindings.get(var.name, var.default)
            if value is None and var.required:
                raise ValueError(f"Required variable '{var.name}' not provided")
            placeholder = f"{{{{{var.name}}}}}"
            result = result.replace(placeholder, str(value) if value is not None else "")
        return result


class ScenarioLoader:
    def __init__(self, base_path: Union[str, Path]):
        self.base_path = Path(base_path)
        self._cache: dict[str, ScenarioDefinition] = {}

    def load(self, scenario_id: str) -> ScenarioDefinition:
        if scenario_id in self._cache:
            return self._cache[scenario_id]
        file_path = self.base_path / f"{scenario_id}.json"
        if not file_path.exists():
            file_path = self.base_path / f"{scenario_id}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Scenario '{scenario_id}' not found in {self.base_path}")
        content = file_path.read_text(encoding="utf-8")
        if file_path.suffix == ".json":
            data = json.loads(content)
        else:
            import yaml
            data = yaml.safe_load(content)
        scenario = ScenarioDefinition(**data)
        self._cache[scenario_id] = scenario
        return scenario

    def load_all(self) -> list[ScenarioDefinition]:
        scenarios = []
        for p in self.base_path.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            scenarios.append(ScenarioDefinition(**data))
        for p in self.base_path.glob("*.yaml"):
            import yaml
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            scenarios.append(ScenarioDefinition(**data))
        return scenarios

    def clear_cache(self):
        self._cache.clear()


class EvaluationResult(BaseModel):
    scenario_id: str
    metric_name: str
    score: float
    max_score: float = 20.0
    details: dict = Field(default_factory=dict)
    passed: bool = True

    @property
    def normalized_score(self) -> float:
        return round(self.score / self.max_score * 20.0, 2)


class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, prompt: str, output: str, expected: Optional[str] = None) -> EvaluationResult:
        ...

    @abstractmethod
    async def aevaluate(self, prompt: str, output: str, expected: Optional[str] = None) -> EvaluationResult:
        ...


class StructureEvaluator(BaseEvaluator):
    def evaluate(self, prompt: str, output: str, expected: Optional[str] = None) -> EvaluationResult:
        score = 0.0
        details = {}
        if output.strip():
            score += 5.0
            details["non_empty"] = True
        if len(output) > 100:
            score += 5.0
            details["sufficient_length"] = True
        if "##" in output or "**" in output:
            score += 5.0
            details["has_structure"] = True
        if "\n" in output:
            score += 5.0
            details["multiline"] = True
        return EvaluationResult(
            scenario_id="", metric_name="structure", score=min(score, 20.0), details=details,
            passed=score >= 15.0
        )

    async def aevaluate(self, prompt: str, output: str, expected: Optional[str] = None) -> EvaluationResult:
        return self.evaluate(prompt, output, expected)


class SafetyEvaluator(BaseEvaluator):
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf", r"DROP\s+TABLE", r"__import__\(",
        r"eval\(", r"exec\(", r"subprocess\.call",
    ]

    def evaluate(self, prompt: str, output: str, expected: Optional[str] = None) -> EvaluationResult:
        violations = []
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                violations.append(pattern)
        score = 20.0 if not violations else max(0, 20.0 - len(violations) * 5.0)
        return EvaluationResult(
            scenario_id="", metric_name="safety", score=score,
            details={"violations": violations, "safe": len(violations) == 0},
            passed=len(violations) == 0
        )

    async def aevaluate(self, prompt: str, output: str, expected: Optional[str] = None) -> EvaluationResult:
        return self.evaluate(prompt, output, expected)


class Combinator:
    def __init__(self):
        self._strategies: dict[str, Callable] = {}

    def register_strategy(self, name: str, strategy: Callable) -> None:
        self._strategies[name] = strategy

    def generate_variants(self, template: str, variables: dict[str, list[Any]]) -> list[str]:
        if not variables:
            return [template]
        var_names = list(variables.keys())
        var_values = list(variables.values())
        variants = []
        from itertools import product
        for combo in product(*var_values):
            result = template
            for name, value in zip(var_names, combo):
                result = result.replace(f"{{{{{name}}}}}", str(value))
            variants.append(result)
        return variants

    def combine_prompts(self, prompts: list[str], strategy: str = "concat") -> str:
        if strategy == "concat":
            return "\n\n---\n\n".join(prompts)
        elif strategy == "hierarchy":
            return "\n\n## 层级组合\n\n".join(prompts)
        elif strategy in self._strategies:
            return self._strategies[strategy](prompts)
        raise ValueError(f"Unknown strategy: {strategy}")

    def detect_conflicts(self, constraints_list: list[ConstraintSet]) -> list[tuple[int, int, str]]:
        conflicts = []
        all_rules: list[tuple[int, str]] = []
        for i, cs in enumerate(constraints_list):
            for c in cs._constraints:
                all_rules.append((i, c.rule))
        for idx1, (i, r1) in enumerate(all_rules):
            for j, r2 in all_rules[idx1 + 1:]:
                if i != j and r1 == r2:
                    conflicts.append((i, j, r1))
        return conflicts


class ExecutionResult(BaseModel):
    scenario_id: str
    status: ExecutionStatus
    output: str = ""
    resolved_prompt: str = ""
    evaluation_results: list[EvaluationResult] = Field(default_factory=list)
    constraints_violations: list[tuple[str, str]] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    trace_id: str = ""
    metadata: dict = Field(default_factory=dict)


class PromptEngine:
    def __init__(self, scenarios_path: Optional[Union[str, Path]] = None):
        self._loader = ScenarioLoader(scenarios_path) if scenarios_path else None
        self._evaluators: list[BaseEvaluator] = []
        self._combinator = Combinator()
        self._global_constraints = ConstraintSet()
        self._adapter: Optional[Callable] = None
        self._pre_hooks: list[Callable] = []
        self._post_hooks: list[Callable] = []
        self._trace_callback: Optional[Callable] = None

    @property
    def loader(self) -> Optional[ScenarioLoader]:
        return self._loader

    @property
    def combinator(self) -> Combinator:
        return self._combinator

    def add_evaluator(self, evaluator: BaseEvaluator) -> "PromptEngine":
        self._evaluators.append(evaluator)
        return self

    def add_constraint(self, constraint: Constraint) -> "PromptEngine":
        self._global_constraints.add(constraint)
        return self

    def set_adapter(self, adapter: Callable) -> "PromptEngine":
        self._adapter = adapter
        return self

    def add_pre_hook(self, hook: Callable) -> "PromptEngine":
        self._pre_hooks.append(hook)
        return self

    def add_post_hook(self, hook: Callable) -> "PromptEngine":
        self._post_hooks.append(hook)
        return self

    def set_trace_callback(self, callback: Callable) -> "PromptEngine":
        self._trace_callback = callback
        return self

    def invoke(self, scenario_id: str, bindings: dict[str, Any],
               llm: Optional[Callable] = None) -> ExecutionResult:
        import time
        start = time.time()
        trace_id = hashlib.sha256(f"{scenario_id}:{time.time()}".encode()).hexdigest()[:16]

        if not self._loader:
            raise RuntimeError("No scenarios path configured")
        scenario = self._loader.load(scenario_id)

        for hook in self._pre_hooks:
            hook(scenario, bindings)

        resolved = scenario.resolve_template(bindings)

        if self._adapter:
            resolved = self._adapter(resolved, scenario)

        violations = self._global_constraints.validate(resolved)
        error_violations = [(lvl, msg) for lvl, msg in violations if lvl == ConstraintLevel.ERROR]
        if error_violations:
            return ExecutionResult(
                scenario_id=scenario_id, status=ExecutionStatus.BLOCKED,
                constraints_violations=error_violations, trace_id=trace_id,
                execution_time_ms=(time.time() - start) * 1000
            )

        output = ""
        if llm:
            output = llm(resolved)
        else:
            output = resolved

        eval_results = []
        for evaluator in self._evaluators:
            eval_results.append(evaluator.evaluate(resolved, output))

        for hook in self._post_hooks:
            hook(scenario, output, eval_results)

        status = ExecutionStatus.SUCCESS
        if any(not r.passed for r in eval_results):
            status = ExecutionStatus.PARTIAL

        result = ExecutionResult(
            scenario_id=scenario_id, status=status, output=output,
            resolved_prompt=resolved, evaluation_results=eval_results,
            constraints_violations=[(str(l), m) for l, m in violations],
            execution_time_ms=(time.time() - start) * 1000,
            trace_id=trace_id
        )

        if self._trace_callback:
            self._trace_callback(result)

        return result

    async def ainvoke(self, scenario_id: str, bindings: dict[str, Any],
                      llm: Optional[Callable] = None) -> ExecutionResult:
        import time
        start = time.time()
        trace_id = hashlib.sha256(f"{scenario_id}:{time.time()}".encode()).hexdigest()[:16]

        if not self._loader:
            raise RuntimeError("No scenarios path configured")
        scenario = self._loader.load(scenario_id)

        for hook in self._pre_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook(scenario, bindings)
            else:
                hook(scenario, bindings)

        resolved = scenario.resolve_template(bindings)

        if self._adapter:
            resolved = self._adapter(resolved, scenario)

        violations = self._global_constraints.validate(resolved)
        error_violations = [(lvl, msg) for lvl, msg in violations if lvl == ConstraintLevel.ERROR]
        if error_violations:
            return ExecutionResult(
                scenario_id=scenario_id, status=ExecutionStatus.BLOCKED,
                constraints_violations=error_violations, trace_id=trace_id,
                execution_time_ms=(time.time() - start) * 1000
            )

        output = ""
        if llm:
            if asyncio.iscoroutinefunction(llm):
                output = await llm(resolved)
            else:
                output = llm(resolved)
        else:
            output = resolved

        eval_results = []
        for evaluator in self._evaluators:
            eval_results.append(await evaluator.aevaluate(resolved, output))

        for hook in self._post_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook(scenario, output, eval_results)
            else:
                hook(scenario, output, eval_results)

        status = ExecutionStatus.SUCCESS
        if any(not r.passed for r in eval_results):
            status = ExecutionStatus.PARTIAL

        return ExecutionResult(
            scenario_id=scenario_id, status=status, output=output,
            resolved_prompt=resolved, evaluation_results=eval_results,
            constraints_violations=[(str(l), m) for l, m in violations],
            execution_time_ms=(time.time() - start) * 1000,
            trace_id=trace_id
        )

    def batch(self, requests: list[tuple[str, dict[str, Any]]],
              llm: Optional[Callable] = None) -> list[ExecutionResult]:
        return [self.invoke(sid, bindings, llm) for sid, bindings in requests]

    async def abatch(self, requests: list[tuple[str, dict[str, Any]]],
                     llm: Optional[Callable] = None) -> list[ExecutionResult]:
        tasks = [self.ainvoke(sid, bindings, llm) for sid, bindings in requests]
        return await asyncio.gather(*tasks)


class PromptEngineBuilder:
    def __init__(self):
        self._scenarios_path: Optional[Path] = None
        self._evaluators: list[BaseEvaluator] = []
        self._constraints: list[Constraint] = []
        self._adapter: Optional[Callable] = None
        self._pre_hooks: list[Callable] = []
        self._post_hooks: list[Callable] = []
        self._trace_callback: Optional[Callable] = None

    def with_scenarios(self, path: Union[str, Path]) -> "PromptEngineBuilder":
        self._scenarios_path = Path(path)
        return self

    def with_evaluator(self, evaluator: BaseEvaluator) -> "PromptEngineBuilder":
        self._evaluators.append(evaluator)
        return self

    def with_default_evaluators(self) -> "PromptEngineBuilder":
        self._evaluators.extend([StructureEvaluator(), SafetyEvaluator()])
        return self

    def with_constraint(self, constraint: Constraint) -> "PromptEngineBuilder":
        self._constraints.append(constraint)
        return self

    def with_adapter(self, adapter: Callable) -> "PromptEngineBuilder":
        self._adapter = adapter
        return self

    def with_pre_hook(self, hook: Callable) -> "PromptEngineBuilder":
        self._pre_hooks.append(hook)
        return self

    def with_post_hook(self, hook: Callable) -> "PromptEngineBuilder":
        self._post_hooks.append(hook)
        return self

    def with_tracing(self, callback: Callable) -> "PromptEngineBuilder":
        self._trace_callback = callback
        return self

    def build(self) -> PromptEngine:
        engine = PromptEngine(self._scenarios_path)
        for e in self._evaluators:
            engine.add_evaluator(e)
        for c in self._constraints:
            engine.add_constraint(c)
        if self._adapter:
            engine.set_adapter(self._adapter)
        for h in self._pre_hooks:
            engine.add_pre_hook(h)
        for h in self._post_hooks:
            engine.add_post_hook(h)
        if self._trace_callback:
            engine.set_trace_callback(self._trace_callback)
        return engine
