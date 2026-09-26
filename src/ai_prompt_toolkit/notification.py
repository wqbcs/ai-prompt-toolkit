"""通知系统 — 参考promptfoo PR评论+Langfuse webhook

核心特性:
- DingTalk/Feishu/Slack/Webhook四大适配器
- YAML配置式通知(promiseval.yaml notifications块)
- Plugin notification Hook集成
- 消息模板引擎(Jinja2风格变量替换)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TEMPLATES: dict[str, str] = {
    "lint_failed": (
        "❌ Prompt Lint失败\n"
        "文件: {{file_path}}\n"
        "发现项: {{total_findings}}\n"
        "严重: {{critical_count}} critical, {{high_count}} high"
    ),
    "lint_passed": ("✅ Prompt Lint通过\n文件: {{file_path}}\n发现项: {{total_findings}}"),
    "scan_failed": (
        "🚨 安全扫描发现风险\n文件: {{file_path}}\n风险: {{total_findings}}\n严重: {{critical_count}} critical"
    ),
    "eval_failed": ("📉 Prompt评估未达标\n文件: {{file_path}}\n分数: {{score}}/{{max_score}}\n阈值: {{threshold}}"),
    "eval_passed": ("📈 Prompt评估通过\n文件: {{file_path}}\n分数: {{score}}/{{max_score}}"),
    "gepa_improved": (
        "🚀 GEPA优化成功\n"
        "Prompt: {{prompt_name}}\n"
        "初始: {{initial_score}} → 最优: {{best_score}}\n"
        "提升: {{improvement}}"
    ),
    "redteam_vulnerability": ("🔴 红队扫描发现漏洞\n目标: {{target}}\n漏洞数: {{vulnerabilities}}"),
    "contest_ready": (
        "🏆 赛事就绪度评估\n"
        "分数: {{contest_score}}/10\n"
        "等级: {{readiness_level}}\n"
        "盘古: {{pangu_status}} | 鸿蒙: {{harmony_status}}"
    ),
}


def render_template(template: str, variables: dict[str, Any]) -> str:
    result = template
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value))
    return result


@dataclass
class NotificationConfig:
    type: str = ""
    webhook: str = ""
    secret: str = ""
    message_template: str = ""
    enabled: bool = True
    events: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "webhook": self.webhook[:20] + "..." if self.webhook else "",
            "enabled": self.enabled,
            "events": self.events,
        }


class NotificationAdapter(ABC):
    @abstractmethod
    def send(self, message: str, config: NotificationConfig) -> bool: ...


class DingTalkAdapter(NotificationAdapter):
    def send(self, message: str, config: NotificationConfig) -> bool:
        url = config.webhook
        if not url:
            return False

        payload: dict[str, Any] = {
            "msgtype": "markdown",
            "markdown": {
                "title": "AI Prompt Toolkit",
                "text": message,
            },
        }

        if config.secret:
            timestamp = str(int(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{config.secret}"
            hmac_code = hmac.new(
                config.secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            sign = urllib.parse.quote_plus(hmac_code)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}timestamp={timestamp}&sign={sign}"

        return _post_json(url, payload)


class FeishuAdapter(NotificationAdapter):
    def send(self, message: str, config: NotificationConfig) -> bool:
        url = config.webhook
        if not url:
            return False

        payload: dict[str, Any] = {
            "msg_type": "interactive",
            "card": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": message,
                    }
                ],
                "header": {
                    "title": {"tag": "plain_text", "content": "AI Prompt Toolkit"},
                },
            },
        }

        if config.secret:
            timestamp = str(int(time.time()))
            string_to_sign = f"{timestamp}\n{config.secret}"
            hmac_code = hmac.new(
                config.secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            sign = hmac_code.hexdigest()
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}timestamp={timestamp}&sign={sign}"

        return _post_json(url, payload)


class SlackAdapter(NotificationAdapter):
    def send(self, message: str, config: NotificationConfig) -> bool:
        url = config.webhook
        if not url:
            return False

        payload: dict[str, Any] = {
            "text": message,
        }
        return _post_json(url, payload)


class WebhookAdapter(NotificationAdapter):
    def send(self, message: str, config: NotificationConfig) -> bool:
        url = config.webhook
        if not url:
            return False

        payload: dict[str, Any] = {
            "event": "promptkit_notification",
            "message": message,
            "timestamp": time.time(),
        }
        headers = {"Content-Type": "application/json"}
        if config.secret:
            headers["Authorization"] = f"Bearer {config.secret}"

        return _post_json(url, payload, headers=headers)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> bool:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        logger.exception("Failed to send notification to %s", url[:30])
        return False


_ADAPTER_MAP: dict[str, type[NotificationAdapter]] = {
    "dingtalk": DingTalkAdapter,
    "feishu": FeishuAdapter,
    "slack": SlackAdapter,
    "webhook": WebhookAdapter,
}


@dataclass
class NotificationManager:
    configs: list[NotificationConfig] = field(default_factory=list)

    def add_config(self, config: NotificationConfig) -> None:
        self.configs.append(config)

    def remove_config(self, index: int) -> bool:
        if 0 <= index < len(self.configs):
            del self.configs[index]
            return True
        return False

    def notify(self, event: str, variables: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        template_key = event
        template = _DEFAULT_TEMPLATES.get(template_key, event)

        for config in self.configs:
            if not config.enabled:
                continue
            if config.events and event not in config.events:
                continue

            adapter_cls = _ADAPTER_MAP.get(config.type)
            if adapter_cls is None:
                logger.warning("Unknown notification type: %s", config.type)
                continue

            msg_template = config.message_template or template
            message = render_template(msg_template, variables)

            adapter = adapter_cls()
            try:
                success = adapter.send(message, config)
                results.append(
                    {
                        "type": config.type,
                        "event": event,
                        "success": success,
                    }
                )
            except Exception as e:
                logger.exception("Notification %s failed", config.type)
                results.append(
                    {
                        "type": config.type,
                        "event": event,
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    def test_connection(self, config: NotificationConfig) -> bool:
        adapter_cls = _ADAPTER_MAP.get(config.type)
        if adapter_cls is None:
            return False
        adapter = adapter_cls()
        return adapter.send("🔧 AI Prompt Toolkit 通知测试", config)

    def list_configs(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self.configs]

    @classmethod
    def from_yaml_config(cls, config_data: dict[str, Any]) -> NotificationManager:
        manager = cls()
        notifications = config_data.get("notifications", {})
        for trigger_type, channels in notifications.items():
            if not isinstance(channels, list):
                continue
            for ch in channels:
                events = ch.get("events", [])
                if trigger_type == "on_failure" and not events:
                    events = ["lint_failed", "scan_failed", "eval_failed", "redteam_vulnerability"]
                elif trigger_type == "on_success" and not events:
                    events = ["lint_passed", "eval_passed", "gepa_improved", "contest_ready"]

                manager.add_config(
                    NotificationConfig(
                        type=ch.get("type", "webhook"),
                        webhook=ch.get("webhook", ""),
                        secret=ch.get("secret", ""),
                        message_template=ch.get("message_template", ""),
                        enabled=ch.get("enabled", True),
                        events=events,
                    )
                )
        return manager
