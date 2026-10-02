# Changelog

本文件记录 AI 提示词体系的所有重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [v67.34.14] - 2026-10-02

### Added (R224-P0: 可信度自证 + 采用入口)

- **`prompt-cli baseline` 一条命令自证双基线**: 漏检/误报度量逻辑与样本
  (113 golden探针+60干净prompt) 移入包内 `ai_prompt_toolkit.baselines`
  作单一真源, 随 wheel 分发 — pip 用户任何机器一条命令复现 0.00%/0.91%,
  无需克隆仓库。`--fail-above-miss/--fail-above-fp` 供 CI 棘轮
- **scripts/check_false_positives.py / check_miss_rate.py 退化为薄封装** —
  与 CLI 复用同一实现, 消除双份度量逻辑漂移
- **README 首屏可信度叙事升级**: 楔子定位行 + 双基线徽章前置 +
  `prompt-cli baseline` 自证指引 + 10行 copy-paste CI 片段 +
  LLM系竞品结构性对比表(promptfoo repeat采样/garak Fisher 54%误红/
  API key/成本模型); 功能计数降级进 details 折叠
- **docs/adoption.md 采用指南**: Day0(report-only+SARIF入Code Scanning)/
  Day1(--gate分阶段收紧)/waiver纪律/双基线棘轮/air-gap安装/常见问答
- **docs/R224_改进方案.md**: 定位反问+竞品调研(promptfoo/garak/
  prompt-defense-audit/taudit)+P0/P1/P2清单+PM自审

### Refactor

- `tests/fixtures/clean_prompts/` 与 `golden_attacks.json` 移入
  `src/ai_prompt_toolkit/data/`(包内单一真源), 原位置留符号链接 —
  24+ 既有测试零改动, wheel 自带基线样本
- baselines.py `_load_golden_probes` 加 cast 消除 mypy no-any-return

## [v67.34.13] - 2026-10-02

### Fixed (R223续: click 8.5.0类型漂移 — mypy棘轮本地0/CI 4)

- **根因**: `click>=8.1` 无上界 — CI装8.5.0, `get_text_stream` 返回类型
  标注改为 object → mypy棘轮(基线0)在CI报4个 `"object" not callable`
  (ruff钉版之后的同款漂移病灶, 本地8.3.3无感知)
- **修复**: `eval_commands.py` 两处stdin读取改用 `sys.stdin`
  (typeshed稳定标注TextIO, 运行时等价) — 彻底消除对click流API的
  类型依赖, 不再靠cast对抗上游标注
- click 8.5.0 环境全链复验: mypy棘轮持平0 / ruff全绿 / 5979 passed
  (运行时行为无回归)
- 本地环境已同步升级 click 8.5.0 — 与CI同版本验证

## [v67.34.12] - 2026-10-02

### Fixed (R223续: jinja2未声明依赖 — 第5连红, 同源病灶收口)

- **根因**: `eval_matrix.py` 运行时 import jinja2 却**未在任何依赖声明** —
  本地venv恰好装有 → 完整渲染器(含feedback) → 本地绿; CI无jinja2 →
  `except ImportError` 静默降级simple模板(feedback丢失) → test_r28断言挂
- **修复两手**:
  1. `jinja2>=3.0` 进core依赖 — `eval matrix` HTML是核心CLI功能,
     pip用户不该静默拿到降级报告(体验短板)
  2. `_render_simple_html` 降级渲染器补feedback显示 —
     **降级不得静默丢数据**; 测试从此环境无关(有/无jinja2都过)
- **五连红同源反思**: YAML语法/fastapi/ruff漂移/硬编码路径/jinja2 —
  都是"本地环境含CI没有的东西, 本地全绿≠CI绿"。教训固化:
  推CI前核对src运行时import全部在pyproject声明, 或clean venv验证
- 本地35 passed + ruff + CI降级路径模拟验证(feedback保留) ✓

## [v67.34.11] - 2026-10-02

### Fixed (R223续: 测试硬编码绝对路径 — 本地绿/CI(Linux)红)

- `tests/test_r117.py` 硬编码 `Path("D:/xinjian/project/prompt")` —
  Linux runner 上不存在, 7 项检查 0 通过 → `assert 0 >= 5` 挂
  (本地 Windows 恰好路径存在 → 本地绿 CI 红的经典环境依赖缺陷)
- 改为 `Path(__file__).resolve().parent.parent` 相对解析仓库根 —
  跨平台同一行为, 不再依赖本机目录布局
- 本地 6 passed + ruff 复验; 推送后以 GitHub Actions 3 版本矩阵为准

## [v67.34.10] - 2026-10-02

### Fixed (R223续: 门禁可复现性 — lint工具版本钉死, 消除CI/本地漂移)

- **根因**: CI 裸 `pip install ruff mypy` 装最新版 — 0.15.14→0.16.10
  间 format 行为变更, `templates/mcp-server-dev.md` 内嵌 Python 块被重排,
  CI `Ruff format check` 红而本地绿 → **门禁结果不可复现**
- **修复(顶配做法)**: ruff==0.16.10 / mypy==2.1.0 钉入 [dev] 单一源,
  CI 不再裸装 — 本地与 CI 同一版本, 门禁可复现; 升级 lint 工具时
  一次性本地+CI同步升并复跑全量
- 按 0.16.10 format 重排 `templates/mcp-server-dev.md`(本地0.15.14也通过,
  双版本格式一致)
- 本地 ruff 0.16.10 复验: check+format 全绿; 推送后以 GitHub Actions
  真实运行为准(此前 3 连红: YAML解析/RUF036/format漂移, 逐一实证修复)

## [v67.34.9] - 2026-10-02

### Fixed (R223续: CI ruff版本漂移 — 本地0.15.14通过/CI最新版拦截)

- CI `pip install ruff` 装最新版, 新 RUF036 拦截
  `rules.py:826` `"Finding | None | list[Finding]"`(None不在联合类型末尾)
  → 注解顺序改为 `"Finding | list[Finding] | None"`(PEP 8标准顺序,
  零运行时影响, 契约不变)
- 教训固化: 本地 ruff 版本落后 CI 最新版时门禁会漂移 — 后续升版 ruff
  时先跑 `ruff check` 全量再提交
- 本地复验: ruff check+format / mypy棘轮 / 版本67.34.9一致 全绿,
  推送触发 CI 复跑验证

## [v67.34.8] - 2026-10-02

### Fixed (R223: 自家CI修复 — 产品卖CI门禁, 自家CI灯必须是真话)

**背景**: 项目首次推送 GitHub 后 Actions 真实运行, 11个 workflow 中 4 个失败。
根因(逐一从 Actions 日志定位, 非猜测):

1. **主门禁 prompt-ci.yml 从未真正运行过(最高危)**: step 名
   `False-positive ratchet (dual baseline: noise side)` 未加引号 —
   YAML 中 `:` 后接空格构成非法 mapping → 整个文件解析失败 → 0 jobs。
   双基线棘轮/SARIF/多版本矩阵 3.10-3.12 等所有"CI 门禁"此前从未在 GitHub
   上真实执行。修复: step 名加引号
2. **fastapi 依赖缺口**: `tests/test_market_api.py` 顶层 import fastapi,
   但 [dev] extras 未含(只在 [full]) → `pip install -e ".[dev]"` 后
   pytest 收集阶段 `ModuleNotFoundError: No module named 'fastapi'`
   (quality-gate run 日志实证)。修复: fastapi+httpx 移入 [dev] 单一源
3. **6 个冗余/损坏 workflow 删除**:
   - `prompt-lint-ci.yml`: `apt lint` 解析为**系统包管理器 apt**(exit 100),
     目标 `prompts/` 目录不存在
   - `prompt-quality.yml`/`prompt-quality-gate.yml`: 与 quality-gate.yml
     同名 "Prompt Quality Gate" x3 堆积; 前者引用坏 composite action
     (装 `ai-prompt-toolkit>=42.0.0` 未加引号致 shell 重定向 + 调用不存在的
     `promptkit` 二进制), 后者 `pip install -e ".[dev]"` 缺 fastapi 必挂
   - `quality-gate.yml`: 全量 pytest 未过滤 slow, 与主门禁矩阵重复
   - `prompt-lint.yml`/`prompt-pr-scan.yml`: 全部 `|| true` 空转 —
     门禁不拦截任何东西, 比没有更危险(假绿灯)
   - 孤儿 `.github/actions/prompt-lint/action.yml` 一并删除

**保留的真实门禁(职责不重叠)**:
- `prompt-ci.yml`(主): 多版本矩阵 + ruff + mypy棘轮 + 双基线 + 模板自lint
- `prompt-pr-gate.yml`: PR增量 prompt 文件门禁(R207-5, 真拦截)
- `release.yml`: tag→PyPI trusted publishing
- `daily-scorecard.yml`/`owasp-llm-scan.yml`: 报告型(continue-on-error 语义明确)

**验证**: 5/5 剩余 workflow YAML 解析通过; 门禁链全绿(5979 passed /
ruff / mypy 0持平 / 双基线 / 版本+README一致); CI 真实状态由本次 push
后 GitHub Actions 运行确认(此前从未绿过 — 诚实标注)

## [v67.34.7] - 2026-10-02

### Fixed (R222-C2: 发布就绪审计 — 打包缺口修复, pip 安装后功能必坏→可用)

**背景**: 项目此前从未真实构建/安装过 wheel — 打包配置与实际运行时资产
脱节, 3 处缺口全部会导致 pip 用户(非仓库内运行)功能损坏或干净环境构建失败:

1. **package-data 漏包运行时资产(最高危)**: `templates/*.md` 被
   `template_commands.py` 运行时从包内读取(`Path(__file__)/../templates`),
   `playground/static/index.html` 被 `playground/server.py` 加载 — 原
   package-data 只含 `data/*.json`, 实测 wheel 中 0 个模板文件 → pip 用户
   `prompt-cli template` 模板安装/playground 必坏。补齐
   `templates/*.md`(26个)+`playground/static/*.html`
2. **build-system 弃用依赖**: `requires = ["setuptools>=68.0", "wheel"]`
   中 `wheel` 已被 PyPA 弃用(镜像源下架)→ PEP 517 隔离构建环境装不上
   → 干净环境构建直接失败。移除 wheel(setuptools>=70.1 自带 bdist_wheel)
3. **PyPI 元数据不完整**: 无 authors/keywords/classifiers, license 用
   旧式 `{text = "MIT"}` → 升级为 PEP 639 表达式 `license = "MIT"`
   (新版 setuptools 禁止与 License classifier 并存, 已按 PEP 639 移除
   classifier 行)

**验证(构建产物即地面真相)**:
- `python -m build --sdist --wheel` 双产物构建成功(67.34.7)
- wheel 实测: templates.md 26 个/playground html 1 个/data json 入包
- sdist 实测: templates.md 26 个/LICENSE/pyproject 入包
- wheel 解压冒烟: 导入 67.34.7 / templates 26 / pricing json / playground
  html 全部就位, `prompt-cli lint` 可执行
- 注: 本机 pip 镜像源(tuna)未同步新版 setuptools, 隔离构建需用
  `--no-isolation`(本地环境限制, 非包缺陷 — CI 走官方 PyPI 无此问题)

**分发纪律**: 仓库名 = 分发名 = 品牌名, 三处一致
(`ai-prompt-toolkit` @ PyPI/GitHub/AtomGit)

- 门禁全绿: 5979 passed / ruff check+format / mypy 0 持平 / 版本+README
  一致 / 双基线 FP 0.91%+漏检 0.00% / gen_rules_doc --check 一致

## [v67.34.6] - 2026-10-02

### Added (R221: 双基线对称可信度 — FP侧对称扩样 + 签名feed设计)

**背景**: R220 扩了漏检侧(golden 80→113), 但 FP 0.91% 只由 58 条干净样本
撑起 — 与 R220 同型可信度弱点。本批对称补齐 + 落 C1 战略设计件。

- **FP 对称扩样 58→60**: 新增 clean59(代码评审)/clean60(文档翻译)真实场景
  干净样本, 逐条验证后纳入(防门禁翻车: 先测预算再写入)
- **扩样暴露 2 处真实 DECL 缺口 → 均修规则(非降级, 非移出)**:
  - P084: "每条问题不超过两行"行数控约未被格式约束 DECL 识别 →
    `_FORMAT_CONSTRAINT_PATTERN` +行数控约形态(中/英数字, 不超过/至多/
    最多/限/within + 行/字符/字/词/lines/words/characters)
  - P158: "不收集、不存储任何个人数据"= 放弃 PII 处理面本身(无 PII 可
    脱敏), 与 R213"放弃防护机制必不放行"方向不冲突 → `_MASKING_DECL`
    +显式不收集 PII 形态
  - 两规则正样本(裸"返回JSON" / "批量导出身份证+手机号")验证仍命中
    — 检测能力未削弱
- **README 双基线带分母(A2)**: "漏检 0.00%"不再裸写 — 补 113探针/108
  期望命中单元 + 误报 0.91%/60干净样本 分母, 安全评审第一问"分母是
  什么"有据可查
- **C1 确定性签名 feed 设计**(`docs/R221_C1签名feed设计.md`, 不实现):
  签名热更新 + ed25519 信任链(公钥内置/fail-closed/版本单调/命名空间
  隔离) + 复用现有 rule_loader_yaml 地基不造轮子; 实现前置=C2 发布落地
  (无消费者的 feed 是低价值打磨)
- 实测: FP **0.91%**(60样本) / 漏检 **0.00%**(113探针/108单元) /
  高误报 0 条 / 高漏检 0 条
- 回归: test_r206 +2(P158 不收集声明放行/正样本保留) + test_r211 +2
  (P084 行数控约放行/裸JSON仍检出) + 9 文件样本数断言 58→60
- 双审查: security-reviewer(0 CRITICAL/HIGH, M1 feed 重序列化陷阱已写
  入设计文档) + code-reviewer(0 BLOCK, 2 MINOR 观察项记录)
- 门禁全绿: ruff check+format(src+tests) / mypy 0 持平 / 版本+README 一致
  / 全量 pytest(含新增 4 条)

## [v67.34.5] - 2026-10-02

### Added (R220-A1: 战略反问转向 — golden 攻击集低覆盖扩样 80→113)

**背景(鬼才 PM 战略反问)**: R216→R219 连续四轮内部打磨(location 契约/行:列/
sentinel), 零用户零分发下属低价值打磨陷阱。R220 战略复盘后转向**核心价值
可信度** — README 旗舰指标"漏检 0.00%"原由 80 条自制探针撑起, 其中 33 条规则
覆盖 <2 探针, 安全评审视角下是循环数字。本批扩样直接放大核心价值。

- **golden_attacks.json +33 探针**(113 条/108 期望命中单元): 覆盖 33 条低覆盖
  规则(P001/P002/P004/P005/P022/P114/P132/P142/P143/P159/P163/P167/P170/
  P176/P178/P180/P182/P201/P206/P207/P216/P221/P222/P224/P239/P241/P244/
  P245/P250/P252-P255), 全 zh-Hans
- **防循环标注纪律**: 每条探针先过 lint_template 全管线(apply_waivers=False)
  验证**真实触发**目标规则才纳入(expected 来自规则语义映射, 不靠"命中"反推)
- **防门禁翻车**: 扩样只进漏检基线(golden 消费者仅 check_miss_rate.py),
  不进 FP 基线(clean_prompts/ 不变) → 误报面零变化
- 实测: 全局漏检率 **0.00%**(108/108, 高漏检 0 条) / FP 0.91% 不变
  (zh-Hans 0/81, en 0/18, ja 0/7, zh-Hant 0/2)
- 回归: `tests/test_r214_name_boundary.py` 探针数 80→113 / zh-Hans 51→84
- 方案文档: `docs/R220_改进方案.md`(战略四问+竞品四段格局+可复用组件+否决清单)

### Fixed (R220-B1/B2: explain 接线 waiver 提示 + 硬编码哨兵清除)

- **B1(痛点: 误报是 adoption killer)**: `format_explanation` 每个 finding 加
  per-finding 静默提示 `promptlint:ignore PNNN (文件级豁免)` — 用户看到误报
  能判断+静默单条规则, 而非禁用整个工具。提示诚实标注"文件级"(waivers.py
  当前作用域, 行级地基见 L3-13, 不误导)
- **B2(用户"避免硬编码")**: `explain.py` location 展示从硬编码
  `not in ("0", "1")` 哨兵改为走 R218 契约 `parse_location` 单一事实源 —
  文件级("")不猜行, 行级(L:<line>:C:<col>)干净显示, 旧哨兵值按契约兼容口径
  解析(与 LSP 历史口径一致)
- 回归: `tests/test_r220_explain_waiver.py`(7 条) — 文件级不猜行/waiver 提示
  带正确 rule_id 不串号/行级走契约

## [v67.34.4] - 2026-10-01

### Added (R219-B1b: 安全集 checker 真实行:列 — 复用 R218 loc_from_match 契约)

**背景**: R218 只给 P260/P261 落真实行:列(注入/编码最高价值面), 其余 259 条
文件级。R219 ast 全量 261 checker 逐个验证后, 把**可安全加行:列的子集**落地
— 零新基建(复用 R218 `loc_from_match` 单一契约)。

**诚实边界(错误行号比没有更糟)**: 只有 match 对**原始 text** 产生的 checker
才能 `loc_from_match(text, m)`。逐个源码验证后:
- **22 站点安全加行:列**(match 对 text, 锚点语义正确):
  - P030 模型依赖 / P178 影子指令×3 / P186-P191 鸿蒙 / P193-P195 Agent
  - P196-P198 LLM推理 / P200 流式 / P204 公平 / P210 嵌入 / P239 DoS
  - P242 透明度 / P258 伪造系统标签
- **诚实留文件级(不猜行, 防错误行号)**:
  - p201/p202/p205: match 对**派生串** `_strip_negated_data(text)`, 偏移错位
  - p256: match 相对 **fence-stripped body**, 非 text
  - p006/p021/p022/p027/p051/p053/p054/p081: finditer 聚合, match 循环结束
    即丢 span, 单 Finding 报"N处"无锚点
  - p183/p192/p199/p203: 复合/bool 触发, 无单一锚点

- **顺带修复 B1a 漏网**: p256 两处**多行** `"1","1"` sentinel(B1a 单行
  search_replace 未命中多行形式) → 修为文件级 `""`
- **行:列覆盖率(诚实声明)**: 261 checker 中 **22 站点**有真实行:列(P260/
  P261 4 子pattern + 本批 22), 其余文件级(诚实不猜行) — 剩余提升需逐 checker
  让 match 存活到 Finding 站点(重构检测逻辑, 非加个 location=, 高风险)
- **回归 tests/test_r219_b1b_linecol.py(13 条)**: 逐 checker 断言触发点行
  == 报告行(不指错行) + 派生串 checker 必须留文件级(不产假行号) + 防假行1
  锚点复发守护
- **行号正交于检测** → 双基线不变: FP 0.91% / 漏检 0.00%
- 门禁全绿: 5968 passed / ruff check+format / mypy 0 持平 / 版本+README 一致

## [v67.34.3] - 2026-10-01

### Fixed (R219-B1a: 96 处垃圾 sentinel Finding 调用 — 去除用户可见"修复:1")

**背景(R219 ast 全量 261 checker 审计)**: 96 处 `Finding()` 调用(跨 81 个
checker, 含 custom_rules 4 处)用 5 位置参数
`Finding(rule_id, severity, description, "1", "1")`, 按签名
`(rule_id, severity, description, location, remediation, details)`:
- `location="1"` = 假行1锚点(CLI 对文件级发现显示 "L1", LSP 标注到第1行)
- `remediation="1"` = **用户可见垃圾文案**(VS Code 扩展/JSON/CLI 全显示"修复: 1")
- 这正是 R218 CLI 那段 `!= "1" and != "0"` 隐藏逻辑的**症状根源**(当时只隐藏了症状)

**修复**: 96 处移除尾部 `, "1", "1"` 位置参数 → `location`/`remediation`
落默认值(`""` 文件级诚实 / 无"修复:1"垃圾)。纯检测无关(location/remediation
是报告字段, 不参与检测逻辑)→ 双基线不变。

- 97 处 `, "1", "1"`(ast 审计 96 单行 + 1 多行, 全部核验为 5 参尾部, 无一
  带第6参 details)跨 17 文件(含 custom_rules.py 4 处)
- 修复后 P176 实测: loc='' rem=''(垃圾已除)
- 双基线不变: FP 0.91% / 漏检 0.00%(检测逻辑未动)
- 门禁全绿: 5955 passed / ruff check+format / mypy 0 持平 / 版本+README 一致

### Note

- R219-B1b(23 single + 16 finditer 安全集 checker 加真实行:列)独立批次

## [v67.34.2] - 2026-10-01

### Added (R218: location 契约 — 三端单一事实源, "Prompt的ESLint"定位补位)

**背景(对抗性自审发现)**: 261 规则 301 处 Finding() 此前**全部无 location**
(0/301 实测) — 定位是"Prompt 的 ESLint"但无法告诉用户问题在哪; 且三端各自
硬编码解析(LSP "line:col" / CLI 隐藏 "1"/"0" / 编辑器 parseInt + description
30字符子串**猜行**) — 契约缺失 + 硬编码互异(用户指令"避免硬编码"直接命中)。

- **types.py location 契约(单一事实源)**: `build_location(line,col)` /
  `parse_location()` / `loc_from_match(text, m)` — 语义: `""`=文件级(消费端
  不得猜行) / `"L:<line>"` / `"L:<line>:C:<col>"`(均 1-based, VS Code/SARIF
  同基准); 兼容旧 "line:col" 纯数字形式(LSP 历史口径)
- **三端去硬编码统一走契约**: LSP `_lint_to_diagnostics`(原 split(":") 手写
  解析 → parse_location; 文件级 0 宽不猜行, 原恒覆盖首行 20 字符硬编码已除) /
  CLI(原 `!= "1" and != "0"` 隐藏逻辑 → parse_location, 有行才显示) /
  SARIF(原读 `f.get("line")` 从未走 location 字段 → parse_location, region
  带 startLine+startColumn, 文件级不写 region=GitHub Code Scanning 文件级标注)
