"""Probe子模块 — 自动发现+注册机制

参考garak probes/__init__.py模块化probe加载模式
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

from ai_prompt_toolkit.redteam.probe import _PROBE_REGISTRY, BaseProbe

logger = logging.getLogger(__name__)


def _discover_probes() -> dict[str, type[BaseProbe]]:
    probes_dir = Path(__file__).parent
    for py_file in sorted(probes_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = f"ai_prompt_toolkit.redteam.probes.{py_file.stem}"
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseProbe)
                    and attr is not BaseProbe
                    and hasattr(attr, "__init__")
                ):
                    try:
                        instance = attr()
                        if instance.name not in _PROBE_REGISTRY:
                            _PROBE_REGISTRY[instance.name] = attr
                            logger.debug("注册Probe: %s → %s", instance.name, attr.__name__)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("加载probe模块失败 %s: %s", py_file.name, e)
    return dict(_PROBE_REGISTRY)


_discover_probes()


def get_available_probes() -> list[str]:
    return list(_PROBE_REGISTRY.keys())
