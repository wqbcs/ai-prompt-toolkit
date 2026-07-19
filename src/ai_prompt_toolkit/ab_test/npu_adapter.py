"""昇腾NPU环境检测与适配 — E-05

华为昇腾AI处理器适配:
- 检测CANN版本和NPU设备
- MindSpore Lite推理适配
- 模型量化(FP16→INT8)支持
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class NPUInfo:
    available: bool = False
    cann_version: str = ""
    npu_count: int = 0
    npu_model: str = ""
    memory_gb: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "cann_version": self.cann_version,
            "npu_count": self.npu_count,
            "npu_model": self.npu_model,
            "memory_gb": self.memory_gb,
        }


def detect_npu() -> NPUInfo:
    info = NPUInfo()

    try:
        result = subprocess.run(
            ["npu-smi", "info"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            info.available = True
            output = result.stdout
            for line in output.splitlines():
                line = line.strip()
                if "Count" in line or "芯片数" in line:
                    try:
                        info.npu_count = int("".join(c for c in line.split(":")[-1] if c.isdigit()))
                    except (ValueError, IndexError):
                        info.npu_count = 1
                if "Ascend" in line or "910" in line or "310" in line:
                    info.npu_model = line.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    cann_path = os.environ.get("ASCEND_HOME_PATH", "")
    if cann_path and os.path.isdir(cann_path):
        version_file = os.path.join(cann_path, "latest", "version.cfg")
        if os.path.isfile(version_file):
            try:
                info.cann_version = open(version_file, encoding="utf-8").read().strip()
            except OSError:
                pass
        if not info.cann_version:
            info.cann_version = os.environ.get("ASCEND_VERSION", "unknown")

    return info


_NPU_OPTIMIZED_MODELS: dict[str, dict[str, Any]] = {
    "pangu-nlp": {"quantization": "int8", "batch_size": 32, "precision": "fp16"},
    "pangu-large": {"quantization": "int8", "batch_size": 16, "precision": "fp16"},
    "qwen-72b": {"quantization": "int8", "batch_size": 8, "precision": "fp16"},
    "qwen-14b": {"quantization": "fp16", "batch_size": 32, "precision": "fp16"},
}


def get_npu_config(model_name: str) -> dict[str, Any]:
    for key, config in _NPU_OPTIMIZED_MODELS.items():
        if model_name.lower().startswith(key.replace("-", "").replace("_", "")[:6]):
            return config
    return {"quantization": "fp16", "batch_size": 16, "precision": "fp16"}


def should_use_npu(model_name: str) -> bool:
    npu = detect_npu()
    if not npu.available:
        return False
    return os.environ.get("PROMPT_CLI_USE_NPU", "").lower() in ("1", "true", "yes")
