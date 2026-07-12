"""pytest配置和共享fixtures"""

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "_scenarios"
SCHEMAS_DIR = PROJECT_ROOT / "_schemas"
COMPILER_DIR = PROJECT_ROOT / "_compiler"
SECURITY_DIR = PROJECT_ROOT / "_security"


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


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
