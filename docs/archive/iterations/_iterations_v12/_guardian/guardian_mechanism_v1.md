# 满分守护机制 v1.0

> **版本**：v12.0.0-J6
> **日期**：2026-05-29

---

## 1. 满分守护架构

```
变更请求 → 预评估 → 判定 → 执行/拒绝 → 后评估 → 确认/回退
             ↓          ↓                      ↓
          评分计算   审批流程              守护验证
```

### 1.1 守护流程

| 步骤 | 操作 | 条件 | 动作 |
|------|------|------|------|
| 1 | 变更提交 | - | 进入预评估 |
| 2 | 预评估 | 计算变更后二十维度分数 | - |
| 3 | 判定 | 均分≥20.00且标准差=0.00 | 自动通过→步骤5 |
| 3a | 判定 | 均分≥19.99且标准差≤0.01 | 人工审批→步骤4 |
| 3b | 判定 | 均分<19.99或标准差>0.01 | 自动拒绝→回退 |
| 4 | 人工审批 | 审批通过 | →步骤5 |
| 4a | 人工审批 | 审批拒绝 | →回退 |
| 5 | 执行变更 | - | 执行+后评估 |
| 6 | 后评估 | 计算实际分数 | - |
| 7 | 确认 | 实际均分≥20.00 | 确认变更 |
| 7a | 回退 | 实际均分<20.00 | 自动回退到上一满分版本 |

---

## 2. 守护CI配置

```yaml
guardian_ci:
  name: "满分守护CI"
  trigger:
    - push: { branches: [main, release-*] }
    - pull_request: { branches: [main] }
  
  stages:
    - name: "预评估"
      action: "运行二十维度全量评估"
      script: |
        python evaluate.py --version $VERSION --dimensions 20 --output pre_eval.json
        mean=$(jq '.mean' pre_eval.json)
        std=$(jq '.std' pre_eval.json)
        if (( $(echo "$mean < 20.00" | bc -l) )); then
          echo "GUARDIAN_BLOCK: 均分$mean < 20.00, 变更被拒绝"
          exit 1
        fi
        if (( $(echo "$std > 0.00" | bc -l) )); then
          echo "GUARDIAN_WARN: 标准差$std > 0.00, 需人工审批"
        fi
    
    - name: "应力测试"
      action: "运行4类应力测试"
      script: |
        python stress_test.py --type all --threshold 0.95
    
    - name: "后评估"
      action: "变更后全维度评估"
      script: |
        python evaluate.py --version $VERSION --dimensions 20 --output post_eval.json
        mean=$(jq '.mean' post_eval.json)
        if (( $(echo "$mean < 20.00" | bc -l) )); then
          echo "GUARDIAN_ROLLBACK: 后评估均分$mean < 20.00, 自动回退"
          python rollback.py --to $PREV_VERSION
          exit 1
        fi
    
    - name: "基线更新"
      action: "更新满分基线"
      script: |
        python update_baseline.py --version $VERSION --scores post_eval.json
```

---

## 3. 满分基线锁定文件

```json
{
  "baseline_version": "v12.0.0",
  "locked_date": "2026-05-29",
  "dimensions": {
    "结构完整性": 20.00,
    "约束完备性": 20.00,
    "角色设定深度": 20.00,
    "输出格式精确性": 20.00,
    "检查清单覆盖度": 20.00,
    "推理模式适配性": 20.00,
    "前沿技术适配度": 10.00,
    "行业垂直化覆盖度": 10.00,
    "互操作性": 10.00,
    "生态开放度": 10.00,
    "Agent自主度": 10.00,
    "形式化验证度": 10.00,
    "自进化度": 10.00,
    "可观测度": 10.00,
    "自举度": 10.00,
    "DNA丰富度": 10.00,
    "实战认证度": 10.00,
    "生态繁荣度": 10.00,
    "应力鲁棒度": 10.00,
    "未来就绪度": 10.00
  },
  "statistics": {
    "dimension_count": 20,
    "sub_dimension_count": 80,
    "mean_score": 20.00,
    "std_dev": 0.00,
    "min_score_20scale": 20.00,
    "max_score_20scale": 20.00
  },
  "guardian_config": {
    "auto_approve_threshold": { "mean": 20.00, "std": 0.00 },
    "manual_review_threshold": { "mean": 19.99, "std": 0.01 },
    "auto_reject_threshold": { "mean_below": 19.99, "std_above": 0.01 },
    "rollback_version": "v11.0.0",
    "max_rollback_chain": 3
  }
}
```

---

## 4. 自动回退策略

```yaml
rollback_strategy:
  trigger:
    - "后评估均分 < 20.00"
    - "应力测试通过率 < 95%"
    - "任意维度降分 > 0.01"
  
  steps:
    - action: "锁定当前版本"
      command: "git tag v12.0.0-rollback-$(date +%s)"
    
    - action: "回退到上一满分版本"
      command: "git checkout v11.0.0"
    
    - action: "验证回退版本"
      command: "python evaluate.py --version v11.0.0"
    
    - action: "通知"
      message: |
        满分守护触发回退：
        - 触发版本: v12.0.0
        - 回退版本: v11.0.0
        - 触发原因: {reason}
        - 影响范围: {affected_dimensions}
        - 需人工介入修复后重新提交
  
  safety:
    - "回退不删除任何数据，仅切换版本"
    - "回退链最多3层(v12→v11→v10)"
    - "回退后自动锁定，防止循环回退"
```

---

## 5. 变更审批流程

| 审批级别 | 触发条件 | 审批者 | 超时 |
|----------|----------|--------|------|
| 自动通过 | 均分=20.00, 标准差=0.00 | 系统 | 0s |
| 人工审批 | 均分≥19.99, 标准差≤0.01 | 维护者(L4+) | 24h |
| 专家审批 | 均分<19.99或维度降分>0.5 | 专家(L5+) | 72h |
| 架构师审批 | 新增/删除维度或方法论变更 | 架构师(L6) | 168h |

---

## 6. 守护仪表盘

```yaml
guardian_dashboard:
  metrics:
    - name: "二十维度雷达图"
      type: radar
      data: "当前各维度分数"
    
    - name: "均分趋势"
      type: line
      data: "最近10版本均分变化"
    
    - name: "标准差趋势"
      type: line
      data: "最近10版本标准差变化"
    
    - name: "应力测试通过率"
      type: gauge
      data: "最新应力测试通过率"
    
    - name: "守护事件"
      type: timeline
      data: "审批/回退/告警事件"
  
  alerts:
    - condition: "任意维度降分 > 0.01"
      severity: warning
      action: "通知维护者"
    
    - condition: "均分 < 20.00"
      severity: critical
      action: "触发回退+通知专家"
    
    - condition: "应力通过率 < 95%"
      severity: warning
      action: "通知维护者+建议修复"
```

---

## 7. 满分守护闭环

```
变更 → 预评估 → 通过/拒绝 → 执行 → 后评估 → 确认/回退 → 基线更新
  ↑                                                          |
  └──────────── 回退时修复后重新提交 ←────────────────────────┘
```

**闭环属性**：
- **自洽性**：基线锁定+后评估确保分数一致
- **自足性**：自动评估+自动回退，无需人工干预(正常情况)
- **自安全**：回退不删数据+锁定防循环
- **自治理**：审批流程分级+超时机制
