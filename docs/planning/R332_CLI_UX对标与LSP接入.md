# R332：CLI UX 对标判定（P5-15）+ LSP 接入指南（P5-16）

> R332（2026-10-19，v67.34.118 规划）· **纯内容轮**（零命令面变更、零新端点、零新目标类型——T6 窗口纪律）
> 前置：R330 §3 C 轴（C1 → P5-15）/ D 轴（D2 → P5-16）；R331 执行 A3/A1，C/D 按"有余力则顺带"顺延至本轮专轮。

## §0 摘要

- **P5-15**：CLI 面对行业事实标准逐项对标（clig.dev / sota-cli-ux Top-10 / cli.style /
  clispec.dev 2026-08 候选 / PatternFly），产出 16 项判定表：**13 项已落地（引用板行）、
  2 项小缺口登记（P5-17 NO_COLOR 语义 / P5-18 配置优先级文档）、1 项拒绝（长尾 --json）**。
  结论：CLI 面已顶配，对标**零"对标=打磨"项**（防滑坡机制生效，判定驱动 DoD 的既有设计产出形态）。
- **P5-16**：LSP 端 R197 起在仓（pygls，stdio/tcp 双模式，diagnostics+hover+codeAction+
  score 通知，300ms debounce），接入面文档为零（MCP 面有 mcp-setup.md，LSP 面无对照）→
  新建 `docs/lsp-setup.md`（VS Code / Neovim / Emacs 三编辑器 snippet，服务端命令全部实跑）
  + hermetic e2e 测试钉死 LSP stdio 往返（"命令实跑验证"CI 常设化）。
- **定位复核（第一性原理）**：确定性 LLM 提示词静态门禁（prompt 的 ESLint）。动态 LLM 测试
  族（promptfoo=应用层动态红队 / garak=模型层探针扫描）均不占本 lane；本轮两项均为
  **接入面/判定面**而非新能力。楔子（逐字节一致 / 零 LLM 成本 / <100ms / 离线）不变。

## §1 反思（5 问，压缩留痕）

**Q1 定位漂移？** 无。纯内容轮：判定表是判定面（不实施），LSP 指南是接入面（能力 R197 起
既有）。零命令面变更，零新端点。

**Q2 方向问题？** 自主面正确延续——P0-03/P0-04（公开/PyPI）仍用户阻塞，R330 执行顺序第三
（C/D 轴 S 级项）是既定路线。LSP=编辑器直连正路（生态早于 MCP 成熟），四端顶配化的真实缺口
（缺的只是接入文档，不是能力）。

**Q3 低价值打磨陷阱自查？** P5-15 判定驱动（DoD 明示缺口不自动实施）；实测 13/16 已顶配，
两个缺口都是文档/验证小面（非"打磨"）；P5-16 零代码内容；e2e 测试=接入面验证常设化
（非新能力）。**拒绝项**：长尾命令 --json（MCP 已是 agent 面单一真源，双机器输出源=漂移风险）/
CLI `--commands JSON` 导出（同上，MCP tools/list 即运行时 schema）/ 长尾 --dry-run（主突变面
已覆盖，余者幂等或低风险）。

**Q4 顶配/无天花板？** 各端既有栈即公认栈：LSP=pygls（Python LSP 生态标准）、编辑器侧=各
平台内置或主流客户端（Neovim 内置 LSP / Emacs Eglot 内置 / VS Code generic-lsp-proxy 主流）。
不加端、不换栈、不造桥（mcp-language-server 1.5k★ 仅参考，不引入）。

**Q5 五年脆弱性？** LSP=12 年以上稳定协议（langserver.org）；编辑器客户端面文档列备选
（generic-lsp-proxy 主 / glspc 备）防单点；pygls/lsprotocol 已声明 `[lsp]` extra（R223 纪律面
已核，pyproject.toml:95-98）。

## §2 P5-15：CLI UX 对标判定表

**对标源**（2026-10-19 联网）：
- clig.dev（Command Line Interface Guidelines——输出/TTY/退出码/空结果经典面）
- sota-cli-ux（Top-10 non-negotiables：流分离/pipe-safe/退出码/零标志常见路径/提示可跳过/
  错误三要素/Ctrl-C/dry-run/版本化 API）
- cli.style（Human & Agent Interface——"agents are first-class users and untrusted input sources"）
- clispec.dev v0.3-candidate（2026-08，6 原则：结构化输出/运行时 schema 自省/流分离/
  非交互默认/安全重试/输出有界）
- PatternFly CLI handbook（可及性：颜色不作唯一语义载体——本仓严重度=🔴✗⚠ℹ 符号+文字双载，符合）
- 竞品 lane（promptfoo CI-native/YAML 声明/compliance mapping；garak JSONL+阈值）：其 CLI
  强项全部已被本仓 SARIF/基线/CI 双触发面覆盖（R330 §2.3 已判定，不重复）

**判定表**（每条：对标项 | 现状证据 | 判定）：