- **P260/P261 参考实现**: 注入/编码最高价值面 4 类子pattern(zw交错/BiDi/
  base64/转义)经 `loc_from_match` 落真实 line:col; 其余 259 条留文件级
  (诚实: 批量改 301 处 Finding() 构造=高风险无样本回归面, 不预支 — 行:列
  覆盖率提升为后续批次, L3-13 地基已就绪)
- **VS Code 扩展 0.5.0→0.6.0**: extension.ts 4 处 `findLineNumber` 猜行调用
  (runLint/runScan/PII/buildRelatedInfo)统一切 `parseLocation`/`rangeFromLocation`
  契约辅助; 删除 parseInt(location)+description 子串搜索 hack; 顺带修复 11 处
  **存量编译错误**(readonly push×2 / QuickPickItem 缺类型标注 / spawn encoding
  类型冲突 / 隐式 any×2 / CodeActionsProvider 拼写错误) — 扩展此前 `tsc`
  构建失败(0 可构建), 现 exit 0 首次通过严格编译(体验短板端消除)
- **测试 tests/test_r218_location_contract.py(19 条)**: 契约单测(构造/解析/
  Match→location 1-based 基准/空/非法/兼容旧形) + P261/P260 四类子pattern
  真实行号 + 三端一致(LSP range/SARIF region 同基准) + 文件级语义(LSP 0 宽
  不猜行 + SARIF 无 region) + 防分叉守护(三端源码引用同一契约函数 + 编辑器
  无旧 hack 残留) + finding 数量不变(契约不改门禁语义)

### Changed

- **L3-13 waiver 行级作用域**: 状态从"无行级地基"升级为"**地基已就绪**" —
  定位契约+参考实现到位, 剩余=waiver 解析器行号作用域 + 规则行:列覆盖率
  (不预支, 重评条件=覆盖率提升批次后)
- **R217 方向反思闭环**: R217 方案指向 R218=L3-6 A/B 显著性检验 — 实施前
  自审发现 golden 75/75 **零方差**, 对自家通过套件做显著性检验=元统计非
  产品价值(低价值打磨陷阱) → R218 改做 location 契约(定位反问四问全过:
  ESLint 定义特性/CI 可度量/硬编码/唯一短板端); L3-6 维持开放(前置=扩样)

## [v67.34.1] - 2026-10-01

### Added (R217 批次: 改进方案与开源调研 — 2 落地 + 3 实证否决)

- **docs/R217-改进方案与开源调研.md**: 定位反问(定位/核心价值/方向问题/
  低价值陷阱/多端栈核对) + 5 新信源调研(PromptGuard v3.7/llmguard-cli/
  promptdiff/tianpan co/garak 2026) + 内部重复覆盖核验表(防内部重复造轮子)
- **README 叙事节 "为什么是确定性静态检测(CI 门禁场景)":** "lint 是 eval
  与生产之间的层" 需求侧论证 + 混合架构(regex+LLM 二审)与 CI 门禁的结构性
  冲突表 + 对手数字适用边界诚实声明(hybrid F1 0.94=一次性离线快照; 双基线
  0.00%=静态可检测面内棘轮持续保证; 语义层攻击=机制上限, 应组合运行时工具
  — 适用域划分而非互相替代)
- **语言面覆盖矩阵**: 补 P261 行 + 3 项缺口行(L3-21a-e) + "攻击家族×探针
  覆盖"交叉表(16 家族, 8 可检验, 3 不足 — L3-6 显著性检验前置条件显式化,
  扩样方向=补 operations/inference/governance 各+1 而非 injection/encoding
  加量)
- **L3**: #22 输出侧攻击面定位边界(莫尔斯/倒序/emoji 输出编码=输出 DLP,
  定位外不做) / #23 P262 dead-var(高价值半边实测已被 P256 check2 覆盖,
  零样本支撑降级 P2) / #24 尾部注入位置感知(强标记载荷实测已被位置无关
  P063/P113/P163/P178 覆盖, 弱标记面=语义层机制上限, 降级观察)

### Changed

- **R217 批次数据裁决记录(先实证再落地纪律第二轮执行)**: 原列 5 项 P1 →
  2 项落地(F1/F3 纯文档高 ROI) + 3 项落地前被实证否决(F2 已被 P256 check2
  覆盖 / F4 输出侧越层 / F5 已被位置无关注入规则覆盖) — 避免 3 条噪音规则
  进入 261 规则基线; F9(显著性检验)排 R218 前置扩样(3 探针)之后

## [v67.34.0] - 2026-10-01

### Added (R217: P261 不可见字符交错/BiDi反转注入面 — L3-20 裁决落地)

- **P261 不可见字符交错/BiDi反转注入面 (HIGH)**: 3 子 pattern 全信源
  ATR-2026-00276 FP 验证后实证值（非自调）— ① 零宽 {U+200B, U+200C, U+2060}
  3+ 交错（间隔≤20 非零宽字符, 单字符触发=65K 语料 15 误报, 其 #323 收紧;
  ZWJ U+200D/BOM U+FEFF 排除=大规模误报移除）② BiDi override/isolate
  {U+202C-2E, U+2066-69} 单字符即报（Trojan Source 显示反转信号, 单个
  U+202E 即可反转整段显示文本）③ 转义形态 `\u200b`/`\u202c-e`/`\u2060-9`
  字面文本（IGNORECASE 覆盖大写 — P260 子4 同型教训）
- **辖区切分**: P260 保持 5+ 连续（连续堆叠面）; P261 覆盖 3+ 交错（含
  1-2 字符间隔及 3-4 连续 — R215-review HIGH "1-4 zw 嵌入双漏"面的 3+ 部分
  由此覆盖）; 5+ 连续两规则交叉命中=双报常态（pattern 双检测不加 skip 代码,
  P258 的"跳过不交叉"是关键词查表双逻辑防冲突, 不迁移）
- **双基线实证**: FP 0.91% 持平零新增（261 checker, 58 clean 0 命中, 0.01 棘轮）;
  漏检 0.00%（75/75 expected 单元, 80 探针, +5 TP 信源探针 +2 已知缺口观察）;
  全量套件 5935 全绿; mypy 0 错误持平
- **已知缺口登记（信源 evasion_tests 明示, 不扩）**: 组合变音符 U+0301/
  软连字 U+00AD 亦属不可见格式字符但不在信源字符集（FP 验证未覆盖该类,
  真实案例驱动重评）→ L3-21; U+200E/U+200F 方向标记不在字符集（不预支）
- **L3**: #20 销账（BiDi 控制字符子族 = P261 子2 落地, 信源 5TN 实证纯 RTL
  文字不触发 — 合法阿/希/波斯文字字符有固有方向性, 仅不可见 override 控制
  字符被报）; #21 新增（组合变音符/软连字已知缺口）
- **探针 73→80**（ATR-2026-00276 5TP + 2 已知缺口观察; 显著性 ≥80 门槛达成,
  但黄金集 A/B 显著性检验仍需扩样至更多真实攻击家族, 不降门槛 — L3-6 维持）

### Fixed

- 存量 format 漂移清零（ruff format ×5: rules.py/rules_p258.py/sync_readme_metrics.py/
  check_builtin_templates.py — CI format 门禁前置修复, 纯空白无语义变更）

## [v67.33.0] - 2026-10-01

### Added (R216: CJK-CJK 空格归一化 — L3-14 裁决落地)

- **作用域受限 CJK 空格归一化**（L3-14 销账）: 删除 CJK-CJK 间的 ASCII 空格
  （汉字/平假名/片假名）— W3C"原则上日文和中文文本不使用空格字符" → CJK 间
  空格=排版异常=规避信号; 严格边界: 谚文不碰（分词符）/ CJK↔拉丁数字边界不碰
  （相反惯例）/ U+3000 不碰（合法用途）/ 换行不碰（行号契约）/ {{...}}占位符
  内部不碰（渲染器契约 — 占位符内空格致渲染器静默填不上 = P256 真实缺陷面,
  B4 全量回归实证抓出契约冲突后补禁区）
- **集成层**: normalize_cjk_spaces + 构造处统一原地包装（functools.wraps 保
  __name__）— 260 检查器全调用点行为一致（lint 管线/FP门禁直调/漏检门禁/
  profiled版）; 行号不变量（仅删行内空格）, details.position 经 pos_map 回映
  原文索引（报告对原文, PromptSonar 归一化优先管线先例）
- **双基线实证**: FP 0.91% 持平零新增（0.01 棘轮）; 漏检 0.00%（70/70,
  atk70/atk71 翻转 +2 单元）; 全量套件 5907 全绿
- **coverage 棘轮锁定**: fail_under 68→75（实测 75.67%, 70+ 目标达成, 锁收益不刷数）
- **L3**: #14 销账; #20 新增（BiDi 控制字符子族, R217+ 与 P261 一并 — 信源
  ATR-2026-00276）

### Fixed

- P258 mypy 类型收窄（m.lastindex None 守卫 — R215-review 遗留, R216 mypy 棘轮
  补抓; R215 收口时 mypy 未复跑, 门禁纪律已补强）

## [v67.32.0] - 2026-10-01

### Added (R215: 新规则×3 — P258伪系统标签 / P259人格切换 / P260编码混淆)

- **P258 伪造系统级标签声明缺失 (HIGH)**: 五标签族 gate（全角【系统/システム】/
  半角[SYSTEM]系/Llama<<SYS>>/模型token<|system|>/双花括号{{SYSTEM}}）
  + 近邻±80字符示例声明放行（严于 P257 文件级声明 — 标签特权强度越高放行越严格,
  ESLint disable 注释近邻原则; 放行/不放行两侧均有单测）
- **P259 人格切换与前约束作废 (HIGH)**: 身份重赋值 AND 前约束作废共现（zh/en/ja
  三语面）— 数据裁决: 宽面"你是X"单独被否决（编写最高频合法句=误报陷阱）,
  复合面 3/3 探针命中 + 58clean + 15 内置模板 0 误报后落地
- **P260 编码/混淆注入面 (HIGH)**: 5 子 pattern 全机械（零宽5+/词内插入
  ATR-2026-00002 L2 阈值 / 8 个 b64 片段有限集 / 解码指令+b64 共现 / 同形异码 /
  hex-URL 编码）— 阈值与集合复用 ATR-2026-00001/00002 实证值非自调; 与
  P021/P177 差异化（质量面通用触发 vs 安全面精确触发, 存量通用检测对 5/7
  编码探针零覆盖）; 机制上限声明: 未知编码载荷必漏（语义层超静态lint范围）
- 探针 52→68（+16: 伪标签×4/人格×2/编码×7/ATR CJK×3, 全部 lang+provenance
  note）; 15 条翻转 expected, 5 条观察型（ATR CJK 新面无对应规则不预支）
- 规则数 257→260; 漏检 0.00%（67/67 单元, 棘轮 0.05）; 误报 0.91%
  （分母 257→260 自然稀释, 棘轮 0.01）; 内置模板 235 finding 不变
- B5 新规则模板第二次复用（一次落地 3 条, 模板可复用性验证通过）
- 同步: 语言面覆盖矩阵（人格/伪标签缺口销账+编码行新增）/ 双基线 R215 段 /
  L3（#12 name盲区销账, #15 pipeline误触 + #16 结构化数据注入 新增）/
  ATLAS 映射（P258→T0051.000, P259→T0054, P260→T0015, 编号联网复核）

- **R215-review（对抗审查修复, code-reviewer + security-reviewer）**: 代码审查
  8 MINOR（7 修 1 登记）; 安全审查 1 HIGH + 2 MEDIUM + 4 LOW — P258 两段式重写
  （HIGH 零宽交叉盲区根治: 括号捕获+≤4 零宽剥离+关键词集查表, 5+ 归 P260 辖区）;
  IGNORECASE 召回缺口×3 修复（P260 子4 大写同形异码 / P259 ZH/JA 小写 ai）;
  token 族补 hidden; 观察探针 +5（68→73: zw/空格×2/词法刚性/单字符同形异码,
  MEDIUM 缺口"探针先行+登记, 放宽留 R216 数据裁决"）; L3 #14 门槛触发 +
  #17-19 登记; 详见 docs/R215-对抗性审查报告.md

## [v67.31.0] - 2026-10-01

### Added (R214: 多语言语言面扩展 — ja/zh-Hant/CJK空格插入)

- 探针 schema 加 BCP-47 `lang` 标签（golden 52 条全标注）, 分语言漏检率
  统计机械派生（借鉴 garak-multilingual per-payload provenance 纪律）
- 多语言探针 +10: ja×6（4 expected + 2 观察型）/ zh-Hant×2 / CJK空格插入×2 —
  首次量化 ja 漏检 2/5=40%、zh-Hant 2/2=100%（先扩样暴露, 不藏盲区）
- 4 处 pattern 语言面扩展（参考 ATR-2026-00097 词源, 思路复用非代码, 逐词核对）:
  - P113: システムプロンプト/系統\s*提示（精确复合词, 裸词防误报不加）
  - RAG门 `_RAG_CTX_GATE`: 検索|ナレッジベース|知識\s*庫|檢\s*索
  - P006/P051: 日语 key 名 APIキー|パスワード|シークレット|トークン
- 新建 `docs/语言面覆盖矩阵.md`（语言×攻击类型覆盖声明, 借鉴 openclaw-defender
  形态; 缺口诚实登记: 人格切换/伪系统标签无对应规则 → R215 候选）

### Fixed

- P241/P243 `_PERSONAL_DATA_PATTERN` 裸 "name" 子串误配 namespace/rename/
  filename（代码常见词）— 加 `\bname\b` 词边界（与 R213-B5 race→trace 同类
  子串盲区, R213 审查发现）

### Changed

- 诊断修正: P007 无需修复（模板语法面语言无关, atk44 日语语境验证命中）
- CJK 空格插入: 有限空格容忍仅 P113/RAG门（不含换行 — R214审查收口; 否决全局
  空白归一化 — 影响 257
  规则全局行为, 风险入 L3-14 重评门槛）
- 双基线: 漏检 0.00%（全语言 52/52, 0.05棘轮）/ FP 0.93%→0.92%（name修复,
  0.01棘轮守住）
- 版本口径: 代码/CHANGELOG/pip/徽章 67.31.0 一致（check_version_consistency 门禁）

## [v67.30.0] - 2026-10-01

### Added (R213 批次B5: P257 新规则 — 双基线流程下首条新规则, 未来新规则样板)

- 新规则 P257 不可信内容边界声明缺失（MEDIUM, rag_security/rag_boundary）:
  RAG 检索语境门（复用 `_RAG_CTX_GATE` 单一事实源）+ 无边界声明（显式不可信标注/
  分隔符包裹/源约束语言三类放行面, clean32/38 基线形态不误伤）
- 开源参考（思路复用非代码）: promptfoo indirect-prompt-injection / AWS 加盐标签 /
  ContextHound INJ-002/003（"treat as data" 边界语言缺失 = 规则语义直接来源）
- ATLAS 对标: AML.T0051.001 Indirect Prompt Injection（docs/mitre-atlas-mapping.md）
- 全流程样板: clean 56→58（clean57中文/clean58英文, 均带边界声明; clean58=0-finding
  参考样本）+ golden +1 探针（atk41, expected=P257）+ 规则数 256→257
  （全部测试快照断言/README/doctor 动态口径同步）

### Fixed (R213-B5 发现的真实 bug)

- P241/P243 `_PERSONAL_DATA_PATTERN` 裸 `race` 子串误配 "trace"（观测日志词）—
  含 trace 的英文 prompt 恒触发个人数据门（与 R206 "fact⊂refactor" 同类子串盲区）;
  加 `\brace\b` 词边界

### Changed

- 双基线: FP 0.96%→0.93%（58样本×257 checker, 0.01棘轮守住）/
  漏检 0.00%（43/43, 0.05棘轮守住）
- 版本口径: 代码/CHANGELOG/pip/徽章 67.30.0 一致（check_version_consistency 门禁）

## [v67.29.0] - 2026-10-01

### Added (R213 批次B1: 否定盲区4条修复 — 最高危安全欠账清零)

