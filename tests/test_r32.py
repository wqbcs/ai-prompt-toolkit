"""R32: TextGrad + OPRO + Prompt Registry 测试套件"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_prompt_toolkit.textgrad import (
    TGDConfig,
    TGDOptimizer,
    TGDResult,
    TextualGradient,
    TextualVariable,
    tgd_optimize,
)
from ai_prompt_toolkit.opro import (
    OPROCandidate,
    OPROConfig,
    OPROOptimizer,
    OPROResult,
    opro_optimize,
)
from ai_prompt_toolkit.prompt_registry import (
    PromptRegistry,
    RegistryEntry,
)


# ═══════════════════════════════════════
# TextGrad 测试
# ═══════════════════════════════════════

class TestTextualGradient:
    def test_creation(self):
        g = TextualGradient(criticism="bad", suggestion="fix it", direction="improve")
        assert g.criticism == "bad"
        assert g.suggestion == "fix it"

    def test_to_dict(self):
        g = TextualGradient(criticism="bad", source="test")
        d = g.to_dict()
        assert d["criticism"] == "bad"
        assert d["source"] == "test"


class TestTextualVariable:
    def test_creation(self):
        v = TextualVariable("hello", role_description="test var")
        assert v.value == "hello"
        assert v.role_description == "test var"
        assert len(v.gradients) == 0

    def test_add_gradient(self):
        v = TextualVariable("hello")
        v.add_gradient(TextualGradient(criticism="too short", suggestion="make longer"))
        assert len(v.gradients) == 1

    def test_apply_gradients(self):
        v = TextualVariable("hello")
        v.add_gradient(TextualGradient(
            criticism="missing role",
            suggestion="add role definition",
        ))
        new_val = v.apply_gradients()
        assert len(v.gradients) == 0
        assert "role definition" in new_val or len(new_val) > 5

    def test_apply_gradients_empty(self):
        v = TextualVariable("hello")
        result = v.apply_gradients()
        assert result == "hello"

    def test_record_score(self):
        v = TextualVariable("hello")
        v.record_score(75.0)
        assert v.best_version[1] == 75.0

    def test_score_history(self):
        v = TextualVariable("hello")
        v.record_score(50.0)
        v.record_score(75.0)
        assert len(v.score_history) == 3

    def test_to_dict(self):
        v = TextualVariable("hello")
        d = v.to_dict()
        assert "value_length" in d
        assert d["value_length"] == 5


class TestTGDOptimizer:
    def test_basic_optimization(self):
        optimizer = TGDOptimizer(TGDConfig(max_iterations=3))
        result = optimizer.optimize(
            "Write something about AI",
            eval_fn=lambda t: 60.0 + (5.0 if "角色" in t or "role" in t.lower() else 0),
        )
        assert isinstance(result, TGDResult)
        assert result.iterations > 0

    def test_convergence(self):
        call_count = [0]

        def stable_eval(t):
            call_count[0] += 1
            return 90.0

        optimizer = TGDOptimizer(TGDConfig(
            max_iterations=10,
            convergence_threshold=0.5,
        ))
        result = optimizer.optimize("good prompt", eval_fn=stable_eval)
        assert result.converged is True

    def test_custom_gradient_fn(self):
        def custom_gradient(text, score):
            return TextualGradient(
                criticism="needs improvement",
                suggestion="add structured output format",
                direction="improve",
            )

        optimizer = TGDOptimizer(TGDConfig(max_iterations=2))
        result = optimizer.optimize("test", eval_fn=lambda t: 70.0, gradient_fn=custom_gradient)
        assert result.iterations > 0

    def test_tgd_optimize_convenience(self):
        result = tgd_optimize("test prompt", max_iterations=2, convergence_threshold=10.0)
        assert isinstance(result, TGDResult)

    def test_result_to_dict(self):
        result = TGDResult(
            initial_text="a",
            optimized_text="b",
            initial_score=50.0,
            final_score=80.0,
            improvement=30.0,
            iterations=3,
        )
        d = result.to_dict()
        assert d["improvement"] == 30.0
        assert d["iterations"] == 3

    def test_momentum(self):
        optimizer = TGDOptimizer(TGDConfig(max_iterations=3, momentum=0.9))
        result = optimizer.optimize("test prompt", eval_fn=lambda t: 65.0)
        assert result.iterations > 0


# ═══════════════════════════════════════
# OPRO 测试
# ═══════════════════════════════════════

class TestOPROCandidate:
    def test_creation(self):
        c = OPROCandidate(instruction="test", score=80.0, generation=1)
        assert c.score == 80.0
        assert c.generation == 1

    def test_to_dict(self):
        c = OPROCandidate(instruction="test", score=85.0, generation=2)
        d = c.to_dict()
        assert d["score"] == 85.0


class TestOPROOptimizer:
    def test_basic_optimization(self):
        config = OPROConfig(max_generations=2, population_size=3, top_k=2)
        optimizer = OPROOptimizer(config)
        result = optimizer.optimize(
            "Tell me about AI",
            eval_fn=lambda t: 60.0 + (10.0 if "专业" in t or "步骤" in t else 0),
        )
        assert isinstance(result, OPROResult)
        assert result.generations > 0

    def test_convergence(self):
        optimizer = OPROOptimizer(OPROConfig(
            max_generations=5,
            convergence_rounds=2,
            population_size=2,
            top_k=1,
        ))
        result = optimizer.optimize("test", eval_fn=lambda t: 90.0)
        assert result.converged is True

    def test_opro_optimize_convenience(self):
        result = opro_optimize("test instruction", max_generations=2, population_size=2)
        assert isinstance(result, OPROResult)

    def test_result_to_dict(self):
        result = OPROResult(
            initial_score=50.0,
            best_score=80.0,
            improvement=30.0,
            generations=3,
            candidates_explored=15,
        )
        d = result.to_dict()
        assert d["improvement"] == 30.0
        assert d["candidates_explored"] == 15

    def test_meta_prompt_generation(self):
        config = OPROConfig(max_generations=1, population_size=2, top_k=1)
        optimizer = OPROOptimizer(config)
        top_k = [OPROCandidate(instruction="hello", score=80.0)]
        meta = optimizer._build_meta_prompt(top_k, "original")
        assert "历史最优" in meta
        assert "hello" in meta

    def test_mutation_strategies(self):
        config = OPROConfig(max_generations=1, population_size=2, top_k=1, mutation_strategies=["rephrase"])
        optimizer = OPROOptimizer(config)
        result = optimizer.optimize("你是一个助手", eval_fn=lambda t: 70.0)
        assert result.generations > 0


# ═══════════════════════════════════════
# Prompt Registry 测试
# ═══════════════════════════════════════

class TestRegistryEntry:
    def test_creation(self):
        e = RegistryEntry(name="test", template="hello", tags=["a", "b"])
        assert e.name == "test"
        assert e.tags == ["a", "b"]

    def test_auto_timestamp(self):
        e = RegistryEntry(name="test", template="hello")
        assert e.created_at != ""
        assert e.updated_at != ""

    def test_to_dict(self):
        e = RegistryEntry(name="test", template="hello", version=2, category="code")
        d = e.to_dict()
        assert d["name"] == "test"
        assert d["version"] == 2
        assert d["category"] == "code"

    def test_from_dict(self):
        data = {"name": "test", "template": "hello", "tags": ["a"], "version": 3}
        e = RegistryEntry.from_dict(data)
        assert e.name == "test"
        assert e.version == 3
        assert e.tags == ["a"]


class TestPromptRegistry:
    def test_push_and_pull(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            entry = RegistryEntry(name="greeting", template="Hello {{name}}!", description="问候模板")
            registry.push(entry)

            pulled = registry.pull("greeting")
            assert pulled is not None
            assert pulled.name == "greeting"
            assert pulled.version == 1
            registry.close()

    def test_pull_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            result = registry.pull("nonexistent")
            assert result is None
            registry.close()

    def test_version_increment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            entry = RegistryEntry(name="test", template="v1")
            registry.push(entry)
            entry2 = RegistryEntry(name="test", template="v2")
            registry.push(entry2)

            latest = registry.pull("test")
            assert latest.version == 2

            v1 = registry.pull("test", version=1)
            assert v1.template == "v1"
            registry.close()

    def test_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="code-review", template="review code", category="coding"))
            registry.push(RegistryEntry(name="translate", template="translate text", category="language"))

            results = registry.search("code")
            assert len(results) >= 1
            assert results[0].name == "code-review"
            registry.close()

    def test_list_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="a", template="ta", category="cat1"))
            registry.push(RegistryEntry(name="b", template="tb", category="cat2"))
            registry.push(RegistryEntry(name="c", template="tc", category="cat1"))

            all_entries = registry.list_entries()
            assert len(all_entries) == 3

            cat1 = registry.list_entries(category="cat1")
            assert len(cat1) == 2
            registry.close()

    def test_list_by_tag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="a", template="ta", tags=["python", "coding"]))
            registry.push(RegistryEntry(name="b", template="tb", tags=["golang"]))

            results = registry.list_entries(tag="python")
            assert len(results) == 1
            registry.close()

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="del-me", template="delete"))
            assert registry.delete("del-me") >= 1
            assert registry.pull("del-me") is None
            registry.close()

    def test_get_versions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="vtest", template="v1"))
            registry.push(RegistryEntry(name="vtest", template="v2"))
            registry.push(RegistryEntry(name="vtest", template="v3"))
            versions = registry.get_versions("vtest")
            assert versions == [1, 2, 3]
            registry.close()

    def test_get_tags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="a", template="t", tags=["python", "ai"]))
            registry.push(RegistryEntry(name="b", template="t", tags=["golang", "ai"]))
            tags = registry.get_tags()
            assert "python" in tags
            assert "golang" in tags
            assert "ai" in tags
            registry.close()

    def test_get_categories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="a", template="t", category="coding"))
            registry.push(RegistryEntry(name="b", template="t", category="language"))
            cats = registry.get_categories()
            assert "coding" in cats
            assert "language" in cats
            registry.close()

    def test_export_import_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PromptRegistry(db_path=db_path)
            registry.push(RegistryEntry(name="export-test", template="hello", description="test export", tags=["test"]))

            export_path = Path(tmpdir) / "export.json"
            registry.export_json(export_path)
            registry.close()
            assert export_path.exists()

            import_data = json.loads(export_path.read_text(encoding="utf-8"))
            assert import_data["count"] == 1
            assert import_data["entries"][0]["name"] == "export-test"

            db2_path = Path(tmpdir) / "test2.db"
            registry2 = PromptRegistry(db_path=db2_path)
            imported = registry2.import_json(export_path)
            assert imported == 1

            pulled = registry2.pull("export-test")
            registry2.close()
            assert pulled is not None
            assert pulled.template == "hello"

    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="a", template="t", category="cat1", tags=["t1"]))
            stats = registry.stats()
            assert stats["total_entries"] == 1
            assert stats["unique_templates"] == 1
            registry.close()

    def test_list_by_author(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            registry.push(RegistryEntry(name="a", template="t", author="alice"))
            registry.push(RegistryEntry(name="b", template="t", author="bob"))
            results = registry.list_entries(author="alice")
            assert len(results) == 1
            registry.close()
