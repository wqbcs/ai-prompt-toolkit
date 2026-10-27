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

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_prompt_toolkit.cli_helpers import read_prompt_text

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
    EVALUATE = "evaluate"


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
        in_degree: dict[str, int] = dict.fromkeys(self.nodes, 0)
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

    _NODE_COLORS: dict[NodeType, str] = {
        NodeType.PROMPT: "#4A90D9",
        NodeType.LLM: "#7B68EE",
        NodeType.PYTHON: "#F5A623",
        NodeType.CONDITION: "#E67E22",
        NodeType.AGGREGATE: "#27AE60",
        NodeType.LINT: "#E74C3C",
        NodeType.SCAN: "#C0392B",
        NodeType.GEPA: "#8E44AD",
        NodeType.EVALUATE: "#3498DB",
    }

    def to_svg(self, width: int = 1200, height: int = 800) -> str:
        order = self.topological_sort()
        layers: dict[str, int] = {}
        for node_name in order:
            preds = [e.source for e in self.edges if e.target == node_name]
            if not preds:
                layers[node_name] = 0
            else:
                layers[node_name] = max(layers.get(p, 0) for p in preds) + 1

        max_layer = max(layers.values()) if layers else 0
        layer_nodes: dict[int, list[str]] = {}
        for name, layer in layers.items():
            layer_nodes.setdefault(layer, []).append(name)

        node_width = 180
        node_height = 56
        layer_spacing = (width - node_width) / max(max_layer, 1) if max_layer > 0 else 0
        positions: dict[str, tuple[float, float]] = {}
        for layer_idx, nodes_in_layer in layer_nodes.items():
            total_height = len(nodes_in_layer) * (node_height + 20) - 20
            start_y = (height - total_height) / 2
            for i, name in enumerate(nodes_in_layer):
                x = layer_idx * layer_spacing + 40
                y = start_y + i * (node_height + 20)
                positions[name] = (x, y)

        lines: list[str] = []
        lines.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        )
        lines.append(f'<rect width="{width}" height="{height}" fill="#1a1a2e" rx="8"/>')

        if self.name:
            lines.append(
                f'<text x="{width / 2}" y="30" text-anchor="middle" fill="#e0e0e0" font-family="monospace" font-size="16" font-weight="bold">{_svg_escape(self.name)}</text>'
            )

        for edge in self.edges:
            if edge.source in positions and edge.target in positions:
                sx, sy = positions[edge.source]
                tx, ty = positions[edge.target]
                x1 = sx + node_width
                y1 = sy + node_height / 2
                x2 = tx
                y2 = ty + node_height / 2
                mx = (x1 + x2) / 2
                lines.append(
                    f'<path d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}" stroke="#555" stroke-width="1.5" fill="none" marker-end="url(#arrow)"/>'
                )
                if edge.condition:
                    cond_text = _svg_escape(edge.condition[:20])
                    lines.append(
                        f'<text x="{mx}" y="{(y1 + y2) / 2 - 8}" text-anchor="middle" fill="#888" font-family="monospace" font-size="9">{cond_text}</text>'
                    )

        lines.append(
            '<defs><marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#555"/></marker></defs>'
        )

        for name, (x, y) in positions.items():
            node = self.nodes[name]
            color = self._NODE_COLORS.get(node.node_type, "#4A90D9")
            lines.append(
                f'<rect x="{x}" y="{y}" width="{node_width}" height="{node_height}" rx="6" fill="{color}" opacity="0.9"/>'
            )
            label = _svg_escape(name[:18])
            type_label = _svg_escape(node.node_type.value)
            lines.append(
                f'<text x="{x + node_width / 2}" y="{y + 22}" text-anchor="middle" fill="white" font-family="monospace" font-size="12" font-weight="bold">{label}</text>'
            )
            lines.append(
                f'<text x="{x + node_width / 2}" y="{y + 40}" text-anchor="middle" fill="#ddd" font-family="monospace" font-size="10">{type_label}</text>'
            )

        lines.append("</svg>")
        return "\n".join(lines)

    def to_dot(self) -> str:
        lines = [f'digraph "{_dot_escape(self.name)}" {{']
        lines.append("  rankdir=LR;")
        lines.append('  node [shape=box, style="rounded,filled", fontname="monospace"];')
        for name, node in self.nodes.items():
            color = self._NODE_COLORS.get(node.node_type, "#4A90D9")
            lines.append(
                f'  "{_dot_escape(name)}" [label="{_dot_escape(name)}\\n{_dot_escape(node.node_type.value)}", fillcolor="{color}", fontcolor="white"];'
            )
        for edge in self.edges:
            cond = f' [label="{_dot_escape(edge.condition)}"]' if edge.condition else ""
            lines.append(f'  "{_dot_escape(edge.source)}" -> "{_dot_escape(edge.target)}"{cond};')
        lines.append("}")
        return "\n".join(lines)

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
        from pathlib import Path

        import yaml

        content = read_prompt_text(Path(yaml_path))
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

        elif node.node_type == NodeType.EVALUATE:
            from ai_prompt_toolkit.evaluator import evaluate_template

            text = inputs.get("text", inputs.get("rendered", ""))
            # R198: _DimensionEvaluator只评单个维度dict; 节点语义是整模板评估,
            # 用真实入口evaluate_template(template_id, text) -> EvaluationReport
            eval_result = evaluate_template(node.name, str(text))
            return {
                "overall_score": eval_result.overall_score,
                "dimensions_count": len(eval_result.scores),
            }

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
            # R197: 改名防result与其他node_type分支同名复用(mypy沿用首次推断)
            gepa_res = gepa_optimize(str(text), metric=metric, auto=auto)
            return {
                "best_instructions": gepa_res.best_instructions,
                "best_score": gepa_res.best_score,
                "improvement": gepa_res.improvement,
            }

        elif node.node_type == NodeType.CONDITION:
            _condition = node.config.get("expression", "")  # 表达式求值未实现, 当前语义为阈值比较
            value = inputs.get("value", inputs.get("score", 0))
            if isinstance(value, (int, float)):
                threshold = node.config.get("threshold", 0)
                return {"passed": value >= threshold, "value": value}

        elif node.node_type == NodeType.AGGREGATE:
            return dict(inputs)

        elif node.node_type == NodeType.PYTHON:
            func_name = node.config.get("function", "")
            if func_name:
                import importlib

                parts = func_name.rsplit(".", 1)
                # R306 深审 M-3: PYTHON 节点=代码执行面。"声明式流水线"心智模型
                # 会让用户把共享仓库的 flow YAML 当数据信任, 而 config.function
                # 语义是任意模块导入+调用。硬闸: 仅 ai_prompt_toolkit. 命名空间
                # 内模块; 命名空间外=跳过(与既有 len(parts)!=2/无函数 的静默跳过
                # 同口径, 不改变输出形状)。
                if len(parts) == 2 and parts[0].startswith("ai_prompt_toolkit."):
                    module = importlib.import_module(parts[0])
                    func = getattr(module, parts[1], None)
                    if func:
                        return func(**inputs)

        return {"output": inputs}


