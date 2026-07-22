"""R29: Flow DAG编排引擎 + GEPA版本管理集成 测试套件"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ai_prompt_toolkit.flow_dag import (
    FlowDAG,
    FlowEdge,
    FlowExecution,
    FlowExecutor,
    FlowNode,
    FlowResult,
    NodeType,
    create_gepa_optimize_flow,
    create_lint_scan_flow,
)
from ai_prompt_toolkit.gepa import ScoreWithFeedback, gepa_optimize


# ═══════════════════════════════════════
# FlowNode 测试
# ═══════════════════════════════════════

class TestFlowNode:
    def test_basic_creation(self):
        node = FlowNode(name="test", node_type=NodeType.PROMPT)
        assert node.name == "test"
        assert node.node_type == NodeType.PROMPT

    def test_to_dict(self):
        node = FlowNode(name="lint", node_type=NodeType.LINT, config={"threshold": 90})
        d = node.to_dict()
        assert d["name"] == "lint"
        assert d["node_type"] == "lint"


# ═══════════════════════════════════════
# FlowDAG 测试
# ═══════════════════════════════════════

class TestFlowDAG:
    def test_add_node(self):
        dag = FlowDAG(name="test")
        dag.add_node(FlowNode(name="a", node_type=NodeType.PROMPT))
        assert "a" in dag.nodes

    def test_add_edge(self):
        dag = FlowDAG(name="test")
        dag.add_node(FlowNode(name="a"))
        dag.add_node(FlowNode(name="b"))
        dag.add_edge("a", "b")
        assert len(dag.edges) == 1

    def test_add_edge_missing_source(self):
        dag = FlowDAG(name="test")
        dag.add_node(FlowNode(name="b"))
        with pytest.raises(ValueError, match="Source node"):
            dag.add_edge("missing", "b")

    def test_topological_sort(self):
        dag = FlowDAG(name="test")
        dag.add_node(FlowNode(name="a"))
        dag.add_node(FlowNode(name="b"))
        dag.add_node(FlowNode(name="c"))
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        order = dag.topological_sort()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_topological_sort_parallel(self):
        dag = FlowDAG(name="test")
        dag.add_node(FlowNode(name="input"))
        dag.add_node(FlowNode(name="lint"))
        dag.add_node(FlowNode(name="scan"))
        dag.add_node(FlowNode(name="aggregate"))
        dag.add_edge("input", "lint")
        dag.add_edge("input", "scan")
        dag.add_edge("lint", "aggregate")
        dag.add_edge("scan", "aggregate")
        order = dag.topological_sort()
        assert order.index("input") < order.index("lint")
        assert order.index("input") < order.index("scan")
        assert order.index("lint") < order.index("aggregate")
        assert order.index("scan") < order.index("aggregate")

    def test_cycle_detection(self):
        dag = FlowDAG(name="test")
        dag.add_node(FlowNode(name="a"))
        dag.add_node(FlowNode(name="b"))
        dag.add_edge("a", "b")
        dag.add_edge("b", "a")
        with pytest.raises(ValueError, match="Cycle"):
            dag.topological_sort()

    def test_get_entry_nodes(self):
        dag = FlowDAG(name="test")
        dag.add_node(FlowNode(name="input"))
        dag.add_node(FlowNode(name="process"))
        dag.add_edge("input", "process")
        entry = dag.get_entry_nodes()
        assert entry == ["input"]

    def test_to_dict(self):
        dag = FlowDAG(name="test")
        dag.add_node(FlowNode(name="a", node_type=NodeType.PROMPT))
        d = dag.to_dict()
        assert d["name"] == "test"
        assert "a" in d["nodes"]

    def test_from_dict(self):
        data = {
            "name": "test-flow",
            "nodes": [
                {"name": "a", "node_type": "prompt"},
                {"name": "b", "node_type": "lint"},
            ],
            "edges": [
                {"source": "a", "target": "b"},
            ],
        }
        dag = FlowDAG.from_dict(data)
        assert len(dag.nodes) == 2
        assert len(dag.edges) == 1

    def test_from_yaml(self):
        import yaml
        data = {
            "name": "yaml-flow",
            "nodes": [
                {"name": "input", "node_type": "prompt"},
            ],
            "edges": [],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "flow.yaml"
            path.write_text(yaml.dump(data), encoding="utf-8")
            dag = FlowDAG.from_yaml(str(path))
            assert dag.name == "yaml-flow"


# ═══════════════════════════════════════
# FlowExecutor 测试
# ═══════════════════════════════════════

class TestFlowExecutor:
    def test_simple_prompt_flow(self):
        dag = FlowDAG(name="simple")
        dag.add_node(FlowNode(
            name="input",
            node_type=NodeType.PROMPT,
            config={"template": "Hello {{name}}!"},
            inputs={"name": "${$inputs.name}"},
        ))
        executor = FlowExecutor(dag)
        result = executor.execute(initial_inputs={"name": "World"})
        assert result.status == "success"
        assert "input" in result.results
        assert result.results["input"].status == "success"

    def test_lint_scan_flow(self):
        dag = create_lint_scan_flow()
        executor = FlowExecutor(dag)
        result = executor.execute(initial_inputs={"text": "You are a professional AI assistant."})
        assert result.status == "success"
        assert "lint" in result.results
        assert "scan" in result.results
        assert "aggregate" in result.results

    def test_condition_node(self):
        dag = FlowDAG(name="condition-test")
        dag.add_node(FlowNode(name="input", node_type=NodeType.PROMPT, config={"template": "test"}, inputs={}))
        dag.add_node(FlowNode(name="check", node_type=NodeType.CONDITION, inputs={"value": "85"}, config={"threshold": 80}))
        dag.add_edge("input", "check")
        executor = FlowExecutor(dag)
        result = executor.execute(initial_inputs={})
        assert result.status == "success"

    def test_aggregate_node(self):
        dag = FlowDAG(name="agg-test")
        dag.add_node(FlowNode(name="a", node_type=NodeType.PROMPT, config={"template": "hello"}, inputs={}))
        dag.add_node(FlowNode(name="b", node_type=NodeType.PROMPT, config={"template": "world"}, inputs={}))
        dag.add_node(FlowNode(name="agg", node_type=NodeType.AGGREGATE, inputs={"a": "${a}", "b": "${b}"}))
        dag.add_edge("a", "agg")
        dag.add_edge("b", "agg")
        executor = FlowExecutor(dag)
        result = executor.execute(initial_inputs={})
        assert result.status == "success"
        assert "agg" in result.results

    def test_variable_resolution(self):
        dag = FlowDAG(name="var-test")
        dag.add_node(FlowNode(name="gen", node_type=NodeType.PROMPT, config={"template": "test"}, inputs={}))
        dag.add_node(FlowNode(name="use", node_type=NodeType.PROMPT, config={"template": "Result: {{data}}"}, inputs={"data": "${gen.rendered}"}))
        dag.add_edge("gen", "use")
        executor = FlowExecutor(dag)
        result = executor.execute(initial_inputs={})
        assert result.status == "success"


# ═══════════════════════════════════════
# 预设Flow测试
# ═══════════════════════════════════════

class TestPresetFlows:
    def test_lint_scan_flow_structure(self):
        dag = create_lint_scan_flow()
        assert len(dag.nodes) == 4
        assert "input" in dag.nodes
        assert "lint" in dag.nodes
        assert "scan" in dag.nodes
        assert "aggregate" in dag.nodes

    def test_gepa_optimize_flow_structure(self):
        dag = create_gepa_optimize_flow()
        assert len(dag.nodes) == 4
        assert "gepa" in dag.nodes


# ═══════════════════════════════════════
# GEPA版本管理集成测试
# ═══════════════════════════════════════

class TestGepaVersionIntegration:
    def test_save_version_on_optimize(self):
        def fast_metric(gold, pred, **kwargs):
            return ScoreWithFeedback(score=0.8, feedback=None)

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_versions.db"
            import ai_prompt_toolkit.prompt_version as pv
            original_default = pv._DEFAULT_DB_PATH
            pv._DEFAULT_DB_PATH = db_path

            try:
                result = gepa_optimize(
                    "test prompt",
                    custom_metric=fast_metric,
                    auto="light",
                    save_version=True,
                    version_name="test-gepa-version",
                )
                assert isinstance(result, object)

                store = pv.PromptVersionStore(db_path=db_path)
                versions = store.list_versions("test-gepa-version")
                assert len(versions) >= 1
                assert versions[0].source == "gepa"
                store.close()
            finally:
                pv._DEFAULT_DB_PATH = original_default
