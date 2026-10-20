# R331 改进方案与实施记录：基线防伪造（P3-20）+ watch 审计（P1-22）+ 增量退出码修复

> 2026-10-19 · 分支 main · 版本 67.34.116 → 67.34.117
> 定位锚（每步反问）：本项目是**确定性 prompt 静态门禁**——零 LLM 成本、逐字节一致裁决、
> <100ms/文件、离线可跑。本轮三项全部服务"门禁裁决不可被绕过/不可自废"这一核心价值，
> 无一是"全端体验"类低价值打磨（反清单：不为全端而全端）。

---

## §1 本轮定项（从 R330 A/B/C/D 清单收敛）

| # | 项 | 来源 | 规模 | 裁决 |
|---|---|---|---|---|
| A3 | `--baseline-from` 基线防伪造 | P3-20（02 总板） | M | **实施** — 门禁完整性漏洞（PR 作者可自废增量门禁） |
| A1 | watch 模式 | P1-22（02 总板，R330 登记"无"） | M→S | **审计+根因修** — 调研"无"是能力存在性漂移，能力已双实现存在 |
| X1 | `--incremental --fail-on` PASS 被全量退出路径覆写 | 本轮实施中发现（从未被测试钉住） | S | **根因修** — 违背 R224 自规格"存量放行, 老仓库接入不被存量打回" |

未选（留痕）：C 轴（文档 i18n 大面=反清单显式禁止）、D 轴（性能面=楔子已达标 <100ms/文件，
无瓶颈证据不动）、B 轴其余项（无红队/探针新缺口证据）。

---

## §2 A3：`--baseline-from` 基线防伪造

### 2.1 威胁模型（第一性原理）

`--incremental --baseline <file>` 默认从**工作树**读基线。PR/MR 上下文中工作树 = PR head：

```
攻击者 = PR 作者
动作   = 在 PR 内把新 findings 塞进基线文件"重存"（表面合规的 commit）
效果   = 新 HIGH/CRITICAL findings 被判 PRE-EXISTING → 增量门禁放行 → 门禁自废
成本   = 0（一个普通 commit）
```

这与 P3-15（content_sha256 篡改检测）互补但不同面：P3-15 检测"基线文件内部自洽性
（findings 段与存储 sha 不匹配）"且是**告警面**（07 TH7：不改退出码契约）；A3 是
**裁决面**——基线来源从"PR 作者可控的工作树"移到"平台/operator 提供的 git ref"。

### 2.2 参考与不重复造轮子

- **golangci-lint `--new-from-merge-base`**：同一问题域的成熟范式（只评 merge-base 后
  新增）。其解法依赖 git 对象——**git 本身就是可复用组件**，无需新依赖。
- 本仓库既有 `git_changed_since_rev`（P2-17 `--new-from-rev`）已确立"git 是仓库固有前提、
  零新依赖"的形态——`git_show_at_ref` 与其同形态（subprocess + timeout=30 + None 失败语义）。
- 未发现 Python 生态有"从 git ref 读文件做门禁"的独立组件（gitpython 引入=重量级新依赖，
  违背楔子：离线可跑+零 LLM 成本不因此受损但依赖面扩大，奥卡姆剃刀否决）。

### 2.3 实现（单一真源链）

| 层 | 落点 | 说明 |
|---|---|---|
| 原语 | `cli_helpers.git_show_at_ref(ref, path, cwd=None) -> str \| None` | `git show ref:path`；**参照系统一**：path 可仓库根相对或 CWD 相对，内部解析绝对 → `git rev-parse --show-toplevel` 转仓库根相对（`as_posix` 正斜杠归一——Windows `Path` str 为反斜杠，Windows 独有坑实测抓出；code_review P3 子目录场景） |
| 解析 | `linter/baseline.load_baseline_text(text)` | 解析单一真源；`load_baseline(path)` 委托之（三来源同解析函数：文件/ref/未来远端，无双源漂移） |
| 裁决面 | `lint --baseline-from REF`（与 `--incremental` 组合） | **预加载单一真源**（对比展示面前：单次 git 调用 + 单次解析 + 单次分歧告警），三表面（对比展示 / json_diff / 增量裁决）共用；工作树≠ref → stderr **分歧告警**（检测面，不改退出码契约，与 P3-15 互补）；ref 模式下损坏的工作树基线不影响运行 |
| 错误契约 | 缺 `--incremental` / 非 git 仓 / ref 不存在 / ref 上无路径 / 仓库外路径 / 损坏基线 JSON（ref 面+工作树面）→ exit 2 + 明确错误 | 与 5 年不变量⑤（0/1/2/3）一致 |
| CI 接线 | `prompt-ci.yml` quality-gate 作业 | PR 上下文：`git fetch origin $BASE_REF --depth 1` + `--baseline-from origin/$BASE_REF`；push 上下文工作树=canonical（CODEOWNERS 保护）不传 ref；**事件字段经 `env:` 注入而非插值进 shell 正文**（模板注入加固，业界 PR 加固模式） |
| 文档 | `docs/ci-integration.md` | 命令面速查 +1 行；新增"基线防伪造"节（GitHub Actions + GitLab CI 复制即用片段 + Azure 同构说明） |

