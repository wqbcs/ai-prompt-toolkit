# 英文翻译规范 v1.0

> **版本**：v1.0
> **日期**：2026-05-29
> **翻译范围**：v7.0.0全量体系英文翻译

---

## 1. 翻译范围

### 1.1 核心文档(00-12)
- 00_项目提示词总览与使用指南 → 00_Project_Prompt_Overview_and_Guide.md
- 01_需求分析与产品规划 → 01_Requirements_Analysis_and_Product_Planning.md
- 02_架构设计与技术选型 → 02_Architecture_Design_and_Tech_Selection.md
- 03_编码规范与AI辅助开发 → 03_Coding_Standards_and_AI_Assisted_Development.md
- 04_代码审查与质量保障 → 04_Code_Review_and_Quality_Assurance.md
- 05_全维度测试策略 → 05_Comprehensive_Testing_Strategy.md
- 06_CI_CD与自动化部署 → 06_CICD_and_Automated_Deployment.md
- 07_监控告警与运维保障 → 07_Monitoring_Alerting_and_Ops.md
- 08_安全审计与合规检查 → 08_Security_Audit_and_Compliance.md
- 09_性能压测与优化 → 09_Performance_Benchmark_and_Optimization.md
- 10_技术文档与知识沉淀 → 10_Technical_Docs_and_Knowledge.md
- 11_项目管理与迭代复盘 → 11_Project_Management_and_Retrospective.md
- 12_AI时代开发专项 → 12_AI_Era_Development_Special.md

### 1.2 辅助文档
- _glossary.md → _glossary_en.md
- _project_context.md → _project_context_en.md
- _reference_index.md → _reference_index_en.md
- _adaptation_matrix.md → _adaptation_matrix_en.md

---

## 2. 翻译标准

### 2.1 术语一致性
- 使用统一术语表(glossary_zh_en.md)
- 同一术语在所有文档中翻译一致
- 术语变更时同步更新所有文档

### 2.2 格式保持
- Markdown结构不变(标题层级+列表+表格+代码块)
- YAML/JSON字段名不翻译(仅翻译注释和说明)
- 代码示例不翻译
- 链接保持有效

### 2.3 语义等价
- 中文语义完整保留
- 不添加原文没有的内容
- 不省略原文的任何信息
- 专业术语不随意意译

### 2.4 专业表达
- 符合英语母语专业人士表达习惯
- 技术文档使用正式语体
- 避免Chinglish
- 使用业界标准术语

---

## 3. 文化适配规则

### 3.1 表达习惯适配
| 中文表达 | 英文表达 | 说明 |
|----------|----------|------|
| 严格执行 | Strictly execute / Enforce | 正式语体 |
| 一定要 | Must / Shall (RFC 2119) | 规范性语言 |
| 不可省略 | MUST NOT be omitted | RFC 2119 |
| 建议 | SHOULD / Recommended | RFC 2119 |
| 可选 | MAY / Optional | RFC 2119 |

### 3.2 术语映射(核心)
| 中文术语 | 英文术语 | 备注 |
|----------|----------|------|
| 提示词 | Prompt | 不译为Prompt Word |
| 场景模板 | Scenario Template | |
| 检查清单 | Checklist | |
| 约束 | Constraint | |
| 角色设定 | Role Definition | |
| 推理模式 | Reasoning Pattern | |
| 输出格式 | Output Format | |
| Agent自主度 | Agent Autonomy Degree | |
| 形式化验证 | Formal Verification | |
| 注入防御 | Injection Defense | |
| 幻觉抑制 | Hallucination Suppression | |
| 效果衰减 | Effect Decay | |
| 零损耗 | Zero-Loss | |

---

## 4. 翻译质量评估

### 4.1 自动化评估
- 术语一致性检查(≥98%)
- 格式保持度检查(100%)
- 关键信息保留率(≥95%)
- 链接有效性检查(100%)

### 4.2 人工评估
- 准确性(≥9/10)
- 流畅性(≥8.5/10)
- 专业性(≥8.5/10)
- 文化适配度(≥8/10)
- 综合评分(≥8.5/10)
