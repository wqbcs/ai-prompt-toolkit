"""统一Probe/Detector注册表 — 全局查询索引

聚合probe_framework._PROBE_REGISTRY和redteam.probe._PROBE_REGISTRY
两个独立注册表为统一查询视图。

架构:
- probe_framework._PROBE_REGISTRY: 23个Probe(ProbeRunner兼容, generate()接口)
- redteam.probe._PROBE_REGISTRY: 5+90个Probe(ExplorationOrchestrator兼容, generate_inputs()接口)
- 本模块提供get_global_probe_registry()合并两处，按来源标记

参考: garak统一registry模式
"""

from __future__ import annotations

from typing import Any


def get_global_probe_registry() -> dict[str, dict[str, Any]]:
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
            if rt_name not in merged:
                rt_entry: dict[str, Any] = {"cls": rt_cls, "source": "redteam"}
                merged[rt_name] = rt_entry
    except ImportError:
        pass
    return merged


def get_global_detector_registry() -> dict[str, dict[str, Any]]:
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
            if rt_name not in merged:
                rt_det_entry: dict[str, Any] = {"cls": rt_det, "source": "redteam"}
                merged[rt_name] = rt_det_entry
    except ImportError:
        pass
    return merged


def list_all_probes() -> list[str]:
    return list(get_global_probe_registry().keys())


def list_all_detectors() -> list[str]:
    return list(get_global_detector_registry().keys())


def find_probe(name: str) -> dict[str, Any] | None:
    reg = get_global_probe_registry()
    return reg.get(name)


def find_detector(name: str) -> dict[str, Any] | None:
    reg = get_global_detector_registry()
    return reg.get(name)


def get_probe_count() -> int:
    return len(get_global_probe_registry())


def get_detector_count() -> int:
    return len(get_global_detector_registry())
