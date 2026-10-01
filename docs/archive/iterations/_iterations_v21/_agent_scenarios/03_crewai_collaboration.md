# R3-03 AI Agent专项-场景3:CrewAI角色协作

> **迭代**：v21-R3-03 | **日期**：2026-07-12

---

## 前置知识

- 掌握Python面向对象编程
- 了解CrewAI Crews+Flows双模型
- 熟悉Pydantic数据模型

## 场景描述

使用CrewAI框架设计角色驱动的Agent团队，通过YAML声明式定义Agent和Task，结合Flows实现事件驱动编排。

## 提示词模板

```markdown
# CrewAI角色协作设计

## 角色
你是一位CrewAI框架专家，擅长设计角色驱动的Agent协作系统。

## 任务
为以下场景设计CrewAI Crew+Flow方案。

## 输入
- 业务场景: {scenario}
- 角色列表: {roles}
- 任务分解: {task_breakdown}
- 输出格式: {output_format}
- 人工审批需求: {human_approval}

## 设计要素
1. Agent角色定义（role/goal/backstory/tools/LLM）
2. Task任务定义（description/expected_output/agent/output_pydantic）
3. Crew编排（sequential/hierarchical/process）
4. Flow事件流（@start/@listen/@router）
5. 结构化输出（Pydantic模型）

## 请输出
1. agents.yaml（Agent声明式配置）
2. tasks.yaml（Task声明式配置）
3. crew.py（Python Crew定义）
4. flow.py（Flow事件编排）
5. output_model.py（Pydantic输出模型）
6. 执行命令+环境变量清单
```

## 常见陷阱

| # | 陷阱 | 严重等级 | 规避方案 |
|---|------|---------|---------|
| 1 | 角色定义模糊：goal/backstory不具体导致Agent行为不可预测 | P1 | role=职位+领域, goal=可量化目标, backstory=3-5句专业背景 |
| 2 | Task描述不精确：expected_output含糊 | P1 | expected_output必须指定格式+长度+必须包含的元素 |
| 3 | 过度自主：Hierarchical模式Manager决策失误 | P2 | 关键决策点添加human_input=True |
| 4 | 工具滥用：Agent随意调用工具 | P1 | 工具添加guardrails+输入验证 |
| 5 | 内存泄漏：长对话Context丢失 | P2 | 启用memory+设置max_memory_size |

## 性能提示

| # | 提示 | 效果 | 实施难度 |
|---|------|------|---------|
| 1 | 缓存Tool结果 | 重复工具调用成本降低80% | 低 |
| 2 | 并行Task执行 | 吞吐量提升2x | 中 |
| 3 | 结构化输出(output_pydantic) | 后处理时间降低90% | 低 |
| 4 | Flow or_/and_逻辑 | 复杂触发简化50% | 低 |
| 5 | Knowledge管理 | RAG检索精度提升30% | 中 |

## 安全提示

| # | 提示 | 威胁类型 | 严重等级 |
|---|------|---------|---------|
| 1 | Agent工具权限控制 | 权限提升 | P1 |
| 2 | 输出内容安全过滤 | 有害内容 | P1 |
| 3 | API Key不硬编码在YAML | 凭证泄露 | P0 |
| 4 | Flow状态隔离 | 数据泄露 | P2 |
| 5 | 遥测数据匿名化 | 隐私泄露 | P2 |

## 扩展阅读

- CrewAI官方文档: https://docs.crewai.com
- CrewAI Examples: https://github.com/crewAIInc/crewAI-examples
- Pydantic V2: https://docs.pydantic.dev/latest/
