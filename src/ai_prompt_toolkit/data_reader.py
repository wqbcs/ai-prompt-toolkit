"""数据连接器框架——参考LlamaIndex BaseReader/Document架构

核心特性:
- Document: 统一数据载体(text+metadata+id)
- BaseReader: 抽象基类(load_data/iter_data)
- FileSystemReader: .md/.txt/.yaml/.json文件加载
- DatabaseReader: SQLite查询加载
- DataReaderFactory: 注册/创建连接器
"""

from __future__ import annotations

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.cli_helpers import read_prompt_text

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


@dataclass
class Document:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = self.metadata.get("file_path", str(hash(self.text)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text_length": len(self.text),
            "metadata": self.metadata,
        }


class BaseReader(ABC):
    @abstractmethod
    def load_data(self) -> list[Document]: ...

    def iter_data(self) -> Iterator[list[Document]]:
        yield self.load_data()


class FileSystemReader(BaseReader):
    SUPPORTED_EXTS = {".md", ".txt", ".yaml", ".yml", ".json"}

    def __init__(
        self,
        input_dir: str | Path,
        *,
        recursive: bool = True,
        required_exts: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        self.input_dir = Path(input_dir)
        self.recursive = recursive
        self.required_exts = required_exts or list(self.SUPPORTED_EXTS)
        self.exclude_patterns = exclude_patterns or []

    def load_data(self) -> list[Document]:
        docs: list[Document] = []
        for path in self._iter_files():
            try:
                doc = self._load_file(path)
                docs.append(doc)
            except Exception as e:
                logger.warning("Failed to load %s: %s", path, e)
        return docs

    def _iter_files(self) -> Iterator[Path]:
        pattern = "**/*" if self.recursive else "*"
        for path in sorted(self.input_dir.glob(pattern)):
            if not path.is_file():
                continue
            if path.suffix not in self.required_exts:
                continue
            if any(p in str(path) for p in self.exclude_patterns):
                continue
            yield path

    def _load_file(self, path: Path) -> Document:
        ext = path.suffix
        if ext == ".json":
            with open(path, encoding="utf-8") as f:
                text = json.dumps(json.load(f), ensure_ascii=False, indent=2)
        elif ext in (".yaml", ".yml"):
            try:
                import yaml

                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    text = (
                        json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, (dict, list)) else str(data)
                    )
            except ImportError:
                text = read_prompt_text(path)
        else:
            text = read_prompt_text(path)

        return Document(
            text=text,
            id=str(path),
            metadata={
                "file_path": str(path),
                "file_name": path.name,
                "file_type": ext,
                "file_size": path.stat().st_size,
                "reader": "filesystem",
            },
        )


class DatabaseReader(BaseReader):
    def __init__(
        self,
        connection_string: str,
        *,
        query: str = "",
        text_columns: list[str] | None = None,
    ) -> None:
        self.connection_string = connection_string
        self.query = query
        self.text_columns = text_columns

    def load_data(self) -> list[Document]:
        conn = sqlite3.connect(self.connection_string)
        try:
            if not self.query:
                self.query = "SELECT name FROM sqlite_master WHERE type='table'"
            cursor = conn.execute(self.query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            docs: list[Document] = []
            for i, row in enumerate(rows):
                if self.text_columns:
                    text_parts = [str(row[columns.index(col)]) for col in self.text_columns if col in columns]
                    text = "\n".join(text_parts)
                else:
                    text = "\n".join(f"{col}: {val}" for col, val in zip(columns, row))

                docs.append(
                    Document(
                        text=text,
                        id=f"db-row-{i}",
                        metadata={
                            "source": "database",
                            "connection": self.connection_string,
                            "columns": columns,
                            "row_index": i,
                            "reader": "database",
                        },
                    )
                )
            return docs
        finally:
            conn.close()


class DataReaderFactory:
    _readers: dict[str, type[BaseReader]] = {}

    @classmethod
    def register(cls, name: str, reader_cls: type[BaseReader]) -> None:
        cls._readers[name] = reader_cls

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> BaseReader:
        if name not in cls._readers:
            raise ValueError(f"Unknown reader: {name}. Available: {list(cls._readers.keys())}")
        return cls._readers[name](**kwargs)

    @classmethod
    def list_readers(cls) -> list[str]:
        return list(cls._readers.keys())


DataReaderFactory.register("filesystem", FileSystemReader)
DataReaderFactory.register("database", DatabaseReader)
