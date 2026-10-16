"""R306 — 全面深度审查加固测试（安全面白名单门控）

覆盖 R306 深审落地修复:
- M-1: MCP mcp_reload 动态导入命名空间白名单（仅 ai_prompt_toolkit.）
- M-3: flow PYTHON 节点命名空间白名单门控（声明式流水线 ≠ 任意代码执行）

hermetic: 零网络零外部依赖, 直接调工具函数/执行器方法。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ai_prompt_toolkit.flow_dag import FlowExecutor, FlowNode, NodeType  # noqa: E402
from ai_prompt_toolkit.mcp_server import _tool_mcp_reload  # noqa: E402


class TestMcpReloadWhitelist:
    def test_outside_namespace_rejected(self) -> None:
        # "json" 为已加载标准库模块: 修复前走 importlib.reload(json) 返回
        # status=reloaded; 白名单修复后先拒(工具参数=agent 可控输入, 任意
        # 模块的模块级代码执行=攻击面)
        result = _tool_mcp_reload({"module": "json"})
        assert result["status"] == "error"
        assert "ai_prompt_toolkit." in result["error"]

    def test_outside_namespace_not_imported(self) -> None:
        # 命名空间外+不存在的模块: 白名单短路, 不触达 importlib
        result = _tool_mcp_reload({"module": "nonexistent_pkg_r306_xyz"})
        assert result["status"] == "error"
        assert "ai_prompt_toolkit." in result["error"]

    def test_inside_namespace_default_reloads(self) -> None:
        result = _tool_mcp_reload({})  # 默认 module=ai_prompt_toolkit.linter.rules
        assert result["status"] == "reloaded"
        assert result["rule_count"] > 0


class TestFlowPythonNodeGate:
    """flow PYTHON 节点=config.function 的 import_module+调用, 修复前任意模块。"""

    def _node(self, func: str) -> FlowNode:
        return FlowNode(name="n1", node_type=NodeType.PYTHON, config={"function": func})

    def test_outside_namespace_skipped_not_executed(self) -> None:
        ex = _bare_executor()
        node = self._node("os.path.join")  # 命名空间外标准库
        out = ex._execute_node(node, {"a": 1})
        # 门控=跳过(与 len(parts)!=2/无函数 的既有静默跳过同口径, 输出形状不变)
        assert out == {"output": {"a": 1}}

    def test_inside_namespace_executed(self) -> None:
        ex = _bare_executor()
        node = self._node("ai_prompt_toolkit.types.parse_location")
        out = ex._execute_node(node, {"location": ""})
        # 白名单内=真实执行, 返回函数结果(≠跳过标记)
        assert out != {"output": {"location": ""}}


def _bare_executor() -> FlowExecutor:
    from ai_prompt_toolkit.flow_dag import FlowDAG

    flow = FlowDAG(name="r306-gate-test")
    flow.add_node(FlowNode(name="n1", node_type=NodeType.PYTHON, config={}))
    return FlowExecutor(flow)
