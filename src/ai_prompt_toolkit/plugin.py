"""Plugin系统v2 — 参考pluggy+setuptools entry_points双层架构

增强特性:
- setuptools entry_points自动发现(pip安装即插即用)
- 更多Hook: lint/scan/evaluate/compile/gepa_optimize/flow_run/notification
- wrapper钩子: before/after生命周期
- 通知Hook: on_notify发送评估结果
"""

from __future__ import annotations

import importlib
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_HOOK_NAMES = frozenset(
    {
        "lint",
        "scan",
        "evaluate",
        "compile",
        "gepa_optimize",
        "flow_run",
        "notification",
    }
)

_WRAPPER_HOOK_NAMES = frozenset(
    {
        "before_lint",
        "after_lint",
        "before_scan",
        "after_scan",
        "before_evaluate",
        "after_evaluate",
        "before_compile",
        "after_compile",
        "before_gepa_optimize",
        "after_gepa_optimize",
        "before_flow_run",
        "after_flow_run",
    }
)


@dataclass
class PluginMeta:
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    hooks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "hooks": self.hooks,
        }


class PluginHook(ABC):
    @abstractmethod
    def name(self) -> str: ...

    def on_lint(self, template: str, findings: list[Any]) -> list[Any]:
        return findings

    def on_scan(self, template: str, findings: list[Any]) -> list[Any]:
        return findings

    def on_evaluate(self, template: str, report: Any) -> Any:
        return report

    def on_compile(self, template: str, compiled: str) -> str:
        return compiled

    def on_gepa_optimize(self, prompt: str, result: Any) -> Any:
        return result

    def on_flow_run(self, flow_name: str, result: Any) -> Any:
        return result

    def on_notify(self, event: str, data: dict[str, Any]) -> dict[str, Any]:
        return data

    def before_lint(self, template: str) -> str:
        return template

    def after_lint(self, template: str, findings: list[Any]) -> list[Any]:
        return findings

    def before_scan(self, template: str) -> str:
        return template

    def after_scan(self, template: str, findings: list[Any]) -> list[Any]:
        return findings

    def before_evaluate(self, template: str) -> str:
        return template

    def after_evaluate(self, template: str, report: Any) -> Any:
        return report

    def before_compile(self, template: str) -> str:
        return template

    def after_compile(self, template: str, compiled: str) -> str:
        return compiled

    def before_gepa_optimize(self, prompt: str) -> str:
        return prompt

    def after_gepa_optimize(self, prompt: str, result: Any) -> Any:
        return result

    def before_flow_run(self, flow_name: str) -> str:
        return flow_name

    def after_flow_run(self, flow_name: str, result: Any) -> Any:
        return result


class Plugin:
    def __init__(self, meta: PluginMeta, hooks: list[PluginHook] | None = None) -> None:
        self.meta = meta
        self._hooks = hooks or []
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def get_hook(self, hook_name: str) -> PluginHook | None:
        for h in self._hooks:
            if h.name() == hook_name:
                return h
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "enabled": self._enabled,
            "hook_count": len(self._hooks),
        }


