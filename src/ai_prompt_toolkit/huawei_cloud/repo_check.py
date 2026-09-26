"""华为云CodeArts Repo规范检查

检查代码仓库是否符合华为云CodeArts规范:
- .codearts/pipeline.yml 存在性+完整性
- .codearts/repo.yml 仓库规范配置
- README.md 存在性
- LICENSE 文件存在性
- .gitignore 存在性
- 代码检查配置(codearts-check)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RepoCheckResult:
    check_name: str
    passed: bool
    message: str
    severity: str = "medium"
    fix_hint: str = ""


_CODEARTS_PIPELINE_REQUIRED_KEYS = {"stages", "name"}
_CODEARTS_REPO_REQUIRED_KEYS = {"project", "quality"}


def check_codearts_repo(repo_root: str | Path) -> list[RepoCheckResult]:
    results = []
    root = Path(repo_root)

    results.append(_check_pipeline(root))
    results.append(_check_repo_yml(root))
    results.append(_check_readme(root))
    results.append(_check_license(root))
    results.append(_check_gitignore(root))
    results.append(_check_changelog(root))
    results.append(_check_contributing(root))

    return results


def _check_pipeline(root: Path) -> RepoCheckResult:
    pipeline_path = root / ".codearts" / "pipeline.yml"
    if not pipeline_path.exists():
        return RepoCheckResult(
            "pipeline.yml",
            False,
            ".codearts/pipeline.yml 不存在, 缺少CI/CD流水线配置",
            "high",
            "创建 .codearts/pipeline.yml 参考华为云CodeArts Pipeline模板",
        )
    try:
        import yaml

        data = yaml.safe_load(pipeline_path.read_text(encoding="utf-8")) or {}
        missing = _CODEARTS_PIPELINE_REQUIRED_KEYS - set(data.keys())
        if missing:
            return RepoCheckResult(
                "pipeline.yml",
                False,
                f"pipeline.yml 缺少必要字段: {missing}",
                "medium",
                f"在pipeline.yml中添加 {missing} 字段",
            )
        return RepoCheckResult("pipeline.yml", True, "pipeline.yml 完整", "low")
    except Exception as e:
        return RepoCheckResult("pipeline.yml", False, f"pipeline.yml 解析失败: {e}", "high")


def _check_repo_yml(root: Path) -> RepoCheckResult:
    repo_path = root / ".codearts" / "repo.yml"
    if not repo_path.exists():
        return RepoCheckResult(
            "repo.yml",
            False,
            ".codearts/repo.yml 不存在, 缺少仓库规范配置",
            "medium",
            "创建 .codearts/repo.yml 配置项目质量门禁和代码规范",
        )
    return RepoCheckResult("repo.yml", True, "repo.yml 存在", "low")


def _check_readme(root: Path) -> RepoCheckResult:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        if (root / name).exists():
            return RepoCheckResult("README", True, f"{name} 存在", "low")
    return RepoCheckResult("README", False, "缺少 README 文件", "high", "创建 README.md 包含项目说明/安装/使用")


def _check_license(root: Path) -> RepoCheckResult:
    for name in ("LICENSE", "LICENSE.md", "LICENCE", "COPYING"):
        if (root / name).exists():
            return RepoCheckResult("LICENSE", True, f"{name} 存在", "low")
    return RepoCheckResult("LICENSE", False, "缺少 LICENSE 文件", "high", "添加开源许可证文件(如MIT/Apache-2.0)")


def _check_gitignore(root: Path) -> RepoCheckResult:
    if (root / ".gitignore").exists():
        return RepoCheckResult(".gitignore", True, ".gitignore 存在", "low")
    return RepoCheckResult(
        ".gitignore", False, "缺少 .gitignore", "medium", "添加 .gitignore 排除 __pycache__/.env/dist等"
    )


def _check_changelog(root: Path) -> RepoCheckResult:
    if (root / "CHANGELOG.md").exists():
        return RepoCheckResult("CHANGELOG", True, "CHANGELOG.md 存在", "low")
    return RepoCheckResult("CHANGELOG", False, "缺少 CHANGELOG.md", "medium", "创建 CHANGELOG.md 记录版本变更")


def _check_contributing(root: Path) -> RepoCheckResult:
    if (root / "CONTRIBUTING.md").exists():
        return RepoCheckResult("CONTRIBUTING", True, "CONTRIBUTING.md 存在", "low")
    return RepoCheckResult("CONTRIBUTING", False, "缺少 CONTRIBUTING.md", "low", "创建 CONTRIBUTING.md 指导贡献者")


def generate_repo_yml_template() -> str:
    return """\
# 华为云CodeArts Repo规范配置
project:
  name: ai-prompt-toolkit
  description: AI提示词体系工具链 - ESLint for Prompts
  language: python
  version: "53.0.0"

quality:
  lint:
    enabled: true
    rules_count: 210
    auto_fixable: 151
  security_scan:
    enabled: true
  test_coverage:
    minimum: 80
  quality_gate:
    enabled: true
    score_threshold: 70
    max_critical: 0
    max_high: 5

codearts:
  pipeline: .codearts/pipeline.yml
  check:
    enabled: true
    tools:
      - ruff
      - mypy
      - pytest
"""
