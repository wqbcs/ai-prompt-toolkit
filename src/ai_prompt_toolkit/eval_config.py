"""YAML声明式评估配置模块

参考promptfoo的promptfooconfig.yaml声明式配置模式,
支持通过YAML文件定义评估目标、断言、阈值和Provider配置。

示例配置文件 (prompt-eval.yaml):
```yaml
targets:
  - path: templates/customer-service.md
    provider: openai
    model: gpt-4o-mini
  - path: templates/rag-assistant.md
    provider: pangu
    model: pangu-nlp

evaluators:
  - type: lint
    threshold: 90
  - type: security
    threshold: 80
  - type: dimension
    dimensions: [D01, D02, D03]
    threshold: 7.0
  - type: assertion
    assertions:
      - name: "角色定义"
        contains: ["你是", "助手"]
      - name: "约束完整"
        contains_any: ["约束", "限制", "不得"]
      - name: "格式指定"
        regex: "输出格式|格式如下"

providers:
  openai:
    api_key_env: OPENAI_API_KEY
    base_url: https://api.openai.com/v1
  pangu:
    api_key_env: HW_CLOUD_API_KEY
    base_url: https://maas.cn-north-4.myhuaweicloud.com/v1

output:
  format: json
  path: eval-results.json
  save_history: true
```
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.cli_helpers import read_prompt_text


@dataclass
class EvalTarget:
    path: str
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    vars: dict[str, str] = field(default_factory=dict)


@dataclass
class AssertionDef:
    name: str
    contains: list[str] = field(default_factory=list)
    contains_any: list[str] = field(default_factory=list)
    regex: str = ""
    not_contains: list[str] = field(default_factory=list)
    icontains: list[str] = field(default_factory=list)


@dataclass
class EvaluatorDef:
    type: str
    threshold: float = 0.0
    dimensions: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    assertions: list[AssertionDef] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)


@dataclass
class ProviderDef:
    api_key_env: str = ""
    base_url: str = ""
    max_retries: int = 3
    timeout: float = 30.0


@dataclass
class OutputDef:
    format: str = "json"
    path: str = ""
    save_history: bool = False


@dataclass
class EvalConfig:
    targets: list[EvalTarget] = field(default_factory=list)
    evaluators: list[EvaluatorDef] = field(default_factory=list)
    providers: dict[str, ProviderDef] = field(default_factory=dict)
    output: OutputDef = field(default_factory=OutputDef)

    @classmethod
    def from_yaml(cls, path: str | Path) -> EvalConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"评估配置文件不存在: {path}")
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls._from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalConfig:
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> EvalConfig:
        targets = []
        for t in data.get("targets", []):
            if isinstance(t, str):
                targets.append(EvalTarget(path=t))
            elif isinstance(t, dict):
                targets.append(
                    EvalTarget(
                        path=t.get("path", ""),
                        provider=t.get("provider", "openai"),
                        model=t.get("model", "gpt-4o-mini"),
                        vars=t.get("vars", {}),
                    )
                )

        evaluators = []
        for e in data.get("evaluators", []):
            if not isinstance(e, dict):
                continue
            assertions = []
            for a in e.get("assertions", []):
                if isinstance(a, dict):
                    assertions.append(
                        AssertionDef(
                            name=a.get("name", ""),
                            contains=a.get("contains", []),
                            contains_any=a.get("contains_any", []),
                            regex=a.get("regex", ""),
                            not_contains=a.get("not_contains", []),
                            icontains=a.get("icontains", []),
                        )
                    )
            evaluators.append(
                EvaluatorDef(
                    type=e.get("type", "lint"),
                    threshold=e.get("threshold", 0.0),
                    dimensions=e.get("dimensions", []),
                    categories=e.get("categories", []),
                    assertions=assertions,
                    rules=e.get("rules", []),
                )
            )

        providers = {}
        for name, p in data.get("providers", {}).items():
            if isinstance(p, dict):
                providers[name] = ProviderDef(
                    api_key_env=p.get("api_key_env", ""),
                    base_url=p.get("base_url", ""),
                    max_retries=p.get("max_retries", 3),
                    timeout=p.get("timeout", 30.0),
                )

        output_data = data.get("output", {})
        output = OutputDef(
            format=output_data.get("format", "json"),
            path=output_data.get("path", ""),
            save_history=output_data.get("save_history", False),
        )

        return cls(targets=targets, evaluators=evaluators, providers=providers, output=output)


def run_assertion(text: str, assertion: AssertionDef) -> dict[str, Any]:
    passed = True
    details: list[str] = []

    for word in assertion.contains:
        if word not in text:
            passed = False
            details.append(f"缺少关键词: {word}")

    if assertion.contains_any:
        found = any(word in text for word in assertion.contains_any)
        if not found:
            passed = False
            details.append(f"缺少任一关键词: {assertion.contains_any}")

    for word in assertion.not_contains:
        if word in text:
            passed = False
            details.append(f"包含禁用关键词: {word}")

    for word in assertion.icontains:
        if word.lower() not in text.lower():
            passed = False
            details.append(f"缺少关键词(不区分大小写): {word}")

    if assertion.regex and not re.search(assertion.regex, text, re.IGNORECASE):
        passed = False
        details.append(f"正则不匹配: {assertion.regex}")

    return {
        "name": assertion.name,
        "passed": passed,
        "details": details,
    }


def run_eval_config(config: EvalConfig, base_dir: str | Path | None = None) -> dict[str, Any]:
    base = Path(base_dir) if base_dir else Path.cwd()
    results: dict[str, Any] = {
        "targets": [],
        "summary": {"total": 0, "passed": 0, "failed": 0},
    }

    for target in config.targets:
        target_path = base / target.path
        if not target_path.exists():
            results["targets"].append(
                {
                    "path": target.path,
                    "error": f"文件不存在: {target_path}",
                    "evaluators": [],
                }
            )
            results["summary"]["total"] += 1
            results["summary"]["failed"] += 1
            continue

        text = read_prompt_text(target_path)
        target_result: dict[str, Any] = {
            "path": target.path,
            "provider": target.provider,
            "model": target.model,
            "evaluators": [],
        }

        for evaluator in config.evaluators:
            eval_result: dict[str, Any] = {
                "type": evaluator.type,
                "threshold": evaluator.threshold,
                "passed": True,
                "details": [],
            }

            if evaluator.type == "lint":
                from ai_prompt_toolkit.linter.linter import PromptLinter

                linter = PromptLinter()
                lint_result = linter.lint(target.path, text)
                eval_result["score"] = lint_result.score
                eval_result["passed"] = lint_result.score >= evaluator.threshold
                eval_result["findings_count"] = len(lint_result.findings)

            elif evaluator.type == "security":
                from ai_prompt_toolkit.security.inheritance_auditor import DictTemplateProvider
                from ai_prompt_toolkit.security.scanner import Scanner

                # R198: 真实API — Scanner需provider, scan需(template_id, text);
                # 无继承上下文时用空provider, 发现数反推得分(0发现=100)
                scanner = Scanner(DictTemplateProvider({}))
                scan_result = scanner.scan(target.path, text)
                eval_result["score"] = max(0, 100 - len(scan_result.injection_findings) * 10)
                eval_result["passed"] = eval_result["score"] >= evaluator.threshold
                eval_result["risk_level"] = scan_result.risk_level.value

            elif evaluator.type == "dimension":
                from ai_prompt_toolkit.evaluator import evaluate_template

                dim_report = evaluate_template(
                    target.path,
                    text,
                    dimensions=evaluator.dimensions or None,
                    categories=evaluator.categories or None,
                )
                avg_score = dim_report.average_score if hasattr(dim_report, "average_score") else 0
                eval_result["score"] = avg_score
                eval_result["passed"] = avg_score >= evaluator.threshold

            elif evaluator.type == "assertion":
                assertion_results = []
                for assertion in evaluator.assertions:
                    ar = run_assertion(text, assertion)
                    assertion_results.append(ar)
                all_passed = all(ar["passed"] for ar in assertion_results)
                eval_result["passed"] = all_passed
                eval_result["details"] = assertion_results

            target_result["evaluators"].append(eval_result)

        all_evals_passed = all(e["passed"] for e in target_result["evaluators"])
        target_result["passed"] = all_evals_passed

        results["targets"].append(target_result)
        results["summary"]["total"] += 1
        if all_evals_passed:
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1

    return results


DEFAULT_EVAL_CONFIG_YAML = """\
# AI Prompt Toolkit 评估配置
# 参考: promptfoo promptfooconfig.yaml
targets:
  - path: templates/customer-service.md
  - path: templates/code-reviewer.md

evaluators:
  - type: lint
    threshold: 90
  - type: assertion
    assertions:
      - name: "角色定义"
        contains: ["你是"]
      - name: "约束完整"
        contains_any: ["约束", "限制", "不得"]
      - name: "格式指定"
        regex: "输出格式|格式如下"

output:
  format: json
  path: eval-results.json
  save_history: true
"""