### 2.4 边界（诚实声明）

- `--baseline-from` 的 path 可**仓库根相对或 CWD 相对**（自动解析为仓库根相对，仓库外路径=不存在；code_review P3 参照系统一——worktree 读取面与 git 面同参照系，子目录可用）。
- 裁决面只接**增量门禁**（`--incremental`）；`--baseline` 的对比展示面（`── 基线对比 ──`）
  不接（语义：对比展示本就是"当前 vs 工作树基线"的信息面，无裁决，无需防伪造）。
- ref 的**存在性/合法性由 git 保证**；本工具不校验 ref 是否"真的是 base"——那是 CI 接线
  的责任（GitHub 的 `github.base_ref` 由平台事件提供，PR 作者不可控；接线文档已写明）。

---

## §3 A1：watch 审计（P1-22）— 能力存在性漂移纠正

### 3.1 审计发现（R339 反清单教训的又一次实证）

R330 调研结论"watch 模式 = 无"为**能力存在性漂移**——全仓检索证实双实现早已存在：

| 实现 | 位置 | 形态 |
|---|---|---|
| `prompt-cli watch` 命令 | `dev_commands.py:181+` | 轮询（`--interval` 1.0s 下限）+ **md5 哈希比对**（比 mtime 强）+ `--debounce` 0.5s + lint/scan/evaluate 三命令 + 初始扫描 |
| `lint --watch` 标志 | `lint_commands.py:246/1155+` | 1s 轮询 mtime + 当前命令参数重跑 |
| 文档暴露 | README.md:195（表格）+ README.md:377（示例） | 已暴露（"零暴露"假设不成立） |

### 3.2 真实缺口（唯一）与根因修

**检测面 ≠ lint 面**：`watch` 目录模式用 `rglob("*.md")`（初始 + 循环两处），而实际 lint
执行走 `discover_templates`（`*.md` / `*.prompt` / `*.prompt.md` + 依赖树排除）→
**.prompt / .prompt.md 文件变更永不触发重 lint**。

根因修（2 行 + 单一真源）：两处 `rglob("*.md")` → `discover_templates(target)`。
检测面从此与 lint 面同源，扩展名集合/排除规则永不漂移。

### 3.3 非决策（留痕）

- **双实现并存不合并**：`lint --watch`（继承当前 lint 参数）与 `watch` 命令（通用重跑器）
  语义不同，合并=公开 CLI 面收缩，T6 发布窗口纪律不做；文档已分别暴露，无"幽灵能力"。
- 轮询 vs inotify/watchdog：引入 watchdog 依赖 = 新依赖面（跨平台事件语义差异是著名坑），
  1s 轮询对静态门禁场景（<100ms/文件）成本可忽略——奥卡姆剃刀维持轮询。

---

## §4 X1：`--incremental --fail-on` PASS 被全量退出路径覆写（发现修复）

### 4.1 缺陷（潜在，从未被测试钉住）

```
lint --incremental --baseline X --fail-on high
  → fail_on 块：NEW 面 0 high → 打印 "✅ PASS"（不退出）
  → 函数末尾：sys.exit(determine_exit_code(has_findings=..., error_severity="high" if has_errors else None))
     has_errors = 全量 findings 任一 HIGH 及以上（存量！）→ True → exit 2
```

**症状**：brownfield 仓库（存量 high 常见——这正是增量门禁的存在理由）上，
`--incremental --fail-on` 的 PASS 永远被覆写为 exit 2 → 门禁永不通过 →
**违背 R224 自规格"存量放行, 老仓库接入不被存量打回"**。

**为何生产未爆**：真实 CI（quality-gate 作业）用 `--gate`——gate 块内 `sys.exit(verdict)`
提前退出，走不到末尾全量路径。`--fail-on`+`--incremental` 组合面只有本地/其他 CI 用户会踩。

### 4.2 修复（最小且零回归面）

- fail-on PASS 且 `incremental and not gate` → 置 `_incremental_failon_pass` 标志；
- 函数末尾全量退出**之前**：标志为真 → `sys.exit(0)`（报告落盘在标志检查之前，不回归）；
- **不触碰**：`--gate` 路径（gate 块自退出）、非增量路径、报告/SARIF 落盘、watch 面。

### 4.3 相邻未修（留痕，P3 候选下轮）

非增量 `--fail-on critical` 时若存量有 high（无 critical）→ 同样被末尾路径推成 exit 2
（fail-on 契约字面：该级别及以上=0 应 PASS）。同族矛盾，但改它动的是更常用的非增量面
契约，T6 窗口不做——登记 02 总板，下轮独立验证面处理。

