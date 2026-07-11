# AI Agent自主执行协议规范 v1.0

> **版本**：v1.0
> **日期**：2026-05-29
> **状态**：E1批次产出
> **协议版本**：semantic-versioning(1.0.0)

---

## 1. 协议总览

本协议定义AI Agent基于提示词自主执行任务的规范，包含角色定义、执行上下文、工具调用、决策边界、人机协作模式、结果校验六大组件。

---

## 2. L0-L4五级Agent自主度

### 2.1 自主度分级定义

| 级别 | 名称 | 定义 | 人工参与 | 适用场景 | 安全要求 |
|------|------|------|----------|----------|----------|
| L0 | 纯人工驱动 | 提示词仅提供参考，所有操作由人工执行 | 全程 | 低信任/高风险操作 | 无Agent执行 |
| L1 | 人工审批+Agent执行 | Agent提出执行方案，人工审批后Agent执行 | 方案审批 | 合规审查/部署审批 | 方案需人工审批 |
| L2 | Agent执行+人工监督 | Agent自主执行，关键节点人工确认 | 关键节点 | 代码审查/性能优化 | 关键决策人工确认 |
| L3 | Agent自主执行+结果汇报 | Agent自主执行全流程，完成后汇报结果 | 结果审阅 | 日常监控/文档生成 | 执行后汇报 |
| L4 | Agent自主执行+自主决策 | Agent自主执行并自主决策，异常时汇报 | 仅异常 | 自动化测试/数据采集 | 异常必须汇报 |

### 2.2 自主度评估方法

```yaml
autonomy_assessment:
  scenario: "场景模板名称"
  current_level: "Lx"
  assessment_criteria:
    task_complexity: "1-5"  # 任务复杂度
    risk_level: "1-5"       # 风险等级
    reversibility: "1-5"    # 可逆性(5=完全可逆)
    trust_level: "1-5"      # 信任等级
    tool_dependency: "1-5"  # 工具依赖度
  recommended_level: "Ly"
  rationale: "推荐理由"
```

**推荐规则**：
- risk_level ≥ 4 → 最大L1（高风险操作需人工审批）
- reversibility ≤ 2 → 最大L2（不可逆操作需人工监督）
- task_complexity ≤ 2 AND risk_level ≤ 2 → 可考虑L3/L4
- 涉及生产环境变更 → 最大L2

---

## 3. Agent角色定义

### 3.1 角色定义模型

```yaml
agent_role:
  name: "Agent名称"
  role: "角色定位"
  goal: "执行目标"
  backstory: "能力背景与工作方式"
  capabilities: ["能力1", "能力2", ...]
  permissions: ["权限1", "权限2", ...]
  decision_boundary:
    autonomous: ["可自主决策范围1", ...]
    requires_approval: ["需人工审批范围1", ...]
    prohibited: ["禁止操作1", ...]
  autonomy_level: "L0-L4"
  tools: ["工具1", "工具2", ...]
```

### 3.2 核心Agent角色

| Agent | 角色 | 自主度 | 适用场景 |
|-------|------|--------|----------|
| CodeReviewAgent | 代码审查执行者 | L2 | 04_代码审查 |
| SecurityAuditAgent | 安全审计执行者 | L1 | 08_安全审计 |
| PerformanceAgent | 性能优化执行者 | L2 | 09_性能压测 |
| MonitorAgent | 监控巡检执行者 | L3 | 07_监控告警 |
| DeployAgent | 部署执行者 | L1 | 06_CI_CD |
| TestAgent | 测试执行者 | L3 | 05_测试策略 |
| DocAgent | 文档生成者 | L4 | 10_技术文档 |
| RefactorAgent | 重构执行者 | L2 | 03_编码规范 |

---

## 4. 执行上下文

```yaml
execution_context:
  input:
    task_description: "任务描述"
    target_files: ["文件列表"]
    constraints: ["约束列表"]
  environment:
    project_root: "项目根目录"
    tech_stack: "技术栈"
    model: "AI模型"
    language: "编程语言"
  tools:
    available: ["可用工具列表"]
    permissions: {"tool": "permission_level"}
  history:
    previous_steps: ["已执行步骤"]
    results: {"step": "result"}
    context_window: "剩余上下文窗口"
```

