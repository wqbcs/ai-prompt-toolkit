"""统一Probe/Detector注册表 — 全局查询索引 + 统一注册入口

聚合probe_framework._PROBE_REGISTRY和redteam.probe._PROBE_REGISTRY
两个注册体系为统一查询视图与统一注册API。

架构(R207统一):
- probe_framework._PROBE_REGISTRY: 23个Probe(ProbeRunner兼容, generate()接口)
- redteam.probe._PROBE_REGISTRY: 5内置+自动发现的Probe(ExplorationOrchestrator兼容,
  generate_inputs()接口)
- 本模块职责:
  1. 统一查询视图: get_global_probe_registry()合并两处(带缓存, id稳定), 按来源标记
  2. 统一注册入口: register_probe()/register_detector()装饰器 — 新增Probe一处注册
  3. 命名冲突检测: 两套体系同名时记录warning, 视图以probe_framework优先

参考: garak统一registry模式
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_P = TypeVar("_P")

_PROBE_REGISTRY_CACHE: dict[str, dict[str, Any]] | None = None
_DETECTOR_REGISTRY_CACHE: dict[str, dict[str, Any]] | None = None


def _build_probe_registry() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    try:
        from ai_prompt_toolkit.probe_framework import _PROBE_REGISTRY as PF_PROBES

        for name, cls in PF_PROBES.items():
            # R197: 显式标注 — 两套BaseProbe体系(probe_framework/redteam)是不同类,
            # 不标注会被首个循环定形为type[PF.BaseProbe]
            entry: dict[str, Any] = {"cls": cls, "source": "probe_framework"}
            merged[name] = entry
    except ImportError:
        pass
    try:
        from ai_prompt_toolkit.redteam.probe import _PROBE_REGISTRY as RT_PROBES

        for rt_name, rt_cls in RT_PROBES.items():  # R197: 改名防cls跨体系循环复用
            if rt_name in merged:
                # R207: 命名冲突不再静默忽略 — 记录warning便于排查
                logger.warning(
                    "Probe命名冲突: %s 同时存在于probe_framework与redteam两套体系, 统一视图以probe_framework优先",
                    rt_name,
                )
                continue
            rt_entry: dict[str, Any] = {"cls": rt_cls, "source": "redteam"}
            merged[rt_name] = rt_entry
    except ImportError:
        pass
    return merged


def _build_detector_registry() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    try:
        from ai_prompt_toolkit.probe_framework import _DETECTOR_REGISTRY as PF_DETECTORS

        for name, cls in PF_DETECTORS.items():
            # R197: 显式标注 — 两套BaseDetector体系是不同类, 防首个循环定形
            entry: dict[str, Any] = {"cls": cls, "source": "probe_framework"}
            merged[name] = entry
    except ImportError:
        pass
    try:
        from ai_prompt_toolkit.redteam.detector import _DETECTOR_REGISTRY as RT_DETECTORS

        for rt_name, rt_det in RT_DETECTORS.items():  # R197: 改名防cls跨体系循环复用
            if rt_name in merged:
                logger.warning(
                    "Detector命名冲突: %s 同时存在于两套体系, 统一视图以probe_framework优先",
                    rt_name,
                )
                continue
            rt_det_entry: dict[str, Any] = {"cls": rt_det, "source": "redteam"}
            merged[rt_name] = rt_det_entry
    except ImportError:
        pass
    return merged


def get_global_probe_registry() -> dict[str, dict[str, Any]]:
    """统一Probe视图(缓存对象, 多次调用返回同一dict实例, id稳定)"""
    global _PROBE_REGISTRY_CACHE
    if _PROBE_REGISTRY_CACHE is None:
        _PROBE_REGISTRY_CACHE = _build_probe_registry()
    return _PROBE_REGISTRY_CACHE


def get_global_detector_registry() -> dict[str, dict[str, Any]]:
    """统一Detector视图(缓存对象, 多次调用返回同一dict实例, id稳定)"""
    global _DETECTOR_REGISTRY_CACHE
    if _DETECTOR_REGISTRY_CACHE is None:
        _DETECTOR_REGISTRY_CACHE = _build_detector_registry()
    return _DETECTOR_REGISTRY_CACHE


def invalidate_registry_cache() -> None:
    """清空统一视图缓存 — 新增Probe注册后调用, 使视图可见新条目"""
    global _PROBE_REGISTRY_CACHE, _DETECTOR_REGISTRY_CACHE
    _PROBE_REGISTRY_CACHE = None
    _DETECTOR_REGISTRY_CACHE = None


def register_probe(probe_cls: type | None = None, *, source: str = "redteam") -> Callable[[type[_P]], type[_P]] | type:
    """统一Probe注册装饰器 — 新增Probe一处注册

    用法(红队体系):
        @register_probe()
        class MyProbe(BaseProbe): ...

    用法(probe_framework体系, 须类带name属性):
        @register_probe(source="probe_framework")
        class MyProbe(BaseProbe): ...

    注册后调用方应再调用invalidate_registry_cache()刷新统一视图。
    """

    def _decorator(cls: type) -> type:
        if source == "probe_framework":
            from ai_prompt_toolkit.probe_framework import _PROBE_REGISTRY as PF_PROBE_REGISTRY
        else:
            from ai_prompt_toolkit.redteam.probe import _PROBE_REGISTRY as RT_PROBE_REGISTRY

        target = PF_PROBE_REGISTRY if source == "probe_framework" else RT_PROBE_REGISTRY
        name = getattr(cls, "name", None) or cls.__name__.lower()
        target[name] = cls
        logger.debug("统一注册Probe: %s (source=%s) -> %s", name, source, cls.__name__)
        return cls

    if probe_cls is None:
        return _decorator
    return _decorator(probe_cls)


def register_detector(
    detector_cls: type | None = None, *, source: str = "probe_framework"
) -> Callable[[type[_P]], type[_P]] | type:
    """统一Detector注册装饰器 — 新增Detector一处注册"""

    def _decorator(cls: type) -> type:
        if source == "probe_framework":
            from ai_prompt_toolkit.probe_framework import (
                _DETECTOR_REGISTRY as PF_DETECTOR_REGISTRY,
            )
        else:
            from ai_prompt_toolkit.redteam.detector import (
                _DETECTOR_REGISTRY as RT_DETECTOR_REGISTRY,
            )

        target = PF_DETECTOR_REGISTRY if source == "probe_framework" else RT_DETECTOR_REGISTRY
        name = getattr(cls, "name", None) or cls.__name__.lower()
        target[name] = cls
        logger.debug("统一注册Detector: %s (source=%s) -> %s", name, source, cls.__name__)
        return cls

    if detector_cls is None:
        return _decorator
    return _decorator(detector_cls)


def list_all_probes() -> list[str]:
    return list(get_global_probe_registry().keys())


def list_all_detectors() -> list[str]:
    return list(get_global_detector_registry().keys())


def find_probe(name: str) -> dict[str, Any] | None:
    return get_global_probe_registry().get(name)


def find_detector(name: str) -> dict[str, Any] | None:
    return get_global_detector_registry().get(name)


def get_probe_count() -> int:
    return len(get_global_probe_registry())


def get_detector_count() -> int:
    return len(get_global_detector_registry())