---

## §4.4 R331 深度检查修复组（用户指令：全面深度多层次验证）

1. **损坏基线 JSON 边界处理**（ref 面 + 工作树面 + json_diff 面）：原为未捕获
   `JSONDecodeError` → traceback（RC=1）→ 现干净 exit 2 + 明确错误（与"基线文件不存在"
   契约同形态；工作树面=既有面同族，顺手修）。
2. **`compare_baseline` 列表序确定性**（楔子展示面）：new/fixed/unchanged 原为 set 差集
   迭代序（进程 hash-seed 随机，**实证同命令两跑展示序不同**）→ 改 key 字典序（元素/计数
   零变更，仅展示序规范化；裁决面本就用 set 不受影响）——"逐字节一致"承诺落到展示面。
3. **`--baseline` 参照系统一**（code_review P3）：worktree 读=CWD 相对、`git show`=仓库根
   相对，子目录+相对路径 → git 侧解析失败误报错（安全失败，CI 不受影响）→ `git_show_at_ref`
   原语内解析绝对 → `rev-parse --show-toplevel` 转仓库根相对（任意子目录可用，与 CLI 其余
   面接受 CWD 相对路径的语义一致）。

---

## §5 测试矩阵（26 测试 = 18 R331 + 8 R224 回归，全 hermetic 零网络）

| 类 | 测试 | 钉住什么 |
|---|---|---|
| 红绿证明对 | 篡改工作树基线+`--baseline-from main --gate` → exit 2 + 分歧告警；对照（无 ref）→ exit 0 | **防伪造生效的唯一变量证明**（与生产 CI 同 `--gate` 口径） |
| 无分歧 | 工作树=main → exit 2 且**无**分歧告警 | 告警面精确（不冤告警） |
| 错误契约 | 缺 `--incremental` / 坏 ref / 非 git 仓 / 子目录 CWD 相对路径 / 损坏基线 JSON（ref+工作树两面）→ exit 2 + 明确错误 ×6 | 5 年不变量⑤ + 参照系统一 |
| plumbing | `git_show_at_ref`（好/坏 ref/坏路径/非 git ×4）；`load_baseline_text ≡ load_baseline` | 原语契约 + 解析单一真源 |
| 楔子展示面 | `compare_baseline` new/fixed/unchanged 列表序 = key 字典序（实证跨进程 hash-seed 非确定 → sorted 规范化，元素/计数零变更） | 确定性楔子展示面字节一致 |
| X1 回归 | 存量 high 不覆写增量 PASS（exit 0 + "✅ PASS"）；NEW high 仍 exit 2 | 修复面双向钉死 |
| A1 回归（`slow`） | 真子进程 watch：.prompt 变更触发"检测到变更" | 检测面=lint面（CI `-k "not slow"` 排除，本地全量实跑；R325 墙钟断言陷阱同纪律） |

夹具自校验：B 必须实火 high/critical 且**至少一条 key 不在 A**（key=rule:desc，
compare_baseline 同键）——不猜具体规则，真源=活注册表；确定性楔子=重算即同 findings。

---

## §6 对抗性审查（鬼才产品经理视角）

1. **这解决真痛点吗？** 是——门禁自废是门禁产品的死刑级漏洞（用户信任=产品生命）；
   brownfield 接入死结直接卡 S2 北极星（存量仓库采用）。
2. **有没更便宜的解？** CODEOWNERS 保护基线文件=零代码但只防"直接改基线"，防不了
   "基线重存"的合规外观 commit；ref 面才是裁决面根治。已是最小根治。
3. **引入新脆弱面吗？** 依赖 git（仓库固有前提，P2-17 已确立）；ref 合法性责任明确划给
   CI 接线（文档写明）；无新第三方依赖。
4. **低价值打磨了吗？** 否——无 i18n 大面、无性能面、无新端；watch 从"新建 M"纠正为
   "审计+S"本身就是反重复造轮子的实证。
5. **5 年后还成立吗？** `git show ref:path` 是 git 核心语法（20 年稳定）；裁决面/检测面
   分离（P3-15 先例）与退出码契约（5 年不变量⑤）正交，可演进。

---

## §7 收口清单（→ #7）

- [ ] CHANGELOG R331 条 + 版本 67.34.117（3 处 + README 徽章）
- [ ] gen_rules_doc.py（非 --check）→ sync_readme_metrics → check_version_consistency
- [ ] 全量验证：pytest 全量（无 cov）+ ruff check/format 全仓 + mypy 全量 + release_gate --skip 1,2
- [ ] 02 板行回写：P3-20 ✅ R331；P1-22 纠正（能力存在审计 + 检测面根因修）；新增 X1 登记
- [ ] 00 交接文档 R331 块
- [ ] commit/push（验证后）
