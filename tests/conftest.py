"""pytest配置和共享fixtures"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "_scenarios"
SCHEMAS_DIR = PROJECT_ROOT / "_schemas"
COMPILER_DIR = PROJECT_ROOT / "_compiler"
SECURITY_DIR = PROJECT_ROOT / "_security"


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(autouse=True)
def _isolate_rule_registry():
    """规则注册表隔离: 每个测试结束恢复全局规则状态, 防止自定义规则注册/原地变更等跨测试污染

    用 deepcopy 快照规则对象: 既覆盖 _RULE_MAP 条目替换, 也覆盖对 LintRule 对象的原地 mutation
    (如 rule.severity = ...)。同时恢复 _CHECKERS/_CHECKERS_EXTENDED 列表长度。
    """
    import copy

    from ai_prompt_toolkit.linter.rules import _CHECKERS, _CHECKERS_EXTENDED, _RULE_MAP

    rules_snapshot = {k: copy.deepcopy(v) for k, v in _RULE_MAP.items()}
    checkers_len = len(_CHECKERS)
    ext_len = len(_CHECKERS_EXTENDED)
    yield
    _RULE_MAP.clear()
    _RULE_MAP.update(rules_snapshot)
    if len(_CHECKERS) > checkers_len:
        del _CHECKERS[checkers_len:]
    if len(_CHECKERS_EXTENDED) > ext_len:
        del _CHECKERS_EXTENDED[ext_len:]


@pytest.fixture
def scenarios_dir() -> Path:
    return SCENARIOS_DIR


@pytest.fixture
def schemas_dir() -> Path:
    return SCHEMAS_DIR


@pytest.fixture
def sample_template() -> str:
    return """---
version: "1.0.0"
author: "AI提示词体系"
updated_at: "2026-07-12"
tags: [test]
applicable_models: [gpt-4o]
inheritance:
  enabled: false
---

# 测试模板

{{#if model == "gpt-4o"}}
请使用JSON Mode输出。
{{#else}}
请使用Markdown格式输出。
{{/if}}
"""


@pytest.fixture
def sample_context() -> dict:
    return {"model": "gpt-4o", "language": "zh", "industry": ""}
