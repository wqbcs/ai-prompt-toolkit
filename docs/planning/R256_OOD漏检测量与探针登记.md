# R256 · OOD 漏检面测量与探针登记

> 生成：2026-10-09 · 版本基线：67.34.48（R255 收口，commit bdda5fc）
> R255 解卡（hf-mirror 通道）后的执行轮：P2-26 附带漏检面 OOD 候选
> （deepset/prompt-injections 662 条）从"通道卡 6 轮"变为"拉取→去重→
> 测量→判据选探针→扩展决策"闭环。**零规则改动**（CLAUDE.md：无探针支撑
> 的规则禁止合入；本轮只登记探针与决策，不动任何 pattern）。

---

## §0 四问（R256 时点，简版——完整四问见 R255 §0，本轮无方向变更）

定位/核心价值未漂移（楔子：确定性/可复现/零 LLM/<100ms/离线）。本轮问题
**"可信度主轴的可审计性"延伸到漏检面**：R255 给过防御面（precision 锚）
配了二阶信号检查器；漏检面的**外部锚**此前缺位——golden 150 探针是自选面
（内部），NotInject 339 是外部但只量过防御（precision 侧）。外部 recall 锚
（"该报的攻击报了吗，在**我方从未见过的**攻击上"）=本轮补上。诚实边界：
正则单腿上限（08 2026-10-08 实证：纯关键词规则 F1=0.125）意味着外部 recall
不会是漂亮数字——**如实测、如实记、不进棘轮**（棘轮语义=回归断言，不是
不可达目标断言；把 25% 召回写进漏检棘轮=红到永远=棘轮语义错误）。

## §1 数据落盘与去重

- **落盘**（external_bench 标准位，NotInject 先例对齐）：
  - `deepset_prompt_injections_train.parquet`（546 条）+ `_test.parquet`
    （116 条）=上游原形态留档
  - `deepset_prompt_injections.json`（662 条）=纯 stdlib 工作副本
    （测量脚本读此，零未声明依赖——pyarrow 未声明，R223 教训同族纪律；
    转换=拉取时一次性本地操作，不进门禁/CI）
  - `LICENSE_NOTES.md` 补 3 行：双许可面留痕（仓库 tag apache-2.0 /
    dataset card 数据面 cc-by-4.0，R256 核实）+ hf-mirror 通道说明
- **去重纪律**（R255 §2.4 约束 1 执行）：deepset 399 良性 ∩ NotInject 339
  良性 = **0 条重叠**（归一化=小写+空白折叠，保守去重宁漏勿误杀）；
  注入面 ∩ NotInject = 0（理论必然，保险查过）。**两个外部基准互不污染，
  各自保持独立 holdout 地位**。

## §2 测量结果（当前 267 规则，确定性可复现）

`scripts/measure_ood_recall.py`（研究测量工具，**不进 release_gate**——
OOD 不入漏检分母的决策见 §3；脚本 air-gap 可跑：数据已入仓，同输入同输出）：

```
deepset 662 条（263 注入 / 399 良性）
安全族 89 规则（overdefense 单一真源 security_family_rules()，零复制）
OOD 召回 = 66/263 = 25.10%
Top 命中: P178(18) P168(16) P167(9) P170(8) P206-P209(6×4) P008(5) P162(5)
```

**197 条漏检的形态分类**（探针判据输入，逐条可复现）：

| 形态 | 条数 | 占比 | 静态 regex 辖区? |
|---|---|---|---|
| **语义变体面**（短且无已知短语形态：paraphrase/上下文嵌入/"Pretend you are an evil AI"/"Attention - stop - I urgently need your help" 类） | 133 | 68% | **否**——意图理解面，静态文本面辖区外（"正则单腿上限"叙事第三方实证；prompt-guard 自曝 OOD recall ~20% 同量级=行业静态/轻量面共识上限区） |
| 长文嵌入（>200 字符，注入指令埋入正常叙述中段） | 51 | 26% | 部分——长窗口共现判定=结构面，现有规则窗口短，扩窗口=过防御面（NotInject 长句）直接冲突 |
| 直接注入短语变体（**词表缺口**：`ignore above`/`Forget everything before that`/`Don'nt answer` 拼写变体/`new tasks follow`） | 18 | 9% | **是**——唯一静态可处理面（P163/P178 词表缺 above/before that/instead 变体） |
| 系统提示提取变体（`what are your instructions` 变体） | 2 | 1% | 是——单例，不满足 ≥2 判据 |
| 越狱人格/编码混淆 | 0 | 0% | —（现有 P163/P260/P261 对 deepset 注入覆盖=0 漏，该两面 deepset 语料占比低） |

