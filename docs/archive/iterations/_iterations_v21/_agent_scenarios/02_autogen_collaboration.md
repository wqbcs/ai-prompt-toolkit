# R3-02 AI Agent专项-场景2:AutoGen多Agent协作

> **迭代**：v21-R3-02 | **日期**：2026-07-12

---

## 前置知识

- 掌握Python异步编程（async/await）
- 了解AutoGen AgentChat核心概念
- 熟悉Docker容器化基础

## 场景描述

使用AutoGen框架编排多Agent协作系统，包括对话式协作、群组讨论、人工介入和代码执行安全沙箱。

## 提示词模板

```markdown
# AutoGen多Agent协作设计

## 角色
你是一位AutoGen框架专家，擅长设计多Agent协作系统。

## 任务
为以下场景设计AutoGen多Agent协作方案。

## 输入
- 业务场景: {scenario}
- Agent数量: {agent_count}
- 协作模式: {collaboration_mode}
- 人工介入点: {human_in_loop_points}
- 代码执行需求: {code_execution_needed}

## 设计要素
1. Agent定义（role/backstory/tools/LLM配置）
2. 协作拓扑（顺序/群组/层级）
3. 消息流设计（@start/@listen/@router）
4. 错误处理策略
5. 代码执行安全策略

## 请输出
1. Agent定义表（名称/角色/工具/LLM/4列）
2. 协作拓扑图（Mermaid格式）
3. 消息流序列图（Mermaid格式）
4. Python代码骨架（async def main）
5. 安全策略清单（5项）
6. 测试方案（单元+集成+端到端）
```

## 常见陷阱

| # | 陷阱 | 严重等级 | 规避方案 |
|---|------|---------|---------|
| 1 | 无限对话循环：Agent互相触发无终止 | P0 | 设置max_turns+终止条件检测 |
| 2 | 代码执行无沙箱：Agent执行恶意代码 | P0 | 强制DockerCommandLineCodeExecutor |
| 3 | 消息爆炸：群组讨论消息量指数增长 | P1 | 设置max_messages+摘要机制 |
| 4 | 人工介入阻塞：等待人工输入无超时 | P1 | 设置human_input_timeout+默认回复 |
| 5 | 状态丢失：Agent间共享状态不一致 | P2 | 使用Core层的AgentRuntime状态管理 |

## 性能提示

| # | 提示 | 效果 | 实施难度 |
|---|------|------|---------|
| 1 | gRPC分布式部署 | 支持跨机器Agent | 高 |
| 2 | 并行Agent执行 | 吞吐量提升3x | 中 |
| 3 | 消息压缩+摘要 | Token降低40% | 中 |
| 4 | 流式输出 | 用户感知延迟降低50% | 低 |
| 5 | 缓存Agent回复 | 重复查询成本降低90% | 低 |

## 安全提示

| # | 提示 | 威胁类型 | 严重等级 |
|---|------|---------|---------|
| 1 | Docker沙箱+网络隔离 | 容器逃逸 | P0 |
| 2 | 代码执行白名单（仅允许指定语言） | 任意代码执行 | P0 |
| 3 | Agent工具权限最小化 | 权限提升 | P1 |
| 4 | 敏感信息过滤（API Key/密码） | 数据泄露 | P1 |
| 5 | 审计日志记录所有Agent决策 | 合规风险 | P2 |

## 扩展阅读

- AutoGen Core文档: https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/
- AutoGen AgentChat: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/
- Docker安全最佳实践: https://docs.docker.com/engine/security/