| # | 对标项 | 现状（证据） | 判定 |
|---|---|---|---|
| 1 | stdout=data / stderr=其余（sota#1, clispec#3） | 协议纯净（P1-05a 板行 ✅）；cli_core.py:128 isatty 分支；MCP/LSP 协议面同内核 | 已落地 = P1-05a |
| 2 | TTY 检测 / pipe-safe（sota#2） | cli_core.py:128 `stdout.isatty()`；rich 自动 TTY 降级 | 已落地 |
| 3 | NO_COLOR 尊重（sota#2, no-color.org） | rich 路径=内置尊重；显式 `--color-theme monokai` 在 NO_COLOR=1 下仍出 ANSI（实测）——显式标志=用户明示意图，git `--color=always` 同形态（可辩护）；**默认主题自定义色路径未验证** | **缺口 → P5-17**（TTY 模拟验证默认主题尊重 NO_COLOR；显式主题覆盖语义文档化） |
| 4 | 每个数据命令 `--json`（sota#2, clispec#1） | lint `--format [json\|html\|cli\|sarif\|summary]`（核心数据命令齐备）；MCP 端=73 tools 运行时结构化访问（agent 面）；48 长尾命令无 --json | 已落地（核心面）+ 长尾**拒绝**（奥卡姆：MCP=agent 面单一真源，双机器输出源=漂移风险） |
| 5 | 退出码契约 0/1/2/3 分离+文档化（sota#3, clig） | 5 年不变量⑤；ci-integration.md 命令面速查；坏目标实测 RC=2；零参实测 RC=2+三要素错误 | 已落地 = 5 年不变量⑤ |
| 6 | 常见路径零必需标志（sota#5） | 零参 `lint` → RC=2 + "需要 --target/-t (或 --stdio 模式)"（实测）；ruff 同形态（`ruff check` 亦要求显式路径）；golangci-lint 默认 cwd | 已落地（设计立场：显式路径 > 隐式全仓扫描，防误扫全仓惊跳；ruff 同形态） |
| 7 | 所有提示可跳过 / CI 非阻塞（sota#6, clispec#4） | `-i/--interactive`=用户主动 opt-in（默认非交互）；`--suggest` 非交互替代；`--ci` 精简模式；eval stdin.isatty 分支（eval_commands.py:685/1429） | 已落地 |
| 8 | 错误三要素：什么失败/为何/怎么修（sota#7, clig） | P3-16 失败首行三要素（板行 ✅）；cli_error_formatter 三段式（三语） | 已落地 = P3-16 |
| 9 | Ctrl-C：130/清理/可恢复（sota#8） | cli_core.py:213 `_sigint_handler` + resume_state.py 进度保存恢复 + `--resume`（--help 实测） | 已落地 |
| 10 | 每个突变命令 `--dry-run`（sota#9） | `lint --fix --dry-run`（--help 实测）；baseline-save/init 未提供 | 部分 → **拒绝**（主突变面已覆盖；baseline-save=幂等覆写（重跑=同结果）, init=低风险脚手架；长尾 dry-run=打磨） |
| 11 | CLI 面=版本化 API（sota#10） | 5 年不变量 + "零命令面变更"轮纪律（T6 窗口）；R331 `--baseline-from`=纯增面 | 已落地 |
| 12 | 配置优先级文档化（sota#10, clispec） | `--config` YAML + .promptignore + init 配置（P2-03 单点配置 ✅）；**统一优先级陈述未文档化** | **缺口 → P5-18**（文档级：配置优先级一表，纯文档） |
| 13 | Schema 自省：运行时命令/输出形状发现（clispec#2） | MCP tools/list=运行时 schema（73 tools）；export-rules（R242 规则元数据 JSON） | 已落地（MCP=agent 面单一真源；CLI `--commands JSON` 导出=双真源，拒绝） |
| 14 | 空结果设计（clispec#6） | 实测：干净文件 → "✨ 全部通过 — 等级 A (99.3/100)" + 4 条下一步建议（badge/eval/baseline-save/scan）——clispec 范例形态（说清查了什么+建议下一步） | 已落地（超标杆） |
| 15 | 输出有界（clispec#6） | `--format summary` / `--statistics` / `--rules` / `--ignore-rules` / SARIF / top-10 slice（基线对比面） | 已落地 |
| 16 | 成功少说（clispec#5, clig） | 实测：成功=一行"✨ 全部通过"+建议；`--ci` 精简模式；`--gate` digest（P3-16） | 已落地 |

**判定汇总**：13/16 已落地（板行锚点齐）/ 2/16 小缺口（P5-17/P5-18，均文档或验证面，S 级）/
1/16 拒绝（长尾 --json，并入 #4）。

**结论（防对标=打磨滑坡）**：对标产出="CLI 面已顶配"——零打磨项。这正是 P5-15 DoD
（判定驱动、缺口不自动实施）的设计产出形态；两个登记缺口留待后续窗口按优先级消化。

## §3 P5-16：LSP 接入指南（docs/lsp-setup.md）