class InteractiveFlowExecutor:
    def __init__(self, flow: FlowDAG) -> None:
        self.flow = flow
        self._context: dict[str, Any] = {}
        self._step_index: int = 0
        self._order: list[str] = []
        self._execution: FlowExecution | None = None
        self._start_time: float = 0.0
        self._paused: bool = False
        self._snapshots: list[dict[str, Any]] = []

    def _save_snapshot(self) -> None:
        self._snapshots.append(
            {
                "step_index": self._step_index,
                "context": {k: (v if not isinstance(v, dict) else dict(v)) for k, v in self._context.items()},
            }
        )

    def rollback(self, step_index: int) -> dict[str, Any]:
        if not self._snapshots:
            return {"status": "error", "error": "No snapshots available"}
        target = None
        for snap in self._snapshots:
            if snap["step_index"] <= step_index:
                target = snap
        if target is None:
            return {"status": "error", "error": f"No snapshot found for step {step_index}"}
        self._step_index = target["step_index"]
        self._context = dict(target["context"])
        self._snapshots = [s for s in self._snapshots if s["step_index"] <= step_index]
        if self._execution:
            for node_name in list(self._execution.results.keys()):
                order_idx = self._order.index(node_name) if node_name in self._order else -1
                if order_idx >= self._step_index:
                    del self._execution.results[node_name]
        self._paused = False
        return {"status": "rolled_back", "step": self._step_index}

    def list_snapshots(self) -> list[dict[str, Any]]:
        return [{"step_index": s["step_index"], "context_keys": list(s["context"].keys())} for s in self._snapshots]

    def start(self, initial_inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        self._context = {"$inputs": initial_inputs or {}}
        try:
            self._order = self.flow.topological_sort()
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        self._step_index = 0
        self._execution = FlowExecution(flow_name=self.flow.name)
        self._start_time = time.perf_counter()
        self._paused = False
        return {
            "status": "started",
            "flow_name": self.flow.name,
            "total_steps": len(self._order),
            "nodes": self._order,
        }

    def step(self) -> dict[str, Any]:
        if self._execution is None:
            return {"status": "not_started", "error": "Call start() first"}
        if self._step_index >= len(self._order):
            return {"status": "completed", "execution": self._execution.to_dict()}
        if self._paused:
            return {"status": "paused", "step": self._step_index}

        node_name = self._order[self._step_index]
        node = self.flow.nodes[node_name]
        node_start = time.perf_counter()

        try:
            resolved = self._resolve_inputs(node)
            output = self._execute_node(node, resolved)
            self._context[node_name] = output
            elapsed = (time.perf_counter() - node_start) * 1000
            result = FlowResult(
                node_name=node_name,
                output=output,
                status="success",
                execution_time_ms=elapsed,
            )
            self._execution.results[node_name] = result
        except Exception as e:
            elapsed = (time.perf_counter() - node_start) * 1000
            result = FlowResult(
                node_name=node_name,
                status="error",
                error=str(e),
                execution_time_ms=elapsed,
            )
            self._execution.results[node_name] = result

        self._step_index += 1
        self._save_snapshot()
        progress = self._step_index / len(self._order)
        return {
            "status": "step_completed",
            "node": node_name,
            "result": result.to_dict(),
            "progress": round(progress, 2),
            "completed_steps": self._step_index,
            "total_steps": len(self._order),
        }

    def run_all(self) -> dict[str, Any]:
        result = self.start()
        if result["status"] == "error":
            return result
        while self._step_index < len(self._order):
            step_result = self.step()
            if step_result.get("result", {}).get("status") == "error":
                return step_result
        return self.get_status()

    def pause(self) -> dict[str, Any]:
        self._paused = True
        return {"status": "paused", "step": self._step_index}

    def resume(self) -> dict[str, Any]:
        self._paused = False
        return {"status": "resumed", "step": self._step_index}

    def get_status(self) -> dict[str, Any]:
        if self._execution is None:
            return {"status": "not_started"}
        total_elapsed = (time.perf_counter() - self._start_time) * 1000
        self._execution.total_time_ms = total_elapsed
        self._execution.status = (
            "success"
            if all(r.status == "success" for r in self._execution.results.values())
            else ("partial" if self._step_index < len(self._order) else "error")
        )
        return {
            "status": "completed" if self._step_index >= len(self._order) else "in_progress",
            "execution": self._execution.to_dict(),
            "progress": round(self._step_index / max(len(self._order), 1), 2),
        }

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
        elif node.node_type == NodeType.EVALUATE:
            from ai_prompt_toolkit.evaluator import evaluate_template

            text = inputs.get("text", inputs.get("rendered", ""))
            # R198: _DimensionEvaluator只评单个维度dict; 节点语义是整模板评估,
            # 用真实入口evaluate_template(template_id, text) -> EvaluationReport
            eval_result = evaluate_template(node.name, str(text))
            return {
                "overall_score": eval_result.overall_score,
                "dimensions_count": len(eval_result.scores),
            }
        elif node.node_type == NodeType.SCAN:
            from ai_prompt_toolkit.security.injection_detector import InjectionDetector

            text = inputs.get("text", inputs.get("rendered", ""))
            detector = InjectionDetector()
            results = detector.detect(str(text), template_id=node.name)
            return {"injection_count": len(results) if isinstance(results, list) else 0}
        elif node.node_type == NodeType.CONDITION:
            _condition = node.config.get("expression", "")  # 表达式求值未实现, 当前语义为阈值比较
            value = inputs.get("value", inputs.get("score", 0))
            if isinstance(value, (int, float)):
                threshold = node.config.get("threshold", 0)
                return {"passed": value >= threshold, "value": value}
        elif node.node_type == NodeType.AGGREGATE:
            return dict(inputs)
        return {"output": inputs}


def create_lint_scan_flow(name: str = "lint-scan-flow") -> FlowDAG:
    dag = FlowDAG(name=name)
    dag.add_node(
        FlowNode(
            name="input", node_type=NodeType.PROMPT, config={"template": "{{text}}"}, inputs={"text": "${$inputs.text}"}
        )
    )
    dag.add_node(FlowNode(name="lint", node_type=NodeType.LINT, inputs={"text": "${input.rendered}"}))
    dag.add_node(FlowNode(name="scan", node_type=NodeType.SCAN, inputs={"text": "${input.rendered}"}))
    dag.add_node(
        FlowNode(
            name="aggregate", node_type=NodeType.AGGREGATE, inputs={"lint_result": "${lint}", "scan_result": "${scan}"}
        )
    )
    dag.add_edge("input", "lint")
    dag.add_edge("input", "scan")
    dag.add_edge("lint", "aggregate")
    dag.add_edge("scan", "aggregate")
    return dag


def create_gepa_optimize_flow(name: str = "gepa-optimize-flow") -> FlowDAG:
    dag = FlowDAG(name=name)
    dag.add_node(
        FlowNode(
            name="input", node_type=NodeType.PROMPT, config={"template": "{{text}}"}, inputs={"text": "${$inputs.text}"}
        )
    )
    dag.add_node(FlowNode(name="lint_before", node_type=NodeType.LINT, inputs={"text": "${input.rendered}"}))
    dag.add_node(
        FlowNode(
            name="gepa",
            node_type=NodeType.GEPA,
            inputs={"text": "${input.rendered}"},
            config={"auto": "light", "metric": "lint_score"},
        )
    )
    dag.add_node(
        FlowNode(
            name="aggregate", node_type=NodeType.AGGREGATE, inputs={"before": "${lint_before}", "optimized": "${gepa}"}
        )
    )
    dag.add_edge("input", "lint_before")
    dag.add_edge("input", "gepa")
    dag.add_edge("lint_before", "aggregate")
    dag.add_edge("gepa", "aggregate")
    return dag


class PromptChain:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self._steps: list[dict[str, Any]] = []
        self._mode: str = "sequential"

    def sequential(self, *node_names: str) -> PromptChain:
        self._mode = "sequential"
        for name in node_names:
            self._steps.append({"name": name, "mode": "sequential"})
        return self

    def parallel(self, *node_names: str) -> PromptChain:
        self._mode = "parallel"
        for name in node_names:
            self._steps.append({"name": name, "mode": "parallel"})
        return self

    def conditional(self, node_name: str, condition: str, true_branch: str, false_branch: str) -> PromptChain:
        self._steps.append(
            {
                "name": node_name,
                "mode": "conditional",
                "condition": condition,
                "true_branch": true_branch,
                "false_branch": false_branch,
            }
        )
        return self

    def build(self) -> FlowDAG:
        dag = FlowDAG(name=self.name)
        all_node_names = set()
        for step in self._steps:
            all_node_names.add(step["name"])
            if step["mode"] == "conditional":
                all_node_names.add(step.get("true_branch", ""))
                all_node_names.add(step.get("false_branch", ""))

        for name in all_node_names:
            if not name:
                continue
            is_cond = any(s["mode"] == "conditional" and s["name"] == name for s in self._steps)
            node_type = NodeType.CONDITION if is_cond else NodeType.PROMPT
            config: dict[str, Any] = {}
            if is_cond:
                cond_step = next(s for s in self._steps if s["name"] == name)
                config["expression"] = cond_step.get("condition", "")
            dag.add_node(FlowNode(name=name, node_type=node_type, config=config))

        sequential_steps = [s for s in self._steps if s["mode"] == "sequential"]
        for i in range(len(sequential_steps) - 1):
            dag.add_edge(sequential_steps[i]["name"], sequential_steps[i + 1]["name"])

        parallel_steps = [s for s in self._steps if s["mode"] == "parallel"]
        if len(parallel_steps) >= 2:
            join_name = f"{parallel_steps[0]['name']}_join"
            dag.add_node(FlowNode(name=join_name, node_type=NodeType.AGGREGATE))
            for step in parallel_steps:
                dag.add_edge(step["name"], join_name)

        for step in self._steps:
            if step["mode"] == "conditional":
                dag.add_edge(step["name"], step["true_branch"], condition="true")
                dag.add_edge(step["name"], step["false_branch"], condition="false")

        return dag


def _svg_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _dot_escape(text: str) -> str:
    return text.replace('"', '\\"').replace("\n", "\\n")
