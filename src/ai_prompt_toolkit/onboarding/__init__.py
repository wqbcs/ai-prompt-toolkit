"""新用户3步引导v3 — 交互式Onboarding

参考 create-react-app / npm init / astro setup 交互式引导:
- Step 1: 初始化项目结构
- Step 2: 创建第一个模板并编译
- Step 3: 执行Lint+安全扫描

设计哲学: "最好的引导是用户感觉不到引导"
- 零配置启动：默认值覆盖80%场景
- 每步都有即时反馈
- 失败时给出明确修复建议
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


_PROJECT_FILES = {
    "README.md": """# AI提示词项目

由 ai-prompt-toolkit 引导创建。

## 快速开始

```bash
# 编译模板
prompt-cli compile -s templates/hello.md -c context.json

# 安全扫描
prompt-cli scan -t templates/

# 质量检查
prompt-cli lint -t templates/
```

## 项目结构

```
├── templates/        # 提示词模板
├── context.json      # 编译上下文
├── output/           # 编译输出
└── reports/          # 扫描/Lint报告
```
""",
    "context.json": json.dumps({
        "model": "gpt-4o",
        "language": "zh-CN",
        "industry": "",
    }, ensure_ascii=False, indent=2),
    "templates/hello.md": """---
version: "3.0.0"
author: "新用户"
updated_at: "{date}"
tags: [getting-started]
applicable_models: [gpt-4o, claude-3.5-sonnet, qwen-max]
inheritance:
  enabled: false
locale: zh-CN
i18n_status: untranslated
market_status: draft
lint_score: 0.0
---

# 你好，AI助手

{{#if model == gpt-4o}}
你是一个基于GPT-4o的智能助手。
{{else}}
你是一个通用AI助手。
{{/if}}

{{#if language == zh-CN}}
请使用中文回答。
{{else}}
Please respond in English.
{{/if}}

## 任务

请帮我完成以下工作：[描述你的需求]
""",
    "templates/.gitkeep": "",
    "output/.gitkeep": "",
    "reports/.gitkeep": "",
}

_SAMPLE_CONTEXT = {
    "model": "gpt-4o",
    "language": "zh-CN",
    "industry": "",
}


def run_onboarding(target_dir: str | Path | None = None, *, non_interactive: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "steps_completed": 0,
        "files_created": 0,
        "errors": [],
    }

    base = Path(target_dir) if target_dir else Path.cwd()
    base.mkdir(parents=True, exist_ok=True)

    # Step 1: 初始化项目结构
    try:
        files = _init_project(base)
        result["files_created"] = files
        result["step1"] = "ok"
        if not non_interactive:
            _print_step(1, 3, "初始化项目结构", f"创建了 {files} 个文件")
    except Exception as e:
        result["errors"].append(f"Step 1: {e}")
        result["step1"] = "error"
        if not non_interactive:
            _print_step(1, 3, "初始化项目结构", f"错误: {e}")
        return result

    result["steps_completed"] = 1

    # Step 2: 创建第一个模板并编译
    try:
        compile_result = _compile_hello(base)
        result["step2"] = "ok"
        result["compile_preview"] = compile_result[:200] if compile_result else ""
        if not non_interactive:
            _print_step(2, 3, "编译第一个模板", "编译成功")
    except Exception as e:
        result["errors"].append(f"Step 2: {e}")
        result["step2"] = "error"
        if not non_interactive:
            _print_step(2, 3, "编译第一个模板", f"错误: {e}")
        return result

    result["steps_completed"] = 2

    # Step 3: Lint + 安全扫描
    try:
        lint_result, scan_result = _run_checks(base)
        result["step3"] = "ok"
        result["lint_findings"] = lint_result
        result["scan_findings"] = scan_result
        if not non_interactive:
            _print_step(3, 3, "Lint + 安全扫描",
                        f"Lint: {lint_result}个问题 | 扫描: {scan_result}个发现")
    except Exception as e:
        result["errors"].append(f"Step 3: {e}")
        result["step3"] = "error"
        if not non_interactive:
            _print_step(3, 3, "Lint + 安全扫描", f"错误: {e}")
        return result

    result["steps_completed"] = 3

    if not non_interactive:
        _print_complete(base)

    return result


def _init_project(base: Path) -> int:
    count = 0
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for rel_path, content in _PROJECT_FILES.items():
        target = base / rel_path
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        resolved = content.replace("{date}", date_str)
        target.write_text(resolved, encoding="utf-8")
        count += 1
    return count


def _compile_hello(base: Path) -> str:
    from ai_prompt_toolkit.compiler import compile_template, CompileContext
    template_path = base / "templates" / "hello.md"
    if not template_path.exists():
        return ""

    text = template_path.read_text(encoding="utf-8")
    ctx = CompileContext(model="gpt-4o", language="zh-CN")
    result = compile_template(text, ctx, use_cache=False)
    return result.compiled_text


def _run_checks(base: Path) -> tuple[int, int]:
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector

    template_path = base / "templates" / "hello.md"
    if not template_path.exists():
        return (0, 0)

    text = template_path.read_text(encoding="utf-8")

    linter = PromptLinter()
    lint_result = linter.lint("hello.md", text)
    lint_findings = lint_result.failed_count

    detector = InjectionDetector()
    scan_findings = len(detector.detect(text))

    return (lint_findings, scan_findings)


def _print_step(step: int, total: int, title: str, status: str) -> None:
    print(f"\n{'='*50}")
    print(f"  Step {step}/{total}: {title}")
    print(f"  {status}")
    print(f"{'='*50}")


def _print_complete(base: Path) -> None:
    print(f"\n{'='*50}")
    print("  引导完成!")
    print(f"  项目目录: {base}")
    print("  下一步:")
    print("    1. 编辑 templates/hello.md 创建你的提示词")
    print("    2. 修改 context.json 设置编译上下文")
    print("    3. 运行 prompt-cli compile -s templates/hello.md -c context.json")
    print(f"{'='*50}")
