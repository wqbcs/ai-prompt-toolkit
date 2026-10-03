"""P1-05a: lint --stdio 常驻协议 server — 编辑器端零进程开销接入

架构定位(adapters 层, 04 §5 协议纪律): 纯文本行 JSON 契约, 内核
(lint_template) 与输出格式(SARIF/JSON/CLI) 均不感知本协议的存在。
VS Code/JetBrains/Neovim 任何一端的 bridge 都实现同一份协议(见
docs/stdio-protocol.md), 新增一端零内核改动。

为什么需要(vscode-eslint 同构): 每文件 spawn 一次 CLI 进程 ~300ms(Python
启动+依赖导入), 编辑器"保存即 lint"场景下不可用; 常驻 server 复用同一解释器,
单文件 lint 耗时=纯规则执行(与 `prompt-cli lint -s` 相同内核, <100ms 预算不变)。

协议(每行一个 JSON 对象, UTF-8, 请求/响应同 id 配对, 严格串行):
  请求  {"op":"lint","id":1,"path":"a.prompt","text":"...","rules":["P16"],"exclude":[]}
  响应  {"ok":true,"id":1,"result":{...LintResult.to_dict()...}}
  错误  {"ok":false,"id":1,"error":"<message>"}   (id 为请求id, 无法解析时为 null)
  探活  {"op":"ping","id":2} → {"ok":true,"id":2,"pong":true,"version":"67.x.x"}
  退出  {"op":"exit"} → server 立即退出(无响应行, 以进程退出为准)

健壮性契约(e2e 断言目标):
  - 非法 JSON 行: 回 {"ok":false,"id":null,...}, server 不死
  - 单请求抛异常: 回 {"ok":false,"id":N,...}, server 不死
  - 串行化: 单线程 for-line 循环, 请求处理顺序=到达顺序
  - 确定性: 相同 (text, rules, exclude) 的两次 lint 响应 result 逐字节一致
"""

from __future__ import annotations

import json
import sys


def _write_response(payload: dict) -> None:
    """单行 JSON + flush — 行边界是协议的唯一同步点, 绝不合并输出"""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _handle_lint(req: dict, req_id: object) -> None:
    from ai_prompt_toolkit.cli_helpers import expand_rule_ids
    from ai_prompt_toolkit.linter import lint_template

    try:
        text = req.get("text")
        path = req.get("path")
        if not isinstance(text, str):
            _write_response({"ok": False, "id": req_id, "error": "text 必须为字符串"})
            return
        # 与 CLI --rules 同语义: 前缀展开("P16"→P16x族), fail-safe 忽略未知条目
        raw_rules = req.get("rules")
        rules = expand_rule_ids(",".join(raw_rules)) if raw_rules else None
        raw_exclude = req.get("exclude")
        exclude = expand_rule_ids(",".join(raw_exclude)) if raw_exclude else None
        result = lint_template(
            str(path or "<stdin>"),
            text,
            fix=False,
            rules=rules,
            exclude=exclude,
            apply_waivers=True,
        )
        _write_response({"ok": True, "id": req_id, "result": result.to_dict()})
    except Exception as e:
        _write_response({"ok": False, "id": req_id, "error": f"{type(e).__name__}: {e}"})


def run_stdio_server() -> None:
    """行 JSON 请求循环。stdin EOF 或 {"op":"exit"} 时退出(exit 0)。"""
    from ai_prompt_toolkit import __version__

    # 启动行: bridge 端可据此确认握手(协议版本写死 1, 未来不兼容变更递增)
    _write_response({"ok": True, "id": None, "hello": "prompt-cli-stdio", "protocol": 1, "version": __version__})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            if not isinstance(req, dict):
                raise ValueError("请求必须是 JSON 对象")
        except (json.JSONDecodeError, ValueError) as e:
            _write_response({"ok": False, "id": None, "error": f"invalid request: {e}"})
            continue

        op = req.get("op")
        req_id = req.get("id")
        if op == "exit":
            return
        if op == "ping":
            _write_response({"ok": True, "id": req_id, "pong": True, "version": __version__})
        elif op == "lint":
            _handle_lint(req, req_id)
        else:
            _write_response({"ok": False, "id": req_id, "error": f"unknown op: {op!r}"})
