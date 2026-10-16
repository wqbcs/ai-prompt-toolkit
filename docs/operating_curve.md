# Operating Points — Severity-Cut Trade-off（公开数据页）

> 版本 `67.34.91` · 生成器 `scripts/gen_operating_curve.py`（确定性：同一数据→同一字节）
> 每个数字都是一条可复现命令的输出 —— **measured, not vibes**。

## 数字

| 运营点（severity 切面） | 活跃规则 | 误报 FP 对级率 | 过防御（外部良性 339） | 漏检单元覆盖（golden 379 单元） | OOD 召回（外部注入 263） |
|---|---|---|---|---|---|
| >= CRITICAL | 12 | 0.97% | 15 (4.42%) | 31/379 (8.2%) | 26 (9.89%) |
| >= HIGH | 118 | 0.72% | 21 (6.19%) | 209/379 (55.1%) | 55 (20.91%) |
| >= MEDIUM | 239 | 0.78% | 32 (9.44%) | 348/379 (91.8%) | 76 (28.90%) |
| >= LOW | 268 | 0.82% | 39 (11.50%) | 379/379 (100.0%) | 77 (29.28%) |
| 全部规则（默认） | 268 | 0.82% | 39 (11.50%) | 379/379 (100.0%) | 77 (29.28%) |

## 每列口径（与已发布数字 100% 同口径，防自相矛盾）

- **fp**：pair-level (rule,sample) pairs / (active_rules x 60 clean samples); single source = baselines.run_false_positives()
- **overdefense**：sample-level, security-family rules x 339 NotInject external benign hard negatives (leolee99/PIGuard, MIT); single source = overdefense.security_family_rules()
- **miss**：golden probe expected units (probe, rule); full-rule row = published 0-miss caliber
- **ood**：sample-level, security-family rules x 263 deepset/prompt-injections external injections (HF, apache-2.0/cc-by-4.0)

数据源：干净样本 60（自选）· NotInject 339（外部独立，零训练零调优）· deepset 263（外部独立 OOD）· golden 探针（内部，379 expected 单元）。外部数据许可见 `src/ai_prompt_toolkit/data/external_bench/LICENSE_NOTES.md`。

## 怎么读

静态规则没有置信阈值（每条规则要么命中要么不命中），**severity 是唯一运营点维度**——切到 ≥X 级 = 只计 X 级及以上 finding，等价于 LLM 检测器把阈值切到 X。例：只看 CRITICAL+HIGH 时，误报对级率 0.97%→0.72%、外部良性过防御 4.42%、外部 OOD 召回 20.91% —— precision/召回的取舍在这一行就能看清。

## FP 预算坐标系对齐（与行业基准可比）

行业 operating point 评检测器常用 **2% FP 预算**线作 operating point（buried-injections 方法论）。静态规则无置信阈值（命中即报），**全规则行是唯一 operating point**：FP 对级率 0.82% 已在 2% 预算内，且不存在可'切到 2% 预算'的中间 operating point = 天然固定 operating point（确定性楔子在评估面的红利：所见即所得，无阈值调优面）。上方 severity 切面表 = 该固定 operating point 内的 precision/召回取舍面。

## 复现（任意机器，离线，零 LLM）

```bash
prompt-cli baseline                # 双基线+分语言（漏检列）
python scripts/check_overdefense.py --json    # 过防御列
python scripts/measure_ood_recall.py          # OOD 列
python scripts/gen_operating_curve.py --check # 断言本页与当前数据一致
```

## 诚实边界

- OOD 列（外部从未见过的注入）是静态文本面的**如实上限**：全部规则行 29.3%，漏检主体（68%）在语义/paraphrase 变体面 = 静态 regex 辖区外（观察区，见 R256/R257 文档），不承诺未知模式全覆盖。
- 过防御列含**防御缺失型真实提醒**（良性 prompt 恰好缺某项声明）——纯 FP 面另见误报对级率列。
- 历史时间序列（收紧史）见 `docs/baseline_history.jsonl` 与 README 内嵌 sparkline。

