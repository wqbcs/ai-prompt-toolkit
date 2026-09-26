"""评估结果持久化存储 — SQLite + 趋势分析 + 回归检测

参考: langfuse Evaluations(数据集+运行+趋势) + promptfoo eval历史(JSON持久化+Web查看)
- SQLite轻量存储，零配置
- 80维度评分快照 + 时间线趋势
- 回归检测: 任一维度评分下降>15%自动告警
- A/B对比: 两个版本评分并排对比
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path.home() / ".ai-prompt-toolkit" / "eval_history.db"

_REGRESSION_THRESHOLD = 0.15


@dataclass
class EvalSnapshot:
    snapshot_id: int = 0
    template_id: str = ""
    template_hash: str = ""
    overall_score: float = 0.0
    percentage: float = 0.0
    dimension_count: int = 0
    category_scores: dict[str, float] = field(default_factory=dict)
    dimension_scores: dict[str, float] = field(default_factory=dict)
    evaluation_time_ms: float = 0.0
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "template_id": self.template_id,
            "template_hash": self.template_hash,
            "overall_score": round(self.overall_score, 4),
            "percentage": round(self.percentage, 2),
            "dimension_count": self.dimension_count,
            "category_scores": {k: round(v, 4) for k, v in self.category_scores.items()},
            "dimension_scores": self.dimension_scores,
            "evaluation_time_ms": round(self.evaluation_time_ms, 2),
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class RegressionAlert:
    dimension_id: str
    dimension_name: str
    previous_score: float
    current_score: float
    change_percent: float
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "dimension_name": self.dimension_name,
            "previous_score": round(self.previous_score, 2),
            "current_score": round(self.current_score, 2),
            "change_percent": round(self.change_percent, 2),
            "severity": self.severity,
        }


@dataclass
class TrendPoint:
    snapshot_id: int
    created_at: str
    overall_score: float
    percentage: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "overall_score": round(self.overall_score, 4),
            "percentage": round(self.percentage, 2),
        }


class EvalStore:
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = _DEFAULT_DB_PATH
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS eval_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id TEXT NOT NULL,
                template_hash TEXT NOT NULL DEFAULT '',
                overall_score REAL NOT NULL DEFAULT 0,
                percentage REAL NOT NULL DEFAULT 0,
                dimension_count INTEGER NOT NULL DEFAULT 0,
                category_scores TEXT NOT NULL DEFAULT '{}',
                dimension_scores TEXT NOT NULL DEFAULT '{}',
                evaluation_time_ms REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_template ON eval_snapshots(template_id);
            CREATE INDEX IF NOT EXISTS idx_snapshots_created ON eval_snapshots(created_at);

            CREATE TABLE IF NOT EXISTS regression_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                dimension_id TEXT NOT NULL,
                dimension_name TEXT NOT NULL DEFAULT '',
                previous_score REAL NOT NULL DEFAULT 0,
                current_score REAL NOT NULL DEFAULT 0,
                change_percent REAL NOT NULL DEFAULT 0,
                severity TEXT NOT NULL DEFAULT 'warning',
                created_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (snapshot_id) REFERENCES eval_snapshots(snapshot_id)
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_snapshot ON regression_alerts(snapshot_id);

            CREATE TABLE IF NOT EXISTS eval_traces (
                trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                operation TEXT NOT NULL DEFAULT '',
                dimension_id TEXT NOT NULL DEFAULT '',
                input_hash TEXT NOT NULL DEFAULT '',
                output_hash TEXT NOT NULL DEFAULT '',
                latency_ms REAL NOT NULL DEFAULT 0,
                token_count INTEGER NOT NULL DEFAULT 0,
                cost REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'ok',
                created_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (snapshot_id) REFERENCES eval_snapshots(snapshot_id)
            );
            CREATE INDEX IF NOT EXISTS idx_traces_snapshot ON eval_traces(snapshot_id);
            CREATE INDEX IF NOT EXISTS idx_traces_operation ON eval_traces(operation);
        """)
        conn.commit()

    def save(self, report: Any) -> EvalSnapshot:
        conn = self._connect()

        dim_scores: dict[str, float] = {}
        for s in report.scores:
            dim_scores[s.dimension_id] = round(s.score, 4)

        cat_scores = {k: round(v, 4) for k, v in report.category_scores.items()}
        template_hash = _compute_hash(report.template_id)

        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        cursor = conn.execute(
            """INSERT INTO eval_snapshots
               (template_id, template_hash, overall_score, percentage, dimension_count,
                category_scores, dimension_scores, evaluation_time_ms, created_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.template_id,
                template_hash,
                round(report.overall_score, 4),
                round(report.percentage, 2),
                report.dimension_count,
                json.dumps(cat_scores, ensure_ascii=False),
                json.dumps(dim_scores, ensure_ascii=False),
                round(report.evaluation_time_ms, 2),
                now,
                json.dumps({}, ensure_ascii=False),
            ),
        )
        snapshot_id = cursor.lastrowid
        conn.commit()

        snapshot = EvalSnapshot(
            snapshot_id=snapshot_id or 0,
            template_id=report.template_id,
            template_hash=template_hash,
            overall_score=report.overall_score,
            percentage=report.percentage,
            dimension_count=report.dimension_count,
            category_scores=cat_scores,
            dimension_scores=dim_scores,
            evaluation_time_ms=report.evaluation_time_ms,
            created_at=now,
        )

        self._check_regression(snapshot, report)

        return snapshot

    def _check_regression(self, snapshot: EvalSnapshot, report: Any) -> list[RegressionAlert]:
        conn = self._connect()
        prev_row = conn.execute(
            """SELECT dimension_scores FROM eval_snapshots
               WHERE template_id = ? AND snapshot_id < ?
               ORDER BY snapshot_id DESC LIMIT 1""",
            (snapshot.template_id, snapshot.snapshot_id),
        ).fetchone()

        if not prev_row:
            return []

        prev_dims = json.loads(prev_row["dimension_scores"])
        alerts: list[RegressionAlert] = []

        dim_name_map = {s.dimension_id: s.name for s in report.scores}

        for dim_id, current_val in snapshot.dimension_scores.items():
            prev_val = prev_dims.get(dim_id)
            if prev_val is None or prev_val == 0:
                continue
            change = (current_val - prev_val) / prev_val
            if change < -_REGRESSION_THRESHOLD:
                severity = "critical" if change < -0.3 else "warning"
                alert = RegressionAlert(
                    dimension_id=dim_id,
                    dimension_name=dim_name_map.get(dim_id, dim_id),
                    previous_score=prev_val,
                    current_score=current_val,
                    change_percent=change * 100,
                    severity=severity,
                )
                alerts.append(alert)
                conn.execute(
                    """INSERT INTO regression_alerts
                       (snapshot_id, dimension_id, dimension_name, previous_score,
                        current_score, change_percent, severity, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        snapshot.snapshot_id,
                        dim_id,
                        alert.dimension_name,
                        alert.previous_score,
                        alert.current_score,
                        round(alert.change_percent, 2),
                        alert.severity,
                        snapshot.created_at,
                    ),
                )

        if alerts:
            conn.commit()
        return alerts

    def get_trend(self, template_id: str, limit: int = 30) -> list[TrendPoint]:
        conn = self._connect()
        rows = conn.execute(
            """SELECT snapshot_id, created_at, overall_score, percentage
               FROM eval_snapshots
               WHERE template_id = ?
               ORDER BY snapshot_id DESC LIMIT ?""",
            (template_id, limit),
        ).fetchall()
        return [
            TrendPoint(
                snapshot_id=r["snapshot_id"],
                created_at=r["created_at"],
                overall_score=r["overall_score"],
                percentage=r["percentage"],
            )
            for r in reversed(rows)
        ]

    def get_snapshots(self, template_id: str, limit: int = 10) -> list[EvalSnapshot]:
        conn = self._connect()
        rows = conn.execute(
            """SELECT * FROM eval_snapshots
               WHERE template_id = ?
               ORDER BY snapshot_id DESC LIMIT ?""",
            (template_id, limit),
        ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def get_alerts(self, template_id: str | None = None, limit: int = 50) -> list[RegressionAlert]:
        conn = self._connect()
        if template_id:
            rows = conn.execute(
                """SELECT ra.* FROM regression_alerts ra
                   JOIN eval_snapshots es ON ra.snapshot_id = es.snapshot_id
                   WHERE es.template_id = ?
                   ORDER BY ra.alert_id DESC LIMIT ?""",
                (template_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM regression_alerts ORDER BY alert_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            RegressionAlert(
                dimension_id=r["dimension_id"],
                dimension_name=r["dimension_name"],
                previous_score=r["previous_score"],
                current_score=r["current_score"],
                change_percent=r["change_percent"],
                severity=r["severity"],
            )
            for r in rows
        ]

    def compare(self, snapshot_id_a: int, snapshot_id_b: int) -> dict[str, Any]:
        conn = self._connect()
        row_a = conn.execute(
            "SELECT * FROM eval_snapshots WHERE snapshot_id = ?",
            (snapshot_id_a,),
        ).fetchone()
        row_b = conn.execute(
            "SELECT * FROM eval_snapshots WHERE snapshot_id = ?",
            (snapshot_id_b,),
        ).fetchone()
        if not row_a or not row_b:
            return {"error": "snapshot not found"}

        dims_a = json.loads(row_a["dimension_scores"])
        dims_b = json.loads(row_b["dimension_scores"])

        diffs: list[dict[str, Any]] = []
        all_dims = set(dims_a.keys()) | set(dims_b.keys())
        for dim_id in sorted(all_dims):
            va = dims_a.get(dim_id, 0)
            vb = dims_b.get(dim_id, 0)
            diff = vb - va
            diffs.append(
                {
                    "dimension_id": dim_id,
                    "score_a": round(va, 2),
                    "score_b": round(vb, 2),
                    "diff": round(diff, 2),
                    "direction": "improved" if diff > 0 else "regressed" if diff < 0 else "unchanged",
                }
            )

        return {
            "snapshot_a": self._row_to_snapshot(row_a).to_dict(),
            "snapshot_b": self._row_to_snapshot(row_b).to_dict(),
            "dimension_diffs": diffs,
            "overall_diff": round(row_b["overall_score"] - row_a["overall_score"], 4),
        }

    def _row_to_snapshot(self, row: sqlite3.Row) -> EvalSnapshot:
        return EvalSnapshot(
            snapshot_id=row["snapshot_id"],
            template_id=row["template_id"],
            template_hash=row["template_hash"],
            overall_score=row["overall_score"],
            percentage=row["percentage"],
            dimension_count=row["dimension_count"],
            category_scores=json.loads(row["category_scores"]),
            dimension_scores=json.loads(row["dimension_scores"]),
            evaluation_time_ms=row["evaluation_time_ms"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata"]),
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def record_trace(
        self,
        snapshot_id: int,
        operation: str,
        dimension_id: str = "",
        input_hash: str = "",
        output_hash: str = "",
        latency_ms: float = 0,
        token_count: int = 0,
        cost: float = 0,
        status: str = "ok",
    ) -> int:
        import datetime

        conn = self._connect()
        now = datetime.datetime.now().isoformat()
        cur = conn.execute(
            "INSERT INTO eval_traces (snapshot_id, operation, dimension_id, input_hash, output_hash, latency_ms, token_count, cost, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (snapshot_id, operation, dimension_id, input_hash, output_hash, latency_ms, token_count, cost, status, now),
        )
        conn.commit()
        return cur.lastrowid

    def get_traces(
        self, snapshot_id: int | None = None, operation: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        conn = self._connect()
        clauses = []
        params: list[Any] = []
        if snapshot_id is not None:
            clauses.append("snapshot_id=?")
            params.append(snapshot_id)
        if operation is not None:
            clauses.append("operation=?")
            params.append(operation)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM eval_traces {where} ORDER BY trace_id DESC LIMIT ?", [*params, limit]
        ).fetchall()
        return [dict(r) for r in rows]

    def get_trace_stats(self, operation: str | None = None) -> dict[str, Any]:
        conn = self._connect()
        where = f"WHERE operation='{operation}'" if operation else ""
        try:
            row = conn.execute(
                f"SELECT COUNT(*) as cnt, AVG(latency_ms) as avg_latency, SUM(token_count) as total_tokens, SUM(cost) as total_cost FROM eval_traces {where}"
            ).fetchone()
            return {
                "count": row["cnt"],
                "avg_latency_ms": round(row["avg_latency"] or 0, 2),
                "total_tokens": row["total_tokens"] or 0,
                "total_cost": round(row["total_cost"] or 0, 4),
            }
        except Exception:
            return {"count": 0, "avg_latency_ms": 0, "total_tokens": 0, "total_cost": 0}


def _compute_hash(template_id: str) -> str:
    import hashlib

    return hashlib.sha256(template_id.encode()).hexdigest()[:16]
