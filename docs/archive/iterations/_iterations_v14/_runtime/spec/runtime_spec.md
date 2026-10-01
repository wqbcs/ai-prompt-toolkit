# 提示词运行时规范

> 版本：v14.0.0 | 日期：2026-05-29 | 规范编号：PE-RT-SPEC-001

---

## 1. 运行时架构(类比JVM规范)

### 1.1 架构总览
```
┌─────────────────────────────────────────────────┐
│              Prompt Application                  │
├─────────────────────────────────────────────────┤
│              Prompt Runtime API                  │
│  (execute/evaluate/optimize/compose)             │
├────────┬────────┬────────┬────────┬─────────────┤
│ Loader │ Parser │Validator│Executor│  Monitor    │
├────────┴────────┴────────┴────────┴─────────────┤
│           Security Manager                       │
│  (Sandbox/Permissions/ResourceLimits/Audit)      │
├─────────────────────────────────────────────────┤
│           Model Adapter Layer                    │
│  (OpenAI/Anthropic/Gemini/Local/Custom)          │
├─────────────────────────────────────────────────┤
│           Transport Layer                        │
│  (HTTP/gRPC/WebSocket/CLI)                       │
└─────────────────────────────────────────────────┘
```

### 1.2 与JVM类比
| JVM概念 | 运行时对应 | 说明 |
|---------|-----------|------|
| Class文件 | Prompt模板文件(.prompt/.uppl) | 提示词字节码 |
| ClassLoader | PromptLoader | 加载+缓存+版本管理 |
| Bytecode Verifier | PromptValidator | 语法+语义+安全验证 |
| Execution Engine | PromptExecutor | 解释执行+JIT优化 |
| Garbage Collector | ResourceReclaimer | 资源回收+缓存淘汰 |
| Security Manager | SecurityManager | 沙箱+权限+审计 |
| JMX | PromptMonitor | 运行时监控+指标 |

---

## 2. 五阶段执行模型

### 2.1 Stage 1：加载(Load)
```
Load(path/URN) → PromptArtifact

职责：
- 从注册表/文件系统/远程仓库加载提示词
- 版本解析(最新/指定/兼容)
- 缓存管理(LRU+TTL)
- 依赖解析(提示词链依赖)

输出：PromptArtifact(源码+元数据+版本信息)
```

### 2.2 Stage 2：解析(Parse)
```
Parse(PromptArtifact) → PromptAST

职责：
- 语法解析(UPPL/自然语言/JSON)
- AST构建(角色/任务/约束/输出/示例)
- 变量槽位提取
- 模板参数绑定

输出：PromptAST(抽象语法树+绑定信息)
```

### 2.3 Stage 3：验证(Validate)
```
Validate(PromptAST, Context) → ValidationResult

职责：
- 语法验证(结构完整性)
- 语义验证(意图可达性)
- 安全验证(注入检测+权限检查)
- 约束验证(约束一致性)
- 资源验证(Token预算+时间预算)

输出：ValidationResult(pass/fail + 诊断信息)
```

### 2.4 Stage 4：执行(Execute)
```
Execute(PromptAST, Context, Options) → ExecutionResult

职责：
- 模型适配(Adapter选择+参数映射)
- 请求构建(系统指令+用户输入+约束注入)
- 安全防护(输入消毒+指令隔离)
- 模型调用(重试+超时+降级)
- 输出处理(格式校验+Schema验证+安全过滤)
- 审计记录(输入/输出/耗时/Token/安全)

输出：ExecutionResult(output + metrics + audit)
```

### 2.5 Stage 5：监控(Monitor)
```
Monitor(ExecutionResult) → Metrics + Alerts

职责：
- 性能指标收集(延迟/吞吐/Token/错误率)
- 安全事件检测(注入尝试/异常输出/权限越界)
- 质量漂移检测(输出质量退化)
- 告警触发(阈值+异常检测)
- 遥测上报(OpenTelemetry)

输出：Metrics(指标) + Alerts(告警)
```

---

## 3. 运行时生命周期管理

### 3.1 提示词生命周期状态机
```
Draft → Staged → Active → Deprecated → Retired
  ↑                  ↓
  └──── Rollback ────┘
```

| 状态 | 允许操作 | 说明 |
|------|---------|------|
| Draft | edit/test/evaluate | 开发中 |
| Staged | review/promote/rollback | 待发布 |
| Active | execute/evaluate/monitor | 生产可用 |
| Deprecated | execute(警告)/migrate | 已废弃(6月过渡) |
| Retired | 无 | 已退役 |

### 3.2 版本管理
- 遵循SemVer 2.0
- 并行版本支持(主版本N/N-1)
- 灰度发布( Canary → 10% → 50% → 100%)
- 即时回滚(≤30s)

---

## 4. 性能指标与监控

### 4.1 核心指标
| 指标 | 类型 | 说明 |
|------|------|------|
| pe_execute_duration | Histogram | 执行延迟(ms) |
| pe_execute_total | Counter | 执行总数 |
| pe_execute_errors | Counter | 执行错误数 |
| pe_tokens_total | Counter | Token消耗总数 |
| pe_injection_attempts | Counter | 注入攻击尝试数 |
| pe_injection_blocked | Counter | 注入防御成功数 |
| pe_evaluation_score | Gauge | 评估分数 |
| pe_cache_hit_rate | Gauge | 缓存命中率 |
| pe_resource_usage | Gauge | 资源使用率 |

### 4.2 监控集成
- **指标**：OpenTelemetry → Prometheus/Grafana
- **日志**：Structured JSON → ELK/Loki
- **追踪**：OpenTelemetry → Jaeger/Zipkin
- **告警**：Prometheus AlertManager