### 3.1 服务端事实（已验证，非规划）

- 入口：`prompt-cli lsp --mode [stdio|tcp] [--host 127.0.0.1] [--port 2087]`（--help 实测）
- 依赖：`[lsp]` extra = `pygls>=1.0` + `lsprotocol>=2023.0`（pyproject.toml:95-98 已声明，
  R223 纪律面已核）→ `pip install "ai-prompt-toolkit[lsp]"`
- 服务端身份：`prompt-lsp` v1.0.0；协议纯净：stdio JSON-RPC 与 MCP 面同内核（P1-05a）
- 能力面（lsp_server.py，238 行，R197 起在仓）：
  - **diagnostics**：did_open / did_change / did_close + 300ms debounce（per-URI timer，
    close 即清 + 空 diagnostics 清除）
  - **hover**：规则详情 + remediation + ⚡ 可自动修复标记（AUTO_FIXABLE_RULES）
  - **codeAction**：QuickFix 双形态（"修复 P###" / "查看 P### 详情"）
  - **custom notification**：`prompt/score`（质量分推送）
  - lint 内核 = 与 CLI 同一内核（裁决逐字节一致，楔子不变量 #1）
- 边界：编辑器客户端扩展（generic-lsp-proxy 等）=第三方生态面，不入本仓门禁范围；
  TCP 模式默认 127.0.0.1:2087（本地环回，无网络暴露面）。

### 3.2 接入形态（≥2 编辑器；选型依据）

| 编辑器 | 客户端 | 选型理由 |
|---|---|---|
| VS Code | **generic-lsp-proxy**（mjmorales，主）+ glspc v2（zsol，备） | VS Code 无内置通用 LSP 客户端；generic-lsp-proxy=配置驱动（.vscode/lsp-proxy.json）+ stdio/tcp 双传输 + 多 server 共存（与 markdown 既有 language server 并存不冲突）；glspc 备选防单点 |
| Neovim | 内置 LSP 客户端（零扩展） | Nvim 0.11+ `vim.lsp.config`/0.10 `vim.lsp.start`，filetypes={markdown, prompt}；零扩展=最稳路径 |
| Emacs | 内置 Eglot（零扩展） | eglot 手动连接形态；bonus 第三编辑器（DoD 要求 ≥2，三语 README 受众面覆盖主流） |

形态决策：`.md` 文件用内置 markdown languageId（零配置直连）；`.prompt`/`.prompt.md`
用 fileAssociations 关联（snippet 内给）。服务端不检查 languageId（任意文本即 lint，
lsp_server.py did_open 无类型分支）→ 关联到任何 languageId 均可工作。

### 3.3 e2e 验证（"命令实跑验证"CI 常设化）

- `tests/test_r332_lsp_e2e.py`（hermetic，`@pytest.mark.slow`）：spawn
  `prompt-cli lsp --mode stdio` 子进程 → `initialize`/`initialized` →
  `textDocument/didOpen`（注入攻击文本）→ 等待 `$/publishDiagnostics` →
  断言非空 + `code`=P### 形态 + severity 枚举合法 → `shutdown`/`exit`。
  debounce 300ms → 等待预算 10s 上限（只断言上限内到达，不做墙钟精确断言——R325 陷阱纪律）。
- TCP 模式本地实跑记录（启动 → 端口监听验证 → 关闭）写入 lsp-setup.md 附录。
- CI 形态：`-k "not slow"` 排除（同 R331 watch e2e 纪律），本地全量实跑。

## §4 验收

- **P5-15**：本文档 §2 判定表 + 02 总板 P5-15 行 → ✅（判定表落本行状态列）+ P5-17 /
  P5-18 缺口行登记（S 级，不自动实施）。
- **P5-16**：`docs/lsp-setup.md`（三编辑器 snippet + 服务端事实 + 前置自检命令）+
  `tests/test_r332_lsp_e2e.py`（slow）+ README:757 MCP 链接位 +1 行 LSP 链接。
- **门禁序**（R331 教训纳入）：版本 67.34.117→67.34.118（3 处 + README 徽章）→
  `gen_rules_doc.py`（非 --check）→ `sync_readme_metrics.py` → **`gen_operating_curve.py`
  （非 --check——工件嵌入 `__version__`，每次升版必重生成，R331 漏跑实证）** →
  `sync_badges.py` → `check_version_consistency.py` → 全量 pytest（预期 6903+1）→
  ruff 双口径（门禁面 + 全仓）→ mypy（改动面 + 全量）→ `release_gate --skip 1,2`
  → commit/push。

## §5 执行顺序

1. LSP e2e 测试（先实跑验证协议路径成立，再入套件钉死）
2. `docs/lsp-setup.md`（服务端命令全部实跑后落笔）
3. README 链接（:757 位 +1 行）
4. 02 总板回写（P5-15 ✅ / P5-16 ✅ / P5-17 / P5-18 登记）+ 00 交接
5. 升版门禁序 + 全量验证
6. commit/push 收口
