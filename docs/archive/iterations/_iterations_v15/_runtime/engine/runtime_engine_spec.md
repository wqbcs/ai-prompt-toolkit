# 提示词运行时引擎核心逻辑设计

> 版本：v1.0 | 日期：2026-05-29

---

## 1. 执行流水线

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Prompt  │──→│ Variable │──→│Constraint│──→│ Execute  │──→│  Output  │
│  Load    │   │  Bind    │   │ Validate │   │          │   │ Validate │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
     ↓              ↓              ↓              ↓              ↓
  scenario      resolved      constraints     raw_output     final_output
  definition    prompt        checked                       + violations
```

## 2. 核心类设计

### 2.1 PromptRuntime

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

class RuntimePhase(str, Enum):
    LOAD = "load"
    BIND = "bind"
    CONSTRAINT_VALIDATE = "constraint_validate"
    EXECUTE = "execute"
    OUTPUT_VALIDATE = "output_validate"
    COMPLETE = "complete"

class RuntimeStatus(str, Enum):
    SUCCESS = "success"
    CONSTRAINT_VIOLATION = "constraint_violation"
    EXECUTION_ERROR = "execution_error"
    OUTPUT_INVALID = "output_invalid"
    TIMEOUT = "timeout"
    SANDBOX_VIOLATION = "sandbox_violation"

@dataclass
class ExecutionContext:
    scenario_id: str
    phase: RuntimePhase
    bindings: dict[str, Any] = field(default_factory=dict)
    resolved_prompt: str = ""
    constraints_result: Optional[ConstraintValidationResult] = None
    raw_output: str = ""
    output_validations: list[OutputValidation] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class RuntimeResult:
    scenario_id: str
    status: RuntimeStatus
    output: str
    context: ExecutionContext
    execution_time_ms: float
    sandbox_metrics: Optional[SandboxMetrics] = None

class PromptRuntime:
    def __init__(
        self,
        engine: PromptEngine,
        sandbox: Optional[SandboxConfig] = None,
        monitor: Optional[RuntimeMonitor] = None,
        timeout_ms: int = 30000,
    ):
        self._engine = engine
        self._sandbox = sandbox
        self._monitor = monitor
        self._timeout_ms = timeout_ms
        self._phase_hooks: dict[RuntimePhase, list[Callable]] = {
            phase: [] for phase in RuntimePhase
        }

    def execute(self, scenario_id: str, bindings: dict[str, Any],
                llm: Optional[Callable] = None) -> RuntimeResult:
        import time
        start = time.time()
        ctx = ExecutionContext(scenario_id=scenario_id, phase=RuntimePhase.LOAD)

        try:
            # Phase 1: Load
            ctx.phase = RuntimePhase.LOAD
            scenario = self._engine.loader.load(scenario_id)
            self._run_phase_hooks(ctx)

            # Phase 2: Bind
            ctx.phase = RuntimePhase.BIND
            ctx.bindings = bindings
            ctx.resolved_prompt = scenario.resolve_template(bindings)
            self._run_phase_hooks(ctx)

            # Phase 3: Constraint Validate
            ctx.phase = RuntimePhase.CONSTRAINT_VALIDATE
            ctx.constraints_result = self._validate_constraints(scenario, ctx.resolved_prompt)
            if ctx.constraints_result.has_errors:
                return RuntimeResult(
                    scenario_id, RuntimeStatus.CONSTRAINT_VIOLATION,
                    "", ctx, (time.time() - start) * 1000
                )
            self._run_phase_hooks(ctx)

            # Phase 4: Execute
            ctx.phase = RuntimePhase.EXECUTE
            if self._sandbox:
                ctx.raw_output = self._execute_in_sandbox(ctx.resolved_prompt, llm)
            elif llm:
                ctx.raw_output = llm(ctx.resolved_prompt)
            else:
                ctx.raw_output = ctx.resolved_prompt
            self._run_phase_hooks(ctx)

            # Phase 5: Output Validate
            ctx.phase = RuntimePhase.OUTPUT_VALIDATE
            ctx.output_validations = self._validate_output(scenario, ctx.raw_output)
            if any(not v.passed for v in ctx.output_validations):
                status = RuntimeStatus.OUTPUT_INVALID
            else:
                status = RuntimeStatus.SUCCESS
            self._run_phase_hooks(ctx)

            # Phase 6: Complete
            ctx.phase = RuntimePhase.COMPLETE
            self._run_phase_hooks(ctx)

            return RuntimeResult(
                scenario_id, status, ctx.raw_output, ctx, (time.time() - start) * 1000
            )

        except TimeoutError:
            return RuntimeResult(
                scenario_id, RuntimeStatus.TIMEOUT, "", ctx, (time.time() - start) * 1000
            )
        except Exception as e:
            return RuntimeResult(
                scenario_id, RuntimeStatus.EXECUTION_ERROR, str(e), ctx, (time.time() - start) * 1000
            )

    def add_phase_hook(self, phase: RuntimePhase, hook: Callable) -> None:
        self._phase_hooks[phase].append(hook)

    def _run_phase_hooks(self, ctx: ExecutionContext) -> None:
        for hook in self._phase_hooks[ctx.phase]:
            hook(ctx)
        if self._monitor:
            self._monitor.on_phase(ctx)

    def _validate_constraints(self, scenario, prompt) -> ConstraintValidationResult:
        violations = []
        for c in scenario.constraints:
            checker = self._get_checker(c)
            if checker and not checker(prompt):
                violations.append(ConstraintViolation(
                    rule=c.get("rule", ""), level=c.get("level", "error"),
                    message=c.get("message", "")
                ))
        return ConstraintValidationResult(
            violations=violations,
            has_errors=any(v.level == "error" for v in violations)
        )

    def _validate_output(self, scenario, output) -> list[OutputValidation]:
        validations = []
        if scenario.output_schema:
            validations.append(self._validate_schema(output, scenario.output_schema))
        return validations

    def _execute_in_sandbox(self, prompt: str, llm: Callable) -> str:
        return SandboxExecutor(self._sandbox).execute(prompt, llm)
```

## 3. 执行上下文管理

```python
class RuntimeContextManager:
    _instance: Optional[RuntimeContextManager] = None

    def __init__(self):
        self._contexts: dict[str, ExecutionContext] = {}
        self._history: list[RuntimeResult] = []

    @classmethod
    def instance(cls) -> RuntimeContextManager:
        if not cls._instance:
            cls._instance = RuntimeContextManager()
        return cls._instance

    def create_context(self, scenario_id: str) -> ExecutionContext:
        ctx = ExecutionContext(scenario_id=scenario_id, phase=RuntimePhase.LOAD)
        self._contexts[scenario_id] = ctx
        return ctx

    def get_context(self, scenario_id: str) -> Optional[ExecutionContext]:
        return self._contexts.get(scenario_id)

    def record_result(self, result: RuntimeResult) -> None:
        self._history.append(result)

    def get_history(self, scenario_id: str = None) -> list[RuntimeResult]:
        if scenario_id:
            return [r for r in self._history if r.scenario_id == scenario_id]
        return self._history
```
