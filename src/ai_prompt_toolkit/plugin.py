"""Plugin系统基础 — 参考promptfoo plugin + pluggy

- 插件注册/发现/加载
- Hook机制: lint/scan/evaluate/compiler 四个扩展点
- 支持Python包和文件两种插件形式
- 插件隔离: 每个插件独立命名空间
"""
from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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
    def name(self) -> str:
        ...

    def on_lint(self, template: str, findings: list[Any]) -> list[Any]:
        return findings

    def on_scan(self, template: str, findings: list[Any]) -> list[Any]:
        return findings

    def on_evaluate(self, template: str, report: Any) -> Any:
        return report

    def on_compile(self, template: str, compiled: str) -> str:
        return compiled


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
                plugin = module.create_plugin()
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
            plugin = module.create_plugin()
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

    def fire_hook(self, hook_name: str, **kwargs: Any) -> Any:
        result = kwargs
        for plugin in self.get_enabled_plugins():
            hook = plugin.get_hook(hook_name)
            if hook is None:
                continue
            try:
                method = getattr(hook, f"on_{hook_name}", None)
                if method:
                    if hook_name == "lint":
                        result["findings"] = method(kwargs.get("template", ""), kwargs.get("findings", []))
                    elif hook_name == "scan":
                        result["findings"] = method(kwargs.get("template", ""), kwargs.get("findings", []))
                    elif hook_name == "evaluate":
                        result["report"] = method(kwargs.get("template", ""), kwargs.get("report"))
                    elif hook_name == "compile":
                        result["compiled"] = method(kwargs.get("template", ""), kwargs.get("compiled", ""))
            except Exception:
                logger.exception("Plugin %s hook %s failed", plugin.meta.name, hook_name)
        return result

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_plugins": len(self._plugins),
            "enabled_plugins": len(self.get_enabled_plugins()),
            "plugins": [p.to_dict() for p in self._plugins.values()],
        }