---

## 5. 工具调用规范

```yaml
tool_invocation:
  tool_name: "工具名称"
  parameters: {"param": "value"}
  return_format: "JSON"
  error_handling:
    retry: 3
    fallback_tool: "替代工具"
    on_failure: "abort|degrade_to_human|skip"
  permission_check: true
  timeout: 30s
  sandbox: true  # 代码执行在沙箱中
```

---

## 6. Agent安全边界

### 6.1 硬性约束

1. **系统提示词不可变**：Agent不可修改System Prompt
   - 规约：AG(SystemPrompt = InitialSystemPrompt)

2. **越权访问阻断**：超出权限范围的工具/数据不可访问
   - 规约：AG(∀tool_call ∈ ToolCalls : tool_call.permission ∈ Agent.permissions)

3. **注入防御穿透**：Agent输出必须经过注入防御v3.0检查
   - 规约：AG(∀agent_output : InjectionDefense(agent_output) = safe)

4. **敏感操作审批**：删除/部署/发布等操作需人工确认
   - 规约：AG(∀sensitive_op ∈ SensitiveOps : HumanApproval(sensitive_op) = true)

5. **执行超时保护**：单步>30s强制终止，全流程>5min终止
   - 规约：AG(step_duration ≤ 30s ∧ total_duration ≤ 300s)

6. **沙箱隔离**：代码执行/文件操作在沙箱中执行
7. **决策边界约束**：自主决策范围显式定义，边界外请求审批
8. **多Agent数据隔离**：Agent间不直接共享敏感数据
9. **Agent不可修改自身权限**：权限变更需人工审批
10. **L4安全敏感操作禁止无监督**：L4 Agent执行安全操作需人工监督

### 6.2 安全边界实现

```yaml
security_boundary:
  system_prompt_immutable: true
  access_control:
    mode: "whitelist"  # 白名单模式
    allowed_tools: [...]
    denied_operations: ["delete_production", "modify_system_prompt", "elevate_privilege"]
  injection_defense:
    version: "v3.0"
    check_agent_output: true
    check_tool_result: true
  human_approval:
    sensitive_operations: ["deploy", "delete", "publish", "security_config_change"]
    approval_timeout: 300s
    on_timeout: "abort"
  execution_limits:
    step_timeout: 30s
    total_timeout: 300s
    max_retries: 3
  sandbox:
    enabled: true
    filesystem: "isolated"
    network: "restricted"
```

---

## 7. Agent工作流编排协议

### 7.1 单Agent执行流

```
Input → ContextInit → ToolSelect → Execute → SelfCheck → Output
                ↓(fail)                    ↓(fail)
            ErrorHandler              Retry/Recover/Abort
```

### 7.2 多Agent协作流

```yaml
agent_workflow:
  name: "工作流名称"
  agents: [Agent1, Agent2, ...]
  communication:
    protocol: "message_passing"  # 消息传递
    format: "JSON"
    timeout: 30s
  task_assignment:
    strategy: "capability_based"  # 按能力分配
    fallback: "round_robin"
  result_aggregation:
    conflict_resolution: "confidence_priority"  # 置信度优先
    consistency_check: true
  human_in_loop:
    approval_points: ["pre_deploy", "post_audit"]
    supervision_points: ["code_review_result", "security_finding"]
```

---

## 8. 执行结果校验

```yaml
result_verification:
  self_check:
    format_check: true      # 输出格式校验
    content_check: true     # 输出内容校验
    fact_check: true        # 事实核查
    consistency_check: true # 自洽性校验
  external_check:
    tool_verification: true # 工具验证
    human_review: true     # 人工审阅(根据自主度)
    regression_test: true  # 回归测试
  confidence_score:
    method: "weighted_average"
    weights: {format: 0.2, content: 0.3, fact: 0.3, consistency: 0.2}
    threshold: 0.85
```
