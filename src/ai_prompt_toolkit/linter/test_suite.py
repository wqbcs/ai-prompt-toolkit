"""声明式Lint+Eval测试套件 — YAML配置驱动的测试规范

借鉴promptfoo的声明式配置:
- TestSuite: 测试套件定义(含多个TestGroup)
- TestGroup: 测试组(目标+规则+评估+断言)
- Assertion: 断言定义(score阈值/finding数量/severity限制)
- load_test_suite: 从YAML加载
- run_test_suite: 执行测试套件
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Assertion:
    type: str = "score"
    threshold: float = 80.0
    max_findings: int = 0
    max_severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "threshold": self.threshold, "max_findings": self.max_findings, "max_severity": self.max_severity}


@dataclass
class TestGroup:
    name: str = ""
    target: str = ""
    config: str = ""
    assertions: list[Assertion] = field(default_factory=list)
    eval_dimensions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "target": self.target,
            "config": self.config,
            "assertions": [a.to_dict() for a in self.assertions],
            "eval_dimensions": self.eval_dimensions,
        }


@dataclass
class TestSuite:
    name: str = ""
    version: str = "1.0"
    description: str = ""
    groups: list[TestGroup] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "groups": [g.to_dict() for g in self.groups],
        }


def load_test_suite(path: str | Path) -> TestSuite:
    p = Path(path)
    content = p.read_text(encoding="utf-8-sig", errors="replace")
    if p.suffix in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(content) or {}
    elif p.suffix == ".json":
        data = json.loads(content)
    else:
        import yaml
        data = yaml.safe_load(content) or {}
    groups = []
    for g in data.get("groups", []):
        assertions = []
        for a in g.get("assertions", []):
            assertions.append(Assertion(
                type=a.get("type", "score"),
                threshold=float(a.get("threshold", 80.0)),
                max_findings=int(a.get("max_findings", 0)),
                max_severity=a.get("max_severity", "medium"),
            ))
        groups.append(TestGroup(
            name=g.get("name", ""),
            target=g.get("target", ""),
            config=g.get("config", ""),
            assertions=assertions,
            eval_dimensions=g.get("eval_dimensions", []),
        ))
    return TestSuite(
        name=data.get("name", ""),
        version=data.get("version", "1.0"),
        description=data.get("description", ""),
        groups=groups,
    )


def run_test_suite(suite: TestSuite, base_dir: str = ".") -> dict[str, Any]:
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.cli_helpers import discover_templates
    linter = PromptLinter()
    results = []
    for group in suite.groups:
        target_path = Path(base_dir) / group.target if group.target else Path(base_dir)
        templates = discover_templates(str(target_path)) if target_path.is_dir() else [target_path] if target_path.exists() else []
        group_results = []
        for tpl in templates:
            text = tpl.read_text(encoding="utf-8") if hasattr(tpl, 'read_text') else ""
            lint_result = linter.lint(str(tpl), text)
            passed = True
            for assertion in group.assertions:
                if assertion.type == "score" and lint_result.score < assertion.threshold:
                    passed = False
                elif assertion.type == "max_findings" and assertion.max_findings > 0 and lint_result.failed_count > assertion.max_findings:
                    passed = False
                elif assertion.type == "max_severity":
                    sev_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
                    max_sev = max((sev_order.get(f.severity.value if hasattr(f.severity, 'value') else str(f.severity), 0) for f in lint_result.findings), default=0)
                    if max_sev > sev_order.get(assertion.max_severity, 1):
                        passed = False
            group_results.append({
                "template": str(tpl),
                "score": lint_result.score,
                "findings": lint_result.failed_count,
                "passed": passed,
            })
        results.append({
            "group": group.name,
            "results": group_results,
            "passed": all(r["passed"] for r in group_results) if group_results else True,
        })
    return {
        "suite": suite.name,
        "version": suite.version,
        "groups": results,
        "passed": all(g["passed"] for g in results),
    }
