# 运行时安全模型

> 版本：v14.0.0 | 日期：2026-05-29

---

## 1. 安全架构(4层防御)

### 1.1 沙箱隔离
```
┌──────────────────────────────────────┐
│        Prompt Execution Sandbox      │
│  ┌──────────┐  ┌──────────┐         │
│  │ Prompt A │  │ Prompt B │         │
│  │ (isolated)│  │ (isolated)│        │
│  └──────────┘  └──────────┘         │
│  - 独立内存空间                      │
│  - 独立文件系统(只读挂载)             │
│  - 独立网络命名空间                  │
│  - 独立环境变量                      │
└──────────────────────────────────────┘
```

沙箱实现选项：
- **进程级**：subprocess + resource limits (Python)
- **容器级**：Docker/gVisor (最强隔离)
- **V8级**：vm2/isolated-vm (TypeScript)
- **WASM级**：wasmtime/wasmer (轻量级)

### 1.2 权限模型(RBAC+ABAC混合)
```yaml
permissions:
  # 基于角色的权限(RBAC)
  roles:
    viewer:
      - prompt:read
      - prompt:evaluate
    editor:
      - prompt:read
      - prompt:write
      - prompt:test
    admin:
      - prompt:*
      - runtime:*
      - security:*
  
  # 基于属性的权限(ABAC)
  rules:
    - effect: deny
      condition: prompt.security_level >= L3 AND user.clearance < L3
    - effect: deny
      condition: prompt.data_classification == PII AND action == export
    - effect: allow
      condition: user.role == admin AND action == override_security
      require_approval: true
```

### 1.3 资源限制
| 资源 | 默认限制 | 可配置 | 超限行为 |
|------|---------|--------|---------|
| Max Tokens (input) | 4,096 | ✓ | 拒绝+告警 |
| Max Tokens (output) | 2,048 | ✓ | 截断+告警 |
| Max Execution Time | 30s | ✓ | 终止+告警 |
| Max Memory | 512MB | ✓ | OOM终止 |
| Max CPU | 50% | ✓ | 限流 |
| Max Concurrent | 10 | ✓ | 排队 |
| Max Retries | 3 | ✓ | 降级 |
| Max Prompt Length | 32,768 chars | ✓ | 拒绝 |
| Rate Limit | 100/min | ✓ | 429响应 |

### 1.4 审计系统
```json
{
  "audit_log": {
    "timestamp": "2026-05-29T10:30:00Z",
    "trace_id": "abc123",
    "span_id": "def456",
    "user": "user@example.com",
    "action": "execute",
    "prompt_id": "prompt://code-review/v2",
    "prompt_version": "2.1.0",
    "model": "gpt-4",
    "input_hash": "sha256:...",
    "output_hash": "sha256:...",
    "tokens_used": 1250,
    "duration_ms": 2300,
    "security_events": [],
    "result": "success"
  }
}
```

---

## 2. 安全策略引擎

### 2.1 策略定义
```yaml
security_policy:
  name: "default-security-policy"
  version: "1.0"
  
  injection_defense:
    enabled: true
    layers:
      - name: input_validation
        rules:
          - max_length: 32768
          - allowed_chars: "UTF-8 printable"
          - deny_patterns: ["ignore_previous", "system_override"]
      
      - name: instruction_isolation
        method: "sandwich"  # system|user|system
        delimiter: "---BOUNDARY---"
      
      - name: output_filtering
        rules:
          - detect_pii: true
          - detect_secrets: true
          - format_enforcement: true
      
      - name: behavior_monitoring
        rules:
          - max_consecutive_calls: 5
          - anomaly_detection: true
          - auto_circuit_break: true
  
  data_protection:
    classification: auto
    encryption:
      at_rest: AES-256-GCM
      in_transit: TLS 1.3
      in_use: homomorphic (optional)
    masking:
      PII: "[REDACTED-PII]"
      PHI: "[REDACTED-PHI]"
      financial: "[REDACTED-FIN]"
```

---

## 3. 安全事件响应

### 3.1 事件分级
| 级别 | 类型 | 示例 | 响应SLA |
|------|------|------|---------|
| CRITICAL | 注入成功 | 提示词注入绕过防御 | ≤5min |
| HIGH | 数据泄露 | PII出现在输出 | ≤15min |
| MEDIUM | 异常行为 | 输出偏离预期 | ≤1h |
| LOW | 性能异常 | 延迟P99>阈值 | ≤4h |
| INFO | 正常防御 | 注入尝试被阻止 | 记录 |

### 3.2 熔断器配置
```yaml
circuit_breaker:
  failure_threshold: 5        # 连续失败5次
  recovery_timeout: 30s       # 30s后半开
  half_open_max_calls: 3      # 半开允许3次
  metrics_window: 60s         # 统计窗口60s
```
