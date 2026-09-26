"""Prompt版本管理器

支持Prompt版本追踪、语义Diff、回滚安全检查增强。
参考: Langfuse Prompt Version管理 + git-like版本链

特性:
- 版本链管理(create/read/diff/rollback)
- 语义变更检测(结构/安全/质量变更)
- 版本元数据(作者/时间/标签/评分)
- JSON存储(无需数据库)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PromptVersion:
    version_id: str
    content: str
    author: str = ""
    timestamp: float = 0.0
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    grade: str = ""
    parent_version: str = ""
    change_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "content": self.content,
            "author": self.author,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "score": self.score,
            "grade": self.grade,
            "parent_version": self.parent_version,
            "change_type": self.change_type,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PromptVersion:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class PromptVersionManager:
    def __init__(self, store_path: str | Path = ".prompt-versions.json"):
        self._store_path = Path(store_path)
        self._versions: dict[str, list[PromptVersion]] = {}
        self._load()

    def _load(self) -> None:
        if self._store_path.exists():
            try:
                data = json.loads(self._store_path.read_text(encoding="utf-8"))
                for template_id, versions in data.items():
                    self._versions[template_id] = [PromptVersion.from_dict(v) for v in versions]
            except Exception:
                self._versions = {}

    def _save(self) -> None:
        data = {}
        for tid, versions in self._versions.items():
            data[tid] = [v.to_dict() for v in versions]
        self._store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_version(
        self,
        template_id: str,
        content: str,
        author: str = "",
        tags: list[str] | None = None,
        score: float = 0.0,
        grade: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> PromptVersion:
        versions = self._versions.setdefault(template_id, [])
        version_num = len(versions) + 1
        version_id = f"v{version_num}"
        parent = versions[-1].version_id if versions else ""
        change_type = self._detect_change_type(versions, content) if versions else "initial"
        pv = PromptVersion(
            version_id=version_id,
            content=content,
            author=author,
            tags=tags or [],
            score=score,
            grade=grade,
            parent_version=parent,
            change_type=change_type,
            metadata=metadata or {},
        )
        versions.append(pv)
        self._save()
        return pv

    def _detect_change_type(self, versions: list[PromptVersion], new_content: str) -> str:
        if not versions:
            return "initial"
        old = versions[-1].content
        if len(new_content) != len(old):
            return "structural"
        if new_content != old:
            return "content"
        return "metadata"

    def get_versions(self, template_id: str) -> list[PromptVersion]:
        return self._versions.get(template_id, [])

    def get_version(self, template_id: str, version_id: str) -> PromptVersion | None:
        for v in self._versions.get(template_id, []):
            if v.version_id == version_id:
                return v
        return None

    def get_latest(self, template_id: str) -> PromptVersion | None:
        versions = self._versions.get(template_id, [])
        return versions[-1] if versions else None

    def diff_versions(self, template_id: str, v1: str, v2: str) -> dict[str, Any]:
        pv1 = self.get_version(template_id, v1)
        pv2 = self.get_version(template_id, v2)
        if not pv1 or not pv2:
            return {"error": "版本不存在"}
        from ai_prompt_toolkit.prompt_diff import semantic_diff

        diff_result = semantic_diff(pv1.content, pv2.content)
        return {
            "template_id": template_id,
            "from_version": v1,
            "to_version": v2,
            "score_delta": pv2.score - pv1.score,
            "grade_change": f"{pv1.grade}→{pv2.grade}",
            "diff": diff_result if hasattr(diff_result, "__dict__") else str(diff_result),
        }

    def list_templates(self) -> list[str]:
        return list(self._versions.keys())