## §3 OOD 扩展决策（02 P2-26 三选一，本轮判定）

**判定：OOD 263 注入不入漏检基线分母；作独立外部 recall 锚 + 观察区。**

1. **不入分母**（对"扩漏检基线分母"选项）：197 漏检 68% 在语义变体面=
   静态辖区外。分母扩到 263 后漏检率从 0% 跳到 74.9%=**棘轮红且永远绿不
   回来**——棘轮语义是"回归断言"（改动不得比基线差），不是"目标断言"
   （基线可达）。把辖区外样本写进辖区指标=指标污染（与 overdefense 口径
   排除 arkts/harmonyos 族同族纪律：口径错误不得在数字里掩盖）。
2. **独立锚 + 观察区**（对"登记观察区"选项，采纳并强化）：
   - `measure_ood_recall.py` 每轮可跑（不在门禁链=不阻断；数字可复现可
     进 P5-11 公开叙事："外部 OOD 召回 25.10%，漏检 68% 在语义面=静态
     辖区外，如实公开"——prompt-guard 把 OOD recall 写 README 的获客
     纪律（08 2026-10-08 行"read this honestly"）同形态）
   - 形态级晋升判据（07 T-6 观察区同族，写死防漂移）：某漏检形态**≥2 条
     真实 TP 探针 + 过防御棘轮（ODT-1）约束下可收窄/扩词**→ 探针先行入
     golden（本轮先例：ignore-previous 形态 2 条）→ 规则改动走 T6 联合
     调优轮（18 条直接短语变体=候选面，**词表扩宽与 NotInject 过防御面
     正面冲突**——扩 `above/before that` 类变体必须先在 339 硬负样本上
     验证零新增过防御，ODT-1 会机器断言）
3. **探针登记（本轮执行面，2 条）**：
   - `r256_ood_tp01_ignore_previous_instructions`（deepset #9，expected
     [P178]）+ `r256_ood_tp02_ignore_preceding_orders`（deepset #12，
     expected [P162, P178]）
   - 判据满足：单形态（ignore-previous 指令重置）≥2 条**真实** TP
     （外部 OOD 样本，非自构造——比自构造探针更强的泛化背书）；**当前
     267 规则已命中**=进漏检分母不加码不降标（expected_total 230→232
     单元，miss 不升，基线非回归=纯收紧面）
   - golden 230→232 条；`expected: []` 观察探针先例（R240）本轮不用——
     133 条语义变体面登记为**文档面观察区**（§2 形态表）而非 133 条
     空探针（奥卡姆：空探针×133=清单稀释，P3-17 板漂移同族教训）

## §4 诚实边界（发布叙事素材，P5-11 引用）

- 静态文本面 OOD 召回 25.10%（外部 deepset 263 注入，零训练零调优零见过）
  = 确定性正则楔子的**如实边界**，与"每次裁决逐字节一致"是不同维度的
  承诺——我们承诺的是**裁决可复现+已知模式零漏检（golden 0 miss）**，
  不承诺**未知模式全覆盖**（那是语义层辖区，08 2026-10-08 行"规则层先挡
  已知模式+语义层补变体"中文社区共识的同构表述）。
- 双外部基准对称结构（P2-25 完成）：precision 锚=NotInject 339（过防御
  11.50%）/ recall 锚=deepset 263（OOD 25.10%）/ 内部=golden 232（0 miss）
  ——三个坐标系各自口径写死在单一真源（overdefense.py / measure_ood_recall.py
  / baselines.py），公开页同坐标系呈现（08 2026-10-05 buried-injections
  "同一坐标系"纪律）。

## §5 不重复造轮子核验

| 项 | 核验 | 判定 |
|---|---|---|
| 测量脚本 | overdefense.security_family_rules()/lint_template 复用（grep 确认单一真源存在） | 复用零复制（仅新增 OOD 口径面） |
| 数据落盘 | external_bench + LICENSE_NOTES 先例（NotInject） | 对齐先例（parquet 留档+JSON 工作副本+双许可留痕） |
| 探针判据 | 07 T-6"单形态 ≥2 真实 TP"+R240 观察探针先例 | 复用既有判据（本轮是 OOD 源的首次应用，非新判据） |
| OOD 入分母 | 02 P2-26 行注记三选一 + 08 2026-10-08 正则单腿上限实证 | **拒绝扩分母**（棘轮语义错误，§3.1） |