- R213-P0-1 否定盲区根治: `rules.strip_negated_decl` 通用否定前缀剥离
  (R206 `_strip_negated_data` 通用化, 声明词串含连续DECL词 — "without any
  audit log" 整体剥离防残留)。P161/P222/P244/P245 的 DECL 匹配前先剥离 —
  "无转义/无需审计/不留任何记录/无合规评估"类明确放弃防护的攻击由全放行转命中
- 双基线: 漏检 9.52%→0.00% (4/42→0/42), 误报 0.96% 持平, 高漏检 4→0, 零检出 3→0
- 漏检棘轮 CI 0.10→0.05 落地(兑现 R212-B 文档承诺); 回归 test_r213_negation_blindspot.py(7)

### Added (R213 批次B2: 内联规则豁免 waiver — 6竞对5家有的体验对齐)

- 两种文件级豁免语法: `<!-- promptlint:ignore P107,P110 -->` / frontmatter
  `lint-ignore: [P119]`; 通配符/非法/未注册ID一律忽略(fail safe)
- 审计: LintResult.waived_rules/waived_finding_count 只报实际生效的豁免;
  CLI `--fail-on-waiver` 严格门禁(任何豁免生效即退出码2)
- 回归 test_r213_waiver.py(18)

### Added (R213 批次B3: MCP配置安全扫描 — 2026新攻击面占位)

- 新命令 `prompt-cli mcp-lint`: 配置级7项检查(MCP-101 http明文端点/MCP-102
  硬编码凭据/MCP-103 通配权限/MCP-104 免审批/MCP-105 宿主凭据透传/MCP-106
  未固定版本/MCP-107 链式路由, 语义借鉴PromptSonar MCP规则族) + tool
  description 走 security 族既有规则(实测收窄: 结构/RAG类对单行文本品类错配,
  误报纪律优先) + Risk Score 0-100四档(与quality_score同权重表机械派生, 无新公式)
- 红线: 不做MCP客户端/运行时执行路径/协议层; 通用${API_KEY}引用是官方推荐模式不告警
- fixture 10个(2安全+8高危) + 回归 test_r213_mcp_lint.py(23)

### Changed (R213 批次B1: 仓库卫生 — L3欠账清账)

- README 12处口径漂移修正; sync_readme_metrics 扩展正文口径检查(漂移即CI失败)
- doctor 规则数硬编码 55/30+ → 动态; 根目录84项历史文档 git mv 归档
  docs/archive/iterations/; L3_unknown 8项销账

验证: 全量 5788 passed (+51) / ruff 全绿 / mypy 棘轮 0 / 误报 0.96% / 漏检 0.00%
版本口径: 代码/CHANGELOG/pip/徽章 67.29.0 一致

## [v67.28.0] - 2026-09-29

### Added (R212 批次A: 第一触点修复 + 口径根治 + P256模板变量完整性)

- R212-1 CLI `-m` 入口真bug: `python -m ai_prompt_toolkit.cli_core` 原只显示
  3/68条命令(__main__守卫在命令簇import前执行+双模块实例)。守卫移到文件尾
  +__main__自别名 + 新增 `__main__.py` 使 `python -m ai_prompt_toolkit` 可用
- R212-2 版本/徽章口径根治: 代码/CHANGELOG/pip/徽章四处版本号统一到67.28.0;
  Tests徽章3665→5707(真实值); 新增 `scripts/check_version_consistency.py`
  (pre-commit钩子, 秒级校验, 根治R194/R207-6两次修过的复发漂移源)
- R212-4 新规则 P256 模板变量完整性(HIGH): 畸形占位符({{my-var}}/含空格,
  渲染器静默保留原样) + 显式声明段外的变量引用; 复用promptci/PromptOps的
  VariableGate思路(思路复用非代码复用); 与渲染引擎 _VAR_PATTERN 同口径
  (中文变量名合法, handlebars指令/|default回退/代码围栏放行); 56干净样本
  0命中从第一天断言。规则数 255→256, 23处计数快照断言同步更新,
  mcp_server prompt_lint描述改动态计算(又一硬编码口径消灭)
- 测试: +test_r212_cli_entry_fix.py(4), +test_r212_p256_template_vars.py(12)
- 文档: R212-改进方案与开源调研-v1.md(定位反问+promptlint/promptfoo/garak/
  promptci/PromptOps调研+8项清单)

验证: 全量 5707 passed / ruff 全绿 / mypy 棘轮 0 / 误报 1.35% / 版本口径一致

### Added (R212 批次B: 双基线对称可信度 — 漏检率基线首版 + probes口径统一)

- R212-3 漏检率基线(度量先行, 本轮不改任何规则): 聚合 `tests/fixtures/golden_attacks.json`
  (41条攻击探针/42个期望命中单元, 覆盖注入/越狱/编码/密钥/PII/结构/供应链/合规/
  多模态/RAG/Agent/治理12类) + `scripts/check_miss_rate.py` + `docs/规则漏检率基线.md`。
  首版全局漏检率 **9.52%** (阈值10%); 排除已知盲区后 **0/38 = 0%** — 对称证明
  R211五轮误报收窄没有削减真阳性(误报基线抓不到, 漏检基线能)
- 定位4条已知否定盲区(同一系统性根因): 规则用"文本含安全词(转义/审计/合规/记录)"
  判定"已有防护", 攻击prompt恰好用否定形式("无转义"/"无需审计"/"无合规评估"/
  "不留任何记录")声明**没有**防护 — P161/P222/P244/P245。R213以否定前缀剥离修复
  (复用R206 `_strip_negated_data` 现成组件)
- R212-7 probes口径统一: 展示口径统一到 `redteam.registry.get_global_probe_registry()`
  (116), `BaseProbe.__subclasses__()`(94)标注弃用口径, `probe_framework._PROBE_REGISTRY`
  (23, ProbeRunner兼容探针)归属在漏检基线文档中声明

验证: 漏检脚本可复现 / 棘轮 exit=0 / 全量回归不变

### Added (R212 批次C: 四维健康分 + 误报Top7清零 + lint成本预估)

- R212-5 四维健康分 (Security/Quality/Completeness/Cost, A–F 总评级): 全部机械派生
  自现有组件(scorecard扣分制 / lint_score / `_STRUCTURE_RULE_IDS` /
  token_analyzer×pricing), 零新启发式零手调权重; 总评级=四维最低档(短板决定,
  不平均); `score --format json` 只增 health 字段, 旧消费者不受影响。
  参考 promptlint 四维设计(思路复用, 非代码复用)
- R212-6 误报第六批处置 — **Top7高误报全部清零**: P107条件收窄+异常声明扩面 /
  P119能力承诺声明门(纯长度门误报根治) / P038-P040多模态输入收窄(移除裸文件/file,
  媒体词加词边界) / P110链式信号分强弱+工具语境门 / P036-P037 RAG语境门(同P035) /
  P109移除裸"文档"。全局误报率 **1.35%→0.96%**, 高误报(>10%)规则 **7→0**
- R212-8 lint成本预估 (INFO级, 不产生finding不进门禁): 复用 token_analyzer×pricing,
  1k/1M调用两档投影, 定价数据缺失优雅降级(仅显token数)
- 双基线CI棘轮: prompt-ci.yml 挂载 `check_false_positives.py --fail-above 0.01` +
  `check_miss_rate.py --fail-above 0.10` (只降不升, R213盲区修复后漏检阈值收紧0.05)
- 测试: +test_r212_false_positive_fix.py (22条: 9规则×56干净样本0命中断言 +
  正样本保留 + R211定位根因样本复核), +test_r212_health_score.py (8条: 等级边界/
  成本档位/短板决定/CLI JSON向后兼容)
- 文档: docs/规则误报率基线.md 增R212列 (0.96%, 高误报0/256)

验证: 全量 5737 passed / ruff 全绿 / mypy 棘轮 0 / 误报 0.96%(高误报0条) /
漏检 9.52%(4盲区已定位)

## [v67.27.0] - 2026-09-29

### Fixed (R211: 误报第五批 — Top9高误报规则处置, 全局 2.04%→1.35%)

- P151-P155 输入校验/输出转义/速率限制/审计/降级: `_API_CTX`泛词(服务/调用/
  请求)命中一切prompt → 共用`_has_prod_ctx`生产语境门, 声明类规则仅生产语境
  强制(沿用R207 P181先例), 本地草稿/文档类prompt不强制
- P161 模板注入防护: 裸`{{`/format/替换泛词打穿模板填充类prompt(数据提取/
  邮件生成) → 收窄到"模板+渲染/注入/引擎/变量"管道组合语义
- P183 环境隔离: 裸多环境词(测试/dev/prod)命中文档prompt → 收窄到≥2个
  不同"X环境"共现 或 environment+config 英文组合
- P244 审计日志: 裸SQL/代码词(查询/修改/DELETE)命中一切代码prompt →
  收窄到"变更类操作作用于敏感对象(用户/权限/凭据/密码/密钥/PII)"
- P182 依赖声明: 裸API泛词使"工具调用/请求体"即触发 → 拆为API实体×
  调用动作共现门(写API文档/审查API设计不触发)
- P084 输出格式: DECL覆盖不全(漏表头行/内联JSON/章节结构/字段定义/
  仅输出约束/英文结构词) → DECL六形态扩充, 裸"返回JSON格式"仍触发
- 测试: 新增 `tests/test_r211_false_positive_fix.py`(8规则×56干净样本0命中
  + P244/P182残留≤2/56 + 20条正负样本断言, 检测能力未削弱)
- mypy: check_p181 早退分支补 `list[Finding]` 显式注解, 棘轮基线保持0
- docs/规则误报率基线.md: 总览表加R211列, 剩余高误报Top17→Top7

验证: 全量 5684 passed / ruff 全绿 / mypy 棘轮 0 / 全局误报率 1.35%(阈值10%)

## [v67.26.0] - 2026-09-28

### Changed (R210: 样本库32→56扩样 — 基线可信度建设)

- 新增24个干净样本(clean33-clean56): 英文6(原仅1)/长文12/Agent工具调用2/
  模板语法{{var}}4/代码块4/多语言2(日语/中英互译), 补齐32样本的覆盖盲区
  (全中文/全短文本/无代码块/无模板)
- 扩样立即暴露6条32样本基线未覆盖的误报规则(P083/P118达41%), 验证
  "先让基线可信再处置误报"的顺序
- 测试适配: test_r206/r207/r208/r209零命中断言样本数32→56,
  check_false_positives.py样本数本就动态, 无硬编码残留
- docs/规则误报率基线.md: 总览表标注56样本口径不可与32样本直接对比

### Fixed (R210-1: 新暴露误报11条规则56样本下清零)

- P083 doctor建议(23/56→0): 纯长度门>200字对一切长prompt恒触发, 加
  生产语境门(仅deploy/production/上线/部署); 收窄排除"发布日期/发布
  检查单/生产库"文档词
- P118 知识截止声明(23/56→0): 加知识密集型门(历史/科学/医学/知识体系),
  "历史"排除交互记录语境(客户历史)
- P165 侧信道防护(12/56→0): LEAK收窄到"时间+推断/攻击/探测"时序组合
  +明确泄露/攻击词(裸"推断"是排障prompt常见词)
- P168 偏见检测(14/56→0): CTX收窄到受保护属性区分/群体评价, 英文词
  全部加词边界(age误配Agent/group误配GROUP BY/裸"简历"误配简历优化)
- P101 冗余表述(14/56→0): 字符级Jaccard改CJK单字+Latin分词(英文字符
  集天然重叠), 英文句号切句, 实义token<3片段排除, 代码围栏剥离(日志行
  共享字段Jaccard0.67/代码片段互比), 阈值保持0.5
- P002 输出格式(3/56→0): 英文pattern补`Output:`冒号式输出声明+模板
  填充等价输出声明
- 测试: 新增tests/test_r210_false_positive_fix.py(11规则×56干净样本
  0命中+17正负样本断言)

### Fixed (R210-2: 旧规则在新样本下的连锁误报清零)

- P003: 补日语约束章节"# 制約"(clean49暴露, 原仅中英)
- P010: "外部"须与服务/工具/依赖/接口组合("不引入外部系统状态假设"
  是约束声明非回退语境)
- P018: 加结构锁定放行(章节清单/段数/sections锁定输出时few-shot价值低,
  clean40 PRD/clean45邮件模板/clean53白皮书暴露)
- P020: select/choose须后接选型对象(framework/solution等), SQL"SELECT
  query"是查询动词非选型(clean34暴露)
- P055/P181: 生产pattern排除`生产(?!库)`, prod加前后词边界(非路径段
  /prod), 发布排除检查单/日期/前(clean43/51/56暴露)
- P105: `_FORMAT_COMPLETE`补带引号JSON键(内联JSON示例本身即字段说明,
  clean46暴露)
- P117: "历史"加负向后行(与P118同口径), DECL补"仅依据/仅基于"
  (grounding即事实性声明)
- P158: 凭据类词须与处理动作(导出/存储/写入)组合("账号密码登录"是
  需求描述非PII处理, clean54/56暴露)
- P167/P068/P170: "引用"须后接来源类词("引用测试输出行"是引用行为非
  事实性风险面), 去裸`data`(误配data analyst角色名), source加词边界
  (误配source_language), DECL补`cite...source/paragraph/number`
- P067: 去date(误配"发布日期"模板字段)/历史, DECL补"仅依据"
- P111: 去裸"原因"(说明/取舍/标注原因是正常指令), 改"分析+原因"组合,
  "排查"排除"排查记录"(交付物声明非推理过程)
- 验证: 全量5660 passed / ruff全绿

## [v67.25.0] - 2026-09-28

### Fixed (R209: 误报率Top6四批处置 — 全局2.16%→1.53%, 高误报规则21→15)

- P169毒性防护: CTX收窄到UGC/评论/社区/群聊真实用户内容输入面
  (原"用户/反馈/互动"泛词11/32误报)
- P242 AI透明度: 收窄到明确AI/模型语义, "生成"仅在紧邻AI/模型/LLM语境
  计入(原"生成"泛词使周报/SQL/工作流生成任务恒触发11/32)
- P222依赖审计: 收窄到第三方库/工具调用/插件具体代码集成面+否定约束
  语境排除("不引入第三方库"是约束声明非依赖引入, 9/32→0)
- P170引用溯源: CTX收窄到研究/文献/事实核查语义+词边界, DECL补
  "引用编号/来源编号/文档ID"(8/32→0)
- P156版本治理/P157灰度发布: CTX加词边界, version排除`key: value`
  形态, 部署排除"失败/问题/错误"排障语境, 发布需与版本/部署/生产共现,
  frontmatter剥离(6/32→0)
- 测试: 新增tests/test_r209_false_positive_fix.py(6规则×32干净样本
  0命中+20正负样本断言)
- docs/规则误报率基线.md: 累计8.38%→1.53%(↓6.85pp), 高误报41→15
- 验证: 全量5643 passed / ruff全绿

### Fixed (R207: 误报率Top8二批处置 — 全局6.03%→3.17%, 高误报规则35→27)

- P009审计: 加敏感操作门+否定语境排除("不生成DELETE"是约束声明非操作)
- P018 Few-shot: 加生成类任务门(写作/摘要/压缩; 通用翻译/指令执行不要求)
- P025长度: 加长文生成门(报告/白皮书/说明书/文章)
- P026回退: 加问答场景门+补RAG回退表达pattern("上下文未覆盖时明确说…")
- P055版本标记/P181版本声明: 加生产场景门(部署失败=排障/发布说明=文档/
  安全约束声明排除), P181移除非生产MEDIUM分支
- P105格式规范: 加结构化输出门(独立schema词误匹配数据库语境)
- P179格式劫持: 恒真has_output分支加不可信输入门(网页/外部文档/抓取)
- 测试: 新增tests/test_r207_false_positive_fix.py(8规则×32干净样本0命中
  +18正负样本断言), 6个既有测试文件正样本升级为强语义词
- docs/规则误报率基线.md: 更新R207处置记录, Top15刷新(P003 75%/P167 72%下轮)
- 验证: 全量5583 passed / ruff全绿

### Fixed (R207-1: completion命令apt残留真bug)

- cli_core.py completion命令docstring/prog_name/complete_var从apt复制粘贴
  未改(用户照抄会执行Debian apt) — 全部改为prompt-cli
- test_r71.py completion测试改走真实CLI入口, 防回归

### Added (R207-3: redteam/probe_framework注册表真统一)

- redteam/registry.py升级为统一注册入口: register_probe()/register_detector()
  装饰器(单点注册, 支持@decorator与@decorator()两种写法) + 统一查询视图
  (缓存, id稳定) + 命名冲突warning可见(encoding_bypass/refusal冲突暴露)
- redteam/probes/__init__.py: 自动发现完成后刷新统一视图缓存
- 向后兼容: 两套原_PROBE_REGISTRY导入路径不变, 仅新增统一层
- 测试: 4条(视图id稳定/双源覆盖/装饰器单点注册/直接装饰写法)

### Added (R207: 改进方案与开源调研文档)

- docs/R207-改进方案与开源调研-v1.md: 定位反问(误报率是lint工具生命线,
  广度膨胀=低价值陷阱) + promptfoo 2025/OWASP Agentic 2026调研 +
  第一批(可信度修复)/第二批(风险评分量化+PR门禁)/第三批(维护根治) +
  明确不做清单(9语言i18n/AOM/新规则P256+/DAG快照)

### Added (R207-4: 红队风险评分三因子量化 + OWASP Agentic Top 10 2026)

- 风险评分从"命中率x10"单一静态值升级为三因子: severity(命中探针严重度
  均值) x probability(暴露面: 用户输入/工具/多轮/Agent特征) x impact
  (命中类别影响面: 代码执行/泄露=1.0 > 注入/越狱=0.8), 0-10分同CVSS刻度
- probe_framework.py: ProbeRunReport新增risk_factors(severity/probability/
  impact/hit_rate分解), ProbeRunner._estimate_probability/_estimate_impact
- 新模块linter/owasp_agentic_mapping.py: OWASP Agentic Top 10 2026
  (ASI01-ASI10)与现有23探针+P141-P145 lint规则映射, Agent特征prompt
  报告输出Agentic评估章节(asi_findings+mitigation), 非Agent prompt不输出
- 测试: 6条(因子边界/分数区间/to_dict兼容/Agent特征判定/ASI映射)

### Added (R207-5: PR级提示词门禁)

- .github/PULL_REQUEST_TEMPLATE.md: 提示词变更必填项(门禁结果对比/影响
  范围/回滚方案)
- .github/workflows/prompt-pr-gate.yml: 仅PR含.prompt/.prompt.md变更时
  触发, 增量文件逐个lint+scan门禁(失败阻塞合并)+evaluate报告
- README CI/CD章节补"改Prompt要过什么门"说明
- 测试: 2条(模板存在性+workflow YAML语法含YAML1.1 "on"布尔键兼容)

### Added (R207-6: README指标动态化根治 — R194/R191口径漂移重复故障源)

- scripts/sync_readme_metrics.py: 从真实加载计算规则/维度/MCP工具数
  (直接导入dispatch表为ground truth, 正则解析会随工具名前缀扩展漂移),
  与README硬编码值比对, 漂移时exit=1+diff报告
- daily-scorecard.yml: 每日跑指标核对门禁
- prompt_doctor.py: 新增DOC-01检查项(README指标核对), doctor报告层面
  暴露漂移, 支持readme_path参数(测试可注入漂移场景)
- 测试: 5条(脚本口径一致/doctor集成/漂移检测/README缺失不崩溃)

### Added (R207-7: 错误信息英文补齐 — 只补en不铺9语言(低价值陷阱规避))

- cli_error_formatter.py: 三段式错误从11条扩至22条(P001-P026/P055/P105/
  P179/P181高频规则 + INJ/PII/CONFIG/PROVIDER/FILE/PERMISSION), 每条补
  problem_en/cause_en/fix_en; format_three_part_error/format_finding_
  three_part加language参数, 按显式参数>LC_ALL/LANG>locale选语言,
  en缺失回退中文
- 测试: 6条(英文格式/中文默认/LANG环境变量选择/全条目英文字段覆盖/
  高频规则覆盖/finding英文输出)
- 验证: 全量5600 passed / ruff全绿

### Fixed (R208: 误报率Top6三批处置 — 全局3.17%→2.16%, 高误报规则27→21)

- P003约束: 补`# 约束`/`# Constraints`裸章节标题识别(24/32→0)
- P167幻觉防护: CTX收窄到引用/来源/事实性语义+英文词边界(防"refactor"
  内嵌"fact"误配), DECL补`do not invent`/`仅依据`(23/32→0)
- P117事实性: 收窄到科学研究/医学/法律/历史/知识体系+词边界(12/32→0)
- P068防编造: RISK收窄+DECL补RAG grounding声明("仅依据上下文")
  (9/32→0)
- P067知识截止: FACTUAL收窄到事实/统计/年份+词边界(8/32→0)
- P111 CoT: 触发收窄到强推理任务(原因/归因/诊断/决策), DECL补
  "编号/步骤"结构化推理声明(7/32→0)
- 测试: 新增tests/test_r208_false_positive_fix.py(6规则×32干净样本0命中
  +18正负样本断言, 含refactor不误配fact回归)
- docs/规则误报率基线.md: 累计8.38%→2.16%(↓6.22pp), 高误报41→21
- 验证: 全量5619 passed / ruff全绿

### Added (R208: probe命令能力可见性接线 — 评分因子/Agentic评估不再只藏JSON)

- cli probe命令: 风险评分下新增"因子分解"行(severity x probability x
  impact x 命中率), R207-4三因子评分对用户可见可决策
- cli probe命令: Agent特征prompt输出"OWASP Agentic风险评估"段
  (命中的ASI条目+检出数+缓解建议), 与R207-4映射模块对齐
- redteam命令核查: RedTeamReport为独立CVSS/健康分框架, 无三因子字段,
  不强塞(避免两套评分体系混淆)
- 测试: 3条(因子分解可见/Agent prompt Agentic段可见/probe list回归)
- 验证: 全量5622 passed / ruff全绿

## [v67.25.0] - 2026-09-27

### Added (R191: PyPI发布工程 — tag触发发布流水线, 补齐用户第一触点)

- .github/workflows/release.yml: v* tag推送触发 — build(twine check) →
  publish(trusted publishing OIDC, 无需API token, pypi environment门禁)
- pyproject补 readme=README.md: 修复PyPI页面空白(twine check警告清零)
- 验证: 本地build whl+tar.gz → twine check全PASSED → 临时venv安装whl冒烟
  (prompt-cli --version/doctor正常) → 全量3665 passed
- R190方案文档P0(F1)落地; 首次真实发布需在PyPI配置trusted publisher指向
  本workflow后推送tag
- 记账: doctor统计显示150条Lint规则与README宣称255不一致, R192核查

## [v67.25.0] - 2026-09-27

### Fixed (R195: mypy治理第三轮 — _CheckerFn契约放宽, list-item 80处清零)

- 根因: P1xx+扩展规则批量返回list[Finding], 但_CheckerFn契约仅声明
  Finding | None — 80个list-item错误全在_CHECKERS_EXTENDED注册处
- 修复: 契约放宽为 Finding | None | list[Finding](与真实调用方linter.py的
  处理逻辑一致), 消费端已按类型分支处理, 无运行时行为变更
- 棘轮基线: 216 → 136 (累计R189→R195: 443 → 136, -69%)

## [v67.25.0] - 2026-09-27

### Fixed (R196: attr-defined批次治理 — mypy 136→99)

- 循环变量同名复用污染(根因): lint_commands/eval_commands多处 `for r in ...`
  与上方dict循环变量r同名, mypy沿用首次推断致 `dict[str, object].findings`
  等误报 — 改名lint_res/tv/ab_result隔离作用域
- CostTracker.limit公开property: 6处provider访问私有_limit的公开语义补充
- ScanResult.findings→all_findings: scan命令4处用真实property(含注入+继承)
- ProbeResult.findings→is_detected: report.py OWASP聚合改用真实语义字段
- eval命令杂项: converged改iterations判定/get_provider死路径type ignore记账/
  tree节点Any标注
- 验证: 全量5507 passed / ruff全绿 / 棘轮99持平(R189累计443→99, -78%)

## [v67.25.0] - 2026-09-27

### Fixed (R197: assignment批次治理 — mypy 99→65, 全部清零)

- 变量跨分支同名复用(主根因): eval_commands的v/result(3处)/opt_pipeline的
  config/optimizer/flow_dag的result/probe_framework的_cls — 分支间类型不同,
  mypy沿用首次推断致冲突; 全部改名隔离
- mcp_server response字典: 首个int值使dict被定形为dict[str,int], 后续str赋值
  报错 — 显式dict[str, Any]标注(2处)
- dataclass默认值反模式: `tags/keywords: list[str] = None` 改
  field(default_factory=list)(2处, 消除可变默认共享隐患)
- registry双BaseProbe体系: 循环变量cls跨probe_framework/redteam体系复用,
  显式标注entry dict防定形
- inheritance_auditor: current显式str|None标注(get_parent_id可返回None)
- cli_core/eval_commands: probe_names联合None标注/yaml分支data标注
- 棘轮基线: 99 → 65 (R189累计443→65, -85%)
- 验证: 全量5507 passed / ruff全绿 / 棘轮持平通过

## [v67.25.0] - 2026-09-27

### Fixed (R198: attr-defined批次治理 — 错误类名修复, mypy 65→56)

- 死类名修复(真实bug): report.py用PF.ProbeResult.is_detected/severity但本文件
  ProbeResult真实字段为is_vulnerable+confidence; opt_pipeline PromptFixer→
  Fixer(返回tuple, 无fix_count); flow_dag PromptEvaluator→evaluate_template;
  eval_config SecurityScanner→Scanner(真实需provider+scan(id,text));
  template_commands MarketClient→MarketService(data_dir, submit需Template)
- otel_tracer hmac bug: `.digest()`后对bytes调.hexdigest()运行时报错 —
  保留HMAC对象; urllib.parse显式导入; importlib.util显式导入
- 类型标注: by_id dict显式标注(原推断为Collection)/stage_result已标注确认/
  evaluator_registry assertion_defs显式list[AssertionDef]
- 验证: 全量5507 passed / ruff全绿 / 棘轮56持平(R189累计443→56, -87%)

## [v67.25.0] - 2026-09-27

### Fixed (R206: 误报规则首批处置 — 6条100%误报清零, 全局8.38%→6.03%)

- P010/P020: 加上下文门 — 回退策略仅查外部API/服务场景, 评估标准仅查
  选型/打分/排名任务(原: 无条件要求所有prompt → 100%误报)
- P158/P164/P166: 上下文门收窄 — 移除"数据/用户/输出/系统/指令/格式"
  等泛词(原门恒真, 退化为纯声明缺失检查), 保留PII/泄露/回显等强语义词
- P203: 加面向终端用户门 — AI标识要求(EU AI Act第52条)仅适用于
  面向终端用户场景, agent/CLI输出由开发者消费不要求标识
- 既有正样本测试同步更新为强语义词(6个测试文件), 新增
  tests/test_r206_false_positive_fix.py 21用例(6规则×32干净样本=0
  命中负样本断言 + 正样本保留断言)
- 级联修复: test_r33条件门测试换稳定低分输入(收窄后原"test"评分
  95.7不再<95, 测试验证的是条件机制非评分细节)
- docs/规则误报率基线.md: 更新R206处置记录 — 全局误报率8.38%→6.03%
  (↓2.35pp), 高误报规则41→35, 100%误报规则6→0, 剩余Top8列下轮候选
- 验证: 全量5557 passed / ruff全绿 / mypy棘轮0 / 误报基线棘轮exit=0

## [v67.25.0] - 2026-09-27

### Added (R205: 失败用例沉淀 + 预设矩阵 — Failure Mining闭环)

- `src/ai_prompt_toolkit/failure_cases.py`: 失败用例模块 — 评估失败编码
  为yaml回归用例(输入hash+阈值+基线维度分+快照findings), 复评断言
  avg≥threshold 且基线维度不降(容差内)
- `prompt-cli capture-failure -t <file> [--threshold N] [-d dims]
  [--preset P] [--out-dir DIR]`: 沉淀失败用例到 tests/fixtures/failures/
- `prompt-cli verify-failure -c <file|dir> [--tolerance N]`: 回归验证 —
  单文件/目录批量, 失败退出码1, 路径不存在退出码2
- `prompt-cli eval-multi --presets default,security-heavy,...`: 目标×
  权重预设笛卡尔积矩阵(avg/10表格+行最佳+列最优) — 静态评估器不依赖
  模型, 矩阵维度为行业权重预设(7选), 暴露场景适配短板
- 测试: tests/test_r205_failure_matrix.py 13用例(模块roundtrip/回归检出/
  阈值失败/非法文件/capture CLI/verify单+批量+缺失/矩阵2预设/未知预设/
  缺文件/单目标)
- 验证: 全量5535 passed(+13) / ruff全绿 / mypy棘轮0

## [v67.25.0] - 2026-09-27

### Added (R204: 评估基线 drift检测 — Drift Sentinel)

- `src/ai_prompt_toolkit/eval_baseline.py`: 评估基线模块 — 整体/类别/
  维度三级快照 + 维度级drift检测(涨跌超阈值即信号, 默认1.5分降噪)
- `prompt-cli evaluate --baseline-save`: 保存评估基线(默认.eval-baseline.json,
  多文件取均值, 记录preset)
- `prompt-cli evaluate --baseline <file> [--drift-threshold N]`: 基线对比 —
  Drift维度涨/跌分列(▼/▲) + 新增/移除维度 + 整体回归判定(下跌超2%
  退出码1, 基线缺失退出码3)
- 定位: 与lint基线(findings级)互补 — eval侧补上「行为漂移」防线,
  回应社区痛点"静默回归: 代码全绿但质量退化"
- 测试: tests/test_r204_eval_baseline.py 9用例(模块roundtrip/无drift/
  涨跌drift/回归信号/多文件均值/CLI保存/同prompt无drift/改高基线回归/
  缺失文件exit3)
- 验证: 全量5522 passed(+9) / ruff全绿 / mypy棘轮0

## [v67.25.0] - 2026-09-27

### Added (R203: CI闭环体验 — fail-on门禁 + 误报基线度量)

- `prompt-cli lint --fail-on {critical,high,medium}`: 显式级别门禁 —
  该级别及以上finding>0时退出码2, 比--gate更直接的CI开关(借鉴
  llm-security-scanner)
- `scripts/check_false_positives.py`: 规则误报率基线脚本 — 32个干净
  prompt样本×255规则, 输出单规则误报率+全局误报率+`--fail-above`棘轮
- `tests/fixtures/clean_prompts/`: 32个干净中文/英文prompt样本集
  (新增干净prompt入库约定已写入基线文档)
- `docs/规则误报率基线.md`: 首版基线 — 全局误报率8.38%, 41/255规则
  超10%阈值, 6条100%误报(P010/P020/P158/P164/P166/P203)列为R206首批处置
- `docs/CI门禁示例.md`: fail-on+SARIF Code Scanning上传+基线回归最小
  工作流 + 退出码语义表(0/1/2/3)
- 测试: tests/test_r203_fail_on_fp.py 6用例(干净PASS/脏样本FAIL退出码2/
  级别过滤/样本集规模/脚本JSON结构/棘轮FAIL路径)
- 验证: 全量5513 passed(+6) / ruff全绿 / mypy棘轮0 / 误报门禁exit=0

## [v67.25.0] - 2026-09-27

### Fixed (R201: 最后14处清零 — mypy 14→0, 类型治理收官)

- 真bug: dataset scan分支 InjectionDetector.detect 的 template_id 是
  keyword-only, 原位置传参运行时必TypeError — 改keyword传参(并补回误删
  的detector实例化); ascend_npu validate 返回cann_version(str)与声明
  bool不符 — 改bool(cann_version)非空校验
- probe/detector注册: mypy对list字面量join ABC子类type-abstract误报
  (最小复现确认) — 提取_PROBE_CLASSES/_DETECTOR_CLASSES显式
  list[type[Base*]]标注消除
- 标注收窄: plugin create_plugin显式Plugin|None / eval_store与
  prompt_registry lastrowid int()兜底 / security L2ClassifierLayer
  _model Callable标注+_predict局部收窄 / rules_p236_p240与wizard
  list标注 / cli_core sarif与mcp_server schema dict[str,Any]标注
- 验证: mypy 0 errors(257文件) / ruff全绿 / 全量5507 passed /
  棘轮0(R189累计443→0, 100%清零)

## [v67.25.0] - 2026-09-27

### Fixed (R200: CLI命令簇/playground/tracing批次治理, mypy 33→14)

- 真bug修复: lint交互分支读LintResult.fixes_applied(不存在, 运行时崩溃) —
  改用真实字段fixed_findings展示rule_id+description; playground限流
  函数属性模式并发丢计数 — 改模块级dict+threading.Lock; playground无index
  时返回dict与声明FileResponse不匹配 — 改抛HTTPException(404)
- template market: submit/review/deploy/status同名result污染 —
  分别改submit_res/review_res/deploy_res/status_res
- eval: weight_preset None收窄(经_wo反推不可行, 显式is not None)
- recommender: EXCLUSION_RULES dict[str,object]的field key显式str()
- rules_p196_p200: 5个check函数findings显式list[Finding]标注
- otel_tracer: Tracer Protocol补齐trace_lint/trace_eval/record_metric
  (OTelTracer/NoopTracer共有但Protocol缺失致调用方报错)
- lint parallel_results dict[str,object]→dict[str,LintResult](源头标注)
- tracing: save_otlp data标注dict[str,Any] / trace_llm cast(Generator)
- 验证: 全量5507 passed / ruff全绿 / 棘轮14(R189累计443→14, -97%)

## [v67.25.0] - 2026-09-27

### Fixed (R199: arg-type/no-redef批次治理, mypy 56→33)

- 真bug修复: redteam --scorecard 把布尔标志当PromptScorecard传入(运行时必崩) —
  改为从探测结果构造findings后compute_scorecard; market/api review端点
  next()返回str传Template(要求TemplateStatus) — 改TemplateStatus(t.status)
  非法值回退DRAFT; plugin create_plugin返回None时直接register崩溃 — 加守卫
- 同名变量重定义(no-redef): compiler/evaluator result→in_result /
  ab_test/provider payload→data / lint_commands rich分支result→lint_res /
  eval_commands yaml分支data→yaml_data
- 类型收窄: renderer condition None守卫收窄 / plugin Plugin|None收窄 /
  security theme cast(Theme) / template review/status空值守卫exit(2)
- 源头签名: rules.run_all_checks_profiled/search_rules 返回
  dict[str,object]→dict[str,Any](值异构, object过严)
- assertion _coerce_numeric helper: 精确复刻原float(value) if value else default
  三态语义(假值默认/数字直转/非法串抛错由engine捕获), 修float(str|dict|list)
- 验证: 全量5507 passed / ruff全绿 / 棘轮33(R189累计443→33, -93%)

## [v67.24.0] - 2026-09-27

### Fixed (R190: mypy治理第二轮 no-any-return批次 + 方案文档落地)

- no-any-return 20处清零: resume_state/compiler evaluator/assertion engine/
  inheritance_auditor/plugin×2/notification/config/frontmatter×2/custom_rules/
  llm_translator/ab_test provider×2/wizard×3/cli_core — 显式类型标注替代Any透传
- supply_chain_detector union-attr 2处: 双重pattern.search(lint+value)改单次
  match捕获, 消除None链式调用隐患 + 减半正则执行
- 棘轮基线: 234 → 216
- docs/R190-改进方案与开源调研-v1.md: 定位反思(反低价值打磨陷阱) + 外部调研
  (promptfoo/garak/deepeval/prompt-review实践) + P0-P2改进清单; 明确拒绝项
  (UI打磨/规则数竞赛/AI攻击生成/新增provider)
- 验证: 全量3665 passed / ruff全绿 / 棘轮持平

## [v67.23.0] - 2026-09-26

### Fixed (R189: mypy审计治理第一轮 — 静默吞错改棘轮门禁 + 真bug修复)

#### 196个int实参错误清零(Finding位置字段)
- 98处 `Finding(..., 1, 1)` 调用把int传给 `location/remediation: str` 字段 —
  运行时静默存储int, 依赖pydantic隐式强转; 消费方(lint输出/HTML报告/explain/LSP)
  均有 `str(f.location)` 防御 → int→"1" 输出逐字节一致, 纯类型修复
- 17个linter规则文件统一替换; 消费方逐一验证过(line 0 vs line 1等边界)

#### call-arg/attr-defined真bug修复
- **CompileReport.to_dict缺失(真bug)**: `compile --report`/playground
  `report.to_dict()` 运行时AttributeError崩溃 → 补to_dict实现
- **eval multi-judge flaky路径崩溃(真bug)**: flaky_retries>0时StableJudge
  absolute路径返回list无to_dict, `result.to_dict()` 崩溃 → 统一归一为dict
- gepa PanguProvider死代码记账: 构造缺config+provider.call不存在, 异常被except
  吞掉静默回退lint_score — R190+清理
- 红队4处 `cls()` type ignore: 40+具体Probe/Detector子类均自带无参__init__
  (运行时扫描验证), 基类签名仅为抽象声明

#### mypy棘轮门禁(替代 `|| true` 静默吞错)
- scripts/check_mypy_ratchet.py: 错误数只减不增, 超基线CI失败+输出新增样例;
  `--update` 刷新基线(需随修复提交)
- mypy_baseline.txt: 基线234(R188审计443 → 本轮-209)
- CI: mypy步骤挂到3.12单跑+棘轮检查(原3矩阵版本重复跑mypy)

#### 验证
- 全量回归: 3665 passed / 0 failed
- ruff check/format: 全绿
- 棘轮负路径实测: 基线200时正确失败exit=1并列出新增样例

### Fixed (R189补: 对抗性审查修复 — 棘轮门禁自身加固)

- --update防抬基线: count>old时拒绝(需显式--force), 堵住"提交时顺手刷基线"
  绕过门禁的漏洞 — 门禁不可被它自己的刷新入口无声击败
- mypy工具故障检测: rc>=2或"0错误但rc非0"判定为工具故障exit=2, 不再当作
  0错误全绿放行(负路径实测: 坏flag触发rc=2被捕获)
- 失败输出文案纠偏: 原误标"新增错误样例"实为全量列表, 改为"全部错误样例
  (含存量; 与基线差集即本次新增)"避免误导排查
- sarif_reporter location核查: write_jsonl_report无生产调用方(仅测试),
  location int→str类型变更无实际消费方影响, 记档无需修复

## [v67.22.0] - 2026-09-26

### Test (R188: 用户核心旅程e2e固化 + git tag发布工程起点)

- tests/test_e2e_workflow.py: 6步全旅程测试(init→lint→baseline→gate→badge→
  evaluate/scan) — 组合断点守护(R186曾在此发现配置闭环断裂)
- mypy审计: 443错误/66文件被CI `|| true` 静默吞掉 — 分类记账(arg-type 210/
  list-item 80/attr-defined 64...), call-arg 6处需运行时验证; 治理记档R189+
- git tag发布工程起点: 从本版本起每版本打tag(语义化版本+CHANGELOG对齐)

## [v67.21.0] - 2026-09-26

### Added (R187: lint --parallel并行恢复 — 真并行非伪并行)

- 实测驱动决策: asyncio(旧inline实现)对CPU-bound正则是伪并行无加速;
  ThreadPoolExecutor实测4线程对50文件1.87x(正则部分释放GIL) → 采用线程池
- lint --parallel N: 多文件目录并行预计算(非交互/非修复/非干跑时启用,
  交互式进度条仍串行渲染), 30文件目录实测3.82x
- test_r79断言升级为行为级(params含parallel; 原源码grep断言曾因命令搬家失效)
- 全量回归: 3659 passed / 0 failed

## [v67.20.0] - 2026-09-26

### Fixed (R186: 配置闭环断裂修复 — init生成的配置首次真正可消费)

#### 核心断点: 配置生成与消费两套体系断裂
- doctor --init生成的.prompt-toolkit.yml(TOML键名体系)无任何消费者 —
  lint自动发现链只认.lint-rc.yml/.prompt-toolkit.yml(YAML lint_config schema)
- 修复: init改生成lint_config schema的YAML(severity_threshold/exclude_categories/
  include_rules等), 配置闭环首次打通; test_r85/test_r94断言更新为真实schema

#### UX修复
- lint --baseline-save单独使用时静默无效(需--baseline路径配合) →
  默认路径.baseline.json并提示

#### 显式记账
- lint --parallel并行恢复(R177死代码手术移除inline版) → test_r79 xfail记账R187

## [v67.19.0] - 2026-09-26

### Test (R185: 性能审计全工具链 + 命令层冒烟第二批)

- 性能基线补全: evaluate/scan在20KB文本下均<100ms — 全工具链"快"的声称
  (lint/evaluate/scan)经实测成立, 无类似P101的超线性热点
- 命令层冒烟第二批: ab-test(空模型/无key路径)/canary/engine(cli+json)/
  eval-matrix/eval-registry/eval-config/init配置生成
- pyproject: lsp可选extra(pygls/lsprotocol)
- 全量回归: 3651+ passed / 0 failed

## [v67.18.0] - 2026-09-26

### Added (R184: score v2方案C第一步 — quality_score并行采样)

- LintResult新增quality_score扣分制质量分: 100 - Σ(每规则critical=12/high=6/
  medium=1/low=0.1), 同规则多次触发只计一次
- 对抗性审查修正: findings数量随文本长度增长, 按finding计罚会惩罚长文本 →
  规则级去重计分 + 语义定位为"绝对质量粗粒度指示"(跨长度不可直接比较)
- CLI lint完成行并行展示双分数(平均分=通过率 + 质量分=扣分制), gate/badge不动
- to_dict含quality_score; RFC(docs/rfc-score-v2.md)校准数据积累中
- 全量回归: 3651 passed / 0 failed

## [v67.17.0] - 2026-09-26

### Fixed (R183: RFC评分设计 + upgrade-fm模块实现 + 命令层补测)

- **docs/rfc-score-v2.md**: lint评分语义演进RFC(通过率模型短文本虚高实测倒挂92.9>89.8;
  三方案对比: 覆盖因子/加权扣分/双层并存; 推荐C起步→B; 影响面清单+陷阱警示) — 待评审
- **新发现入口级缺陷**: upgrade-fm命令import的template_upgrader模块从未存在
  (调用即ModuleNotFoundError) → 最小实现UpgradeResult+upgrade_template
  (无frontmatter补v2.0骨架, 已有则跳过) + upgrade_batch
- en/README.md: i18n示例参数对齐真实签名(-s是源语言非文件路径)
- 命令层补测: i18n/upgrade-fm/locale/feedback/rules-yaml CliRunner冒烟
- dataset冒烟改API验证数据落库(绕开rich Console单例与CliRunner捕获顺序耦合)

## [v67.16.0] - 2026-09-26

### Test (R182: 命令层冒烟测试 — 端可达性验证+coverage 73→74%)

- CliRunner冒烟: dataset(create/import/list全链路)/score/badge/redteam(离线probe)/
  plugin list/init配置生成 — 8个命令真实跑通
- 修复测试假设错误2处(dataset import需数据集ID非名称; probe名为prompt_injection非dan)
- 覆盖率: dataset_commands 56%/redteam 48%/plugin 32%/security 41%
- 全量回归: 3641 passed / 0 failed

## [v67.15.0] - 2026-09-26

### Fixed (R181: 端完整性治理 — demo/LSP/VSCode扩展)

- demo.sh: banner版本硬编码42.0.0→动态读取; evaluate调用参数修正
  (-s→-t, --mode quick→--quick, 对齐真实签名); 全流程冒烟通过
- LSP: pyproject新增lsp可选extra(pygls/lsprotocol), 补全"每端可选依赖"声明
- VSCode扩展: version list/diff调用对齐真实签名(原子命令风格+--from/--to
  均不存在, 集成必坏) — 端参数与注册表逐一审计
- 评分模型演进(记档): score=规则通过率对极短prompt虚高(4字得92.9),
  设计项为"覆盖因子"加权, 涉及gate/badge/等级全链路ripple, 单独立项

## [v67.14.0] - 2026-09-26

### Fixed (R180: 矛盾/歧义检测精度治理 — 模板自洽债务清零)

#### 伪语义检测精度修复
- P102: 移除"请/不要矛盾"pattern — "请做X, 不要Y"是正常指令形态, 正则词对
  大量误报; P102/P023(伪语义检测精度天花板低)HIGH→MEDIUM与P016对齐
- P023: positive提取跨越否定语境(把同行"不得编造"声明吞进positive再与
  negative子串匹配, 自相冲突) → positive含否定词跳过
- P016: 引号内内容是被引用/禁止的词(模板写'避免"可能"等模糊词汇'反被命中)
  → 匹配前剥离引号内容
- P021: 长串须含数字(驼峰方法名列表onCreate/onWindowStageCreate误报);
  decode须API名精确形态(atob小写/大写Decode普通词排除)
- P163: 防御性禁止声明("不得建议绕过/不得提供攻击方法")视作越狱防护
- P035: 需RAG检索语境证据 — 客服"订单查询"不构成RAG面

#### 模板自洽债务清零
- 237(R178记账) → 16 → 5 → **0**
- harmonyos-performance措辞精确化("可能导致"→"若引发")
- 全量回归: 3634 passed / 0 failed

## [v67.13.0] - 2026-09-26

### Fixed (R179: 模板自洽债务消化 — 237→16条)

#### 部署语境规则豁免(显式带理由, 同ESLint overrides逻辑)
- 45条部署语境规则对模板豁免(模型选型/数据治理/运行时编排/多模态处理/
  ArkTS代码规范五大类) — 适用对象是生产部署配置, 模板是资产源文件
- 豁免清单显式记账于守护测试, 逐条带理由可审查

#### 规则误报修复
- P177 Base64启发式: "Critical/Major/Minor/Suggestion"(严重级词汇表)曾被
  [A-Za-z0-9+/=]{16,}整体匹配 → 收紧为须字母数字混合+长度>=20(真编码特征)
- P181 版本pattern支持引号包裹值(frontmatter version: "2.0"漏检)
- P022 剥离markdown代码块(教学代码示例import {...}非prompt注入标记)

#### 债务快照收缩: 237 → 16条
- 剩余16条为模板内容真问题(P023指令冲突×4/P102逻辑矛盾×3/P163×2/
  P021×2/P016/P035), 记账待R180逐个修复

## [v67.12.0] - 2026-09-26

### Fixed (R178: 内置模板自洽专项 — golden快照守护)

#### 误报修复(规则语境再校准)
- P100/P221/P224/P225: 模型/部署语境规则剥离YAML frontmatter —
  model_compatibility元数据是资产声明而非部署事实(修复30+误报)
- P180(CRITICAL): 链式编排需"步骤间数据传递"证据 — 裸"步骤/流程/链式思考"
  是普通工作流描述, 不再触发链式注入CRITICAL
- rules.py新增strip_frontmatter共享helper(单一实现)

#### 自洽守护机制(golden快照)
- tests/fixtures/template_high_baseline.json: 26个模板的237条HIGH显式记账
- 守护测试: 快照外新增HIGH即红(新误报必须先审查); 债务只允许收缩;
  修复后重新生成快照固化成果 — 模板自洽债务渐进消化(R179+)
- baseline机制dogfooding: 用项目自身的记账思想守护自身资产

## [v67.11.0] - 2026-09-26

### Fixed (R177: 死代码手术3248行 + 功能回归修复 + coverage达标73%)

#### 死代码手术(cli_core 3943→695行, -3248行)
- AST精确定位43个被cli/commands/模块同名注册覆盖的死命令函数 — 模块化重构
  遗留的单体残骸(总缺失覆盖2063行的主体), 全量回归全绿即等价性证明
- 覆盖率 68.49% → **73%**(超70目标), cli_core缺失行2063→246

#### 功能回归修复(死代码审计的意外收获)
- **lint/scan --resume 功能曾随inline死代码静默丢失**(R71的进度保存/恢复,
  SIGINT中断后可续跑) — 恢复到lint_commands版本(恢复进度/全完成清理/逐文件save)
- test_r71移除importlib.reload脆弱技巧(reload后commands/模块绑定旧group,
  制造与真实运行失真的注册环境 — 这正是死代码"复活"的原因)

#### 自洽性审计(工具自己的资产必须通过自己的lint)
- 内置模板26个全部有HIGH/CRITICAL — P221将model_compatibility兼容性元数据
  误判为"调用模型需来源验证" → 声明兼容性即视作已验证选型; 剩余热点
  (P241/P224/P100/P180/P161/P162)记入R178待办

#### coverage债务清单(更新)
- cli命令层(lint_commands 37%/eval_commands等)与ab_test/statistics为下一批补测目标

## [v67.10.0] - 2026-09-26

### Fixed (R175/R176: 性能基线+覆盖率门禁诚实化)

#### 性能(核心价值"快"首次量化)
- 性能审计: 50KB文本lint 6266ms, 其中check_p101(语义冗余)占92% —
  O(n²)两两Jaccard且每对重复建set
- 优化: frozenset预计算+min/max数学等价剪枝+报告上限截断(50+"标注)
  → 546ms(**11.5倍**), 正常文本结果逐字节一致
- 性能守护测试: 50KB全重复文本P101必须在1秒内完成

#### 覆盖率门禁诚实化(三层矛盾修复)
- 实际68.02% < pyproject承诺70 < CI虚标80
- 补测: exceptions统一异常契约(0%→97%) + ab_test并行引擎关键路径(20%→82%:
  provider初始化/进度/重试/取消/run/run_pairwise端到端mock)
- pyproject fail_under=68钉住真实水位(防倒退), 70目标列入债务清单; CI对齐pyproject

## [v67.9.0] - 2026-09-26

### Fixed (R174: 新用户第一分钟 — 入口一致性治理)

#### 核心断点: MCP Server无CLI入口
- mcp_server.run_server()(stdio JSON-RPC循环)从未接线到CLI — README声称的
  MCP Server能力对用户不可达; 新增 `prompt-cli mcp` 命令(含--validate-only校验模式)
- serverInfo.version硬编码42.0.0(过期漂移) → 动态取包版本__version__
- README功能表/优势/MCP章节: serve(playground HTTP)误标为MCP Server → 修正为mcp;
  新增标准.mcp.json接入片段(args: ["mcp"])

#### 文档入口漂移(命令引用 vs 注册表审计)
- README: scorecard→score(实际命令名), diff→prompt-diff
- pyproject: 新增 `prompt` 别名入口(文档/用户习惯的裸prompt命令可用)
- OSC参赛示例/README: MCP工具数55+/53 → 73(注册表真实值)
- 审计方法: 提取文档命令引用→比对click注册表, 全部引用可达

## [v67.8.0] - 2026-09-26

### Changed (R173: 同义规则治理)

- 语料重叠率审计: 描述相似度粗筛71对→25个语料验证; P094~P130(checker同逻辑双登记, 重叠50%)为真冗余
- 引擎: SYNONYM_RULE_GROUPS+suppress_synonym_findings(同触抑制从规则, 独立触发保留; 数据驱动)
- 工具固化: scripts/audit_synonym_rules.py(相似度+重叠率两步审计)
- 规则文档自动标注同义组; C5反模式查重结论: P015/P024/P002已覆盖, 零新增规则
- P181决策反转: checker有生产语境动态severity(合理设计), 不降级

## [v67.7.0] - 2026-09-26

### Added (R172: U1 trace可视化完整版)

- 内核: otel_tracer.build_span_tree — 扁平span列表→父子树(纯函数, 孤儿span挂根, 按时间排序)
- CLI: prompt-cli trace -f <file> — Rich Tree渲染lint --trace-json落盘文件
  (span树+耗时着色+关键属性摘要+metrics统计), 与既有进程内tracing命令合并(不造重复命令)
- 测试: 树嵌套/孤儿挂根/CLI渲染/缺失文件exit码守护; 全量3595 passed

## [v67.6.0] - 2026-09-26

### Changed (R171: Lint门禁修复 — ruff 3905→0, 声明门禁成真)

#### 真实缺陷修复(F821 undefined-name, 22处)
- statistics.py: f-string `{n=}`引用未定义变量(运行时NameError)×5 → `{sample_size}`
- html_report.py/report/html_reporter.py: 嵌套同引号f-string是Python 3.12语法
  (PEP 701), 声明支持的3.10/3.11上无法导入 → 提取变量(修复2个模块的版本兼容)
- cli_core.py: `console=console`引用未定义变量×2(eval/scan的rich路径NameError)、
  quiet分支avg_score先用后算
- 补齐缺失导入: tempfile/hashlib/click/Any; discrete_eval aspect→name;
  provider AbTestError注解TYPE_CHECKING化

#### Lint治理(ruff check 3905→0)
- 配置: 中文项目噪音规则关闭(RUF001/002/003全角标点1830条)+__init__.py
  F401合法re-export豁免+性能/命名类规则带理由关闭
- 自动修复1690+条: 导入排序/未用导入/引号风格/f-string等
- 人工judgment修复: F841未用变量21处逐个审(区分死代码/副作用调用/
  未完成功能三案处理); B904异常链; B007循环变量
- ruff format: 406文件一次性对齐, format --check门禁成真(441全合规)

#### 质量守护
- 全量回归: 3591 passed / 0 failed
- CI的ruff check + ruff format --check首次成为真实门禁

## [v67.5.0] - 2026-09-26

### Changed (R169: 自举审计驱动的规则校准)

- 方法升级: 对仓库自身35个提示词语料做dogfooding审计, 按"HIGH/CRITICAL且命中率>=80%"定位过热规则
- P068 HIGH→MEDIUM(与P167幻觉声明对齐); P184 HIGH→MEDIUM(与P155降级声明对齐, 定义+内联同步)
- P176门控收紧: 需真实多轮会话语义(多轮/历史消息/chat history) — 裸"对话/上下文/历史"
  曾让单轮Prompt触发CRITICAL上下文污染; 补单轮反例守护
- 复扫结果: 高危层仅剩P177(语料含编码示例所致, 真实提示词上为正当信号)
- 全量回归: 3590 passed / 0 failed

## [v67.4.0] - 2026-09-26

### Changed (R168: 声明类规则误报治理 — Q1家族清零)

#### 规则严重级校准(HIGH→MEDIUM, 10条)
- 声明类规则(P151输入边界/P152输出转义/P158脱敏/P164提取防护/P165侧信道/
  P166输出过滤/P167幻觉/P169毒性/P182依赖/P242透明度)降为MEDIUM:
  "未声明X"属advisory最佳实践提示, HIGH会炸CI门禁且对优秀Prompt误报
- Q1干净基线(结构完备/安全完备/极简)实现零HIGH/CRITICAL, ADVISORY_FAMILY
  从14条收缩至0, 作为回归绊线保留

#### 触发门控收紧(修复过宽上下文)
- P113: 需"受保护系统指令"语义 — 裸"你是/角色"角色定义不再触发(R168前
  角色定义越完善误报越多), _INJECTION_DEFENSE补"指令不可见/输出过滤/防提取"
- P159: 需"执行不可信代码/脚本"语义 — 裸"运行/代码/工具"过宽
- P163: 需对抗性劫持语义(越狱/绕过/DAN/扮演) — 裸"系统/角色/指令/禁止"
  曾让几乎任何带角色的Prompt触发CRITICAL

#### 体验(D3/U3)
- D3: lint无高危发现时输出下一步引导(等级/徽章/评估/基线命令)
- U3: doctor首次运行输出快速入门命令块

## [v67.1.0] - 2026-09-26

### Added (R165: Batch 0 基线修复+可观测性+徽章同步)

#### R165: 基线修复与工程卫生
- 修复 mcp_reload 类身份分裂: 核心类模块(rules/types)不再 in-process reload,
  仅热重载数据型扩展模块(rules_p*/owasp_mapping), 消除跨重载 isinstance 失效
- 修复6条规则误报缺陷: P194裸"消息"误触发多Agent、P196/P197/P239"逐步推理"
  (思维链)误判为推理服务、P201/P202/P205否定式声明("不收集")误报、
  P221裸"模型"词误报供应链风险、P237漏识别"响应时间恒定"防护、P246裸版本号
  即报HIGH治理告警
- huawei_cloud 单文件→包(iam.py迁移+__init__统一re-export), 消除模块/包同名冲突
- otel_tracer.py: OTel GenAI语义约定对齐的可观测性Tracer(无SDK硬依赖)
- scripts/sync_badges.py: README徽章/核心数据从注册表真实生成(评估维度130、
  MCP工具73等漂移数字已纠正), 不再手写
- tests/conftest.py: 规则注册表隔离fixture, 防跨测试污染
- 清理97个会话调试产物+.gitignore防再污染
- 全量回归: 3539 passed / 0 failed

## [v67.0.0] - 2026-07-30

### Added (R161-R163: 测试套件+配置发现+成本追踪)

#### R163: 成本追踪维度(借鉴Langfuse)
- cost_tracker.py: CostRecord+CostTracker+多模型定价(GPT/Claude/鹏鹏/DeepSeek/Qwen)
- Token使用+成本USD+延迟追踪+按模型分组统计

#### R162: 配置文件自动发现+退出码语义化
- 自动发现.lint-rc.yml/.prompt-toolkit.yml
- 退出码: 0=PASS, 1=WARN, 2=FAIL, 3=ERROR

#### R161: 声明式Lint+Eval测试套件(借鉴promptfoo)
- test_suite.py: TestSuite/TestGroup/Assertion+YAML/JSON配置
- MCP工具test_suite_run

## [v66.0.0] - 2026-07-30

### Added (R159-R160: 包幻觉+PII增强+Lint过滤)

## [v65.0.0] - 2026-07-30

### Added (R159: 包幻觉+PII增强探测)

#### R159: P251-P255 包幻觉+PII增强探测
- P251: 包幻觉检测(模型推荐不存在的包/库/模块)
- P252: 生物特征PII泄露(指纹/面部/虹膜/声纹) - CRITICAL
- P253: 金融PII泄露(银行卡/信用卡/证券) - CRITICAL
- P254: 医疗PII泄露(诊断/处方/病历/基因) - CRITICAL
- P255: 未成年人信息泄露(年龄<18/学籍/监护人) - CRITICAL
- 借鉴garak packagehallucination+ProPILE
- 250→255条规则, 191→196可自动修复

## [v64.0.0] - 2026-07-30

### Added (R156-R157: MCP热重载+配置文件)

#### R157: lint --config配置文件支持
- lint_config.py: LintConfig+load_lint_config+merge_config_with_cli
- YAML/JSON配置: severity_threshold/exclude_categories/include_categories/include_rules/exclude_rules/max_findings/fail_on/parallel/timeout_ms
- CLI选项覆盖配置文件

#### R156: MCP热重载(mcp_reload)
- _tool_mcp_reload: importlib.reload+dispatch清空
- 支持指定模块热重载(默认rules)

## [v63.0.0] - 2026-07-30

### Added (R154: Prompt治理与运营安全)

#### R154: P246-P250 Prompt治理与运营安全规则
- P246: Prompt版本审计缺失(无版本控制/变更审批/回滚)
- P247: A/B测试安全风险(匿名/公平性/数据隔离)
- P248: Prompt漂移检测(语义diff/回归测试/告警)
- P249: 级联Prompt风险(最大深度/超时/断路器)
- P250: Prompt缓存中毒(命名空间隔离/签名/TTL)
- 245→250条规则, 186→191可自动修复

## [v62.0.0] - 2026-07-30

### Added (R150-R152: 解释增强+合规审计+lcov导出)

#### R152: lint --export-lcov覆盖率导出
- lcov_export.py: generate_lcov_report+generate_coverage_summary
- lint --export-lcov: lcov格式规则覆盖率(TN/FN/DA+按类别统计)

#### R151: P241-P245 Prompt合规审计规则
- P241: GDPR数据最小化违规
- P242: AI Act透明度缺失
- P243: 数据保留策略缺失
- P244: 审计日志不完整
- P245: 跨境数据传输合规
- 240→245条规则, 181→186可自动修复

#### R150: lint --explain交互式解释增强
- explain.py: explain_finding+OWASP参考+风险等级+修复方案
- lint --explain: 详细说明+中英文支持

## [v61.0.0] - 2026-07-30

### Added (R147-R148: JSON diff+推理引擎安全)

#### R148: P236-P240 LLM推理引擎安全规则
- P236: 模型量化安全(量化后对抗鲁棒性降级)
- P237: 推理侧信道风险(时序/功耗/缓存泄露)
- P238: KV缓存污染(注入/越界读写)
- P239: 推理资源耗尽(无速率限制DoS)
- P240: 模型权重完整性(加载未校验替换攻击)
- 235→240条Lint规则, 176→181可自动修复

#### R147: lint --json-diff结构化对比输出
- structured_diff.py: generate_structured_diff+format_diff_json
- lint --json-diff: JSON格式diff(verdict/摘要/规则级统计), CI/CD集成

## [v60.0.0] - 2026-07-30

### Added (R144-R145: 修复建议+联邦学习安全)

#### R145: P231-P235联邦学习安全规则
- P231: 梯度泄露风险(梯度反转攻击还原训练数据)
- P232: 差分隐私缺失(联邦聚合未添加DP噪声)
- P233: 模型投毒防护缺失(无Krum/鲁棒聚合)
- P234: 安全聚合协议缺失(梯度未加密)
- P235: 客户端身份验证缺失(Sybil伪装攻击)
- 230→235条Lint规则, 171→176可自动修复

#### R144: lint --suggest修复建议智能推荐
- suggest.py: generate_suggestions+Suggestion+优先级排序+影响评估
- lint --suggest: 按严重度/频率排序+操作步骤+中英文支持

## [v59.0.0] - 2026-07-30

### Added (R139-R142: .promptignore+statistics+ArkTS+baseline)

#### R142: lint --baseline基线管理
- baseline.py: BaselineSnapshot/BaselineDiff/save/load/compare
- lint --baseline指定基线文件, --baseline-save保存基线快照
- 对比检测: 新增/修复/回归分类+回归告警

#### R141: P226-P230 ArkTS安全规则
- P226: ArkTS动态类型滥用(@ts-ignore/any绕过类型安全)
- P227: ArkUI状态管理风险(敏感@State未加密)
- P228: 鸿蒙权限声明缺失(Ability缺ohos.permission)
- P229: ArkTS跨组件通信风险(router/Emitter未校验)
- P230: 鸿蒙沙箱隔离违规(越界路径/网络无域名)
- 225→230条Lint规则, 166→171可自动修复

#### R140: lint --statistics规则命中率统计
- compute_rule_statistics: 命中次数+占比+按类别/严重度分组
- lint --statistics: 显示规则命中率排行表

#### R139: .promptignore忽略文件支持
- load_promptignore/should_ignore/discover_templates_with_ignore
- lint --ignore-file: 支持自定义忽略文件+!否定模式

## [v58.0.0] - 2026-07-30

### Added (R135-R137: Finding行号+eval-multi+Pipeline模板)

#### R137: 华为云CodeArts Pipeline模板
- .codearts/pipeline-lint.yml: lint+eval+security+probe+报告生成流水线

#### R136: eval-multi多模板评估对比
- eval-multi --targets: 并排表格对比+最优标记+均分对比

#### R135: Finding行号定位
- find_line()辅助函数 + lint CLI显示行号

## [v57.0.0] - 2026-07-30

### Added (R132-R133: csv+规则文档)

#### R133: 规则文档自动生成
- docs/rules.md: 全部225条规则详细列表(类别/等级/OWASP/可修复)

#### R132: eval --format csv
- 标准CSV格式输出(header行+转义处理)

## [v56.0.0] - 2026-07-30

### Added (R124-R130: profile+owasp+search+supply_chain+dry-run)

#### R130: lint --fix --dry-run 干运行修复预览
- --dry-run: 预览修复内容但不实际修改文件

#### R129: lint --rules-search 规则搜索引擎
- search_rules() 中英文双语fuzzy评分 + OWASP/category过滤

#### R128: P221-P225 供应链安全规则
- P221: 模型来源验证 | P222: 依赖审计 | P223: 数据溯源 | P224: 版本锁定 | P225: 签名验证
- 总规则220→225, AUTO_FIXABLE 161→166

#### R127: OWASP映射100%覆盖
- 44条未映射规则补全, 覆盖率80%→100%

#### R126: 改进清单v3.0
- 功能7+内容4+细节5+体验5+赛事4项改进清单文档

#### R125: OWASP映射覆盖率报告
- lint --owasp-report + generate_owasp_report()

#### R124: lint --profile 性能分析
- run_all_checks_profiled() + Top10慢规则 + 总耗时统计

## [v55.0.0] - 2026-07-28

### Added (R121-R122: eval markdown+MCP version_diff+多模态安全)

#### R122: P216-P220 多模态安全规则
- P216: 图像注入风险 | P217: 音频指令注入 | P218: 跨模态信息泄露 | P219: 模态降级安全 | P220: 多模态输出验证
- 总规则215→220, AUTO_FIXABLE 156→161

#### R121: eval --format markdown + MCP prompt_version_diff
- evaluate --format markdown: Markdown表格格式输出(维度/名称/类别/分数/权重)
- MCP prompt_version_diff: 对比两个Prompt版本差异(语义+结构)

## [v54.0.0] - 2026-07-28

### Added (R117-R120: CodeArts Repo+鸿蒙API16+benchmark)

#### R120: 版本升级 v54.0.0
- __init__.py: v53.0.0→v54.0.0

#### R119: eval --benchmark基准测试
- BenchmarkResult + run_benchmark() 评分历史趋势对比
- JSON存储历史评分, 支持delta计算

#### R118: P211-P215 鸿蒙NEXT API 16规则
- P211: LazyForEach懒加载 | P212: @ObservedV2 | P213: NAPI安全 | P214: 权限 | P215: 分布式安全
- 总规则210→215, AUTO_FIXABLE 151→156

#### R117: 华为云CodeArts Repo规范
- repo_check.py: 7项仓库规范检查 + .codearts/repo.yml

## [v53.0.0] - 2026-07-28

### Added (R111-R115: 合规规则+RAG安全+CI模式+diff)

#### R115: lint --ci + lint --diff
- --ci: CI模式精简输出(files/findings/score + PASS/FAIL)
- --diff: 修复前后unified diff展示(参考difflib)

#### R114: P206-P210 RAG/知识库安全规则
- P206: 检索注入风险 | P207: 幻觉检测缺失 | P208: 来源溯源缺失
- P209: 上下文窗口溢出 | P210: 嵌入偏移风险
- 总规则205→210, AUTO_FIXABLE 146→151

#### R113: 改进清单文档v2.0
- 功能增添7项+内容改进4项+细节优化4项+用户体验5项+赛事贴合4项

#### R112: lint --watch实时监听
- 文件变更自动重新lint(mtime轮询+Ctrl+C退出)

#### R111: P201-P205 Prompt合规规则
- P201: 数据合规声明 | P202: 用户同意机制 | P203: AI输出标识
- P204: 偏见公平声明 | P205: 数据留存策略
- 总规则200→205, AUTO_FIXABLE 141→146

## [v52.0.0] - 2026-07-28

### Added (R108-R110: LLM推理安全+TUI浏览+版本升级)

#### R110: 版本升级 v52.0.0
- __init__.py: v51.0.0→v52.0.0
- pyproject.toml: version 52.0.0

#### R109: lint --tui交互式终端界面
- tui_browser.py: Rich Tree+Table交互式浏览lint结果
- lint --tui选项: 交互式浏览模式
- 颜色编码: CRITICAL/HIGH/MEDIUM/LOW分级着色
- 统计摘要: 分类统计+评分+等级(SABCDF)
- 基于开源调查: Rich(56K stars)轻量方案

#### R108: P196-P200 LLM推理安全规则
- P196: LLM推理超时风险(未设置timeout)
- P197: LLM输出长度失控(未限制max_tokens)
- P198: LLM温度参数不当(temperature>1.5)
- P199: LLM采样参数冲突(top_p+temperature双重随机)
- P200: LLM流式响应安全(未做实时内容审核)
- 总规则195→200, AUTO_FIXABLE 136→141

## [v51.0.0] - 2026-07-28

### Added (R99-R104: 改进循环+Agent安全+ModelArts增强+评分等级+CodeArts Pipeline)

#### R104: CodeArts Pipeline + 版本v51.0.0
- .codearts/pipeline.yml: 华为云CodeArts Pipeline Prompt质量门禁
- __init__.py: v50.0.0→v51.0.0

#### R103: 评分等级 + PASS/FAIL决策
- score_to_grade(): S/A/B/C/D/F等级评定
- score_to_decision(): PASS/FAIL决策(可配置阈值)
- evaluate输出增加等级+决策

#### R102: ModelArts Provider增强
- 扩展模型定价: Qwen2.5-72B/DeepSeek-V3/Llama3.1-70B/ChatGLM4-9B
- MaaS API 2.0/AgentArts文档

#### R101: P191-P195 AI Agent安全规则
- P191: Agent权限边界 | P192: 工具调用约束 | P193: CoT泄露 | P194: 多Agent协调 | P195: 记忆隔离
- 总规则190→195, AUTO_FIXABLE 131→136

#### R100: CHANGELOG R95-R98 + MCP同步校验 + lint --changed优化
- _validate_tools_dispatch_sync(): 启动时校验tools/dispatch一致性
- lint --changed: relative_path精确匹配

#### R99: 改进清单文档 + 开源项目复用调查
- docs/99-改进分析-改进清单-v1.0#0.md: 8功能+4内容+5细节+4体验+4赛事
- 01-调研-开源项目复用调查-v1.0.md: promptfoo/garak/DSPy/Langfuse/llm-guard/DeepEval

## [v50.0.0] - 2026-07-28

### Added (R95-R98: 文档更新+增量lint+鸿蒙API15+华为云FG模板)

#### R98: 华为云FunctionGraph Prompt模板 + 2个新MCP工具
- huawei_cloud/fg_template.py: 4种FG模板(ai_inference/conversation/embedding/content_moderation)
- MCP工具: fg_template_list + fg_template_generate
- prompt_lint描述更新180→190

#### R97: P186-P190鸿蒙NEXT API 15规则
- P186: ArkUI声明式范式迁移 | P187: Node-API线程安全 | P188: 沙箱2.0
- P189: 模块化编译依赖 | P190: 元服务(Atomic Service)规范
- AUTO_FIXABLE: 126→131, 总规则185→190

#### R96: lint --changed增量模式 + --cache-dir缓存目录
- --changed: 仅lint git变更/未提交文件(git diff + ls-files)
- --cache-dir: 指定增量缓存目录(默认.prompt-toolkit-cache/)

#### R95: CHANGELOG R91-R94 + CONTRIBUTING.md更新
- CONTRIBUTING.md: Lint规则类别表(9类P001-P190) + WeightPreset预设表

### Added (R91-R94: CHANGELOG+运维规则+eval预设格式统一+weight_preset配置)

#### R94: eval --preset + table/yaml格式统一 + doctor --init weight_preset
- cli_core.py evaluate: 添加--preset选项 + weight_overrides传递
- eval_commands.py: --format扩展支持table/yaml输出
- doctor --init: 配置模板添加weight_preset字段

#### R93: P181-P185 Prompt运维Lint规则
- P181: Prompt版本声明缺失(生产环境必须有版本号)
- P182: Prompt依赖声明缺失(外部API/模型/工具依赖需显式声明)
- P183: Prompt环境隔离不足(生产/测试/开发环境配置隔离)
- P184: Prompt降级策略缺失(模型不可用时无降级方案)
- P185: Prompt灰度发布配置缺失(新版本灰度发布策略)
- AUTO_FIXABLE: 121→126, OWASP LLM01/LLM09映射

#### R92: scan --explain交互式安全扫描解释 + MCP工具
- scan --explain: 交互式安全扫描解释模式
- 3个新MCP工具: rollback_safety_check/html_report_generate/weight_preset_list
- __init__.py: v42.0.0→v50.0.0

#### R91: CHANGELOG.md更新记录R85-R90

### Added (R76-R90: 输出安全+DevEco+权重预设+高级安全规则+回滚检查+HTML报告+主题)

#### R90: lint --color-theme + --html报告
- lint --color-theme: 5种颜色主题(default/monokai/solarized/nord/dracula)
- lint --html: 一键生成交互式HTML报告
- PROMPT_TOOLKIT_THEME环境变量: 运行时主题切换

#### R89: HTML报告交互式折叠
- generate_html_report(): 独立HTML报告(内联CSS/JS, 零外部依赖)
- 交互式折叠+深浅主题切换+搜索过滤+统计面板+分数进度条

#### R88: Prompt Diff回滚安全检查
- rollback_safety_check(): 检测回滚是否引入安全降级
- RollbackCheckResult: is_safe/risk_level/security_score_delta/recommendations
- 风险等级: safe/warning/dangerous三级

#### R87: P176-P180高级安全Lint规则(参考garak/promptfoo)
- P176: 多轮对话上下文污染检测(continuation probe)
- P177: Base64/编码混淆注入检测(encoding probe)
- P178: 影子指令注入(HTML注释/Markdown隐藏指令)
- P179: 输出格式劫持(强制JSON/SQL输出绕过)
- P180: 链式Prompt注入(跨步骤传播检测)

#### R86: 评估维度权重体系
- WeightPreset类: 7个行业预设(default/security-heavy/quality-balanced/performance-first/harmonyos-strict/redteam-ready/cost-efficient)
- evaluate --preset CLI选项
- evaluate_template()支持weight_overrides参数

#### R85: doctor --init配置模板
- doctor --init: 首次运行自动生成.prompt-toolkit.yml配置模板
- 删除dev_commands.py中旧版doctor(与cli_core.py冲突)

#### R81-R84: (已在之前commit中记录)

### Stats
- Lint规则: 180 (P001-P180)
- 自动修复: 121条
- 评估维度: 130
- 行业预设: 7个
- MCP工具: 46+
- Provider: 25
- Probe: 116 (含4个glitch)

#### R80: LSP Server增强
- textDocument/hover: 悬浮显示规则详情+修复建议+自动修复标识
- textDocument/codeAction: QuickFix快速修复+查看详情

#### R79: lint并行处理
- lint --parallel/-j: 多线程并行lint(0=CPU核数)
- lint类别统计+严重度统计输出

#### R78: 条件模板渲染+NIST AI RMF
- render_conditional: {% if %}/{% else %}/{% endif %}, {% for %}, {% i18n %}
- NIST AI RMF 1.0映射: GOVERN/MAP/MEASURE/MANAGE 4大功能37子类别
- EU AI Act映射: Article5/9/10/14/15/52合规

#### R77: Glitch Probe+描述更新
- 4个Glitch Probe: glitch_token/glitch_repeat/glitch_zerowidth/glitch_separator
- MCP描述更新: 130→170规则

#### R76: 输出安全+DevEco配置
- P166-P170输出安全Lint规则(内容过滤/幻觉防护/偏见检测/毒性过滤/引用验证)
- output_scanners.py: 6类输出安全扫描器(NoRefusal/Bias/Toxicity/Relevance/FactualConsistency/Citation)
- DevEco Studio配置生成: generate_deveco_config + hvigorfile.ts + GitHub Actions
- lint --explain: 交互式修复建议(规则详情+双语+OWASP+自动修复+鸿蒙模板)
- AUTO_FIXABLE: 106→111条, OWASP映射补充

### Stats
- Lint规则: 170 (P001-P170)
- 自动修复: 111条
- 评估维度: 120
- MCP工具: 46+
- Provider: 25
- Probe: 116 (含4个glitch)

## [v42.0.0] - 2026-07-18

### Added (第二十三轮成熟度循环 R23: v41→v42 — lintlang参考检测器+PII+Quality Gate+中文注入库)

#### P0关键问题修复
- 新增根目录 README.md 完整项目文档
- 完善 .gitignore 覆盖 Python/Node/IDE/OS 常见忽略项
- 新增 LICENSE (MIT) 和 CONTRIBUTING.md

#### lintlang参考7大检测器 (P041-P047)
- P041: 工具描述模糊性检测(H1) - 检测Agent型Prompt中工具描述是否清晰
- P042: 缺失约束脚手架检测(H2) - 检测条件分支和边界约束是否完整
- P043: Schema-Intent不匹配检测(H3) - 检测参数Schema与意图是否一致
- P044: 上下文边界侵蚀检测(H4) - 检测上下文传递的隐私泄露风险
- P045: 隐式指令失败检测(H5) - 检测隐含但未明确的期望
- P046: 模板格式契约违反检测(H6) - 检测模板变量与格式规范一致性
- P047: 角色混淆检测(H7) - 检测多角色Prompt中的角色冲突

#### 中文特有Lint规则 (P048-P050)
- P048: 中文标点混用检测 - 检测中英文标点混用问题
- P049: Token消耗预警 - 预估Prompt Token消耗，超过阈值告警
- P050: 中文冗余表述检测 - 检测叠词、重复表述等

#### Quality Gate (CI集成)
- 新增 Verdict-based Quality Gate（PASS/WARN/FAIL）
- 支持配置化门禁规则：fail_on_critical、fail_on_high、min_score等
- CLI lint命令新增 --gate 选项
- 门禁结果影响退出码：PASS=0, WARN=1, FAIL=2

#### PII个人隐私信息检测
- 新增 PIIDetector：10种PII类型检测（邮箱/手机/身份证/银行卡/IP/护照等）
- 自动脱敏功能：redact_text() 支持自动替换敏感信息
- 集成到 Scanner.scan() 流程
- 身份证/银行卡检测自动升级为 CRITICAL 级别

#### 中文Prompt注入模式库
- 新增 15条中文特有注入检测规则 (INJ-ZH-001 ~ INJ-ZH-015)
- 覆盖：中文指令覆盖、角色劫持、DAN变体、语义漂移、情感操纵、虚构场景注入等
- 集成到 Scanner，默认启用

#### CLI增强
- lint命令新增 --gate 选项（Quality Gate CI模式）
- lint命令新增 SARIF 输出格式（GitHub Code Scanning集成）
- 新增 _generate_sarif() SARIF 2.1.0格式生成器

#### 赛事准备
- 新增 demo.sh 一键演示脚本
- 新增 CONTRIBUTING.md 贡献指南
- 新增 LICENSE (MIT) 开源许可

## [v33.5.0] - 2026-07-14

### Changed (第二十轮成熟度循环 R20: v33.4→v33.5 — Provider重构+代码清理)

#### P1重构
- provider.py 5个Provider invoke方法重构: 提取`_invoke_openai_compatible()`到BaseProvider
  - OpenAI/DeepSeek/Aliyun: invoke方法从30+行→2行(调用通用方法)
  - Anthropic/Huawei: 保持自定义invoke(自有API格式)，但使用`_PROVIDER_LABEL`
- provider.py estimate_cost提升到BaseProvider: 5个重复方法→1个通用实现+_PRICING/_DEFAULT_RATES
- BaseProvider新增类属性: `_PRICING`, `_DEFAULT_RATES`, `_PROVIDER_LABEL`

#### P3清理
- cli.py: 移除evaluate命令中未使用的`from pathlib import Path as _Path`

## [v33.4.0] - 2026-07-14

### Changed (第十九轮成熟度循环 R19: v33.3→v33.4 — P2硬编码魔数提取)

#### P2硬编码魔数→命名常量
- injection_detector.py: `10`→`_SCAN_TIME_WARN_MS`
- evaluator.py: `4.0`→`_LOW_SCORE_THRESHOLD`，`2.0`→`_VERY_LOW_SCORE_THRESHOLD`
- provider.py: `30.0`/`100`/`20`→`_HTTP_TIMEOUT`/`_HTTP_MAX_CONNECTIONS`/`_HTTP_MAX_KEEPALIVE`
- market/service.py: `10`→`_MAX_FINDINGS_DISPLAY`(2处)
- scanner.py: `4`→`_DEFAULT_MAX_WORKERS`
- detector.py: `20`→`_LEAK_PREVIEW_LEN`
- statistics.py: `0.05`→`_DEFAULT_ALPHA`(2处)

## [v33.3.0] - 2026-07-14

### Fixed (第十八轮成熟度循环 R18: v33.2→v33.3 — P0安全+P1bug修复+P3优化)

#### P0安全修复
- Playground API异常信息泄露: `str(e)`→通用错误消息+`logger.exception()`记录详情
- Playground CORS通配符: `localhost:*`→固定端口列表(5173/3000/8080)

#### P1核心修复
- market/deploy.py ValueError格式化bug: `f"模板 %s 不在灰度发布中", id`→`f"模板 {id} 不在灰度发布中"`(2处)
- cli_helpers.py determine_exit_code逻辑bug: error_severity无作用→high/critical=1, medium=2, low/info=0
- provider.py全局状态线程安全: httpx AsyncClient延迟初始化添加双重检查锁(threading.Lock)
- evaluator.py维度ID格式: "D1"→"D01"自动补零匹配+文档明确ID格式
- evaluator.py docstring版本号: "v10"→移除过时版本号+"D1-D62"→"D01-D62"

#### P3优化
- RiskLevel比较O(n)→O(1): 预计算_RANK字典替代每次构建order列表(与Severity保持一致)
- server.py重复代码: 提取`_build_context()`消除api_compile和ws_compile中CompileContext构造重复
- server.py docstring更新: 补充lint/scan/evaluate/templates/version端点说明

### Added
- 新增evaluator维度ID短格式测试: "D1"/"D2"/"D3"自动补零为"D01"/"D02"/"D03"
- 新增determine_exit_code medium/critical场景测试
- 测试总数从554→557(+3)

## [v33.2.0] - 2026-07-14

### Fixed (第十七轮成熟度循环 R17: v33.1→v33.2 — P2/P3级别改进+测试覆盖)

#### P2增强
- evaluator正则预编译: 内部`import re`移到模块级
- evaluator `_count_pattern` bug修复: 单参数→`*patterns`可变参数
- P006敏感信息脱敏: findings.details.matches中API Key明文→REDACTED
- Severity比较O(n)→O(1): `__ge__`/`__gt__`预计算_RANK字典替代每次构建order列表
- InjectionDetector双重扫描优化: 逐行+全文→单次全文扫描+_find_line_number定位
- RuleLoader Severity比较bug修复: `rule.severity.value > existing.severity.value`(字符串比较)→`rule.severity > existing.severity`(枚举比较)

#### P3优化
- 清理未使用import: compiler/lexer.py移除`from typing import NoReturn`
- 精确化类型标注: `_CHECKERS`/`_CHECKERS_EXTENDED`/`_CHECKERS_P021_P030`从`list[Any]`→`list[_CheckerFn]`(Callable[[str], Finding | None])

### Added
- 新增test_evaluator.py: 17个evaluator测试(评估模板/评估报告/维度分数/维度API)
- 新增test_fixer.py: 18个fixer测试(P005/P006/P016修复逻辑+FixResult+dry_run)
- 新增test_rule_loader.py: 22个rule_loader测试(规则集/加载/过滤/自定义规则/冲突处理)
- 测试总数从497→554(新增57个测试)

## [v33.1.0] - 2026-07-14

### Fixed (第十六轮成熟度循环 R16: v33.0→v33.1 — P0崩溃+安全修复)

#### P0紧急修复
- 修复CLI `ab-test`命令NameError: `get_cost_tracker()`未导入导致崩溃
- 修复CLI `evaluate`命令AttributeError: `dimension_scores`属性不存在(应为`scores`)
- 修复Playground `/api/evaluate`接口字段不匹配: `result.dimensions`→`result.scores`
- 修复Playground CORS安全: 限制为localhost源+关闭`allow_credentials`(修复CSRF风险)
- 实现断言引擎ReDoS防护: 响应长度截断50000字符+RecursionError捕获+移除未使用signal import
- Levenshtein距离长度保护: max_len=5000截断

#### P1核心修复
- RuleLoader规则集(recommended/strict/huawei-cloud)补充P021-P030规则
- evaluator.py文档注释修正: "52个维度"→"62个维度"

## [v33.0.0] - 2026-07-14

### Added (第十五轮成熟度循环 R15: v32→v33)

#### Prompt断言/期望系统
- 新增 `assertion/` 模块: types.py + engine.py 策略模式架构
- 8种AssertType: contains/not-contains/regex/json_schema/similarity/llm-rubric/latency/cost
- AssertionEngine: 策略模式注册表 + evaluate_batch批量评估 + Levenshtein距离
- CLI `evaluate` 子命令: --target/--dimensions/--categories/--threshold/--format/--output
- CLI `assert` 子命令: --response/--config/--format
- 安全防护: 禁止exec/eval + 正则ReDoS防护 + JSON Schema深度限制
- 参考: promptfoo assert架构 + langfuse evaluation

#### Lint规则扩展 P021-P030
- 10条新Lint规则(P021-P030): 编码混淆/模板注入标记/指令冲突/示例与指令不一致/输出长度未指定/缺少错误恢复指引/文化敏感内容/链式指令缺失/变量未转义/过度依赖
- `_extract_ngrams` 中文bigram词重叠匹配算法
- P017/P023冲突降级: 同时触发时P017降级为LOW
- knowledge型模板豁免P025/P028/P030
- P025/P026/P029自动修复: 追加输出长度/错误恢复/输入校验
- 总计30条Lint规则(原20条)

#### 模板市场安全门禁增强
- MarketService.run_security_scan: 真实InjectionDetector调用
- MarketService.run_lint: 真实PromptLinter调用
- MarketService.check_security_gate: 安全扫描+Lint最低分70分门禁
- SECURITY_GATE_MIN_LINT_SCORE/SECURITY_GATE_MAX_HIGH_FINDINGS/SECURITY_GATE_MAX_CRITICAL_FINDINGS

#### VS Code扩展增强 v0.2.0
- CodeLensProvider: Prompt Score/issue数/Evaluate按钮
- QuickFixProvider: P005/P016/P006/P025/P026/P029自动修复
- SideBar TreeDataProvider: 规则分组树形展示
- 新增命令: evaluateActiveFile / showLintScore / fix

#### Playground评估Tab
- POST /api/evaluate端点: 62维度评估 + 维度分数
- 评估Tab: SVG雷达图 + 维度得分列表 + 综合评分
- evalTimer debounce 1500ms

#### 测试
- 67条断言系统测试 + 55条P021-P030测试 + 8条市场门禁测试
- 总计497个测试全通过

## [v32.0.0] - 2026-07-13

### Added (第十四轮成熟度循环 R14: v31→v32)

#### 对抗性红队探测引擎
- 新增 `redteam/` 模块: Probe/Detector/Exploration/Report 四层架构
- 5种Probe探测器: 提示注入/越狱/编码绕过/多轮诱导/敏感泄露(各5个探测输入)
- 3种Detector检测器: 泄露检测(密钥/连接串/系统提示)/合规检测/拒绝检测
- ExplorationOrchestrator: 离线模式(run_offline)+在线模式(run_with_provider)
- RedTeamReport: 漏洞率/风险等级(4级)/详细探测结果/摘要
- CLI `redteam` 命令: --target(离线)/--provider(在线)/--probes/--format json
- 参考: garak probe/detector架构 + promptfoo redteam策略

#### D53-D62评估器真实评分逻辑
- 10个维度从固定值(5.0)改为基于文本特征的真实计算
- D53 Lint前置质量/D54 国际化/D55 真实API/D56 CLI完备度
- D57 Playground/D58 CI/CD/D59 模板类型感知/D60 FM v3/D61 VS Code/D62 引导

#### Playground生产级改造
- CSS变量暗色/亮色主题系统(localStorage+系统偏好检测)
- Compile/Lint/Scan三Tab切换
- Scan Tab: 安全扫描面板(15条INJ规则可视化)
- 后端新增 POST /api/scan 端点(InjectionDetector集成)
- 主题切换按钮(🌙/☀️)

#### Provider基础设施
- httpx共享AsyncClient连接池(max_connections=100)，消除每次新建Client
- `_make_simulated_result` 从OpenAIProvider上移至BaseProvider，消除跨类调用
- A/B测试CLI端到端打通: ParallelEngine.run()+结果表格+JSON输出
- 新增 `prompt-cli serve` 命令(--host/--port/--reload)

### Fixed
- evaluator.py文档修正: "52维度"→"62维度"

### Changed
- CLI子命令: 8→10个(新增redteam/serve)
- 测试总数: 337→367(新增30个红队测试)
- Provider: httpx连接池复用(性能提升)

## [v31.0.0] - 2026-07-13

### Added (第十三轮成熟度循环 R13: v30→v31)

#### HuaweiProvider真实API调用
- 实现华为云ModelArts/盘古API真实调用(X-Auth-Token认证)
- 降级模拟策略: SIMULATED_MODE下自动降级
- 新增pangu-nlp/pangu-vision/qwen-72b定价

#### AliyunProvider独立Provider
- 新增AliyunProvider(通义千问dashscope API)
- ProviderType新增DEEPSEEK枚举，Aliyun不再映射到DeepSeek
- qwen-max/qwen-plus/qwen-turbo/qwen-long定价

#### 安全扫描规则扩展(5→15条)
- INJ-006 间接注入(OWASP LLM01, CRITICAL)
- INJ-007 越狱攻击(OWASP LLM02, CRITICAL)
- INJ-008 多轮攻击(OWASP LLM06, HIGH)
- INJ-009 编码绕过(OWASP LLM02变体, HIGH)
- INJ-010 多语言注入(中文变体, HIGH)
- INJ-011 系统提示泄露(OWASP LLM07, HIGH)
- INJ-012 输出操纵(OWASP LLM05, MEDIUM)
- INJ-013 权限提升(OWASP LLM08, HIGH)
- INJ-014 供应链注入(OWASP LLM03, MEDIUM)
- INJ-015 情感操纵(OWASP LLM02变体, MEDIUM)

#### 13个新场景模板
- 华为云prompt模板(e15-e18): CCE运维/GaussDB优化/ModelArts开发/DEH规划
- 鸿蒙模板(e5-e10): Stage模型/DataShare/Form卡片/AVSession/NEXT迁移/ArkUI-X
- 国产化模板(domestic_infra/e1-e3): 鲲鹏ARM/昇腾NPU/openEuler运维

#### Linter模板类型感知增强
- knowledge型新增排除: P004(过长)/P006(敏感)/P015(约束过多)/P016(歧义)
- 9条规则豁免(从5条扩展)，知识文档合理豁免
- Lint评分: 74.0→84.9/100 (+14.7%)

#### Playground Lint可视化
- SVG环形评分仪表盘(80+绿/60+黄/<60红)
- Lint问题列表(按严重级别着色)
- debounce 800ms自动Lint

#### 版本号动态注入
- CLI/Playground/HTML报告: 从__version__动态读取
- 新增 GET /api/version 端点
- 消除所有硬编码版本号

### Fixed
- evaluator.py D40: 移除未定义变量length引用(NameError崩溃修复)
- TTL测试稳定性: sleep 0.01→0.05

### Changed
- 模板总数: 38→51(新增13个)
- 测试总数: 294→337(新增43个A/B测试)
- 安全扫描规则: 5→15条(OWASP LLM Top 10对齐)
- Provider枚举: 4→5种(ALIYUN/DEEPSEEK独立)

## [v30.0.0] - 2026-07-13

### Added (第十二轮成熟度循环 R12: v29→v30)

#### Linter模板类型感知
- 38个场景模板新增 `template_type` 字段: 34个 knowledge + 4个 prompt
- Linter自动检测 template_type: knowledge型排除 P001/P002/P018/P019/P020 规则
- CLI lint 新增 `_detect_template_type()` 辅助函数，自动读取YAML front matter
- Lint评分大幅提升: 61.8→72.4/100 (+17%)，问题数 290→165 (-43%)

#### 评估框架v10
- 58→62维度(D59-D62): 模板类型感知/FM v3合规/VS Code扩展/引导系统

#### Playground增强
- 新增 GET /api/templates 端点: 返回可用模板列表
- 新增 POST /api/lint 端点: 对提示词文本执行Lint检查
- 前端可浏览模板+实时Lint反馈

#### Lint评分回写
- 38个场景模板 front matter 已回写实际 lint_score
- `scripts/update_lint_scores.py`: 支持 template_type 的评分回写脚本

### Fixed
- 修复TTL测试偶发失败: `time.sleep(0.01)`→`0.05`，Windows稳定性提升

### Changed
- `scripts/fix_p001_role.py`: P001角色定义修复脚本
- 版本号: v29.0.0→v30.0.0

## [v29.0.0] - 2026-07-13

### Added (第十一轮成熟度循环 R11完成 + R11补充)

#### 专业级HTML报告生成器
- `report/html_reporter.py`: 安全扫描+Lint双模HTML报告
- SVG圆环图(风险分布)+评分仪表盘+暗色/亮色主题切换
- 按严重级别分组折叠面板+详情展开+修复建议
- XSS安全转义+响应式布局

#### 条件编译性能基准测试
- `benchmarks/__init__.py`: 11项微基准(Lexer/Parser/Evaluator/Renderer/端到端)
- LRU缓存命中vs未命中对比+5种模板复杂度缩放测试
- BenchSuite+BenchResult数据结构+JSON序列化
- CLI入口: `python -m ai_prompt_toolkit.benchmarks.compile_benchmark`

#### 鸿蒙4个新场景模板
- `harmonyos/e1_arkts_ui.md`: @State/LazyForEach/生命周期/@Builder/多设备适配
- `harmonyos/e2_distributed.md`: 分布式数据同步/任务调度/设备发现/流转状态
- `harmonyos/e3_performance.md`: 渲染优化/内存泄漏/启动优化/图片优化/线程模型
- `harmonyos/e4_security.md`: 权限管理/HUKS加密/沙箱/网络安全

#### YAML Front Matter v3升级
- `frontmatter/__init__.py`: FrontMatterV3 Schema + v2→v3升级工具
- v3新增: i18n_status(6枚举)/market_status(7枚举)/lint_score(0-100)/locale/translation_key
- CLI新增 `upgrade-fm` 命令: `prompt-cli upgrade-fm -t _scenarios --dry-run`
- 38个场景模板全部升级至v3

#### VS Code Prompt Lint扩展
- `vscode-prompt-lint/`: VS Code扩展完整项目(TypeScript)
- 3个命令: lintActiveFile/scanActiveFile/compileActiveFile
- 自动Lint: onSave + onType(可选)触发
- 参考vscode-markdownlint轻量模式架构

#### 新用户3步引导v3
- `onboarding/__init__.py`: Step1初始化→Step2编译→Step3检查
- CLI新增 `init` 命令: `prompt-cli init -t ./my-project`
- 零配置启动+幂等设计+即时反馈

### Fixed
- 修复renderer.py else分支bug: CONDITIONAL节点else-body未正确展开
- 修复parser.py `in`关键字误匹配: `industry`被解析为`in`+`dustry`，改用`\b`词边界
- 修复lint命令HTML输出格式支持(--format html)和--output选项

### Changed
- lint命令新增`--output`选项和`html`格式支持
- scan命令HTML报告现在使用专业级报告器(SVG圆环图+主题切换)
- 测试总数: 164→294个

## [v28.0.0] - 2026-07-13

### Added (第十一轮成熟度循环 R11: v27→v28 — "代码→产品"质变)

#### CLI深度集成 (F2)
- `cli_helpers.py`: 路径校验/JSON上下文加载/YAML配置/模板发现/报告写入/HTML报告生成/退出码判定
- compile子命令: 调用完整编译管线(Lexer→Parser→Renderer)+输出+报告+退出码语义
- scan子命令: 调用InjectionDetector注入检测+批量扫描+CLI/JSON/HTML三种输出格式
- lint子命令: 调用PromptLinter全部20条规则+质量评分+自动修复+批量模式
- 退出码: 0=成功 1=有发现项 2=参数错误 3=引擎异常

#### Provider真实API调用 (F1)
- httpx.AsyncClient连接池+指数退避重试(1/2/4/8/16s，最多5次)
- 429 Rate Limit处理: retry-after头+指数退避
- CostTracker费用累计控制(PROMPT_CLI_COST_LIMIT默认$10)
- SIMULATED_MODE降级: 无PROMPT_CLI_REAL_API环境变量时自动降级为模拟响应
- AliyunProvider→DeepSeekProvider(更符合赛事场景)
- Provider验证: OpenAI(sk-) / Anthropic(sk-ant-) / DeepSeek / HuaweiCloud

#### 条件编译Playground Web UI (F3)
- FastAPI后端: POST /api/compile + WebSocket /ws/compile + GET /api/context-schema
- 前端: 左右分栏编辑器+debounce 500ms自动编译+Tailwind CSS暗色主题
- 参考Handlebars Playground实时预览模式
- 上下文变量编辑(模型/语言/行业)

#### 评估框架v9 (F7)
- 54→58维度
- D55: 真实API调用能力
- D56: CLI完备度
- D57: Playground可用性
- D58: CI/CD集成度

#### CI/CD流水线集成 (F5)
- `.github/workflows/quality-gate.yml`: Python 3.10/3.11/3.12矩阵测试
- PR增量检查+main全量检查
- prompt-cli lint + scan质量门禁

### Changed
- CLI子命令从骨架echo升级为端到端引擎集成
- Provider从模拟响应升级为httpx真实API调用+SIMULATED_MODE降级

## [v27.0.0] - 2026-07-13

### Added (第十轮成熟度循环 R10: v26→v27)

#### 核心质变：设计完备→工具链可运行

- 包名从 `prompt-toolkit` 重命名为 `ai-prompt-toolkit`（修复与第三方库冲突）
- 修复 `pyproject.toml` build-backend（`setuptools.build_meta`）

#### 条件编译引擎 (F1) — 7个Python文件
- `compiler/types.py`: Token/ASTNode/CompileResult/CompileContext类型
- `compiler/lexer.py`: Lexer词法分析器（5种Token类型）
- `compiler/parser.py`: Parser语法分析器（递归下降，嵌套深度≤3）
- `compiler/evaluator.py`: Evaluator条件求值器（10种运算符+副作用检测）
- `compiler/renderer.py`: Renderer渲染器
- `compiler/cache.py`: CompileCache（LRUCache+SHA-256键+TTL 1h）

#### 安全扫描器 (F3) — 5个Python文件
- `security/types.py`: Finding/ScanResult/RiskLevel类型
- `security/injection_detector.py`: 8条注入规则（INJ-001~008）
- `security/inheritance_auditor.py`: 继承链审计（6类问题检测）
- `security/scanner.py`: Scanner主入口+增量扫描+3种输出格式

#### Prompt Linter (F4) — 4个Python文件
- `linter/rules.py`: 20条质量规则（P001-P020，4大类）
- `linter/linter.py`: PromptLinter主类+LintResult+FixAction
- `linter/rule_loader.py`: RuleLoader（3种规则集+自定义规则+冲突处理）
- `linter/fixer.py`: Fixer自动修复（P005/P006/P016+dry-run+diff）

#### A/B测试框架 (F2) — 6个Python文件
- `ab_test/types.py`: TestConfig/ModelResult/StatReport类型
- `ab_test/provider.py`: 4个Provider（OpenAI/Anthropic/HuaweiCloud/DeepSeek）
- `ab_test/engine.py`: ParallelEngine并行执行引擎
- `ab_test/statistics.py`: 5种统计方法（Shapiro-Wilk/t-test/Mann-Whitney U/Cohen's d/CI）
- `ab_test/recommender.py`: Recommender推荐器

#### i18n国际化框架 (F5) — 6个Python文件
- `i18n/types.py`: BCP 47 Locale+TranslationEntry+CoverageReport
- `i18n/glossary.py`: 术语表（YAML+华为云18个领域术语）
- `i18n/fallback.py`: 回退链（10语言+PROMPT_LANGUAGE环境变量）
- `i18n/resource.py`: JSON资源文件管理+覆盖率统计
- `i18n/translation.py`: 翻译引擎+缓存+人工审校保护
- `i18n/manager.py`: I18nManager主类+generate()+get_translation()

#### 模板市场v2 (F6) — 4个Python文件
- `market/types.py`: Template+Review+DeployConfig+LifecycleManager状态机
- `market/review.py`: ReviewPipeline（门禁+14天提醒+21天关闭）
- `market/deploy.py`: DeployManager（灰度5%→25%→50%→100%+自动回滚）
- `market/service.py`: MarketService主服务+JSON持久化

#### CLI统一入口
- `cli.py`: 6个子命令（compile/ab-test/scan/lint/i18n/market）
- `output.py`: rich集成（彩色输出+进度条）
- `types.py`: 通用类型（Severity/Finding/BaseReport）

#### 评估框架升级
- 52维度→54维度（新增D53 Lint前置质量+D54 国际化完备度）
- `evaluator.py`: evaluate_template()函数+EvaluationReport

#### 测试
- 164个单元测试全通过（compiler 47+security 23+linter 47+i18n 22+market 15+evaluator 10）
- 测试覆盖率：compiler≥80%, security≥80%, linter≥80%

#### 数据文件
- `_i18n/locales/zh-CN/templates.json`: 10个中文模板
- `_i18n/locales/en-US/templates.json`: 10个英文模板

### Changed
- Linter中文正则修复：P001角色检测/P005长度/P008权限/P012冗余/P016歧义
- 包名 `prompt-toolkit` → `ai-prompt-toolkit`（避免与Jonathan Slenders的终端UI库冲突）

## [v15.0.0] - 2026-05-29

### Added (第十三轮深度迭代M1-M10批次 2026-05-29)

#### SDK参考实现(M1)
- 新增 `_iterations_v15/_sdk/python/prompt_engine.py`：Python SDK完整实现(PromptEngine+ScenarioLoader+Evaluator+Combinator+Builder)
- 新增 `_iterations_v15/_sdk/typescript/prompt-engine.ts`：TypeScript SDK完整实现(同架构)
- 新增 `_iterations_v15/_sdk/docs/sdk_api_docs.md`：SDK API文档+使用示例

#### UPPL编译器原型(M2)
- 新增词法分析器(14 Token+8状态+状态机)、语法分析器(21 AST节点+EBNF)、3目标编译器(NL/JSON/Agent)

#### 提示词运行时原型(M3)
- 新增5阶段流水线+沙箱(进程隔离+资源限制+网络白名单+3安全等级)+监控(追踪+指标+告警)

#### 行业联盟倡议(M4)
- 新增PEA联盟组织架构(理事会+TC+EC+CC+SC)+运营机制(6类活动)+4级会员体系+IP策略

#### 影响力度量(M5)
- 新增5类15项指标+Dashboard数据模型+综合分数算法+报告模板+基线17.8/100

#### 3年路线图(M6)
- 新增v15→v18(2026-2029)路线图+里程碑+资源规划(67FTE+$12.7M)

### Changed
- 评估框架：24维度→26维度(新增实现完整度+影响力指数)
- 子维度：96→104(+8)
- 设计原则：30→32(+实现验证+影响度量)
- 反模式：30→32(+纸上谈兵+影响空心)
- 门禁：19→21(+实现门禁+影响力门禁)
- 闭环：11→13(+实现闭环+影响力闭环)
- 级别：满分标准学术引领级→满分实现影响力级

---

## [v12.0.0] - 2026-05-29

### Added (第十轮深度迭代J1-J10批次 2026-05-29)

#### 应力测试(J1)
- 新增 `_iterations_v12/_stress_test/stress_test_framework_v1.md`：4类38用例应力测试框架+18防御指令
- 应力鲁棒度基线10.00(模型切换稳定性+输入异常容忍度+并发一致性+版本兼容性)

#### 未来防御(J2)
- 新增 `_iterations_v12/_future_proof/future_proof_v1.md`：GPT-5/Claude-4/Gemini-2预适配+能力抽象层10接口+指令弹性4级
- 未来就绪度基线10.00(模型预适配覆盖+指令弹性度+迁移路径完备+前瞻趋势覆盖)

#### 跨域迁移(J3)
- 新增 `_iterations_v12/_cross_domain/cross_domain_v1.md`：法律/医疗/教育/科研4领域×5场景+7共性模式

#### 历史归档(J4)
- 新增 `_iterations_v12/_archive/evolution_archive_v1.md`：v2.9→v12.0.0进化轨迹+18决策记录+版本矩阵

#### 终极文档(J5)
- 新增 `_iterations_v12/_manual/complete_manual_v1.md`：完全手册7章

#### 满分守护(J6)
- 新增 `_iterations_v12/_guardian/guardian_mechanism_v1.md`：守护机制+CI+基线锁定+3级审批+仪表盘

#### 方法论v9.0
- 新增 `_iterations_v12/methodology/methodology_v9.md`：26原则+26反模式+20维度80子维度+15门禁+9闭环

#### 调研
- 新增 `_iterations_v12/research/R12-01_next_gen_llm_prediction.md`
- 新增 `_iterations_v12/research/R12-02_cross_domain_prompt_engineering.md`

### Changed
- 评估框架：18维度→20维度(新增应力鲁棒度+未来就绪度)
- 子维度：72→80(+8)
- 设计原则：24→26(+应力优先+未来适配)
- 反模式：24→26(+脆弱满分+模型锁定)
- 门禁：13→15(+应力门禁+未来门禁)
- 闭环：8→9(+满分守护闭环)
- 行业覆盖：5→9(+法律/医疗/教育/科研跨域)

### Fixed
- 补强输入异常防御(null/编码/递归/矛盾/注入)
- 补强并发写冲突防御(乐观锁+快照读+令牌桶限流)
- 补强版本冲突防御(向上引用降级+三方合并)
- 完善模型切换格式归一化层

---

## [v5.0.0] - 2026-05-29

### Added (第三轮深度迭代C10-C14批次 2026-05-29)

- 新增 `_iterations_v5/adaptation/deepseek_v3_cot_selfcorrect.md`：DeepSeek-V3 CoT+自纠错组合适配指令(迭代47)
- 新增 `_iterations_v5/adaptation/qwen_structured_json_mode.md`：Qwen-Max结构化输出+JSON模式适配指令(迭代48)
- 新增 `_iterations_v5/adaptation/kimi_long_context_strategy.md`：Kimi长上下文适配策略(迭代49)
- 新增 `_iterations_v5/adaptation/adaptation_matrix_v3.md`：7模型×55场景完整适配矩阵v3.0(迭代50)
- 新增 `_evaluations_v5/judge_templates/judge_template.md`：LLM-as-Judge评估脚本模板(迭代51)
- 新增 `_evaluations_v5/regression/core_scenario_test_cases.md`：核心场景回归测试用例36个(迭代52)
- 新增 `_evaluations_v5/ab_tests/ab_test_config.yaml`：A/B测试配置模板+5个预定义测试(迭代53)
- 新增 `_evaluations_v5/reports/evaluation_v4_8_0.md`：八维度第三次全量评估(92.5分)(迭代54)
- 新增 `_evaluations_v5/reports/convergence_analysis.md`：分数趋势图与收敛分析(迭代55)
- 新增 `_iterations_v5/evaluations/frontier_tech_supplement.md`：前沿技术适配补充(Agent-First/PoT/Active-Prompt)(迭代56)
- 新增 `_iterations_v5/evaluations/industry_scenario_supplement.md`：行业专用场景模板(金融/医疗/电商)(迭代57)
- 新增 `_iterations_v5/evaluations/constraint_supplement.md`：全体系约束补充22项(迭代58)
- 新增 `_iterations_v5/evaluations/structure_integrity_verification.md`：55场景5要素100%覆盖验证(迭代59)
- 新增 `_evaluations_v5/reports/evaluation_v4_9_0_final.md`：八维度第四次全量评估(96.5分)(迭代60)
- 新增 `_evaluations_v5/reports/integrity_regression_check.md`：引用完整性回归276/276通过(迭代61)
- 新增 `_evaluations_v5/reports/convergence_final_report.md`：收敛判定报告(迭代62)
- 新增 `_iterations_v5/methodology/design_principles.md`：设计原则v2.0(8→12条)
- 新增 `_iterations_v5/methodology/anti_patterns.md`：反模式v2.0(8→12种)
- 新增 `_iterations_v5/methodology/evaluation_framework.md`：八维度评估框架v2.0
- 新增 `_iterations_v5/methodology/optimization_process.md`：优化流程v2.0(三轮螺旋+五元组)
- 新增 `_iterations_v5/traces/C10_trace.json ~ C14_trace.json`：C10-C14批次追溯记录
- 新增 `_iterations_v5/C10_C14_execution_report.md`：C10-C14批次执行报告
- 新增 `_iterations_v5/final_audit_report.md`：v5.0.0最终验收报告(16/16通过)
- 新增 `_iterations_v5/release_v5_0_0.md`：v5.0.0发布报告

### Changed (C10批次-国产模型深度适配 迭代47-50)

- **04_代码审查场景A**：添加DeepSeek-V3 CoT+自纠错组合指令(5步推理+4项自检+JSON强制)
- **08_安全审计场景A**：添加DeepSeek-V3 CoT+自纠错(攻击者思维6步+4项自检)
- **09_性能优化场景B**：添加DeepSeek-V3 CoT+自纠错(方法论5步+4项自检)
- **01_需求分析场景A**：添加Qwen-Max JSON模式+结构化输出指令(JSON Schema+5步中文推理)
- **02_架构设计场景A**：添加Qwen-Max结构化输出+JSON模式(6质量属性+风险矩阵)
- **03_编码规范场景A**：添加Qwen-Max编码规范JSON输出(命名+结构+示例)
- **02_架构设计场景A**：添加Kimi长文档分析策略(200K全量注入+4阶段分析+联网搜索)
- **_adaptation_matrix.md**：v2.0→v3.0，7模型×55场景完整适配矩阵+适配效果评分

### Changed (C12批次-维度逼近优化 迭代56-59)

- **05/06/07/10/11场景**：补充Agent-First/PoT/Active-Prompt前沿技术适配指令
- 新增金融代码审查/医疗安全审计/电商性能优化3个行业专用场景模板
- 全体系补充22项缺失约束(安全3项+性能10项+合规9项)
- 10个场景补充验收标准，55场景5要素100%覆盖

## [v4.6.0] - 2026-05-29

### Added (第三轮深度迭代C7-C9批次 2026-05-29)

- 新增 `_workflows/requirement_test_deploy.yaml`：需求→测试计划→部署配置工作流(01→05→06)
- 新增 `_workflows/security_hardening_verify.yaml`：安全审计→安全编码→安全测试工作流(08→03→05)
- 新增 `_workflows/incident_response.yaml`：故障响应→安全排查→复盘工作流(07→08→11)
- 新增 `_workflows/capacity_optimize_verify.yaml`：容量分析→代码优化→性能验证工作流(09→03→05)
- 新增 `_workflows/financial_audit_deploy.yaml`：金融行业专用工作流(08金融→06金融→07金融)
- 新增 `_industries/financial/` 目录：金融行业3文件(checklist+glossary+compliance)
- 新增 `_industries/healthcare/` 目录：医疗行业3文件(checklist+glossary+compliance)
- 新增 `_industries/ecommerce/` 目录：电商行业3文件(checklist+glossary+compliance)
- 新增 `_industries/saas/` 目录：SaaS行业3文件(checklist+glossary+compliance)
- 新增 `_industries/gaming/` 目录：游戏行业3文件(checklist+glossary+compliance)
- 新增 `_iterations_v5/traces/C7_trace.json`：C7批次6次迭代追溯
- 新增 `_iterations_v5/traces/C8_trace.json`：C8批次5次迭代追溯
- 新增 `_iterations_v5/traces/C9_trace.json`：C9批次3次迭代追溯
- 新增 `_iterations_v5/C7_C9_execution_report.md`：C7-C9批次执行报告
- 新增 `_evaluations_v5/reports/mid_term_evaluation_v4_6_0.md`：八维度中期评估报告(89.2分)

### Changed (C7批次-工作流深度编排 迭代33-38)

- **review_fix_verify.yaml**：v1.0→v2.0，新增transformation_rules(审查→修复→验证完整字段映射+4类测试生成规则+4条验证规则)
- **requirement_design_coding.yaml**：v1.0→v2.0，新增PRD→架构约束(5种质量属性)→编码规范(4种架构选择)完整映射链

### Changed (C8批次-行业垂直化扩展 迭代39-43)

- 每行业含专项检查清单(PCI-DSS/HIPAA/高并发/多租户/反作弊等)
- 每行业含30个专业术语的中英文对照表
- 每行业含合规要求(中国法规+国际标准)及01-12号提示词集成指引

### Changed (C9批次-三维融合 迭代44-46)

- **00_项目提示词总览与使用指南**：v3.4→v3.5，新增六-A行业垂直化体系+六-B链式工作流索引(9条)

## [v4.3.0] - 2026-05-29

### Added (第三轮深度迭代C4-C6批次 2026-05-29)

- 新增 `_iterations_v5/traces/C4_trace.json`：C4批次8次迭代追溯
- 新增 `_iterations_v5/traces/C5_trace.json`：C5批次6次迭代追溯
- 新增 `_iterations_v5/traces/C6_trace.json`：C6批次4次迭代追溯
- 新增 `_iterations_v5/C4_C6_execution_report.md`：C4-C6批次执行报告

### Changed (C4批次-低分场景深度打磨 迭代15-22)

- **06_CI/CD场景E**：补充环境隔离矩阵(8维度)+配置差异清单(10项)+环境晋升流程图+质量门禁(17条)
- **10_文档沉淀场景D**：补充新人7天Onboarding计划(14项)+知识图谱模板+TOP20 FAQ(含严重度分级)
- **12_AI时代场景B**：深化为30项完整审查清单(安全10+正确8+性能6+可维护6)，每项含示例
- **11_项目管理场景D**：补充4大类风险框架(13子类)+量化矩阵(5维度加权)+5种应对策略库
- **03_编码规范场景C**：补充迁移决策树+风险矩阵(5维度)+增量迁移策略(5阶段)+兼容性8项
- **07_监控运维场景D**：补充On-Call分级SOP(4级+5步法)+MTTA/MTTR框架(5指标)+疲劳防治(8措施)
- **05_测试策略场景D**：补充契约定义模板+消费者驱动流程+Pact示例+Spring Cloud Contract示例
- **02_架构设计场景E**：补充API规范+BF决策树+前后端6维度契约+REST vs GraphQL决策矩阵

### Changed (C5批次-领域专家知识嵌入 迭代23-28)

- **08_安全审计**：嵌入OWASP Top10 2024(10项)+STRIDE威胁建模(6类)+CVE检索指令(6步)
- **09_性能优化**：嵌入USL通用可扩展性定律+Little's Law+Amdahl定律(含推论和应用实例)
- **04_代码审查**：嵌入SOLID原则审查清单(5项)+设计模式反模式检测(7项)+Clean Code 10条规则
- **06_CI/CD**：嵌入12-Factor App清单(12项)+GitOps原则(4条)+不可变基础设施+声明式部署
- **07_监控运维**：嵌入Google SRE四大支柱+SLI/SLO/SLA误差预算框架+Toil消除策略(7类)
- **02_架构设计**：嵌入AWS/Azure Well-Architected Framework六大支柱+演进式架构7原则

### Changed (C6批次-前沿技术融合 迭代29-32)

- **04_代码审查场景A**：添加Program-of-Thoughts(PoT)指令(3步+4适用场景)
- **08_安全审计场景A**：添加Active-Prompt指令(基于不确定性优先审查，4步+6级评分)
- **02_架构设计场景A**：添加Agent-First架构适配指令(4个Agent+协作策略)
- **全体系L1场景**：为04/06/07/08/09共9个L1场景添加结构化输出强制指令

## [v4.0.0] - 2026-05-28

### Added (第三轮深度迭代C1-C3批次 2026-05-29)

- 新增 `_iterations_v5/research/R3-C1-01_llm_as_judge_best_practices.md`：LLM-as-Judge评估最佳实践调研
- 新增 `_iterations_v5/research/R3-C1-02_domestic_models_capability.md`：国产大模型能力与适配调研
- 新增 `_iterations_v5/research/R3-C1-03_prompt_frontier_techniques.md`：Prompt前沿技术(PoT/Active-Prompt/APE/Agent-First)调研
- 新增 `_evaluations_v5/evaluation_framework_v5.md`：八维度评估框架v2.0.0（前沿技术适配度+行业垂直化覆盖度）
- 新增 `_evaluations_v5/llm_judge_templates.md`：LLM-as-Judge评估prompt模板集（6个维度模板）
- 新增 `_evaluations_v5/regression/test_case_index.md`：55场景回归测试用例索引（44个核心用例）
- 新增 `_evaluations_v5/ab_tests/ab_test_framework.md`：A/B测试框架设计文档
- 新增 `_evaluations_v5/baseline/baseline_v4_0_0.json`：v4.0.0八维度基线分数（加权总分80.5）
- 新增 `_evaluations_v5/reports/baseline_v4_0_0_report.md`：基线评估报告
- 新增 `_evaluations_v5/reports/low_score_scenarios_top15.md`：低分Top15场景识别+优化路线
- 新增 `_iterations_v5/model_profiles/qwen-max.yaml`：Qwen-Max详细模型画像
- 新增 `_iterations_v5/model_profiles/deepseek-v3.yaml`：DeepSeek-V3详细模型画像（含R1关联）
- 新增 `_iterations_v5/model_profiles/ernie-4.0.yaml`：ERNIE-4.0详细模型画像
- 新增 `_iterations_v5/model_profiles/kimi.yaml`：Kimi详细模型画像
- 新增 `_iterations_v5/adaptation/domestic_model_matrix_v5.md`：55场景×4国产模型适配策略矩阵
- 新增 `_iterations_v5/traces/C1_trace.json`：C1批次6次迭代追溯
- 新增 `_iterations_v5/traces/C2_trace.json`：C2批次4次迭代追溯
- 新增 `_iterations_v5/traces/C3_trace.json`：C3批次4次迭代追溯

### Changed (第三轮深度迭代C1-C3批次 2026-05-29)

- **04_代码审查与质量保障提示词**：场景A添加国产模型适配指令（DeepSeek中文CoT优化+Qwen结构化输出）
- **08_安全审计与合规检查提示词**：场景A添加国产模型适配指令（DeepSeek+ERNIE合规增强+Qwen）
- **01_需求分析与产品规划提示词**：场景A添加中文推理模式优化指令（Qwen深度推理+DeepSeek+Kimi长文档）
- **_adaptation_matrix.md**：v1.0.0→v2.0.0，国产模型从整体拆分为Qwen/DeepSeek/ERNIE/Kimi 4列，策略矩阵扩展为7模型列

### Added

- 新增 `_iterations/traces/B10_trace.json`：B10批次(最终收敛与固化)7次迭代追溯记录(迭代58-64)
- 新增 `_iterations/convergence_report.md`：迭代收敛报告，包含64次迭代摘要、六维度三次评估对比、收敛判定结论
- 新增 `_iterations/methodology/design_principles.md`：提示词设计原则文档（8条原则，含调研依据和迭代验证）
- 新增 `_iterations/methodology/anti_patterns.md`：提示词反模式清单（8种反模式，含修复方案）
- 新增 `_iterations/methodology/evaluation_framework.md`：六维度评估框架（维度定义/评分标准/评估流程/收敛判定）
- 新增 `_iterations/methodology/optimization_process.md`：提示词优化流程（螺旋闭环/8步执行/批次管理/追溯规范）
- 新增 `_iterations/final_audit_report.md`：最终验收报告

### Changed

- **04_代码审查与质量保障提示词**：
  - 场景C/D补充5要素结构表+约束显式声明
- **05_全维度测试策略提示词**：
  - 场景C/D/E补充5要素结构表+CoT指令
- **06_CI_CD与自动化部署提示词**：
  - 补充DevOps工作方式描述+安全约束显式声明
- 全体系CoT/Few-shot/ReAct/Self-Correction/Prompt-Chaining/Meta-Prompting/Directional-Stimulus标注统一为HTML注释块格式：`<!-- 模式名:描述 -->`
- **iteration_state.json**：版本号更新至v4.0.0，completed_iterations=64，B10批次completed=7，收敛状态全部converged=true

### Fixed

- 55个场景模板5要素结构完整性100%覆盖（迭代61验证通过）
- 全体系引用完整性回归检查通过（迭代62验证无断链/锚点错误/反向引用缺失）

## [v3.7.0] - 2026-05-28

### Added

- 新增 `_iterations/research/RSH-B7-1_react_meta_chaining.md`：B7批次增量调研（ReAct/Prompt Chaining/Meta-Prompting/Self-Correction/Directional Stimulus/Prompt Caching最佳实践）
- 新增 `_iterations/research/B9_evaluation_comparison.md`：B9批次六维度二次全量评估对比报告
- 新增 `_iterations/traces/B7_trace.json`：B7批次(最佳实践融合)7次迭代追溯记录
- 新增 `_iterations/traces/B8_trace.json`：B8批次(综合质量提升)7次迭代追溯记录
- 新增 `_iterations/traces/B9_trace.json`：B9批次(收敛验证与微调)7次迭代追溯记录

### Changed

- **04_代码审查与质量保障提示词**：
  - 场景A添加ReAct模式指令：Thought→Action→Observation→Fix循环
- **08_安全审计与合规检查提示词**：
  - 场景A添加ReAct攻击者思维循环：假设攻击路径→验证可达性→确认风险→纵深防御
- **09_性能压测与优化提示词**：
  - 场景B添加Prompt Chaining指令：瓶颈定位→根因分析→优化方案→验证确认4子任务链
- **02_架构设计与技术选型提示词**：
  - 场景A添加Meta-Prompting指令：根据技术栈自动生成专用审查清单
  - 场景C添加微服务拆分决策框架(5步)和反模式清单(8种)
- **05_全维度测试策略提示词**：
  - 场景B添加Self-Correction+工具验证指令：覆盖率自检/边界补全/异常补全/P0验证
- **06_CI_CD与自动化部署提示词**：
  - 场景A添加Prompt Caching优化标注和CoT指令(6步+自纠错)
  - 场景E补充5要素结构表+CoT指令(5步)+多环境检查清单(12项4维度)
- **01_需求分析与产品规划提示词**：
  - 场景A添加Directional Stimulus Prompting：[PRD输出]方向性引导标记
- **10_技术文档与知识沉淀提示词**：
  - 场景A添加CoT指令(5步+完整性自检)
  - 场景D补充5要素结构表+Few-shot示例(项目结构段落+常见问题TOP10)
- **12_AI时代开发专项提示词**：
  - 深化角色设定(10年+OSCP/AI安全认证+4工作方式：威胁建模/零信任/持续监测/纵深防御)
  - 添加Prompt注入攻击类型分类表(8类攻击手法)
  - 添加防御策略矩阵(14策略×4防御层)
- **11_项目管理与迭代复盘提示词**：
  - 场景C补充复盘CoT流程(回顾→分析→提炼→行动4步)
  - 场景C补充复盘输出模板(数据总览+5Whys+鱼骨图+Start/Stop/Continue+行动计划)
- **03_编码规范与AI辅助开发提示词**：
  - 场景A添加CoT指令(5步+自纠错检查)
  - 场景C补充迁移风险检查清单(10项5维度)+回滚策略(4种)+兼容性验证方案(4种)
- **07_监控告警与运维保障提示词**：
  - 场景A添加CoT指令(6步+自纠错检查)
  - 场景C补充容量建模公式(5个)+扩缩容决策树+成本效率评估维度表(8项)

## [v3.6.0] - 2026-05-28

### Added

- 新增 `_iterations/traces/B4_traces.json`：B4批次(输出格式精确化)6次迭代追溯记录
- 新增 `_iterations/traces/B5_traces.json`：B5批次(检查清单全覆盖)6次迭代追溯记录
- 新增 `_iterations/traces/B6_traces.json`：B6批次(CoT/多轮/自我纠错模式)6次迭代追溯记录

### Changed

- **04_代码审查与质量保障提示词**：
  - 场景A补充结构化输出JSON模板(summary/issues/qualityScore/releaseRecommendation字段)
  - 场景A添加CoT指令：逐步分析(理解意图→识别问题→评估严重度→提供修复方案)
- **06_CI_CD与自动化部署提示词**：
  - 场景A补充Pipeline YAML结构化输出模板(7个job节点+阶段策略表+质量门禁)
  - 补充部署安全检查清单(密钥管理/网络策略/镜像安全/合规审计4维度14项)
- **07_监控告警与运维保障提示词**：
  - 场景A补充Prometheus告警规则YAML输出模板+Grafana Dashboard JSON模板
  - 补充监控覆盖度检查清单(四大黄金指标/业务指标/日志/链路追踪/告警5维度15项)
- **08_安全审计与合规检查提示词**：
  - 场景A补充安全审计报告结构化JSON模板(auditSummary/vulnerabilities/complianceGaps/hardeningPlan)
  - 场景A添加CoT指令：攻击者思维逐步分析(识别攻击面→STRIDE评估→构建攻击链→纵深防御)
- **09_性能压测与优化提示词**：
  - 场景A补充压测报告结构化JSON模板(benchmarkSummary/scenarios/optimizationSuggestions)
  - 场景B添加CoT指令：性能分析方法论(建立基线→识别瓶颈→假设验证→优化实施→效果确认)
  - 补充性能优化验证清单(基线对比/回归测试/资源监控/容量规划4维度12项)
- **01_需求分析与产品规划提示词**：
  - 场景D补充竞品分析矩阵输出模板(对比维度×竞品评分矩阵+权重+加权总分)
  - 场景A添加Few-shot CoT示例：完整的需求分析推理过程(6步从模糊需求到PRD)
- **03_编码规范与AI辅助开发提示词**：
  - 补充AI生成代码专项检查清单(安全审查/正确性验证/性能评估/可维护性4维度13项)
- **02_架构设计与技术选型提示词**：
  - 场景B添加自纠错指令：完成架构评审后自我检查(非功能需求/单点故障/扩展性/成本)
- **05_全维度测试策略提示词**：
  - 场景A添加多轮对话指令：4轮交互(确定范围→设计用例→补充边界→评估覆盖率)
- **11_项目管理与迭代复盘提示词**：
  - 补充项目健康度检查清单(进度/质量/风险/团队/沟通/交付6维度14项，含健康/预警/危险三级阈值)
- **12_AI时代开发专项提示词**：
  - 补充AI安全专项检查清单(Prompt注入/数据泄露/模型偏见/合规审计/可解释性5维度17项)

## [v3.5.0] - 2026-05-28

### Added

- 新增 `_iterations/research/evaluation_baseline.json`：六维度全量评估基线，覆盖01-12号文档55个场景模板
- 新增 `_iterations/traces/B1_traces.json`：B1批次(结构优化)6次迭代追溯记录
- 新增 `_iterations/traces/B2_traces.json`：B2批次(约束完备化)6次迭代追溯记录
- 新增 `_iterations/traces/B3_traces.json`：B3批次(角色设定深化)6次迭代追溯记录

### Changed

- **01_需求分析与产品规划提示词**：
  - 场景A新增5要素结构表(描述/输入/输出/检查清单/验收标准)和输出示例片段
  - 场景B新增5要素结构表
- **02_架构设计与技术选型提示词**：
  - 场景A新增结构化输出示例(架构总览表+技术选型对比矩阵)
  - 场景B新增结构化输出示例(架构瓶颈识别表+优化方案对比表)
- **03_编码规范与AI辅助开发提示词**：
  - 场景A新增Few-shot示例(用户注册功能完整代码+3类测试用例)
  - 场景D新增Few-shot示例(NoneType Bug完整修复流程)
- **04_代码审查与质量保障提示词**：
  - 核心约束新增第7条：安全审查约束(OWASP Top 10全量/L3审查/P0阻断)
  - 核心约束新增第8条：性能审查约束(N+1/连接池/GC/锁/退化>10%)
- **06_CI_CD与自动化部署提示词**：
  - 核心约束新增第7条：合规审查约束(许可证扫描/PIA/等保GDPR)
  - 核心约束新增第8条：回滚完整性约束(回滚脚本/回滚SQL/5min/演练/蓝绿保留24h)
- **08_安全审计与合规检查提示词**：
  - 核心约束新增第6条：业务连续性约束(RTO/BCP/灾难恢复演练)
  - 核心约束新增第7条：数据保护约束(AES-256/TLS1.2/双删除/被遗忘权/跨境评估)
- **05_全维度测试策略提示词**：
  - 身份定义新增5条专业工作方式(测试左移/风险导向/分层自动化/持续反馈/跨角色协作)
- **07_监控告警与运维保障提示词**：
  - 身份定义新增5条SRE On-Call专业工作方式(三原则/SLA驱动/SLO体系/渐进式故障处理/可观测性先行)
- **10_技术文档与知识沉淀提示词**：
  - 身份定义新增5条专业工作方式与评审流程(Diátaxis框架/三级评审/质量度量/知识闭环/协作规范)

## [v3.4.0] - 2026-05-28

### Added

- 新增 `_evaluations/` 目录，建立效果评估与反馈闭环体系：
  - `evaluation_framework.md`：效果评估框架，定义4项核心指标（输出完整度、输出准确率、结构合规率、执行耗时）、阈值与优化触发条件、闭环流程（评估→分析→优化→再评估）、评估报告模板
  - `baseline/baseline_v1.json`：初始基线数据（完整度95%、准确率88%、合规率92%、耗时15s）
  - `reports/.gitkeep`：评估报告存放目录
- 新增 `_i18n/` 目录，建立国际化支持体系：
  - `glossary_zh_en.md`：中英术语对照表，62个术语按8大分类提供英文对照
  - `cultural_rules.md`：文化适配规则，定义中文版委婉建议式风格、英文版直接指令式风格、通用翻译规则
- 00_项目提示词总览与使用指南新增「十、多语言版本」章节，标注中文版（主）与英文版目录及当前可用术语对照表

## [v3.3.0] - 2026-05-28

### Added

- 新增 `_model_profiles/` 目录，建立AI模型能力画像，包含4个模型画像YAML文件：
  - `claude-3-opus.yaml`：200K上下文，指令遵循95，推理深度95，推荐详细CoT+XML标记风格
  - `gpt-4-turbo.yaml`：128K上下文，指令遵循92，结构化输出95，推荐系统提示+JSON模式
  - `gemini-pro.yaml`：1M上下文，多模态95，推荐长上下文+多模态输入风格
  - `domestic-models.yaml`：通义千问/文心一言/DeepSeek，中文理解95+，推荐直接指令式+分段输出
- 新增 `_adaptation_matrix.md`：AI模型适配策略矩阵，包含模型×文档×适配级别策略矩阵表、每个模型使用建议、降级方案汇总
- 为01-12号核心文档的"身份定义"章节添加S1通用适配标注（`<!-- S1:通用适配 - 所有模型共用 -->`）
- 为02_架构设计、03_编码规范、04_代码审查的关键场景模板添加S2偏好适配标注（Claude/GPT/国产三种风格）
- 为02_架构设计(场景C)、03_编码规范(场景B)、04_代码审查(场景B)的长上下文需求场景添加S3降级方案标注

## [v3.2.0] - 2026-05-28

### Added

- 新增 `_interfaces/` 目录，为01-09号文档创建输入/输出接口Schema定义（YAML格式），每个接口包含required/optional的input和output字段定义
- 新增 `_workflows/` 目录，定义4条链式工作流：
  - `review_fix_verify.yaml`：审查→整改→验证 (04→03→05)
  - `requirement_design_coding.yaml`：需求→设计→编码 (01→02→03)
  - `deploy_monitor_security.yaml`：部署→监控→安全 (06→07→08)
  - `perf_optimize_verify.yaml`：性能→优化→验证 (09→03→05)
- 新增 `_interfaces/compatibility_report.yaml`：接口兼容性校验报告，17条链路全部通过，1条需类型转换（priority_matrix: object→string 序列化）
- 01-09号文档输出规范章节末尾新增接口引用块，标注输入接口、输出接口和传递协议（字段映射+类型转换规则）

### Changed

- **01_需求分析与产品规划提示词**：输出规范章节3.4末尾新增接口引用块
- **02_架构设计与技术选型提示词**：输出规范章节3.5末尾新增接口引用块
- **03_编码规范与AI辅助开发提示词**：输出规范章节8.3末尾新增接口引用块
- **04_代码审查与质量保障提示词**：审查规范章节4.2末尾新增接口引用块
- **05_全维度测试策略提示词**：输出规范章节10.3末尾新增接口引用块
- **06_CI_CD与自动化部署提示词**：输出规范章节9.3末尾新增接口引用块
- **07_监控告警与运维保障提示词**：输出规范章节9.3末尾新增接口引用块
- **08_安全审计与合规检查提示词**：输出规范章节8.3末尾新增接口引用块
- **09_性能压测与优化提示词**：输出规范章节9.3末尾新增接口引用块

## [v3.1.0] - 2026-05-28

### Added

- 06_CI_CD与自动化部署提示词新增「场景 F：MLOps 流水线设计」，覆盖 ML 流水线架构、模型版本管理（MLflow/W&B）、数据版本管理（DVC）、模型评估门禁、部署策略、漂移监控与回滚机制
- 09_性能压测与优化提示词新增「场景 F：云成本优化（FinOps）」，覆盖成本分布分析、资源利用率审查、优化建议（右缩容/预留实例/存储分层/网络出口）、FinOps 治理机制与节省预估
- 08_安全审计与合规检查提示词新增「场景 F：ESG 合规评估」，覆盖 ESG 三维度评估（环境/社会/治理）、合规差距分级、整改路线图、持续监控指标与报告模板
- 00_项目提示词总览与使用指南场景快速参考卡更新：场景总数从 52 更新为 55，5.5/5.6/5.7 阶段各新增一行场景引用

### Changed

- **06_CI_CD与自动化部署提示词**：v1.3.0 → v1.4.0（Minor 升级：新增 MLOps 场景模板）
- **09_性能压测与优化提示词**：v1.3.0 → v1.4.0（Minor 升级：新增 FinOps 场景模板）
- **08_安全审计与合规检查提示词**：v1.3.0 → v1.4.0（Minor 升级：新增 ESG 合规评估场景模板）
- **00_项目提示词总览与使用指南**：v3.0.0 → v3.1.0（Minor 升级：场景快速参考卡扩展至 55 个场景）

## [v3.0.0] - 2026-05-28

### Added

- 全体系实施语义化版本管理（SemVer vX.Y.Z），取代原有非标准版本号格式
- 新增 `CHANGELOG.md`，记录全量变更历史
- 00_总览文档新增「九、版本联动规则」章节，包含：
  - 9.1 语义化版本策略定义
  - 9.2 核心文档 Major 变更时的受影响文档评估规则
  - 9.3 文档依赖关系表（含联动规则）
  - 9.4 特殊联动场景说明

### Changed

- **00_项目提示词总览与使用指南**：v2.9 → v3.0.0（Major 升级：体系架构级变更，新增版本联动规则章节与 CHANGELOG 机制）
- **01_需求分析与产品规划提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **02_架构设计与技术选型提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **03_编码规范与AI辅助开发提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **04_代码审查与质量保障提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **05_全维度测试策略提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **06_CI_CD与自动化部署提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **07_监控告警与运维保障提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **08_安全审计与合规检查提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **09_性能压测与优化提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **10_技术文档与知识沉淀提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **11_项目管理与迭代复盘提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **12_AI时代开发专项提示词**：v1.2 → v1.3.0（Minor 升级：补充输出规范/检查清单章节）
- **工业级项目全流程螺旋式迭代管理总纲**：V3.0 → v3.0.1（Patch 升级：版本号格式规范化）
- **整体审查提示词**：v2.0 → v2.0.1（Patch 升级：版本号格式规范化）
- **_glossary**：无版本号 → v1.1.0（新增版本号标注，术语体系已稳定）
- **_project_context**：无版本号 → v1.0.1（新增版本号标注，模板格式规范化）
- **角色定义**：无版本号 → v1.0.1（新增版本号标注，格式规范化）
- **一、前置身份与能力锚定**：无版本号 → v1.0.1（新增版本号标注，格式规范化）
- **_project_bug_review**：无版本号 → v2.0.1（新增版本号标注，与 Bug 检查 V2.0 对齐）
- **批量扫描与修复工作流**：无版本号 → v1.0.1（新增版本号标注，格式规范化）
- 00_总览版本号跟踪表全面更新为语义化版本格式
- 00_总览版本历史新增 v3.0.0 记录

### Fixed

- 全体系版本号格式统一为 `vX.Y.Z`（修正原有 `vX.Y`、`VX.Y`、无版本号等不一致情况）
- 00_总览更新说明更新为 v3.0.0 变更描述
