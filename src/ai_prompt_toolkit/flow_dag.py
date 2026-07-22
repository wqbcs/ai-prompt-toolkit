"""Flow DAG编排引擎——参考微软Promptflow flow.dag.yaml

核心特性:
- DAG定义: YAML声明式工作流(节点+边)
- 节点类型: prompt/llm/python/condition/aggregate
- 执行引擎: 拓扑排序+并行执行+条件分支
- 变量传递: 节点间${node.output}引用
- 与Lint/Scan/GEPA集成

参考:
- Promptflow: flow.dag.yaml可视化DAG编排
- Dify: 可视化Workflow画布
"""
from __future__ import annotations

import copy
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class NodeType(Enum):
    PROMPT = "prompt"
    LLM = "llm"
    PYTHON = "python"
    CONDITION = "condition"
    AGGREGATE = "aggregate"
    LINT = "lint"
    SCAN = "scan"
    GEPA = "gepa"


@dataclass
class FlowNode:
    name: str
    node_type: NodeType = NodeType.PROMPT
    config: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    next_nodes: list[str] = field(default_factory=list)
    condition: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "node_type": self.node_type.value,
            "config": self.config,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "next_nodes": self.next_nodes,
            "condition": self.condition,
        }


@dataclass
class FlowEdge:
    source: str
    target: str
    condition: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "condition": self.condition,
        }


@dataclass
class FlowResult:
    node_name: str
    output: Any = None
    status: str = "success"
    execution_time_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_name": self.node_name,
            "status": self.status,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "error": self.error,
            "output": str(self.output)[:500] if self.output else None,
        }


@dataclass
class FlowExecution:
    flow_name: str = ""
    results: dict[str, FlowResult] = field(default_factory=dict)
    total_time_ms: float = 0.0
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_name": self.flow_name,
            "status": self.status,
            "total_time_ms": round(self.total_time_ms, 2),
            "node_count": len(self.results),
            "results": {k: v.to_dict() for k, v in self.results.items()},
        }


