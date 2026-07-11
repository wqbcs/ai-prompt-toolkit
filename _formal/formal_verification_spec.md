# 提示词形式化验证体系 v1.0

> **版本**：v1.0
> **日期**：2026-05-29
> **覆盖场景**：04_代码审查 / 08_安全审计（优先实施）

---

## 1. 属性规约语言

### 1.1 语言定义

属性规约语言(Prompt Property Specification Language, PPSL)用于形式化描述提示词应满足的属性，支持安全/功能/性能三类属性规约。

### 1.2 安全属性规约

```
SPEC SafetyProperties =
  // S1: 注入不可达 - 不存在注入输入使输出含恶意内容
  PROP S1_injection_unreachable =
    AG(¬∃inject ∈ AttackSet : output(inject) ∈ MaliciousContent)

  // S2: 信息不泄露 - 敏感数据不出现在输出中
  PROP S2_no_information_leak =
    AG(∀sensitive ∈ SensitiveData : output ∉ Contains(sensitive))

  // S3: 角色边界保持 - 角色始终在定义边界内
  PROP S3_role_boundary =
    AG(role ∈ DefinedRoles)

  // S4: 幻觉抑制 - 事实性声明必有来源引用
  PROP S4_hallucination_suppression =
    AG(∀claim ∈ Output : isFactual(claim) → hasCitation(claim))

  // S5: 系统提示不可变 - Agent不可修改系统提示
  PROP S5_system_prompt_immutable =
    AG(SystemPrompt = InitialSystemPrompt)

  // S6: 权限边界保持 - 操作不超出权限范围
  PROP S6_permission_boundary =
    AG(∀op ∈ Operations : op.permission ∈ AllowedPermissions)
END
```

### 1.3 功能属性规约

```
SPEC FunctionalProperties =
  // F1: 输出格式合规 - 输出必须匹配JSON Schema
  PROP F1_output_format_compliance =
    AG(output ∈ JsonSchema(DefinedSchema))

  // F2: 输出内容完整 - 所有必需字段存在
  PROP F2_output_completeness =
    AG(∀field ∈ RequiredFields : field ∈ output)

  // F3: 指令遵循 - 每条指令在输出中得到响应
  PROP F3_instruction_following =
    AG(∀instr ∈ Instructions : ∃resp ∈ Output : satisfies(resp, instr))

  // F4: 上下文传递完整 - 传递字段全部保留
  PROP F4_context_integrity =
    AG(∀field ∈ ContextFields : field ∈ nextInput)

  // F5: 检查清单覆盖 - 检查清单项全部被执行
  PROP F5_checklist_coverage =
    AG(∀item ∈ Checklist : executed(item) = true)
END
```

### 1.4 性能属性规约

```
SPEC PerformanceProperties =
  // P1: 准确率阈值
  PROP P1_accuracy_threshold =
    AG(accuracy(output) ≥ AccuracyThreshold)

  // P2: 响应时间约束
  PROP P2_response_time =
    AG(responseTime ≤ ResponseThreshold)

  // P3: 召回率阈值
  PROP P3_recall_threshold =
    AG(recall(output) ≥ RecallThreshold)

  // P4: 一致性约束
  PROP P4_consistency =
    AG(∀i1,i2 : semEq(i1,i2) → semEq(output(i1),output(i2)))
END
```

---

## 2. 04_代码审查形式化属性

```
SPEC CodeReviewProperties EXTENDS SafetyProperties, FunctionalProperties =
  // CR1: 所有发现关联具体代码位置
  PROP CR1_finding_localized =
    AG(∀finding ∈ Findings : hasLocation(finding) ∧ hasCode(finding))

  // CR2: 严重度分级正确
  PROP CR2_severity_valid =
    AG(∀finding ∈ Findings : finding.severity ∈ {critical,major,minor,info})

  // CR3: 修复建议与发现一致
  PROP CR3_fix_consistent =
    AG(∀finding ∈ Findings : finding.fix ≠ null → addresses(finding.fix, finding))

  // CR4: 安全发现不遗漏
  PROP CR4_security_complete =
    AG(∀vuln ∈ SecurityVulnerabilities : ∃finding ∈ Findings : finding.type = vuln.type)

  // CR5: 输出Schema合规
  PROP CR5_schema_compliance =
    AG(output ∈ JsonSchema(CodeReviewOutputSchema))
END
```

