"""P1-05a: lint --stdio 协议 e2e 测试 — 真子进程(非 CliRunner)

为什么真子进程: stdio 协议的存在意义就是"常驻进程 + 行边界同步",
CliRunner 模拟不出 stdin/stdout 行流。覆盖协议契约的四个断言面:
1. 握手 hello 行(协议版本)
2. lint 请求→响应(result 与 lint_template 直调一致=内核同一真源)
3. 健壮性: 非法 JSON/未知 op/单请求异常 均不杀死 server
4. 确定性: 相同请求两次响应逐字节一致(楔子)
5. exit 请求 → 进程干净退出(无僵尸输出)
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

# 正样本: R213 验证的稳定触发文本(命中 P001/P003/P005/P022/P046/P081/P161)
_ATTACK = "模板渲染引擎处理 {{user_input}} 变量，无转义。"


@pytest.fixture()
def stdio_server():
    """启动 `python -m ai_prompt_toolkit lint --stdio` 真子进程"""
    proc = subprocess.Popen(
        [sys.executable, "-m", "ai_prompt_toolkit", "lint", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    yield proc
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=10)


def _roundtrip(proc: subprocess.Popen, request: dict | str, expect_response: bool = True) -> dict:
    """发一行请求, 读一行响应"""
    if isinstance(request, dict):
        request = json.dumps(request, ensure_ascii=False)
    proc.stdin.write(request + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, "server 未响应(协议要求每请求一行响应)"
    return json.loads(line)


class TestStdioProtocol:
    def test_hello_handshake(self, stdio_server):
        """启动行: 协议版本+server版本(bridge 端握手确认)"""
        line = stdio_server.stdout.readline()
        hello = json.loads(line)
        assert hello["ok"] is True
        assert hello["hello"] == "prompt-cli-stdio"
        assert hello["protocol"] == 1
        assert "version" in hello

    def test_lint_request_matches_direct_kernel(self, stdio_server):
        """内核同一真源: stdio 响应的 result == lint_template 直调"""
        stdio_server.stdout.readline()  # 吃掉 hello
        from ai_prompt_toolkit.linter import lint_template

        direct = lint_template("e2e.prompt", _ATTACK, fix=False, apply_waivers=True).to_dict()
        resp = _roundtrip(stdio_server, {"op": "lint", "id": 1, "path": "e2e.prompt", "text": _ATTACK})
        assert resp["ok"] is True
        assert resp["id"] == 1
        # 剥离进程间必然不同的字段(耗时), 其余逐字段一致
        a, b = dict(resp["result"]), dict(direct)
        a.pop("lint_time_ms", None)
        b.pop("lint_time_ms", None)
        assert a == b
        assert a["failed_count"] > 0  # 攻击文本必须有 findings(防空转)

    def test_lint_rules_filter(self, stdio_server):
        """rules 过滤透传: 只跑 P0 族"""
        stdio_server.stdout.readline()
        resp = _roundtrip(stdio_server, {"op": "lint", "id": 2, "path": "a.prompt", "text": _ATTACK, "rules": ["P0"]})
        assert resp["ok"] is True
        rule_ids = {f["rule_id"] for f in resp["result"]["findings"]}
        assert rule_ids and all(rid.startswith("P0") for rid in rule_ids)

    def test_deterministic_repeated_requests(self, stdio_server):
        """楔子 e2e: 相同请求两次, result 逐字节一致(去耗时字段)"""
        stdio_server.stdout.readline()
        req = {"op": "lint", "id": 1, "path": "x.prompt", "text": _ATTACK}
        r1 = _roundtrip(stdio_server, req)
        r2 = _roundtrip(stdio_server, dict(req, id=2))
        s1 = json.dumps(r1["result"], ensure_ascii=False, sort_keys=True)
        s2 = json.dumps(r2["result"], ensure_ascii=False, sort_keys=True)
        # lint_time_ms 是墙钟 — 剥离后必须逐字节一致
        assert s1.replace('"lint_time_ms": ' + str(json.loads(s1)["lint_time_ms"]), "") == s2.replace(
            '"lint_time_ms": ' + str(json.loads(s2)["lint_time_ms"]), ""
        )

    def test_invalid_json_does_not_kill_server(self, stdio_server):
        """健壮性1: 非法 JSON 行 → 错误响应(id=null), server 存活"""
        stdio_server.stdout.readline()
        resp = _roundtrip(stdio_server, "{not valid json")
        assert resp["ok"] is False
        assert resp["id"] is None
        assert "invalid" in resp["error"]
        # server 存活: 下一个合法请求仍正常
        resp2 = _roundtrip(stdio_server, {"op": "ping", "id": 9})
        assert resp2["ok"] is True and resp2["pong"] is True

    def test_unknown_op_responds_error(self, stdio_server):
        """健壮性2: 未知 op → 错误响应, 不崩"""
        stdio_server.stdout.readline()
        resp = _roundtrip(stdio_server, {"op": "frobnicate", "id": 3})
        assert resp["ok"] is False
        assert resp["id"] == 3
        assert "unknown op" in resp["error"]

    def test_lint_missing_text_responds_error(self, stdio_server):
        """健壮性3: text 缺失/非字符串 → 错误响应, 不崩"""
        stdio_server.stdout.readline()
        resp = _roundtrip(stdio_server, {"op": "lint", "id": 4, "path": "a.prompt"})
        assert resp["ok"] is False
        assert resp["id"] == 4
        _roundtrip(stdio_server, {"op": "ping", "id": 5})  # 存活确认

    def test_serialization_order_preserved(self, stdio_server):
        """串行化: 连发3请求, 响应顺序=到达顺序(单线程处理)"""
        stdio_server.stdout.readline()
        for i in range(3):
            proc = stdio_server
            proc.stdin.write(json.dumps({"op": "lint", "id": i, "path": f"f{i}.prompt", "text": _ATTACK}) + "\n")
        stdio_server.stdin.flush()
        for i in range(3):
            resp = json.loads(stdio_server.stdout.readline())
            assert resp["id"] == i, f"响应乱序: 期望 id={i}, 实得 {resp['id']}"

    def test_exit_terminates_cleanly(self, stdio_server):
        """退出: {"op":"exit"} 后进程退出码 0, 无僵尸响应"""
        stdio_server.stdout.readline()  # hello
        stdio_server.stdin.write(json.dumps({"op": "exit"}) + "\n")
        stdio_server.stdin.flush()
        stdio_server.stdin.close()
        assert stdio_server.wait(timeout=15) == 0

    def test_empty_lines_ignored(self, stdio_server):
        """空行: 协议允许空白行(编辑器 bridge 的换行噪声), 不产生响应"""
        stdio_server.stdout.readline()  # hello
        stdio_server.stdin.write("\n\n")
        stdio_server.stdin.flush()
        resp = _roundtrip(stdio_server, {"op": "ping", "id": 7})
        assert resp["ok"] is True and resp["id"] == 7