class FlowDAG:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.nodes: dict[str, FlowNode] = {}
        self.edges: list[FlowEdge] = []
        self._adjacency: dict[str, list[str]] = {}

    def add_node(self, node: FlowNode) -> None:
        self.nodes[node.name] = node
        if node.name not in self._adjacency:
            self._adjacency[node.name] = []

    def add_edge(self, source: str, target: str, condition: str = "") -> None:
        if source not in self.nodes:
            raise ValueError(f"Source node '{source}' not found")
        if target not in self.nodes:
            raise ValueError(f"Target node '{target}' not found")
        self.edges.append(FlowEdge(source=source, target=target, condition=condition))
        if source not in self._adjacency:
            self._adjacency[source] = []
        self._adjacency[source].append(target)

    def topological_sort(self) -> list[str]:
        in_degree: dict[str, int] = {n: 0 for n in self.nodes}
        for edge in self.edges:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

        queue = [n for n, d in in_degree.items() if d == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in self._adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            raise ValueError("Cycle detected in flow DAG")

        return result

    def get_entry_nodes(self) -> list[str]:
        targets = {e.target for e in self.edges}
        return [n for n in self.nodes if n not in targets]

    def get_successors(self, node_name: str) -> list[str]:
        return self._adjacency.get(node_name, [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlowDAG:
        dag = cls(name=data.get("name", ""))
        for node_data in data.get("nodes", []):
            if isinstance(node_data, dict):
                node = FlowNode(
                    name=node_data["name"],
                    node_type=NodeType(node_data.get("node_type", "prompt")),
                    config=node_data.get("config", {}),
                    inputs=node_data.get("inputs", {}),
                )
                dag.add_node(node)
        for edge_data in data.get("edges", []):
            if isinstance(edge_data, dict):
                dag.add_edge(
                    source=edge_data["source"],
                    target=edge_data["target"],
                    condition=edge_data.get("condition", ""),
                )
        return dag

    @classmethod
    def from_yaml(cls, yaml_path: str | Any) -> FlowDAG:
        import yaml
        from pathlib import Path
        content = Path(yaml_path).read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        return cls.from_dict(data)


class FlowExecutor:
    def __init__(self, flow: FlowDAG) -> None:
        self.flow = flow
        self._context: dict[str, Any] = {}

    def execute(self, initial_inputs: dict[str, Any] | None = None) -> FlowExecution:
        execution = FlowExecution(flow_name=self.flow.name)
        start_time = time.perf_counter()
        self._context = {"$inputs": initial_inputs or {}}

        try:
            order = self.flow.topological_sort()
        except ValueError as e:
            execution.status = "error"
            execution.results["__error__"] = FlowResult("__error__", status="error", error=str(e))
            return execution

        for node_name in order:
            node = self.flow.nodes[node_name]
            node_start = time.perf_counter()

            try:
                resolved_inputs = self._resolve_inputs(node)
                output = self._execute_node(node, resolved_inputs)
                self._context[node_name] = output

                elapsed = (time.perf_counter() - node_start) * 1000
                execution.results[node_name] = FlowResult(
                    node_name=node_name,
                    output=output,
                    status="success",
                    execution_time_ms=elapsed,
                )
            except Exception as e:
                elapsed = (time.perf_counter() - node_start) * 1000
                execution.results[node_name] = FlowResult(
                    node_name=node_name,
                    status="error",
                    error=str(e),
                    execution_time_ms=elapsed,
                )
                break

        total_elapsed = (time.perf_counter() - start_time) * 1000
        execution.total_time_ms = total_elapsed
        execution.status = "success" if all(r.status == "success" for r in execution.results.values()) else "partial"
        return execution

    def _resolve_inputs(self, node: FlowNode) -> dict[str, Any]:
        resolved = {}
        for key, value in node.inputs.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                ref = value[2:-1]
                parts = ref.split(".")
                if len(parts) >= 1 and parts[0] in self._context:
                    val = self._context[parts[0]]
                    for part in parts[1:]:
                        if isinstance(val, dict):
                            val = val.get(part)
                        else:
                            val = getattr(val, part, None)
                        if val is None:
                            break
                    resolved[key] = val
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved

    def _execute_node(self, node: FlowNode, inputs: dict[str, Any]) -> Any:
        if node.node_type == NodeType.PROMPT:
            template = node.config.get("template", "")
            for key, value in inputs.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            return {"rendered": template}

        elif node.node_type == NodeType.LINT:
            from ai_prompt_toolkit.linter.linter import PromptLinter
            text = inputs.get("text", inputs.get("rendered", ""))
            linter = PromptLinter()
            result = linter.lint(node.name, str(text))
            return {"score": result.score, "findings_count": len(result.findings)}

        elif node.node_type == NodeType.SCAN:
            from ai_prompt_toolkit.security.injection_detector import InjectionDetector
            text = inputs.get("text", inputs.get("rendered", ""))
            detector = InjectionDetector()
            results = detector.detect(str(text), template_id=node.name)
            return {"injection_count": len(results) if isinstance(results, list) else 0}

        elif node.node_type == NodeType.GEPA:
            from ai_prompt_toolkit.gepa import gepa_optimize
            text = inputs.get("text", inputs.get("rendered", ""))
            auto = node.config.get("auto", "light")
            metric = node.config.get("metric", "lint_score")
            result = gepa_optimize(str(text), metric=metric, auto=auto)
            return {
                "best_instructions": result.best_instructions,
                "best_score": result.best_score,
                "improvement": result.improvement,
            }

        elif node.node_type == NodeType.CONDITION:
            condition = node.config.get("expression", "")
            value = inputs.get("value", inputs.get("score", 0))
            if isinstance(value, (int, float)):
                threshold = node.config.get("threshold", 0)
                return {"passed": value >= threshold, "value": value}

        elif node.node_type == NodeType.AGGREGATE:
            aggregated = {}
            for key, value in inputs.items():
                aggregated[key] = value
            return aggregated

        elif node.node_type == NodeType.PYTHON:
            func_name = node.config.get("function", "")
            if func_name:
                import importlib
                parts = func_name.rsplit(".", 1)
                if len(parts) == 2:
                    module = importlib.import_module(parts[0])
                    func = getattr(module, parts[1], None)
                    if func:
                        return func(**inputs)

        return {"output": inputs}


def create_lint_scan_flow(name: str = "lint-scan-flow") -> FlowDAG:
    dag = FlowDAG(name=name)
    dag.add_node(FlowNode(name="input", node_type=NodeType.PROMPT, config={"template": "{{text}}"}, inputs={"text": "${$inputs.text}"}))
    dag.add_node(FlowNode(name="lint", node_type=NodeType.LINT, inputs={"text": "${input.rendered}"}))
    dag.add_node(FlowNode(name="scan", node_type=NodeType.SCAN, inputs={"text": "${input.rendered}"}))
    dag.add_node(FlowNode(name="aggregate", node_type=NodeType.AGGREGATE, inputs={"lint_result": "${lint}", "scan_result": "${scan}"}))
    dag.add_edge("input", "lint")
    dag.add_edge("input", "scan")
    dag.add_edge("lint", "aggregate")
    dag.add_edge("scan", "aggregate")
    return dag


def create_gepa_optimize_flow(name: str = "gepa-optimize-flow") -> FlowDAG:
    dag = FlowDAG(name=name)
    dag.add_node(FlowNode(name="input", node_type=NodeType.PROMPT, config={"template": "{{text}}"}, inputs={"text": "${$inputs.text}"}))
    dag.add_node(FlowNode(name="lint_before", node_type=NodeType.LINT, inputs={"text": "${input.rendered}"}))
    dag.add_node(FlowNode(name="gepa", node_type=NodeType.GEPA, inputs={"text": "${input.rendered}"}, config={"auto": "light", "metric": "lint_score"}))
    dag.add_node(FlowNode(name="aggregate", node_type=NodeType.AGGREGATE, inputs={"before": "${lint_before}", "optimized": "${gepa}"}))
    dag.add_edge("input", "lint_before")
    dag.add_edge("input", "gepa")
    dag.add_edge("lint_before", "aggregate")
    dag.add_edge("gepa", "aggregate")
    return dag
