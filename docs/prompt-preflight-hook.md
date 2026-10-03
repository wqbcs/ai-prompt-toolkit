# Prompt Preflight Hook — AI 编码助手接入（P1-14）

把 `prompt-cli` 的确定性规则挂进 **AI 编码助手的 UserPromptSubmit hook**：
你写给模型的 prompt 在提交前过一遍静态质量检查——模糊/缺角色/缺格式约束/
模板注入风险等，**critical/high 阻断提交**（exit 2），提示回注到会话上下文。

这是 2026 年的新分发渠道信号（LaunchDarkly 等团队已把 prompt 管理挂进
编码助手生命周期）：prompt 的入口不再只是"仓库里的 .md 文件"（CI 面），
还有"人对 AI 助手说的话"（会话面）。本 hook 只做后者。

## 边界纪律（必读，勿混语义）

| | CI 安全门禁（主产品） | 本 hook（preflight） |
|---|---|---|
| 检测面 | 仓库→CI（.prompt 文件/模板） | 人→模型（会话内 prompt） |
| 失败语义 | **fail-closed**（红=阻断合并） | **fail-open**（hook 故障=放行，绝不卡住你的会话） |
| 语义 | 安全裁决 | 质量提示 |
| 文档 | README / adoption.md | 本文档 |

红线：hook **不替代** CI 门禁，也不引入 LLM 调用（楔子完整，纯规则执行）。

## 安装（一个命令覆盖 Claude Code 与 Codex）

两端的 UserPromptSubmit 输入格式兼容（stdin JSON 含 `prompt` 字段，
exit 2 阻断）——**同一份 hook 命令**，只是配置位置不同。

### Claude Code（`~/.claude/settings.json` 或项目 `.claude/settings.json`）

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m ai_prompt_toolkit --preflight-hook"
          }
        ]
      }
    ]
  }
}
```

### Codex CLI（`~/.codex/config.toml`）

```toml
[hooks.UserPromptSubmit]
command = "python -m ai_prompt_toolkit --preflight-hook"
```

### 通用行为

- **stdin**：hook 收 JSON（`{"prompt": "...", ...}`）；非 JSON 输入回退原文
- **stdout（exit 2 时）**：`{"decision":"block","reason":"...","hookSpecificOutput":{"additionalContext":"..."}}`
- **stdout（exit 0 且有提示时）**：纯文本 findings 列表，作为上下文注入（助手可见、可忽略）
- **退出码**：`2`=阻断（有 critical/high finding），`0`=放行（干净/仅 medium/low/故障）

## 调节

| 机制 | 用法 | 效果 |
|---|---|---|
| 提示模式（不阻断） | 命令加 `--nudge` | 永不 exit 2，findings 只作上下文注入 |
| 阻断阈值 | 环境变量 `PROMPT_PREFLIGHT_SEVERITY` | `critical`/`high`(默认)/`medium`/`low`/`none`(永不阻断) |

```bash
# 例: 只提示不阻断 + 只 critical 阻断
PROMPT_PREFLIGHT_SEVERITY=critical python -m ai_prompt_toolkit --preflight-hook
```

## 为什么 fail-open

hook 是**体验层**不是**安全层**：安全裁决在 CI gate（fail-closed）。
若 hook 自身故障（依赖缺失/规则异常/输入畸形）阻断你的 AI 会话，
"门禁工具"就成了"可用性杀手"。所以 hook 的任何异常都 exit 0 放行，
故障信息走 stderr（助手日志可见）。

## 限制（诚实声明）

- 单 prompt 全量 lint（无增量），典型耗时 ~50ms（261 规则，无 LLM）
- 会话面检测的是"你写的指令质量"，**不检测**模型输出（输出安全走 CI 面模板/运行时）
- 阻断阈值默认 high——首次接入建议 `--nudge` 跑一周观察误拦截率，再收紧

## 测试

`tests/test_r226_preflight_hook.py`（16 条，含真子进程 e2e：
阻断 JSON 结构/nudge 放行/空 prompt 静默/畸形输入 fail-open/环境阈值覆盖）
