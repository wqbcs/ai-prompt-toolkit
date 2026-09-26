"""CI/CD集成模块 — 参考promptfoo CI+DeepEval pytest集成

核心特性:
- JUnit XML报告输出(兼容CI平台)
- --fail-on-error质量门禁
- --tag CI上下文附加
- GitHub Actions集成模板
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CITestCase:
    name: str = ""
    classname: str = ""
    time_ms: float = 0.0
    status: str = "passed"
    message: str = ""
    stdout: str = ""

    def to_xml(self) -> ET.Element:
        tc = ET.Element(
            "testcase",
            {
                "name": self.name,
                "classname": self.classname,
                "time": f"{self.time_ms / 1000:.3f}",
            },
        )
        if self.status == "failed":
            fail = ET.SubElement(tc, "failure", {"message": self.message})
            fail.text = self.stdout
        elif self.status == "error":
            err = ET.SubElement(tc, "error", {"message": self.message})
            err.text = self.stdout
        elif self.status == "skipped":
            ET.SubElement(tc, "skipped", {"message": self.message})
        return tc


@dataclass
class CITestSuite:
    name: str = ""
    tests: list[CITestCase] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def failures(self) -> int:
        return sum(1 for t in self.tests if t.status == "failed")

    @property
    def errors(self) -> int:
        return sum(1 for t in self.tests if t.status == "error")

    @property
    def skipped(self) -> int:
        return sum(1 for t in self.tests if t.status == "skipped")

    @property
    def total_time_ms(self) -> float:
        return sum(t.time_ms for t in self.tests)

    def to_xml(self) -> ET.Element:
        suite = ET.Element(
            "testsuite",
            {
                "name": self.name,
                "tests": str(self.total),
                "failures": str(self.failures),
                "errors": str(self.errors),
                "skipped": str(self.skipped),
                "time": f"{self.total_time_ms / 1000:.3f}",
            },
        )
        if self.properties:
            props = ET.SubElement(suite, "properties")
            for k, v in self.properties.items():
                ET.SubElement(props, "property", {"name": k, "value": v})
        for tc in self.tests:
            suite.append(tc.to_xml())
        return suite


class JUnitReporter:
    def __init__(self, suite_name: str = "promptkit", ci_tags: dict[str, str] | None = None) -> None:
        self.suite = CITestSuite(name=suite_name)
        if ci_tags:
            self.suite.properties.update(ci_tags)

    def add_lint_result(self, file_path: str, findings: list[dict[str, Any]], elapsed_ms: float) -> None:
        has_error = any(f.get("severity") in ("critical", "high") for f in findings)
        tc = CITestCase(
            name=f"lint:{Path(file_path).name}",
            classname="promptkit.lint",
            time_ms=elapsed_ms,
            status="failed" if has_error else "passed",
            message=f"{len(findings)} findings" if findings else "OK",
            stdout=json.dumps(findings, ensure_ascii=False, indent=2) if findings else "",
        )
        self.suite.tests.append(tc)

    def add_scan_result(self, file_path: str, findings: list[dict[str, Any]], elapsed_ms: float) -> None:
        has_error = any(f.get("severity") in ("critical", "high") for f in findings)
        tc = CITestCase(
            name=f"scan:{Path(file_path).name}",
            classname="promptkit.scan",
            time_ms=elapsed_ms,
            status="failed" if has_error else "passed",
            message=f"{len(findings)} issues" if findings else "OK",
            stdout=json.dumps(findings, ensure_ascii=False, indent=2) if findings else "",
        )
        self.suite.tests.append(tc)

    def add_eval_result(
        self, file_path: str, score: float, passed: bool, details: str = "", elapsed_ms: float = 0.0
    ) -> None:
        tc = CITestCase(
            name=f"eval:{Path(file_path).name}",
            classname="promptkit.eval",
            time_ms=elapsed_ms,
            status="passed" if passed else "failed",
            message=f"Score: {score:.1f}",
            stdout=details,
        )
        self.suite.tests.append(tc)

    def add_gepa_result(self, prompt_name: str, best_score: float, improvement: float, elapsed_ms: float) -> None:
        tc = CITestCase(
            name=f"gepa:{prompt_name}",
            classname="promptkit.gepa",
            time_ms=elapsed_ms,
            status="passed" if improvement > 0 else "failed",
            message=f"Best: {best_score:.4f}, Improvement: {improvement:+.4f}",
        )
        self.suite.tests.append(tc)

    def add_redteam_result(self, target: str, vulnerabilities: int, passed: bool, elapsed_ms: float) -> None:
        tc = CITestCase(
            name=f"redteam:{target}",
            classname="promptkit.redteam",
            time_ms=elapsed_ms,
            status="passed" if passed else "failed",
            message=f"{vulnerabilities} vulnerabilities",
        )
        self.suite.tests.append(tc)

    def to_xml_string(self, pretty: bool = True) -> str:
        root = ET.Element("testsuites")
        root.set("name", "promptkit")
        root.append(self.suite.to_xml())
        if pretty:
            ET.indent(root)
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def write(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_xml_string(), encoding="utf-8")
        return path

    @property
    def has_failures(self) -> bool:
        return self.suite.failures > 0 or self.suite.errors > 0


def generate_github_actions_workflow(
    *,
    python_version: str = "3.11",
    trigger_on: list[str] | None = None,
    fail_on_error: bool = True,
    threshold: float = 60.0,
    redteam: bool = False,
) -> str:
    triggers = trigger_on or ["push", "pull_request"]
    on_block_lines = []
    for t in triggers:
        on_block_lines.append(f"  {t}:")
        if t in ("push", "pull_request"):
            on_block_lines.append("    branches: [main, develop]")

    on_block = "\n".join(on_block_lines)

    steps = f"""    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '{python_version}'
      - run: pip install ai-prompt-toolkit
      - run: promptkit lint --format junit-xml --output lint-results.xml .
      - run: promptkit scan --format junit-xml --output scan-results.xml .
      - run: promptkit evaluate --quick --threshold {threshold}{" --fail-on-error" if fail_on_error else ""} --format junit-xml --output eval-results.xml ."""

    if redteam:
        steps += """
      - run: promptkit redteam --probes essential --output redteam-results.json ."""

    steps += """
      - uses: mikepenz/action-junit-report@v4
        if: always()
        with:
          report_paths: '*.xml'
          fail_on_failure: true"""

    return f"""name: Prompt Quality Gate

on:
{on_block}
{steps}
"""


def extract_ci_tags() -> dict[str, str]:
    import os

    tags: dict[str, str] = {}
    env_map = {
        "GITHUB_SHA": "ci_sha",
        "GITHUB_REF": "ci_ref",
        "GITHUB_REPOSITORY": "ci_repo",
        "GITHUB_RUN_ID": "ci_run_id",
        "GITLAB_CI": "ci_gitlab",
        "CI_COMMIT_SHA": "ci_sha",
        "CI_COMMIT_REF_NAME": "ci_ref",
        "JENKINS_URL": "ci_jenkins",
        "BUILD_NUMBER": "ci_build_number",
    }
    for env_var, tag_name in env_map.items():
        val = os.environ.get(env_var)
        if val:
            tags[tag_name] = val
    return tags
