# MCP 接入（Claude Desktop / Cursor / Windsurf）

> P1-20 工件：把既有 MCP server（73 tools）接入 AI 编码助手的一键配置。
> 叙事定位："AI 写的 prompt 也要过门禁"——agent-first 采用面。
>
> 服务端事实（已验证，非规划）：
> - 入口：`python -m ai_prompt_toolkit.mcp_server`（stdio JSON-RPC，零依赖手写实现）
> - CLI 自检：`prompt-cli mcp --validate-only`（仅校验工具注册表与 tools_list 一致性，供 CI/冒烟）
> - 73 个 tool 全是确定性内核包装（无 LLM 调用）
> - 协议版本协商已实现（2025-06-18 / 2025-03-26 / 2024-11-05，R239 收口）
>
> 边界声明：registry 收录（mcp.so 等）与 ≥1 客户端实连冒烟为发布后动作，
> 已登记 02 总板 P1-20。

## 前置

```bash
pip install ai-prompt-toolkit   # 或 uv tool install ai-prompt-toolkit
python -m ai_prompt_toolkit.mcp_server --help >/dev/null && echo OK
```

Python 3.10+。零 key、零网络依赖（server 本地 stdio，不回调任何服务）。

## 标准配置（三客户端通用 mcpServers 格式）

```json
{
  "mcpServers": {
    "prompt-toolkit": {
      "command": "python",
      "args": ["-m", "ai_prompt_toolkit.mcp_server"]
    }
  }
}
```

各客户端落点（以客户端官方文档为准）：

| 客户端 | 配置位置 |
|---|---|
| Claude Desktop | `claude_desktop_config.json`（macOS `~/Library/Application Support/Claude/`，Windows `%APPDATA%\Claude\`） |
| Cursor | 项目级 `.cursor/mcp.json`，或 Settings → MCP |
| Windsurf | Settings → MCP Servers（全局 `mcp_config.json`） |

## 零安装变体（uvx，需本机已装 uv）

```json
{
  "mcpServers": {
    "prompt-toolkit": {
      "command": "uvx",
      "args": ["--from", "ai-prompt-toolkit", "python", "-m", "ai_prompt_toolkit.mcp_server"]
    }
  }
}
```

隔离环境运行，不落全局 site-packages；首次启动拉包后缓存。

## 接入后自检

1. 客户端 MCP 面板应列出 **73 个 tools**（`prompt_lint` / `prompt_scan` /
   `prompt_evaluate` / `prompt_redteam` / `prompt_doctor` 等）
2. 让客户端调用 `prompt_lint` 传一段含注入风险的 prompt 文本 → 应返回确定性
   findings（与 CLI `prompt-cli lint` 同一内核、同一真源，裁决逐字节一致）
3. CI/冒烟：`prompt-cli mcp --validate-only`（退出码 0=注册表一致）

## 能力面速览（73 tools 分组）

Lint/Scan（prompt_lint 268 规则、prompt_scan、prompt_judge、canary）·
评估（prompt_evaluate 130 维度、scorecard、dataset）· 安全引擎（5 层融合、
badge、token 分析）· 红队/Probe（probe_run/detect/list/owasp_report）·
编译/优化（compile、gepa、auto_optimize、sanitize）· 版本/缓存 ·
报告（junit、sarif、diff、merge）· 模板渲染/doctor/trace。
完整工具清单以 `prompt-cli mcp --validate-only` 输出与运行时 `tools/list` 为准。