class PluginManager:
    _instance: PluginManager | None = None

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    @classmethod
    def get_instance(cls) -> PluginManager:
        if cls._instance is None:
            cls._instance = PluginManager()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def register(self, plugin: Plugin) -> None:
        if plugin.meta.name in self._plugins:
            logger.warning("Plugin %s already registered, replacing", plugin.meta.name)
        self._plugins[plugin.meta.name] = plugin
        logger.info("Plugin registered: %s v%s", plugin.meta.name, plugin.meta.version)

    def unregister(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    def get_plugin(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def get_enabled_plugins(self) -> list[Plugin]:
        return [p for p in self._plugins.values() if p.enabled]

    def load_from_module(self, module_path: str) -> Plugin | None:
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, "create_plugin"):
                # R201: 显式标注收窄Any — 消除no-any-return
                plugin: Plugin | None = module.create_plugin()
                if plugin is None:
                    return None  # R199: create_plugin契约允许返回None
                self.register(plugin)
                return plugin
            logger.warning("Module %s has no create_plugin()", module_path)
            return None
        except Exception:
            logger.exception("Failed to load plugin from %s", module_path)
            return None

    def load_from_file(self, file_path: Path | str) -> Plugin | None:
        p = Path(file_path)
        if not p.exists():
            logger.warning("Plugin file not found: %s", file_path)
            return None
        import importlib.util

        spec = importlib.util.spec_from_file_location(p.stem, str(p))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "create_plugin"):
            # R201: 显式标注收窄Any — 消除no-any-return
            plugin: Plugin | None = module.create_plugin()
            if plugin is None:
                return None  # R199: create_plugin契约允许返回None
            self.register(plugin)
            return plugin
        return None

    def load_from_directory(self, dir_path: Path | str) -> list[Plugin]:
        p = Path(dir_path)
        if not p.is_dir():
            return []
        loaded = []
        for py_file in sorted(p.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            plugin = self.load_from_file(py_file)
            if plugin:
                loaded.append(plugin)
        return loaded

    def load_from_entry_points(self, group: str = "promptkit.plugins") -> list[Plugin]:
        try:
            if sys.version_info >= (3, 12) or sys.version_info >= (3, 10):
                from importlib.metadata import entry_points as _ep

                eps = _ep(group=group)
            else:
                from importlib.metadata import entry_points as _ep

                all_eps = _ep()
                eps = [ep for ep in all_eps.get("promptkit.plugins", []) if ep.group == group]
        except Exception:
            logger.debug("Failed to load entry_points for group %s", group)
            return []

        loaded = []
        for ep in eps:
            try:
                factory = ep.load()
                if callable(factory):
                    plugin = factory() if not isinstance(factory, Plugin) else factory
                    if isinstance(plugin, Plugin):
                        self.register(plugin)
                        loaded.append(plugin)
                    elif hasattr(plugin, "create_plugin"):
                        p = plugin.create_plugin()
                        self.register(p)
                        loaded.append(p)
            except Exception:
                logger.exception("Failed to load entry_point %s", ep.name)
        return loaded

    def fire_hook(self, hook_name: str, **kwargs: Any) -> Any:
        result = kwargs
        for plugin in self.get_enabled_plugins():
            for hook in plugin._hooks:
                try:
                    method = getattr(hook, f"on_{hook_name}", None)
                    if method is None:
                        continue
                    if hook_name == "lint" or hook_name == "scan":
                        result["findings"] = method(kwargs.get("template", ""), kwargs.get("findings", []))
                    elif hook_name == "evaluate":
                        result["report"] = method(kwargs.get("template", ""), kwargs.get("report"))
                    elif hook_name == "compile":
                        result["compiled"] = method(kwargs.get("template", ""), kwargs.get("compiled", ""))
                    elif hook_name == "gepa_optimize":
                        result["result"] = method(kwargs.get("prompt", ""), kwargs.get("result"))
                    elif hook_name == "flow_run":
                        result["result"] = method(kwargs.get("flow_name", ""), kwargs.get("result"))
                    elif hook_name == "notification":
                        result["data"] = method(kwargs.get("event", ""), kwargs.get("data", {}))
                except Exception:
                    logger.exception("Plugin %s hook %s failed", plugin.meta.name, hook_name)
        return result

    def fire_before_hook(self, hook_name: str, **kwargs: Any) -> Any:
        result = kwargs
        for plugin in self.get_enabled_plugins():
            for hook in plugin._hooks:
                try:
                    method = getattr(hook, f"before_{hook_name}", None)
                    if method is None:
                        continue
                    if hook_name in ("lint", "scan", "evaluate", "compile"):
                        result["template"] = method(kwargs.get("template", ""))
                    elif hook_name == "gepa_optimize":
                        result["prompt"] = method(kwargs.get("prompt", ""))
                    elif hook_name == "flow_run":
                        result["flow_name"] = method(kwargs.get("flow_name", ""))
                except Exception:
                    logger.exception("Plugin %s before_%s failed", plugin.meta.name, hook_name)
        return result

    def fire_after_hook(self, hook_name: str, **kwargs: Any) -> Any:
        result = kwargs
        for plugin in self.get_enabled_plugins():
            for hook in plugin._hooks:
                try:
                    method = getattr(hook, f"after_{hook_name}", None)
                    if method is None:
                        continue
                    if hook_name in ("lint", "scan"):
                        result["findings"] = method(kwargs.get("template", ""), kwargs.get("findings", []))
                    elif hook_name == "evaluate":
                        result["report"] = method(kwargs.get("template", ""), kwargs.get("report"))
                    elif hook_name == "compile":
                        result["compiled"] = method(kwargs.get("template", ""), kwargs.get("compiled", ""))
                    elif hook_name == "gepa_optimize":
                        result["result"] = method(kwargs.get("prompt", ""), kwargs.get("result"))
                    elif hook_name == "flow_run":
                        result["result"] = method(kwargs.get("flow_name", ""), kwargs.get("result"))
                except Exception:
                    logger.exception("Plugin %s after_%s failed", plugin.meta.name, hook_name)
        return result

    def fire_notification(self, event: str, data: dict[str, Any]) -> dict[str, Any]:
        for plugin in self.get_enabled_plugins():
            for hook in plugin._hooks:
                try:
                    data = hook.on_notify(event, data)
                except Exception:
                    logger.exception("Plugin %s notification failed", plugin.meta.name)
        return data

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_plugins": len(self._plugins),
            "enabled_plugins": len(self.get_enabled_plugins()),
            "plugins": [p.to_dict() for p in self._plugins.values()],
        }
