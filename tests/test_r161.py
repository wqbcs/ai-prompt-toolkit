"""R161: 声明式Lint+Eval测试套件"""

import json

from ai_prompt_toolkit.linter.test_suite import (
    Assertion,
    TestGroup,
    TestSuite,
    load_test_suite,
    run_test_suite,
)


def test_load_test_suite_yaml(tmp_path):
    suite = tmp_path / "suite.yaml"
    suite.write_text("""
name: my-prompt-tests
version: "1.0"
description: 测试套件
groups:
  - name: security-check
    target: prompts/
    assertions:
      - type: score
        threshold: 80.0
      - type: max_findings
        max_findings: 5
      - type: max_severity
        max_severity: medium
    eval_dimensions:
      - relevance
      - safety
""")
    ts = load_test_suite(suite)
    assert ts.name == "my-prompt-tests"
    assert len(ts.groups) == 1
    assert ts.groups[0].name == "security-check"
    assert len(ts.groups[0].assertions) == 3
    assert ts.groups[0].assertions[0].threshold == 80.0
    assert ts.groups[0].assertions[1].max_findings == 5


def test_load_test_suite_json(tmp_path):
    suite = tmp_path / "suite.json"
    suite.write_text(
        json.dumps(
            {
                "name": "test",
                "version": "2.0",
                "groups": [{"name": "g1", "target": ".", "assertions": [{"type": "score", "threshold": 90}]}],
            }
        )
    )
    ts = load_test_suite(suite)
    assert ts.name == "test"
    assert ts.version == "2.0"


def test_test_suite_to_dict():
    ts = TestSuite(name="test", groups=[TestGroup(name="g1", assertions=[Assertion(threshold=85.0)])])
    d = ts.to_dict()
    assert d["name"] == "test"
    assert d["groups"][0]["assertions"][0]["threshold"] == 85.0


def test_assertion_defaults():
    a = Assertion()
    assert a.type == "score"
    assert a.threshold == 80.0


def test_run_test_suite_empty(tmp_path):
    ts = TestSuite(name="empty", groups=[])
    result = run_test_suite(ts, base_dir=str(tmp_path))
    assert result["passed"] is True
