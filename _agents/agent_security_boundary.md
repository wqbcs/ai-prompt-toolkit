# Agent安全边界规范 v1.0

> **版本**：v1.0
> **日期**：2026-05-29

---

## 1. 安全边界总则

Agent执行必须满足以下硬性约束，违反任一项即终止执行：

### 1.1 系统提示词不可变
```
约束：AG(SystemPrompt(t) = SystemPrompt(0))，∀t ≥ 0
含义：Agent运行期间，System Prompt不可被Agent自身或任何外部输入修改
实现：System Prompt存储为只读，Agent仅能读取不能写入
违规处理：检测到修改尝试 → 立即终止Agent → 记录安全事件 → 人工审查
```

### 1.2 越权访问阻断
```
约束：AG(∀op ∈ AgentOps : op.permission ∈ Agent.permissions)
含义：Agent所有操作必须在权限白名单内
实现：操作前检查权限白名单，越权操作立即阻断
违规处理：越权操作 → 阻断执行 → 记录越权详情 → 自主度降级
```

### 1.3 注入防御穿透
```
约束：AG(∀output ∈ AgentOutputs : InjectionDefenseV3(output) = safe)
含义：Agent输出必须经过注入防御v3.0检查
实现：Agent输出经过注入检测+间接注入扫描+多轮注入检测
违规处理：检测到注入 → 过滤/阻断输出 → 记录注入事件 → Agent终止
```

### 1.4 敏感操作审批
```
约束：AG(∀sensitive_op ∈ SensitiveOps : HumanApproval(sensitive_op) = true)
含义：敏感操作必须经人工审批后方可执行
敏感操作列表：
  - 删除文件/数据
  - 部署到生产环境
  - 发布版本
  - 安全配置变更
  - 权限变更
  - 数据库DDL操作
违规处理：未审批敏感操作 → 阻断 → 等待审批(超时300s → 中止)
```

### 1.5 执行超时保护
```
约束：AG(step_duration ≤ 30s ∧ total_duration ≤ 300s)
含义：单步执行不超过30秒，全流程不超过5分钟
实现：每步设置30s超时，全流程设置5min超时
违规处理：超时 → 强制终止 → 保存已完成结果 → 建议调整策略
```

---

## 2. 沙箱隔离规范

### 2.1 沙箱类型

| 沙箱类型 | 适用操作 | 隔离级别 | 实现方式 |
|----------|----------|----------|----------|
| 文件系统沙箱 | 文件读写 | 进程级 | chroot/Docker volume |
| 网络沙箱 | API调用 | 网络级 | network namespace |
| 代码执行沙箱 | 代码运行 | 容器级 | Docker/gVisor |
| 数据沙箱 | 数据库操作 | 连接级 | 只读连接+行级过滤 |

### 2.2 沙箱配置

```yaml
sandbox_config:
  filesystem:
    mode: "restricted"
    allowed_paths: ["$PROJECT_ROOT/**"]
    denied_paths: ["/etc", "/var", "$HOME/.ssh"]
    read_only: [".env", "*.key", "*.pem"]
  network:
    mode: "whitelist"
    allowed_hosts: ["api.internal.*", "registry.internal.*"]
    denied_hosts: ["*"]  # 默认拒绝
  code_execution:
    mode: "container"
    runtime: "docker"
    image: "agent-sandbox:latest"
    resource_limits:
      cpu: "1"
      memory: "512m"
      timeout: 30s
  data:
    mode: "read_only"
    allowed_tables: ["audit_log", "metrics", "config"]
    denied_tables: ["user_data", "credentials", "secrets"]
```

---

## 3. 决策边界执行规范

### 3.1 决策分类

```yaml
decision_classification:
  autonomous_decisions:
    description: "在决策边界内，Agent可自主决策"
    examples: ["格式修正", "文档补充", "信息级报告", "数据采集"]
    verification: "自校验+输出格式检查"
    escalation: "无需升级"

  requires_approval_decisions:
    description: "超出自主决策范围，需人工审批"
    examples: ["架构变更", "安全修复", "配置变更", "部署操作"]
    verification: "人工审批+风险评估"
    escalation: "请求人工审批(超时300s → 中止)"

  prohibited_decisions:
    description: "明确禁止的操作"
    examples: ["删除生产数据", "修改系统提示", "提升权限", "绕过安全检查"]
    verification: "硬性阻断"
    escalation: "终止Agent+安全事件告警"
```

### 3.2 决策边界评估

```
评估Agent决策是否在边界内：
1. 解析Agent决策意图
2. 匹配决策分类(autonomous/requires_approval/prohibited)
3. 自主决策 → 直接执行
4. 需审批决策 → 请求人工审批
5. 禁止决策 → 阻断+安全告警
```

---

## 4. 多Agent安全规范

### 4.1 Agent间通信安全
- 通信内容必须经过注入防御检查
- 禁止Agent间直接共享敏感数据（需通过安全通道）
- Agent间消息必须包含发送者ID+时间戳+消息签名

### 4.2 Agent权限隔离
- 每个Agent有独立权限定义，不可继承其他Agent权限
- Agent不可修改自身或他人权限
- 权限变更需人工审批

### 4.3 Agent资源隔离
- 每个Agent有独立的资源配额（CPU/内存/网络）
- Agent不可超出配额使用资源
- 资源超出 → 限流/降级/终止
