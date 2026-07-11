# 场景间上下文传递标准 v2.0

> **版本**：v2.0
> **日期**：2026-05-29
> **适用**：AI提示词体系55场景模板间数据/上下文传递

---

## 一、上下文传递架构

### 1.1 上下文封装格式

```json
{
  "context": {
    "global": {
      "project_info": {
        "name": "<项目名>",
        "tech_stack": ["<技术栈>"],
        "industry": "<行业>",
        "team_size": "<团队规模>"
      },
      "user_info": {
        "role": "<用户角色>",
        "expertise_level": "<专业水平>"
      },
      "execution_meta": {
        "session_id": "<会话ID>",
        "timestamp": "<ISO8601时间戳>",
        "version": "v6.0.0"
      }
    },
    "local": {
      "upstream_outputs": [
        {
          "scenario_id": "<前序场景ID>",
          "document_id": "<文档编号>",
          "output_summary": "<输出摘要>",
          "output_artifacts": ["<产出物列表>"],
          "quality_score": "<质量评分>"
        }
      ],
      "current_state": {
        "scenario_id": "<当前场景ID>",
        "step_index": "<当前步骤序号>",
        "checkpoint": "<断点位置>"
      },
      "error_context": {
        "has_error": false,
        "error_type": null,
        "error_message": null,
        "recovery_strategy": null
      }
    }
  }
}
```

### 1.2 上下文传递规则

| 规则ID | 规则名称 | 定义 | 验收条件 |
|--------|----------|------|----------|
| CCR-01 | 字段完整性 | 全局上下文所有必需字段必须传递至下游 | 下游接收字段数 = 源发送字段数 |
| CCR-02 | 语义零漂移 | 上下文传递后语义不得发生偏移 | 语义等价性校验通过 |
| CCR-03 | 类型安全 | 传递字段类型必须与接口定义一致 | 类型校验100%通过 |
| CCR-04 | 默认值填充 | 可选字段缺失时使用默认值而非省略 | 无null必需字段 |
| CCR-05 | 错误隔离 | 单场景错误不传播至无关节点 | 错误隔离域正确 |

---

## 二、场景间数据传递契约标准

### 2.1 契约定义格式

每个场景间传递关系必须定义以下YAML契约：

```yaml
contract:
  source: "<源场景ID>"
  target: "<目标场景ID>"
  version: "v2.0"
  field_mappings:
    - source_field: "<源字段路径>"
      target_field: "<目标字段路径>"
      type: "<数据类型>"
      required: true|false
      default: "<默认值>"
      transform: "<转换规则>"
      semantic_check: "<语义校验规则>"
  validation_rules:
    - rule: "<校验规则描述>"
      severity: "error|warning"
```

### 2.2 核心工作流传递契约

#### 2.2.1 01→02 需求→架构传递

```yaml
contract:
  source: "01_需求分析"
  target: "02_架构设计"
  version: "v2.0"
  field_mappings:
    - source_field: "output.prd_document"
      target_field: "input.business_requirements"
      type: object
      required: true
      transform: "extract_functional_requirements"
      semantic_check: "需求完整且无矛盾"
    - source_field: "output.user_story_list"
      target_field: "input.user_stories"
      type: array
      required: true
      transform: "normalize_story_format"
    - source_field: "output.priority_matrix"
      target_field: "input.priority_weights"
      type: object
      required: true
      transform: "map_to_architecture_concern_weights"
    - source_field: "output.mvp_scope"
      target_field: "input.mvp_boundary"
      type: array
      required: false
      default: []
```

#### 2.2.2 04→03 审查→编码传递

```yaml
contract:
  source: "04_代码审查"
  target: "03_编码规范"
  version: "v2.0"
  field_mappings:
    - source_field: "output.issues"
      target_field: "input.code_issues"
      type: array
      required: true
      transform: "filter_actionable_issues"
    - source_field: "output.recommendation"
      target_field: "input.refactoring_guidance"
      type: object
      required: true
```

#### 2.2.3 04→05 审查→测试传递

```yaml
contract:
  source: "04_代码审查"
  target: "05_全维度测试"
  version: "v2.0"
  field_mappings:
    - source_field: "output.issues"
      target_field: "input.risk_areas"
      type: array
      required: true
      transform: "map_severity_to_risk_level"
    - source_field: "output.score"
      target_field: "input.quality_baseline"
      type: number
      required: true
```

---

## 三、Prompt Chaining零损耗协议v2.0

### 3.1 链式执行状态管理

```yaml
chain_execution:
  chain_id: "<链路唯一ID>"
  workflow: "<工作流名称>"
  status: "running|paused|completed|failed"
  steps:
    - step_id: "<步骤ID>"
      scenario_id: "<场景ID>"
      status: "pending|running|completed|failed|skipped"
      input_hash: "<输入数据哈希>"
      output_hash: "<输出数据哈希>"
      started_at: "<ISO8601>"
      completed_at: "<ISO8601>"
      quality_score: <0-20>
  checkpoint:
    last_completed_step: "<最后完成步骤ID>"
    next_step: "<下一待执行步骤ID>"
    preserved_outputs: ["<已保留的输出引用>"]
```

### 3.2 断点续传

| 条件 | 行为 |
|------|------|
| 链路中断(网络/超时) | 从checkpoint.next_step恢复执行 |
| 单步骤失败 | 标记该步骤failed，根据错误策略决定是否跳过或重试 |
| 全局上下文丢失 | 从preserved_outputs重建上下文 |
| 质量门禁未通过 | 暂停链路，等待人工确认后继续 |

### 3.3 错误传播与隔离

```yaml
error_policy:
  propagation: "isolated"
  isolation_scope: "step"
  retry:
    max_attempts: 3
    backoff: "exponential"
    retryable_errors: ["timeout", "rate_limit", "transient_failure"]
  fallback:
    on_non_retryable: "skip_and_log"
    on_max_retries_exceeded: "fail_chain"
  notification:
    on_step_failure: true
    on_chain_failure: true
```

---

## 四、9条工作流接口转换规则

| 工作流 | 涉及场景 | 关键传递点 | 零损耗保障 |
|--------|----------|------------|------------|
| 需求→架构→编码 | 01→02→03 | PRD→架构设计→编码规范 | 字段映射+语义校验 |
| 编码→审查→测试 | 03→04→05 | 代码→审查结果→测试策略 | 风险等级映射+覆盖矩阵 |
| 部署→监控→安全 | 06→07→08 | 部署配置→监控指标→安全基线 | 配置一致性+指标覆盖 |
| 性能→优化→验证 | 09→09(自迭代) | 基线→瓶颈→优化方案→验证 | 基准对比+回归校验 |
| 需求→项目管理 | 01→11 | PRD→项目计划 | 需求-任务双向追溯 |
| 架构→技术文档 | 02→10 | 架构决策→技术文档 | ADR→文档章节映射 |
| 全链路质量 | 04→05→06 | 质量门禁→测试通过→部署准入 | 门禁级联+质量传递 |
| 安全→合规→审计 | 08→08(深化) | 漏洞→修复→复测 | 漏洞生命周期管理 |
| 运维→AI专项 | 07→12 | 运维数据→AI开发策略 | 数据驱动+反馈闭环 |
