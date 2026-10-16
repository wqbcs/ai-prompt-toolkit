# L3 约束（团队层硬性约定 — 从代码与 CHANGELOG 实际惯例提取）

> 更新: R310 (2026-10-16) | 首版: R213
> 这些约定违反即 CI 红或基线回退, 新改动必须遵守

## 规则工程纪律

1. **60 干净样本 0 命中**: 任何新规则/规则修改, 从第一天断言 60 干净样本 0 命中
   （tests/test_rXXX_false_positive_fix.py 模式）
2. **正样本保留**: 收窄触发门时必须断言真场景仍命中（检测能力未削弱）+ 逐样本根因复核
3. **规则编号顺延**: P001-P268 只增不跳; 双基线达标前冻结规则数（R212 非目标, R213 解除视基线而定）
4. **触发门收窄优先序**: 修规则 > 降级 > 移出默认集（R206-R212 处置原则）
5. **否定前缀剥离**: DECL/放行类 pattern 必须防否定形式（"无转义"≠"有转义"）—
   `_strip_negated_data` / `strip_negated_decl` 现成组件复用
6. **探针先行 (T1)**: 新规则必须 TP+TN 各 ≥2 条独立真实案例进 `data/golden_attacks.json`
   才可合入; 无探针支撑的规则禁止合入; 新规则必须带 OWASP 映射
7. **golden 单一真源**: `golden_attacks.json` 变更必须走探针先行+双基线不回归
   （redline-guard 钩子直接拦截编辑, exit 2）

## 棘轮纪律（只收紧不放松）

| 棘轮 | 当前值 | 挂载 |
|---|---|---|
| mypy 基线 | 0 / 0（禁抬; 验证前先 `rm -rf .mypy_cache` 排除陈旧缓存假绿） | release_gate + CI |
| mypy strict 注册表 | 286/286 (100%, R300 收口) | check_mypy_ratchet S1-S4; 注册表变更唯一路径 `--update-strict`（红线钩子拦截直改） |
| 误报率 | 阈值 0.01（实际 0.82%, 60 样本） | check_false_positives --fail-above 0.01 |
| 漏检率 | 阈值 0.05（实际 0.00%, 379/379 单元） | check_miss_rate --fail-above 0.05 |
| coverage | fail_under 75（R216 实测 75.67% 锁定, 不刷数） | pyproject |
| 版本一致性 | pyproject / __init__ / README 徽章 / CHANGELOG 最新条目 四处一致 | check_version_consistency（门禁第 17 步, fail-fast） |
| 环境一致性 | ruff 0.16.10 / mypy 2.1.0 / redoctor 0.1.5 钉版（漂移硬红, 不要改钉版） | check_env_parity |
| 板 vs 代码 | 5 机器检查（sha 可解析/⬜行 CHANGELOG 声称/✅行规则引用 vs 活注册表/⬜行自相矛盾） | check_board_status（R243 脚本化, R294 check 4/5; /board 命令加声称抽查层） |
| 分层 | L1 rules→io/adapters 禁入表 + L2 kernel 纯度 | check_layering（R254） |
| 性能楔子 | <100ms/文件 | check_lint_performance |

## 收口纪律

- 收口一律 `python scripts/release_gate.py`（29 步; 本地 `--skip 1,2` + 全量 pytest 单独实跑
  + 覆盖率棘轮交 CI 同形态判定）; **禁止管道吞退出码**（`| tail` 退出码来自 tail, 曾致假绿）
- **升版门禁序**: 版本三处+README 徽章 → **CHANGELOG 段（check_version_consistency 要求
  CHANGELOG 最新条目=当前版本, 必须先行于门禁——R308 第 17 步首红实证）** → gen_rules_doc.py
  （非 --check）→ sync_readme_metrics → 门禁
- 升版后必跑 gen_rules_doc.py（非 --check）— 连续两轮漏跑致 CI Docs drift 红的教训
- 基线文件重存: 必须独立 commit + 理由; 不要为重存基线让 gate 通过
- 收口回写板状态列必须带可验证引用（commit sha + 验证命令）
- 本地 venv 含未声明依赖时本地 pytest 全绿 ≠ CI 绿 — 推 CI 前核对 src 运行时 import
  全部在 pyproject 声明（或 clean venv 验证）

## 依赖与复用纪律

- **零新第三方依赖**: core 运行时依赖锁定 7 个（R306 实证剔除 scipy/numpy 零 import 死重）;
  新增需论证
- **不重复造轮子**: 实现功能前先查现有模块/开源参考（`_strip_negated_data`、RAG 语境门同构等先例）
- **JSON 只增不改**: 新字段追加, 旧消费者不破（R212-5 health 先例）
- **口径唯一事实源**: 展示数字（probes/规则数/版本号/测试数/auto-fixable 数）必须读同一
  注册表, 禁止多处硬编码（R212-2/R212-7 根治漂移源; R310 再抓 "71 AUTO_FIXABLE" 注释漂移）
- **门禁命令禁止引入 LLM 调用**（确定性楔子: 每次裁决逐字节一致 + 零 LLM 成本 + <100ms/文件 + 离线可跑）

## 产品定位约束

10. **零 LLM 调用是核心定位**: lint/scan/probe 保持纯静态; 需 LLM 的能力（optimize/ab-test）隔离在可选依赖
11. **中文优先**: 错误信息双语, 中文 Lint 规则（全角标点为正常写作, ruff RUF001-003 ignore; 新代码标识符用英文）
12. **i18n 仅 zh-CN/en-US/ja-JP（+zh-Hant 小面）**: 不做 9 语言 / i18n 本地化大面（显式禁止）
13. **静态探针**: 不做动态红队（需 LLM, 与定位冲突）; 输出侧攻击面=层外（组合运行时工具, 不越层）
14. **不为全端而全端**: 端按 ICP 信号逐个上（npm 优先=P1-04 既有登记）; 反清单权威位置=
    02 任务总板 §不做什么（执行 agent 禁止自主启动反清单项）

## 工程约定

15. Python 3.10+, ruff check + **ruff format --check**（CI 有 format 门禁; 历轮只跑 check 致
    格式漂移积累的教训）; line-length 120, double quote, ignore 清单有逐条理由（pyproject 注释）
16. 提交: Conventional Commits（`type(scope): 摘要`）+ Co-Authored-By trailer; 每批次全量回归
    + ruff（check+format）+ mypy 棘轮（**收口后代码变更必须复跑 mypy** — R215 跳跑致缺陷
    拖一轮才抓出）+ 双基线后才 commit
    （R213 版 "R{轮次}-{批次}/v{版本}" 消息格式已被 Conventional Commits 取代, R286+ 实测口径）
17. 基线文档: 口径变更必须标注（如 32/56/60 样本不可直接对比）
18. 探针扩样: 标注 expected（可空=仅观察）; "已知否定盲区" note 前缀单列不藏
19. `.atomcode/` 配置面 local-only（.gitignore）: AtomCode 自动化（skill/hook/MCP/命令）不入库
20. 5 年不变量: 架构生命周期 ≥5 年的决策不随轮次翻转（确定性楔子/分层/零 LLM 内核）
