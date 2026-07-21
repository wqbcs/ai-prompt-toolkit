"""i18n消息翻译 — CLI/Playground界面文本的国际化支持

参考: gettext + babel
- 中英文双语消息
- 运行时切换语言
- 支持变量插值
"""

from __future__ import annotations

import locale as _locale
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_LOCALE = "zh-CN"

_MESSAGES: dict[str, dict[str, str]] = {
    "zh-CN": {
        "cli.lint.start": "开始Lint检查...",
        "cli.lint.complete": "Lint检查完成",
        "cli.lint.no_findings": "未发现问题",
        "cli.lint.findings_count": "发现{count}个问题",
        "cli.scan.start": "开始安全扫描...",
        "cli.scan.complete": "安全扫描完成",
        "cli.scan.critical": "发现{count}个严重安全问题",
        "cli.evaluate.start": "开始质量评估...",
        "cli.evaluate.complete": "质量评估完成",
        "cli.evaluate.score": "综合评分: {score}/100",
        "cli.compile.start": "开始条件编译...",
        "cli.compile.complete": "条件编译完成",
        "cli.compile.error": "编译失败，请检查模板语法",
        "cli.dataset.created": "数据集已创建: {id}",
        "cli.dataset.deleted": "数据集已删除: {id}",
        "cli.dataset.imported": "已导入{count}条用例",
        "cli.dataset.exported": "已导出到: {path}",
        "cli.watch.start": "Watch模式启动",
        "cli.watch.exit": "Watch模式已退出",
        "cli.init.welcome": "欢迎使用AI Prompt Toolkit!",
        "playground.title": "AI Prompt Toolkit Playground",
        "playground.compile": "编译",
        "playground.lint": "Lint",
        "playground.scan": "安全扫描",
        "playground.evaluate": "评估",
        "playground.market": "模板市场",
        "playground.trace": "追踪",
        "playground.dataset": "数据集",
        "playground.scorecard": "评分卡",
        "cli.score.start": "开始安全评分...",
        "cli.score.complete": "安全评分完成",
        "cli.score.grade": "评分等级: {grade} ({score}/100)",
        "cli.score.decision": "决策: {decision}",
        "cli.rules_yaml.generated": "示例规则文件已生成到: {path}",
        "cli.rules_yaml.loaded": "已加载{count}条自定义规则",
        "cli.anomaly.detected": "异常检测: {description}",
        "cli.sarif.exported": "SARIF报告已导出到: {path}",
        "error.generic": "操作失败",
        "error.no_file": "请打开一个Markdown文件",
        "error.timeout": "操作超时",
        "success.saved": "已保存",
        "success.completed": "操作完成",
    },
    "en-US": {
        "cli.lint.start": "Starting lint check...",
        "cli.lint.complete": "Lint check completed",
        "cli.lint.no_findings": "No issues found",
        "cli.lint.findings_count": "Found {count} issues",
        "cli.scan.start": "Starting security scan...",
        "cli.scan.complete": "Security scan completed",
        "cli.scan.critical": "Found {count} critical security issues",
        "cli.evaluate.start": "Starting evaluation...",
        "cli.evaluate.complete": "Evaluation completed",
        "cli.evaluate.score": "Overall score: {score}/100",
        "cli.compile.start": "Starting compilation...",
        "cli.compile.complete": "Compilation completed",
        "cli.compile.error": "Compilation failed, check template syntax",
        "cli.dataset.created": "Dataset created: {id}",
        "cli.dataset.deleted": "Dataset deleted: {id}",
        "cli.dataset.imported": "Imported {count} cases",
        "cli.dataset.exported": "Exported to: {path}",
        "cli.watch.start": "Watch mode started",
        "cli.watch.exit": "Watch mode exited",
        "cli.init.welcome": "Welcome to AI Prompt Toolkit!",
        "playground.title": "AI Prompt Toolkit Playground",
        "playground.compile": "Compile",
        "playground.lint": "Lint",
        "playground.scan": "Security",
        "playground.evaluate": "Evaluate",
        "playground.market": "Market",
        "playground.trace": "Trace",
        "playground.dataset": "Dataset",
        "playground.scorecard": "Scorecard",
        "cli.score.start": "Starting security scoring...",
        "cli.score.complete": "Security scoring completed",
        "cli.score.grade": "Grade: {grade} ({score}/100)",
        "cli.score.decision": "Decision: {decision}",
        "cli.rules_yaml.generated": "Sample rules file generated: {path}",
        "cli.rules_yaml.loaded": "Loaded {count} custom rules",
        "cli.anomaly.detected": "Anomaly detected: {description}",
        "cli.sarif.exported": "SARIF report exported to: {path}",
        "error.generic": "Operation failed",
        "error.no_file": "Please open a Markdown file",
        "error.timeout": "Operation timed out",
        "success.saved": "Saved",
        "success.completed": "Completed",
    },
}

_current_locale: str = ""


def _detect_system_locale() -> str:
    try:
        loc = _locale.getdefaultlocale()[0]
        if loc:
            if loc.startswith("zh"):
                return "zh-CN"
            if loc.startswith("en"):
                return "en-US"
    except Exception:
        pass
    return _DEFAULT_LOCALE


def get_current_locale() -> str:
    global _current_locale
    if not _current_locale:
        _current_locale = _detect_system_locale()
    return _current_locale


def set_locale(loc: str) -> None:
    global _current_locale
    if loc in _MESSAGES:
        _current_locale = loc
    else:
        _current_locale = _DEFAULT_LOCALE


def get_supported_locales() -> list[str]:
    return list(_MESSAGES.keys())


def t(key: str, **kwargs: Any) -> str:
    loc = get_current_locale()
    msg = _MESSAGES.get(loc, {}).get(key)
    if msg is None:
        msg = _MESSAGES.get(_DEFAULT_LOCALE, {}).get(key)
    if msg is None:
        return key
    if kwargs:
        try:
            return msg.format(**kwargs)
        except (KeyError, IndexError):
            return msg
    return msg


def add_messages(loc: str, messages: dict[str, str]) -> None:
    if loc not in _MESSAGES:
        _MESSAGES[loc] = {}
    _MESSAGES[loc].update(messages)
