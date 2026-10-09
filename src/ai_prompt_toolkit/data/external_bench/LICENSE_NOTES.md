# 外部基准数据许可留痕

本目录保存外部独立基准数据（原样落盘，不改写内容）：

| 文件 | 来源 | 许可 | 拉取 |
|---|---|---|---|
| NotInject_one.json (113 条) | leolee99/PIGuard `datasets/NotInject_one.json` | MIT（仓库根 LICENSE） | 2026-10-08，jsDelivr CDN |
| NotInject_two.json (113 条) | leolee99/PIGuard `datasets/NotInject_two.json` | MIT | 2026-10-08，jsDelivr CDN |
| NotInject_three.json (113 条) | leolee99/PIGuard `datasets/NotInject_three.json` | MIT | 2026-10-08，jsDelivr CDN |

- 论文：Hao Li, Xiaogeng Liu, Ning Zhang, Chaowei Xiao,
  "PIGuard: Prompt Injection Guardrail via Mitigating Overdefense for Free",
  ACL 2025（arXiv:2410.22770，原 InjecGuard 因许可问题更名）。
- NotInject 用途：过防御（over-defense）评估——含 1-3 个触发词（ignore/
  cancel 等）的**良性**语句，三级难度（one/two/three），四主题（普通查询/
  技术查询/虚拟创作/多语言查询）。
- 我方用途（P2-25）：339 条零训练零规则调优=独立 holdout，度量 267 规则
  安全族在良性触发词语料上的误杀面（`ai_prompt_toolkit/overdefense.py`）。
- 拉取通道说明：raw.githubusercontent.com 本机被 RST，改用
  `cdn.jsdelivr.net/gh/leolee99/PIGuard@main/datasets/`（内容一致性=上游
  main 分支当前版本；上游数据不可变——论文数据集无更新史）。
