# DeepSeek-V3 CoT+自纠错组合适配指令

> **版本**：v1.0.0
> **日期**：2026-05-29
> **迭代**：C10-迭代47
> **适用场景**：04_代码审查/08_安全审计/09_性能优化

---

## 一、适配原理

DeepSeek-V3核心优势在于代码理解(95分)和推理深度(90分)，但结构化输出稳定性较弱(82分)。CoT+自纠错组合策略可最大化其推理优势，同时通过自纠错循环弥补输出格式不稳定的缺陷。

---

## 二、场景适配指令

### 2.1 04_代码审查场景A(增量审查) CoT+自纠错

```markdown
<!-- DeepSeek-V3 适配指令 -->
【DeepSeek-V3 CoT+自纠错优化】

请按以下步骤逐步分析代码变更：

**Step 1: 代码理解**
- 读取变更diff，理解每个hunk的修改意图
- 识别涉及的模块、类、方法及其调用关系
- 标注变更类型：新增/修改/删除/重构

**Step 2: 逐维度审查（CoT推理）**
- 正确性：逻辑错误、边界条件、异常处理、空指针
- 安全性：OWASP Top10、输入验证、权限检查、SQL注入
- 性能：N+1查询、连接池泄漏、GC压力、算法复杂度
- 可维护性：命名规范、注释充分、代码结构、SOLID原则

**Step 3: 严重度评估**
- P0(阻断)：安全漏洞/数据丢失/服务不可用
- P1(严重)：逻辑错误/性能退化>10%
- P2(一般)：代码规范/可维护性
- P3(建议)：优化建议/最佳实践

**Step 4: 修复方案生成**
- 对P0/P1问题给出可直接应用的修复代码
- 对P2/P3问题给出修改建议和示例

**Step 5: 自纠错循环**
完成后执行自检：
- [ ] 检查项1：所有P0/P1问题是否都有修复方案？
- [ ] 检查项2：修复方案是否可直接应用（无语法错误）？
- [ ] 检查项3：审查是否覆盖了所有变更文件？
- [ ] 检查项4：输出格式是否符合JSON规范？
如发现遗漏或错误，立即补充修正。

**Step 6: 结构化输出强制**
请严格按照以下JSON格式输出审查报告：
```json
{
  "summary": {"total_files": 0, "total_issues": 0, "p0_count": 0, "p1_count": 0},
  "issues": [{"id": "", "severity": "P0|P1|P2|P3", "category": "", "description": "", "location": "", "fix": ""}],
  "quality_score": 0,
  "recommendation": "APPROVE|REQUEST_CHANGES|BLOCK"
}
```
输出必须是合法JSON，可直接被JSON.parse()解析。不要在JSON前后添加任何文字。
```

### 2.2 08_安全审计场景A(安全审计) CoT+自纠错

```markdown
<!-- DeepSeek-V3 适配指令 -->
【DeepSeek-V3 安全审计CoT+自纠错优化】

请按以下攻击者思维逐步分析：

**Step 1: 攻击面识别**
- 入口点：API端点、用户输入、文件上传、外部服务调用
- 数据流：敏感数据流转路径、存储位置、传输方式
- 信任边界：内部/外部服务边界、认证/授权边界

**Step 2: STRIDE威胁建模**
- Spoofing(仿冒)：身份认证绕过可能
- Tampering(篡改)：数据完整性破坏可能
- Repudiation(抵赖)：审计日志缺失可能
- Information Disclosure(信息泄露)：敏感数据暴露可能
- Denial of Service(拒绝服务)：资源耗尽可能
- Elevation of Privilege(提权)：权限提升可能

**Step 3: 漏洞深度分析（CoT推理）**
对每个威胁构建攻击链：
- 攻击前提 → 攻击步骤1 → ... → 攻击步骤N → 攻击影响
- 评估可利用性：高/中/低
- 评估影响范围：系统级/应用级/数据级

**Step 4: 防御方案生成**
- 纵深防御：网络层+应用层+数据层+监控层
- 每层防御措施含具体实施代码/配置

**Step 5: 自纠错循环**
完成后执行自检：
- [ ] OWASP Top10是否逐项检查？
- [ ] 每个威胁是否都有对应的防御方案？
- [ ] 防御方案是否可落地（含具体实施步骤）？
- [ ] 是否考虑了合规要求（等保2.0/GDPR/个保法）？
如发现遗漏，立即补充。

**Step 6: 结构化输出强制**
请严格按照以下JSON格式输出审计报告：
```json
{
  "audit_summary": {"scope": "", "risk_level": "HIGH|MEDIUM|LOW", "total_findings": 0},
  "threats": [{"id": "", "stride_category": "", "attack_chain": "", "exploitability": "", "impact": "", "defense": ""}],
  "compliance_gaps": [{"regulation": "", "requirement": "", "gap": "", "remediation": ""}],
  "hardening_plan": [{"priority": "", "measure": "", "implementation": ""}]
}
```
输出必须是合法JSON。
```

### 2.3 09_性能优化场景B(性能优化) CoT+自纠错

```markdown
<!-- DeepSeek-V3 适配指令 -->
【DeepSeek-V3 性能优化CoT+自纠错优化】

请按以下方法论逐步分析：

**Step 1: 基线建立**
- 当前性能指标：QPS/延迟P50/P95/P99/错误率
- 资源利用率：CPU/内存/磁盘IO/网络IO/连接池
- 识别正常与异常区间

**Step 2: 瓶颈识别（CoT推理）**
- 应用USL通用可扩展性定律分析：X(N)=λN/(1+σ(N-1)+κN(N-1))
- 应用Little's Law验证：L=λ×W
- 识别瓶颈类型：CPU密集/IO密集/锁竞争/内存分配/GC压力

**Step 3: 根因分析**
- 对每个瓶颈构建因果链：现象→指标→代码路径→根因
- 验证假设：是否可通过profiling/flame-graph确认

**Step 4: 优化方案生成**
- 每个根因给出2-3种优化方案
- 评估优化效果预期：改善幅度/实施成本/风险等级
- 给出具体代码/配置修改

**Step 5: 自纠错循环**
完成后执行自检：
- [ ] 是否覆盖了所有性能瓶颈？
- [ ] 每个优化方案是否有预期效果数据？
- [ ] 是否考虑了优化引入的风险（如正确性/兼容性）？
- [ ] 是否给出了验证方法（压测/回归/监控）？
如发现遗漏，立即补充。

**Step 6: 结构化输出强制**
请严格按照以下JSON格式输出优化报告：
```json
{
  "baseline": {"qps": 0, "latency_p95": 0, "error_rate": 0},
  "bottlenecks": [{"id": "", "type": "", "root_cause": "", "evidence": ""}],
  "optimizations": [{"bottleneck_id": "", "approach": "", "expected_improvement": "", "risk": "", "code_change": ""}],
  "verification": {"load_test_plan": "", "regression_scope": "", "monitoring_metrics": []}
}
```
输出必须是合法JSON。
```

---

## 三、适配效果预期

| 维度 | 适配前 | 适配后 | 提升 |
|------|--------|--------|------|
| 指令遵循率 | 88 | 92 | +4 |
| 输出格式稳定性 | 82 | 88 | +6 |
| 推理深度利用 | 85 | 93 | +8 |
| 自纠错覆盖率 | 0 | 90 | +90 |

---

*本文件为C10批次迭代47产出，为DeepSeek-V3在04/08/09场景的CoT+自纠错组合适配指令。*
