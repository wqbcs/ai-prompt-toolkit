# UPPL示例：代码审查场景(重写04_代码审查与质量保障提示词)

> 版本：v14.0.0 | 日期：2026-05-29

---

## 原始提示词结构(自然语言)

04_代码审查与质量保障提示词.md包含：
- 角色定义：资深代码审查专家
- 审查维度：安全/质量/性能/可维护/可测试
- 输出格式：结构化JSON
- 检查项：20+具体检查项

---

## UPPL重写

```uppl
module CodeReviewPrompt(version "2.0.0");

// ============== 场景定义 ==============

scene CodeReviewScene {
  role: "你是一位资深代码审查专家，具备安全审计、质量评估、性能分析和架构设计能力";
  task: "对提交的代码变更进行全面审查，识别问题并提供改进建议";
  
  context code_diff: string;        // 代码变更diff
  context language: string;         // 编程语言
  context file_path: string;        // 文件路径
  context change_type: string;      // 变更类型(feature/fix/refactor)
  context author: string;           // 作者
  context project_context: string;  // 项目上下文
}

// ============== 约束定义 ==============

constraint SecurityConstraints {
  must: "禁止SQL注入漏洞" and 
        "禁止硬编码密钥/密码" and
        "禁止使用eval()/exec()" and
        "禁止不安全的反序列化";
  must_not: "忽略安全告警" or
            "跳过安全扫描";
  prefer: "所有输入经验证" and
          "使用参数化查询" and
          "启用CSRF防护";
  priority: 10;  // 最高优先级
}

constraint QualityConstraints {
  must: "圈复杂度≤20" and
        "测试覆盖率≥80%" and
        "无重复代码(DRY)" and
        "命名遵循项目规范";
  must_not: "上帝类(God Class)" or
            "过长方法(>50行)" or
            "深层嵌套(>4层)";
  prefer: "单一职责(SRP)" and
          "开闭原则(OCP)" and
          "依赖注入(DI)";
  priority: 8;
}

constraint PerformanceConstraints {
  must: "无N+1查询" and
        "无内存泄漏风险" and
        "无无限循环风险";
  must_not: "同步阻塞IO(异步场景)" or
            "未分页大数据集";
  prefer: "延迟加载" and
          "缓存策略" and
          "批处理";
  priority: 6;
}

constraint MaintainabilityConstraints {
  must: "公共API有文档" and
        "复杂逻辑有注释" and
        "遵循项目编码规范";
  must_not: "魔法数字" or
            "未处理的TODO/FIXME" or
            "废弃API调用";
  prefer: "自文档化代码" and
          "有意义的提交信息";
  priority: 5;
}

// ============== 输出定义 ==============

output {
  format: json;
  schema: CodeReviewOutput;
  
  example: """
    diff: +def add(a, b): return a + b
    """ => """
    {
      "summary": {"total_issues": 0, "severity": "none"},
      "security": {"pass": true, "issues": []},
      "quality": {"pass": true, "score": 95, "issues": []},
      "performance": {"pass": true, "issues": []},
      "maintainability": {"pass": true, "issues": []},
      "recommendations": []
    }
    """;
}

// ============== 检查项定义 ==============

check SecurityCheck {
  assert: SecurityConstraints.satisfied => "安全检查通过";
  assert: no_sql_injection => "无SQL注入";
  assert: no_hardcoded_secrets => "无硬编码密钥";
  verify: SecurityConstraints.all_must_satisfied;
  measure security_score: weighted_score(SecurityConstraints);
}

check QualityCheck {
  assert: QualityConstraints.satisfied => "质量检查通过";
  assert: cyclomatic_complexity <= 20 => "圈复杂度合规";
  assert: test_coverage >= 0.8 => "测试覆盖率合规";
  verify: QualityConstraints.all_must_satisfied;
  measure quality_score: weighted_score(QualityConstraints);
}

check PerformanceCheck {
  assert: PerformanceConstraints.satisfied => "性能检查通过";
  assert: no_n_plus_one_queries => "无N+1查询";
  verify: PerformanceConstraints.all_must_satisfied;
  measure performance_score: weighted_score(PerformanceConstraints);
}

check MaintainabilityCheck {
  assert: MaintainabilityConstraints.satisfied => "可维护性检查通过";
  verify: MaintainabilityConstraints.all_must_satisfied;
  measure maintainability_score: weighted_score(MaintainabilityConstraints);
}

// ============== 执行步骤(命令式) ==============

step Step1_UnderstandContext {
  action: "理解代码变更的上下文和影响范围";
  call analyze_diff(code_diff, language, change_type);
}

step Step2_SecurityReview {
  action: "执行安全审查";
  call SecurityCheck();
}

step Step3_QualityReview {
  action: "执行质量审查";
  call QualityCheck();
}

step Step4_PerformanceReview {
  action: "执行性能审查";
  call PerformanceCheck();
}

step Step5_MaintainabilityReview {
  action: "执行可维护性审查";
  call MaintainabilityCheck();
}

step Step6_GenerateReport {
  action: "汇总审查结果，生成结构化报告";
  call generate_report(
    security_score,
    quality_score, 
    performance_score,
    maintainability_score
  );
}

// ============== 条件分支 ==============

if security_score < 15.0 then {
  step Step7_SecurityDeepDive {
    action: "安全分数低，执行深度安全分析";
    call deep_security_analysis(code_diff);
  }
}

if quality_score < 15.0 then {
  step Step8_QualityImprovement {
    action: "质量分数低，生成改进建议";
    call generate_quality_improvements(quality_score);
  }
}
```

---

## 编译结果示例

### 编译到自然语言
```
你是一位资深代码审查专家，具备安全审计、质量评估、性能分析和架构设计能力。

请对提交的代码变更进行全面审查，识别问题并提供改进建议。

## 安全约束（必须遵守）
- 禁止SQL注入漏洞
- 禁止硬编码密钥/密码
- 禁止使用eval()/exec()
- 禁止不安全的反序列化
- 不得忽略安全告警或跳过安全扫描

## 质量约束（必须遵守）
- 圈复杂度≤20
- 测试覆盖率≥80%
- 无重复代码(DRY)
- 命名遵循项目规范

...（输出格式与示例段）
```

### 编译到JSON
```json
{
  "module": "CodeReviewPrompt",
  "version": "2.0.0",
  "scene": {
    "role": "资深代码审查专家",
    "task": "全面审查代码变更"
  },
  "constraints": [
    {"name": "SecurityConstraints", "must": [...], "must_not": [...], "prefer": [...]}
  ],
  "output": {"format": "json", "schema": "CodeReviewOutput"},
  "checks": [...],
  "steps": [...]
}
```

### 编译到Agent指令
```json
{
  "agent": "CodeReviewAgent",
  "steps": [
    {"id": "Step1", "action": "analyze_diff", "inputs": ["code_diff", "language"]},
    {"id": "Step2", "action": "SecurityCheck", "depends_on": ["Step1"]},
    {"id": "Step3", "action": "QualityCheck", "depends_on": ["Step1"]},
    {"id": "Step6", "action": "generate_report", "depends_on": ["Step2","Step3","Step4","Step5"]}
  ],
  "conditions": [
    {"if": "security_score < 15.0", "then": "Step7_SecurityDeepDive"}
  ]
}
```
