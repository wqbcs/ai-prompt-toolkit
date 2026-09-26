"""Dataset管理模块 — 参考promptfoo dataset + langfuse dataset

- Dataset: 测试用例集合(输入+期望输出+标签)
- CRUD: 创建/读取/更新/删除数据集和用例
- 导入/导出: JSON/CSV格式
- 运行: 对数据集批量执行lint/scan/evaluate
- SQLite持久化
"""

from __future__ import annotations

import csv
import io
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path.home() / ".ai-prompt-toolkit" / "datasets.db"


@dataclass
class DatasetCase:
    case_id: str = ""
    dataset_id: str = ""
    input_text: str = ""
    expected_output: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "dataset_id": self.dataset_id,
            "input_text": self.input_text,
            "expected_output": self.expected_output,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class Dataset:
    dataset_id: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    case_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "case_count": self.case_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class DatasetRunResult:
    case_id: str
    status: str = "pending"
    lint_score: float = 0.0
    scan_findings: int = 0
    eval_score: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "lint_score": round(self.lint_score, 2),
            "scan_findings": self.scan_findings,
            "eval_score": round(self.eval_score, 2),
            "error": self.error,
        }


class DatasetStore:
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
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                case_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS dataset_cases (
                case_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                input_text TEXT NOT NULL DEFAULT '',
                expected_output TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
            );
            CREATE INDEX IF NOT EXISTS idx_cases_dataset ON dataset_cases(dataset_id);

            CREATE TABLE IF NOT EXISTS dataset_versions (
                version_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                version_number INTEGER NOT NULL DEFAULT 1,
                snapshot TEXT NOT NULL DEFAULT '[]',
                case_count INTEGER NOT NULL DEFAULT 0,
                content_hash TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
            );
            CREATE INDEX IF NOT EXISTS idx_versions_dataset ON dataset_versions(dataset_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_versions_did_num ON dataset_versions(dataset_id, version_number);
        """)
        conn.commit()

    def create_dataset(self, name: str, description: str = "", tags: list[str] | None = None) -> Dataset:
        import uuid

        conn = self._connect()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        ds_id = uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO datasets (dataset_id, name, description, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                ds_id,
                name,
                description,
                json.dumps(tags or [], ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.commit()
        return Dataset(
            dataset_id=ds_id,
            name=name,
            description=description,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )

    def list_datasets(self, page: int = 1, page_size: int = 20) -> tuple[list[Dataset], int]:
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) as cnt FROM datasets").fetchone()["cnt"]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM datasets ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
        datasets = [self._row_to_dataset(r) for r in rows]
        return datasets, total

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        conn = self._connect()
        row = conn.execute("SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)).fetchone()
        return self._row_to_dataset(row) if row else None

    def delete_dataset(self, dataset_id: str) -> bool:
        conn = self._connect()
        conn.execute("DELETE FROM dataset_cases WHERE dataset_id = ?", (dataset_id,))
        cursor = conn.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))
        conn.commit()
        return cursor.rowcount > 0

    def add_case(
        self,
        dataset_id: str,
        input_text: str,
        expected_output: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DatasetCase:
        import uuid

        conn = self._connect()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        case_id = uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO dataset_cases (case_id, dataset_id, input_text, expected_output, tags, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                case_id,
                dataset_id,
                input_text,
                expected_output,
                json.dumps(tags or [], ensure_ascii=False),
                json.dumps(metadata or {}, ensure_ascii=False),
                now,
            ),
        )
        conn.execute(
            "UPDATE datasets SET case_count = case_count + 1, updated_at = ? WHERE dataset_id = ?",
            (now, dataset_id),
        )
        conn.commit()
        return DatasetCase(
            case_id=case_id,
            dataset_id=dataset_id,
            input_text=input_text,
            expected_output=expected_output,
            tags=tags or [],
            metadata=metadata or {},
            created_at=now,
        )

    def get_cases(self, dataset_id: str) -> list[DatasetCase]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM dataset_cases WHERE dataset_id = ? ORDER BY created_at",
            (dataset_id,),
        ).fetchall()
        return [self._row_to_case(r) for r in rows]

    def delete_case(self, case_id: str) -> bool:
        conn = self._connect()
        case = conn.execute("SELECT dataset_id FROM dataset_cases WHERE case_id = ?", (case_id,)).fetchone()
        if not case:
            return False
        conn.execute("DELETE FROM dataset_cases WHERE case_id = ?", (case_id,))
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            "UPDATE datasets SET case_count = case_count - 1, updated_at = ? WHERE dataset_id = ?",
            (now, case["dataset_id"]),
        )
        conn.commit()
        return True

    def import_json(self, dataset_id: str, json_data: list[dict[str, Any]]) -> int:
        count = 0
        for item in json_data:
            self.add_case(
                dataset_id,
                input_text=item.get("input", ""),
                expected_output=item.get("expected", ""),
                tags=item.get("tags", []),
                metadata=item.get("metadata", {}),
            )
            count += 1
        return count

    def import_csv(self, dataset_id: str, csv_text: str) -> int:
        reader = csv.DictReader(io.StringIO(csv_text))
        count = 0
        for row in reader:
            self.add_case(
                dataset_id,
                input_text=row.get("input", ""),
                expected_output=row.get("expected", ""),
            )
            count += 1
        return count

    def export_json(self, dataset_id: str) -> str:
        cases = self.get_cases(dataset_id)
        data = [
            {
                "input": c.input_text,
                "expected": c.expected_output,
                "tags": c.tags,
                "metadata": c.metadata,
            }
            for c in cases
        ]
        return json.dumps(data, ensure_ascii=False, indent=2)

    def export_csv(self, dataset_id: str) -> str:
        cases = self.get_cases(dataset_id)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["input", "expected", "tags"])
        writer.writeheader()
        for c in cases:
            writer.writerow(
                {
                    "input": c.input_text,
                    "expected": c.expected_output,
                    "tags": ",".join(c.tags),
                }
            )
        return output.getvalue()

    def run_dataset(self, dataset_id: str, run_type: str = "all") -> list[DatasetRunResult]:
        cases = self.get_cases(dataset_id)
        results: list[DatasetRunResult] = []
        for case in cases:
            r = DatasetRunResult(case_id=case.case_id)
            try:
                if run_type in ("lint", "all"):
                    from ai_prompt_toolkit.linter.linter import PromptLinter

                    linter = PromptLinter()
                    lint_result = linter.lint(case.case_id, case.input_text)
                    r.lint_score = lint_result.score
                if run_type in ("scan", "all"):
                    from ai_prompt_toolkit.security.injection_detector import (
                        InjectionDetector,
                    )

                    detector = InjectionDetector()
                    findings = detector.detect(case.input_text, template_id=case.case_id)
                    r.scan_findings = len(findings)
                if run_type in ("evaluate", "all"):
                    from ai_prompt_toolkit.evaluator import evaluate_template

                    eval_result = evaluate_template(case.case_id, case.input_text)
                    r.eval_score = eval_result.overall_score
                r.status = "completed"
            except Exception as e:
                r.status = "error"
                r.error = str(e)
            results.append(r)
        return results

    async def run_dataset_async(self, dataset_id: str, run_type: str = "all") -> list[DatasetRunResult]:
        import asyncio

        cases = self.get_cases(dataset_id)
        results: list[DatasetRunResult] = []
        semaphore = asyncio.Semaphore(5)

        async def _run_case(case: DatasetCase) -> DatasetRunResult:
            r = DatasetRunResult(case_id=case.case_id)
            async with semaphore:
                try:
                    if run_type in ("lint", "all"):
                        from ai_prompt_toolkit.linter.linter import PromptLinter

                        linter = PromptLinter()
                        lint_result = await asyncio.to_thread(linter.lint, case.case_id, case.input_text)
                        r.lint_score = lint_result.score
                    if run_type in ("scan", "all"):
                        from ai_prompt_toolkit.security.injection_detector import (
                            InjectionDetector,
                        )

                        detector = InjectionDetector()
                        findings = await asyncio.to_thread(detector.detect, case.input_text, case.case_id)
                        r.scan_findings = len(findings)
                    if run_type in ("evaluate", "all"):
                        from ai_prompt_toolkit.evaluator import evaluate_template

                        eval_result = await asyncio.to_thread(evaluate_template, case.case_id, case.input_text)
                        r.eval_score = eval_result.overall_score
                    r.status = "completed"
                except Exception as e:
                    r.status = "error"
                    r.error = str(e)
            return r

        tasks = [_run_case(c) for c in cases]
        results = await asyncio.gather(*tasks)
        return list(results)

    def _row_to_dataset(self, row: sqlite3.Row) -> Dataset:
        return Dataset(
            dataset_id=row["dataset_id"],
            name=row["name"],
            description=row["description"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            case_count=row["case_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_case(self, row: sqlite3.Row) -> DatasetCase:
        return DatasetCase(
            case_id=row["case_id"],
            dataset_id=row["dataset_id"],
            input_text=row["input_text"],
            expected_output=row["expected_output"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def create_version(self, dataset_id: str, author: str = "", message: str = "") -> dict[str, Any]:
        import hashlib
        import uuid

        conn = self._connect()
        cases = self.get_cases(dataset_id)
        snapshot = json.dumps([c.to_dict() for c in cases], ensure_ascii=False)
        content_hash = hashlib.sha256(snapshot.encode("utf-8")).hexdigest()[:16]

        latest = conn.execute(
            "SELECT MAX(version_number) as max_ver FROM dataset_versions WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()
        next_ver = (latest["max_ver"] or 0) + 1

        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        version_id = uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO dataset_versions (version_id, dataset_id, version_number, snapshot, case_count, content_hash, author, message, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (version_id, dataset_id, next_ver, snapshot, len(cases), content_hash, author, message, now),
        )
        conn.commit()
        return {
            "version_id": version_id,
            "dataset_id": dataset_id,
            "version_number": next_ver,
            "case_count": len(cases),
            "content_hash": content_hash,
            "created_at": now,
        }

    def list_versions(self, dataset_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT version_id, dataset_id, version_number, case_count, content_hash, author, message, created_at FROM dataset_versions WHERE dataset_id = ? ORDER BY version_number DESC",
            (dataset_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_version(self, dataset_id: str, version_number: int) -> dict[str, Any] | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM dataset_versions WHERE dataset_id = ? AND version_number = ?",
            (dataset_id, version_number),
        ).fetchone()
        if not row:
            return None
        return dict(row)

    def restore_version(self, dataset_id: str, version_number: int) -> int:
        conn = self._connect()
        row = conn.execute(
            "SELECT snapshot FROM dataset_versions WHERE dataset_id = ? AND version_number = ?",
            (dataset_id, version_number),
        ).fetchone()
        if not row:
            return 0

        cases_data = json.loads(row["snapshot"])
        conn.execute("DELETE FROM dataset_cases WHERE dataset_id = ?", (dataset_id,))

        count = 0
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        for case_dict in cases_data:
            import uuid

            case_id = uuid.uuid4().hex[:12]
            conn.execute(
                "INSERT INTO dataset_cases (case_id, dataset_id, input_text, expected_output, tags, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    case_id,
                    dataset_id,
                    case_dict.get("input_text", ""),
                    case_dict.get("expected_output", ""),
                    json.dumps(case_dict.get("tags", []), ensure_ascii=False),
                    json.dumps(case_dict.get("metadata", {}), ensure_ascii=False),
                    now,
                ),
            )
            count += 1

        conn.execute(
            "UPDATE datasets SET case_count = ?, updated_at = ? WHERE dataset_id = ?",
            (count, now, dataset_id),
        )
        conn.commit()
        return count

    def diff_versions(self, dataset_id: str, version_a: int, version_b: int) -> dict[str, Any]:
        va = self.get_version(dataset_id, version_a)
        vb = self.get_version(dataset_id, version_b)
        if not va or not vb:
            return {"error": "版本不存在"}

        cases_a = {c["input_text"]: c for c in json.loads(va["snapshot"])}
        cases_b = {c["input_text"]: c for c in json.loads(vb["snapshot"])}

        added = [k for k in cases_b if k not in cases_a]
        removed = [k for k in cases_a if k not in cases_b]
        common = [k for k in cases_a if k in cases_b]
        modified = [k for k in common if cases_a[k] != cases_b[k]]

        return {
            "version_a": version_a,
            "version_b": version_b,
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "unchanged": len(common) - len(modified),
            "added_inputs": added[:10],
            "removed_inputs": removed[:10],
        }
