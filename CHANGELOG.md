# Changelog

本文件记录 AI 提示词体系的所有重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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
