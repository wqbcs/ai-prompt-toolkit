"""攻击签名学习 — 基于向量相似度的注入攻击记忆与拦截

参考:
- Rebuff (protectai/rebuff) — VectorDB攻击签名存储+余弦匹配
- FAISS (facebookresearch/faiss) — 向量索引(本项目不依赖)
- Annoy (spotify/annoy) — 近似最近邻(本项目不依赖)

核心特性:
- AttackVault: 纯Python实现的攻击签名存储和检索
- 余弦相似度匹配, 零外部依赖(无需FAISS/Annoy/ChromaDB)
- 新攻击自动学习, 相似攻击自动拦截
- 支持持久化(JSON)和导出
- 与InjectionDetector集成, 作为多层防御的补充层
"""

from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AttackSignature:
    text: str
    attack_type: str = ""
    detected_at: float = field(default_factory=time.time)
    embedding: list[float] = field(default_factory=list)
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text[:200],
            "attack_type": self.attack_type,
            "detected_at": self.detected_at,
            "embedding_dim": len(self.embedding),
            "source": self.source,
        }


def _simple_hash_embedding(text: str, dim: int = 64) -> list[float]:
    result = [0.0] * dim
    for i, ch in enumerate(text):
        idx = (ord(ch) + i * 31) % dim
        result[idx] += 1.0
    words = text.lower().split()
    for _i, word in enumerate(words):
        idx = hash(word) % dim
        result[idx] += 0.5
    norm = math.sqrt(sum(x * x for x in result))
    if norm > 0:
        result = [x / norm for x in result]
    return result


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class AttackVault:
    def __init__(self, dim: int = 64, threshold: float = 0.75, maxsize: int = 10000) -> None:
        self._dim = dim
        self._threshold = threshold
        self._maxsize = maxsize
        self._signatures: list[AttackSignature] = []
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        return len(self._signatures)

    @property
    def threshold(self) -> float:
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        self._threshold = max(0.0, min(1.0, value))

    def learn(
        self, text: str, attack_type: str = "", source: str = "", metadata: dict[str, Any] | None = None
    ) -> AttackSignature:
        embedding = _simple_hash_embedding(text, self._dim)
        sig = AttackSignature(
            text=text,
            attack_type=attack_type,
            embedding=embedding,
            source=source,
            metadata=metadata or {},
        )
        with self._lock:
            if len(self._signatures) >= self._maxsize:
                self._signatures.pop(0)
            self._signatures.append(sig)
        return sig

    def check(self, text: str) -> tuple[bool, float, AttackSignature | None]:
        embedding = _simple_hash_embedding(text, self._dim)
        best_score = 0.0
        best_sig: AttackSignature | None = None
        with self._lock:
            for sig in self._signatures:
                score = _cosine_similarity(embedding, sig.embedding)
                if score > best_score:
                    best_score = score
                    best_sig = sig
        is_match = best_score >= self._threshold
        return is_match, best_score, best_sig

    def get_all(self) -> list[AttackSignature]:
        with self._lock:
            return list(self._signatures)

    def clear(self) -> None:
        with self._lock:
            self._signatures.clear()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            types: dict[str, int] = {}
            for sig in self._signatures:
                types[sig.attack_type] = types.get(sig.attack_type, 0) + 1
            return {
                "size": len(self._signatures),
                "maxsize": self._maxsize,
                "dim": self._dim,
                "threshold": self._threshold,
                "attack_types": types,
            }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        with self._lock:
            data = {
                "dim": self._dim,
                "threshold": self._threshold,
                "maxsize": self._maxsize,
                "signatures": [
                    {
                        "text": s.text[:200],
                        "attack_type": s.attack_type,
                        "detected_at": s.detected_at,
                        "embedding": s.embedding,
                        "source": s.source,
                    }
                    for s in self._signatures
                ],
            }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> AttackVault:
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        vault = cls(
            dim=data.get("dim", 64),
            threshold=data.get("threshold", 0.75),
            maxsize=data.get("maxsize", 10000),
        )
        for s_data in data.get("signatures", []):
            sig = AttackSignature(
                text=s_data["text"],
                attack_type=s_data.get("attack_type", ""),
                detected_at=s_data.get("detected_at", 0),
                embedding=s_data.get("embedding", []),
                source=s_data.get("source", ""),
            )
            vault._signatures.append(sig)
        return vault


_vault: AttackVault | None = None


def get_attack_vault() -> AttackVault:
    global _vault
    if _vault is None:
        _vault = AttackVault()
    return _vault


def configure_attack_vault(dim: int = 64, threshold: float = 0.75, maxsize: int = 10000) -> AttackVault:
    global _vault
    _vault = AttackVault(dim=dim, threshold=threshold, maxsize=maxsize)
    return _vault