---

## 3. 08_安全审计形式化属性

```
SPEC SecurityAuditProperties EXTENDS SafetyProperties, FunctionalProperties =
  // SA1: 漏洞不遗漏 - OWASP Top10漏洞全部检查
  PROP SA1_owasp_coverage =
    AG(∀vuln ∈ OWASPTop10 : checked(vuln) = true)

  // SA2: 严重漏洞人工确认
  PROP SA2_critical_human_confirmed =
    AG(∀finding ∈ Findings : finding.severity = critical → humanConfirmed(finding))

  // SA3: 修复方案安全 - 修复方案不引入新漏洞
  PROP SA3_fix_safe =
    AG(∀fix ∈ Fixes : ¬introducesNewVulnerability(fix))

  // SA4: 合规检查完整
  PROP SA4_compliance_complete =
    AG(∀rule ∈ ComplianceRules : checked(rule) = true)

  // SA5: 敏感数据不泄露
  PROP SA5_no_sensitive_leak =
    AG(∀sensitive ∈ SensitiveData : output ∉ Contains(sensitive))

  // SA6: 注入攻击不可达
  PROP SA6_injection_unreachable =
    AG(¬∃inject ∈ AttackSet : auditOutput(inject) ∈ MaliciousContent)
END
```

---

## 4. 模型检查配置

### 4.1 抽象模型

```yaml
abstract_model:
  type: "finite_state_transition_system"
  states: ["initial", "input_parsed", "role_activated", "reasoning", "output_generated", "verified", "completed", "error"]
  transitions:
    - {from: "initial", to: "input_parsed", action: "parse_input"}
    - {from: "input_parsed", to: "role_activated", action: "activate_role"}
    - {from: "role_activated", to: "reasoning", action: "execute_reasoning"}
    - {from: "reasoning", to: "output_generated", action: "generate_output"}
    - {from: "output_generated", to: "verified", action: "verify_output", guard: "format_valid"}
    - {from: "output_generated", to: "error", action: "reject_output", guard: "¬format_valid"}
    - {from: "verified", to: "completed", action: "finalize"}
  abstraction_levels:
    L1: "coarse"     # 3 states: {initial, processing, terminal}
    L2: "medium"     # 5 states: {initial, parsed, processing, verified, completed}
    L3: "fine"       # 8 states: full model
    L4: "refined"    # 12+ states: with sub-steps
```

### 4.2 验证工具链

```yaml
verification_toolchain:
  model_checker:
    primary: "nuXmv"
    alternative: "ITS-Tools"
    properties: ["CTL", "LTL"]
    timeout: 30s

  proof_assistant:
    primary: "Coq"
    alternative: "Lean4"
    use: "safety_critical_proofs"

  abstraction_refinement:
    method: "CEGAR"
    initial_level: "L2"
    max_refinement: 4

  statistical_model_checking:
    tool: "UPPAAL-SMC"
    use: "large_state_spaces"
    samples: 10000
    confidence: 0.95
```

### 4.3 验证流程

```
1. 属性规约 → PPSL解析 → CTL/LTL公式
2. 提示词+模型 → 抽象建模 → 有限状态转换系统(L2)
3. 模型检查 → CTL/LTL验证
4. IF 验证通过 → 出具属性满足证明
5. IF 验证不通过 → 生成反例
6. IF 状态爆炸 → 抽象精化(CEGAR, L2→L3→L4)
7. 反例 → 提示词修正 → 重新验证(max 3轮)
8. 安全关键属性 → 交互式证明(Coq/Lean)
9. 验证报告生成
```

---

## 5. 形式化验证报告模板

```yaml
formal_verification_report:
  scenario: "场景名称"
  version: "v7.0.0"
  date: "2026-05-29"

  properties_verified:
    - id: "S1"
      name: "注入不可达"
      type: "safety"
      method: "model_checking"
      result: "satisfied|not_satisfied|inconclusive"
      proof: "证明详情链接"
      counterexample: "反例(若不满足)"

  coverage:
    total_properties: 0
    verified: 0
    coverage_rate: "0%"

  verification_depth:
    model_checking: true
    proof: false
    automated: true
    continuous_monitoring: false

  recommendations:
    - "建议修正..."
```
