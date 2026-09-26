"""R30: 数据连接器框架 测试套件"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from ai_prompt_toolkit.data_reader import (
    BaseReader,
    DatabaseReader,
    DataReaderFactory,
    Document,
    FileSystemReader,
)


class TestDocument:
    def test_basic_creation(self):
        doc = Document(text="hello world")
        assert doc.text == "hello world"
        assert doc.metadata == {}
        assert doc.id != ""

    def test_auto_id_from_metadata(self):
        doc = Document(text="test", metadata={"file_path": "/tmp/test.md"})
        assert doc.id == "/tmp/test.md"

    def test_custom_id(self):
        doc = Document(text="test", id="custom-id")
        assert doc.id == "custom-id"

    def test_to_dict(self):
        doc = Document(text="hello", metadata={"key": "value"}, id="doc-1")
        d = doc.to_dict()
        assert d["id"] == "doc-1"
        assert d["text_length"] == 5
        assert d["metadata"]["key"] == "value"


class TestFileSystemReader:
    def test_load_md_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.md").write_text("# Hello", encoding="utf-8")
            (Path(tmpdir) / "readme.txt").write_text("World", encoding="utf-8")
            reader = FileSystemReader(tmpdir)
            docs = reader.load_data()
            assert len(docs) == 2
            texts = [d.text.strip() for d in docs]
            assert "# Hello" in texts
            assert "World" in texts

    def test_load_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"key": "value", "num": 42}
            (Path(tmpdir) / "data.json").write_text(json.dumps(data), encoding="utf-8")
            reader = FileSystemReader(tmpdir)
            docs = reader.load_data()
            assert len(docs) == 1
            parsed = json.loads(docs[0].text)
            assert parsed["key"] == "value"

    def test_load_yaml_file(self):
        try:
            import yaml
        except ImportError:
            pytest.skip("yaml not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"name": "test", "items": [1, 2, 3]}
            (Path(tmpdir) / "config.yaml").write_text(yaml.dump(data), encoding="utf-8")
            reader = FileSystemReader(tmpdir)
            docs = reader.load_data()
            assert len(docs) == 1

    def test_non_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "sub"
            subdir.mkdir()
            (Path(tmpdir) / "top.md").write_text("top", encoding="utf-8")
            (subdir / "nested.md").write_text("nested", encoding="utf-8")
            reader = FileSystemReader(tmpdir, recursive=False)
            docs = reader.load_data()
            assert len(docs) == 1
            assert docs[0].text.strip() == "top"

    def test_custom_extensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.md").write_text("md file", encoding="utf-8")
            (Path(tmpdir) / "data.csv").write_text("csv file", encoding="utf-8")
            reader = FileSystemReader(tmpdir, required_exts=[".md"])
            docs = reader.load_data()
            assert len(docs) == 1

    def test_exclude_patterns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "good.md").write_text("good", encoding="utf-8")
            (Path(tmpdir) / "bad.md").write_text("bad", encoding="utf-8")
            reader = FileSystemReader(tmpdir, exclude_patterns=["bad"])
            docs = reader.load_data()
            assert len(docs) == 1
            assert docs[0].text.strip() == "good"

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = FileSystemReader(tmpdir)
            docs = reader.load_data()
            assert docs == []

    def test_metadata_populated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.md").write_text("hello", encoding="utf-8")
            reader = FileSystemReader(tmpdir)
            docs = reader.load_data()
            assert len(docs) == 1
            meta = docs[0].metadata
            assert meta["file_name"] == "test.md"
            assert meta["file_type"] == ".md"
            assert meta["reader"] == "filesystem"
            assert "file_size" in meta

    def test_iter_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.md").write_text("hello", encoding="utf-8")
            reader = FileSystemReader(tmpdir)
            batches = list(reader.iter_data())
            assert len(batches) == 1
            assert len(batches[0]) == 1


class TestDatabaseReader:
    def test_load_from_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE prompts (name TEXT, content TEXT)")
            conn.execute("INSERT INTO prompts VALUES ('greeting', 'Hello!')")
            conn.execute("INSERT INTO prompts VALUES ('farewell', 'Goodbye!')")
            conn.commit()
            conn.close()

            reader = DatabaseReader(str(db_path), query="SELECT * FROM prompts")
            docs = reader.load_data()
            assert len(docs) == 2
            assert any("greeting" in d.text for d in docs)
            assert any("farewell" in d.text for d in docs)

    def test_text_columns_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE data (name TEXT, content TEXT, extra TEXT)")
            conn.execute("INSERT INTO data VALUES ('a', 'content-a', 'extra-a')")
            conn.commit()
            conn.close()

            reader = DatabaseReader(str(db_path), query="SELECT * FROM data", text_columns=["content"])
            docs = reader.load_data()
            assert len(docs) == 1
            assert docs[0].text.strip() == "content-a"

    def test_default_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE foo (x INT)")
            conn.close()

            reader = DatabaseReader(str(db_path))
            docs = reader.load_data()
            assert len(docs) >= 1

    def test_metadata_populated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE t (val TEXT)")
            conn.execute("INSERT INTO t VALUES ('hello')")
            conn.commit()
            conn.close()

            reader = DatabaseReader(str(db_path), query="SELECT * FROM t")
            docs = reader.load_data()
            assert docs[0].metadata["source"] == "database"
            assert docs[0].metadata["reader"] == "database"

    def test_empty_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE empty_t (val TEXT)")
            conn.commit()
            conn.close()

            reader = DatabaseReader(str(db_path), query="SELECT * FROM empty_t")
            docs = reader.load_data()
            assert docs == []


class TestDataReaderFactory:
    def test_registered_readers(self):
        readers = DataReaderFactory.list_readers()
        assert "filesystem" in readers
        assert "database" in readers

    def test_create_filesystem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = DataReaderFactory.create("filesystem", input_dir=tmpdir)
            assert isinstance(reader, FileSystemReader)

    def test_create_database(self):
        reader = DataReaderFactory.create("database", connection_string=":memory:")
        assert isinstance(reader, DatabaseReader)

    def test_unknown_reader_raises(self):
        with pytest.raises(ValueError, match="Unknown reader"):
            DataReaderFactory.create("nonexistent")

    def test_custom_reader_registration(self):
        class DummyReader(BaseReader):
            def load_data(self):
                return [Document(text="dummy")]

        DataReaderFactory.register("dummy", DummyReader)
        reader = DataReaderFactory.create("dummy")
        docs = reader.load_data()
        assert len(docs) == 1
        assert docs[0].text == "dummy"
