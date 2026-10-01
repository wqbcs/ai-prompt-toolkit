# L3 未知/已识别欠账（显式标记, 不藏）

> 现状扫描发现、尚未解决的问题 — 改进方案的输入

## 文档漂移（已定位, 低危）

1. README 正文"255 规则/P001-P255/15 Probe+8 Detector"多处过期（徽章已是 256/23+11）— 同 R212-2 版本漂移同类, 需 sync_readme_metrics 覆盖
2. 漏检基线 9.52% 与 R213 收紧 0.05 之间有 4 条否定盲区未修（P161/P222/P244/P245）
3. coverage 68.49% vs "R177+ 目标 70+" 未完成

## 代码异味（已定位）

4. import 时向 stdout 打印 "Probe命名冲突: encoding_bypass..." — 污染 `python -m`/库导入的输出（R212-7 只统一了口径, 未消除 print）
5. doctor 规则数一致性核查（R192 遗留, recall 提及未闭环）
6. 黄金集无统计检验（A/B 显著性）— R212 非目标, R213 候选

## 仓库卫生（已定位, 影响观感与 AI 可消费性）

7. 仓库根目录 30+ 份 01-*/70-* 调研/改进文档 + 20+ 个 _iterations_v* 目录 — 无归档策略, 新会话定位成本高
8. project_wiki 此前完全缺失（R213 本次建立）
9. 记忆文件（SESSION_BRIEF/L0-L3）此前缺失 — memory-recall 无源可召回, 本 wiki 即首个替代

## 产品面未知（需调研回答, 见改进方案 R213）

10. 竞品（garak/promptfoo/LLM Guard/PyRIT/promptlint）当前版本的真实能力边界 — 需联网核实, 不凭印象
11. 用户真实痛点分布 — 需从 GitHub issues/社区/博客核实
