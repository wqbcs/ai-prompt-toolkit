"""评估智能降频 — 基于历史数据智能调整评估频率

P2-05: 减少不必要的评估执行，降低API成本
- 稳定模板降频: 连续3次评分>8.0，评估频率降低50%
- 变更检测: 模板内容变化时立即评估
- 预算控制: 月度/每日API预算限制
- 缓存策略: 相同内容跳过重复评估
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sqlite3


_DEFAULT_DB = Path.home() / ".prompt-toolkit" / "eval_frequency.db"


@dataclass
class EvalFrequencyConfig:
    stable_threshold: float = 8.0
    stable_runs_required: int = 3
    reduction_factor: float = 0.5
    daily_budget: float = 5.0
    monthly_budget: float = 100.0
    content_change_always_eval: bool = True


@dataclass
class EvalDecision:
    should_eval: bool
    reason: str
    frequency_multiplier: float = 1.0
    estimated_cost: float = 0.0
    budget_remaining: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_eval": self.should_eval,
            "reason": self.reason,
            "frequency_multiplier": self.frequency_multiplier,
            "estimated_cost": self.estimated_cost,
            "budget_remaining": self.budget_remaining,
        }


class EvalFrequencyManager:
    def __init__(
        self,
        db_path: str | Path | None = None,
        config: EvalFrequencyConfig | None = None,
    ):
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._config = config or EvalFrequencyConfig()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS eval_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                avg_score REAL NOT NULL,
                cost REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_eval_tid ON eval_history(template_id);
            CREATE INDEX IF NOT EXISTS idx_eval_ts ON eval_history(timestamp);

            CREATE TABLE IF NOT EXISTS eval_budget (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                cost REAL NOT NULL,
                UNIQUE(date)
            );
        """)
        self._conn.commit()

    def _content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def should_evaluate(self, template_id: str, content: str, estimated_cost: float = 0.01) -> EvalDecision:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        budget_row = self._conn.execute(
            "SELECT cost FROM eval_budget WHERE date = ?", (today,)
        ).fetchone()
        today_spent = budget_row[0] if budget_row else 0.0

        if today_spent + estimated_cost > self._config.daily_budget:
            return EvalDecision(
                should_eval=False,
                reason=f"超出每日预算(${today_spent:.2f}/${self._config.daily_budget:.2f})",
                estimated_cost=estimated_cost,
                budget_remaining=max(0, self._config.daily_budget - today_spent),
            )

        content_hash = self._content_hash(content)

        recent = self._conn.execute(
            "SELECT avg_score, content_hash FROM eval_history WHERE template_id = ? ORDER BY timestamp DESC LIMIT ?",
            (template_id, self._config.stable_runs_required),
        ).fetchall()

        if recent:
            last_hash = recent[0][1]
            if self._config.content_change_always_eval and content_hash != last_hash:
                return EvalDecision(should_eval=True, reason="内容变更，立即评估", frequency_multiplier=1.0)

            if len(recent) >= self._config.stable_runs_required:
                scores = [r[0] for r in recent]
                if all(s >= self._config.stable_threshold for s in scores):
                    return EvalDecision(
                        should_eval=False,
                        reason=f"模板稳定(连续{len(scores)}次>{self._config.stable_threshold})",
                        frequency_multiplier=self._config.reduction_factor,
                    )

        return EvalDecision(
            should_eval=True,
            reason="需要评估",
            frequency_multiplier=1.0,
            estimated_cost=estimated_cost,
            budget_remaining=self._config.daily_budget - today_spent,
        )

    def record_eval(self, template_id: str, content: str, avg_score: float, cost: float = 0.01) -> None:
        content_hash = self._content_hash(content)
        timestamp = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO eval_history (template_id, content_hash, avg_score, cost, timestamp) VALUES (?, ?, ?, ?, ?)",
            (template_id, content_hash, avg_score, cost, timestamp),
        )
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._conn.execute(
            "INSERT OR REPLACE INTO eval_budget (date, cost) VALUES (?, COALESCE((SELECT cost FROM eval_budget WHERE date = ?), 0) + ?)",
            (today, today, cost),
        )
        self._conn.commit()

    def get_stable_templates(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT template_id, COUNT(*) as runs, AVG(avg_score) as avg
               FROM eval_history
               GROUP BY template_id
               HAVING runs >= ? AND avg >= ?""",
            (self._config.stable_runs_required, self._config.stable_threshold),
        ).fetchall()
        return [{"template_id": r[0], "runs": r[1], "avg_score": round(r[2], 2)} for r in rows]

    def get_budget_status(self) -> dict[str, Any]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = self._conn.execute("SELECT cost FROM eval_budget WHERE date = ?", (today,)).fetchone()
        spent = row[0] if row else 0.0
        return {
            "daily_budget": self._config.daily_budget,
            "daily_spent": round(spent, 4),
            "daily_remaining": round(self._config.daily_budget - spent, 4),
        }
