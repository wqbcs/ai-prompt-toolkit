"""进度保存与恢复 — SIGINT中断后可恢复

架构:
- _save_progress(): 保存当前lint/scan结果到 .apt-cache/resume/
- _load_progress(): 加载上次中断的进度
- lint --resume: 从中断处继续
- 参考: pytest --lf(last-failed)机制
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_CACHE_DIR = Path(".apt-cache") / "resume"


def _ensure_cache_dir() -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


def save_progress(
    command: str,
    results: list[Any],
    completed_files: list[str],
    pending_files: list[str],
    metadata: dict[str, Any] | None = None,
) -> Path:
    cache_dir = _ensure_cache_dir()
    state = {
        "command": command,
        "timestamp": time.time(),
        "completed_files": completed_files,
        "pending_files": pending_files,
        "results_count": len(results),
        "metadata": metadata or {},
    }
    state_file = cache_dir / f"{command}_state.json"
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    results_file = cache_dir / f"{command}_results.json"
    serialized = []
    for r in results:
        if hasattr(r, "to_dict"):
            serialized.append(r.to_dict())
        elif isinstance(r, dict):
            serialized.append(r)
        else:
            serialized.append(str(r))
    results_file.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")
    return state_file


def load_progress(command: str) -> dict[str, Any] | None:
    state_file = _CACHE_DIR / f"{command}_state.json"
    if not state_file.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(state_file.read_text(encoding="utf-8"))
        if time.time() - data.get("timestamp", 0) > 86400:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def load_results(command: str) -> list[dict[str, Any]]:
    results_file = _CACHE_DIR / f"{command}_results.json"
    if not results_file.exists():
        return []
    try:
        results: list[dict[str, Any]] = json.loads(results_file.read_text(encoding="utf-8"))
        return results
    except (json.JSONDecodeError, OSError):
        return []


def clear_progress(command: str) -> None:
    for name in [f"{command}_state.json", f"{command}_results.json"]:
        path = _CACHE_DIR / name
        if path.exists():
            path.unlink()


def has_progress(command: str) -> bool:
    return load_progress(command) is not None
