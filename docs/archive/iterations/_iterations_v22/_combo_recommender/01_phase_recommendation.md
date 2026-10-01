# S2-01 提示词组合推荐器 - 项目阶段识别+最佳序列

> **迭代**：v22-S2-01 | **日期**：2026-07-12

---

## 组合推荐器

### 项目阶段识别

```json
{
  "comboRecommender": {
    "projectPhases": {
      "requirement": {
        "name": "需求阶段",
        "indicators": ["需求文档编写", "用户故事梳理", "功能优先级排序"],
        "recommendedScenes": [
          {"sceneId": "requirement-analysis", "priority": 1, "reason": "核心需求分析"},
          {"sceneId": "user-story-writing", "priority": 2, "reason": "用户故事格式化"},
          {"sceneId": "priority-matrix", "priority": 3, "reason": "优先级决策矩阵"},
          {"sceneId": "competitor-analysis", "priority": 4, "reason": "竞品分析"},
          {"sceneId": "api-design", "priority": 5, "reason": "API契约先行"}
        ],
        "sequence": "requirement-analysis → user-story-writing → priority-matrix → competitor-analysis → api-design"
      },
      "design": {
        "name": "设计阶段",
        "indicators": ["架构设计", "技术选型", "接口定义"],
        "recommendedScenes": [
          {"sceneId": "architecture-design", "priority": 1, "reason": "架构设计"},
          {"sceneId": "tech-selection", "priority": 2, "reason": "技术选型决策"},
          {"sceneId": "api-doc-generation", "priority": 3, "reason": "API文档生成"},
          {"sceneId": "db-schema-design", "priority": 4, "reason": "数据库设计"},
          {"sceneId": "security-design", "priority": 5, "reason": "安全设计审查"}
        ],
        "sequence": "architecture-design → tech-selection → api-doc-generation → db-schema-design → security-design"
      },
      "development": {
        "name": "开发阶段",
        "indicators": ["编码实现", "代码审查", "单元测试"],
        "recommendedScenes": [
          {"sceneId": "code-generation", "priority": 1, "reason": "代码生成"},
          {"sceneId": "code-review", "priority": 2, "reason": "代码审查"},
          {"sceneId": "unit-test-gen", "priority": 3, "reason": "单元测试生成"},
          {"sceneId": "debug-assistant", "priority": 4, "reason": "调试辅助"},
          {"sceneId": "refactoring", "priority": 5, "reason": "重构建议"}
        ]
      },
      "testing": {
        "name": "测试阶段",
        "indicators": ["测试用例", "集成测试", "性能测试"],
        "recommendedScenes": [
          {"sceneId": "test-case-gen", "priority": 1},
          {"sceneId": "integration-test", "priority": 2},
          {"sceneId": "perf-test", "priority": 3},
          {"sceneId": "security-test", "priority": 4},
          {"sceneId": "e2e-test", "priority": 5}
        ]
      },
      "deployment": {
        "name": "部署阶段",
        "indicators": ["CI/CD", "容器化", "环境配置"],
        "recommendedScenes": [
          {"sceneId": "dockerfile-gen", "priority": 1},
          {"sceneId": "cicd-pipeline", "priority": 2},
          {"sceneId": "k8s-manifest", "priority": 3},
          {"sceneId": "env-config", "priority": 4},
          {"sceneId": "rollback-plan", "priority": 5}
        ]
      },
      "operations": {
        "name": "运维阶段",
        "indicators": ["监控告警", "日志分析", "故障排查"],
        "recommendedScenes": [
          {"sceneId": "monitoring-config", "priority": 1},
          {"sceneId": "log-analysis", "priority": 2},
          {"sceneId": "incident-response", "priority": 3},
          {"sceneId": "capacity-planning", "priority": 4},
          {"sceneId": "cost-optimization", "priority": 5}
        ]
      }
    },
    "contextAware": {
      "alreadyUsedFilter": true,
      "complementaryBoost": 1.5,
      "conflictDetection": true
    }
  }
}
```

### 陷阱5

| # | 陷阱 | 严重等级 | 修复方法 |
|---|------|---------|---------|
| 1 | 推荐过于通用，不针对具体项目 | P1 | 项目标签+技术栈+团队规模过滤 |
| 2 | 忽略场景间依赖关系 | P1 | 依赖图+拓扑排序推荐 |
| 3 | 推荐"最优"但不"最适合" | P2 | 多目标优化(效果+成本+时间) |
| 4 | 已用场景重复推荐 | P2 | 已用过滤+互补推荐+进阶推荐 |
| 5 | 阶段判断错误 | P0 | 多信号融合+用户确认+自动修正 |

### 性能5

| # | 优化项 | 效果 |
|---|--------|------|
| 1 | 推荐结果预计算+缓存 | 推荐延迟<100ms |
| 2 | 上下文感知增量更新 | 场景变更后1s内更新推荐 |
| 3 | 多阶段批量推荐 | 6阶段同时推荐<500ms |
| 4 | 推荐解释生成 | 每场景推荐理由生成<50ms |
| 5 | A/B推荐效果对比 | 推荐采纳率统计+模型优化 |

### 最小可执行示例

```
输入：我正在开发一个Go后端API项目，刚完成技术选型
提示词：
作为提示词组合推荐器，请为当前项目推荐最佳场景组合：
- 项目阶段：设计→开发过渡期
- 技术栈：Go+PostgreSQL+Docker
- 已用场景：需求分析、技术选型
请输出：当前阶段推荐Top5场景+下一阶段推荐+场景间依赖关系。

预期输出：
{
  "currentPhase": "design_to_dev_transition",
  "recommendations": [
    {"sceneId": "api-doc-generation", "priority": 1, "reason": "API契约驱动开发"},
    {"sceneId": "db-schema-design", "priority": 2, "reason": "PG表结构设计"},
    {"sceneId": "dockerfile-gen", "priority": 3, "reason": "Go多阶段构建"},
    {"sceneId": "code-review", "priority": 4, "reason": "Go代码规范审查"},
    {"sceneId": "unit-test-gen", "priority": 5, "reason": "Go表格驱动测试"}
  ],
  "nextPhasePreview": ["code-generation", "cicd-pipeline", "integration-test"],
  "dependencies": "api-doc-generation → db-schema-design → code-generation"
}
```

### 常见错误Top5

| # | 错误 | 错误示例 | 修复方法 |
|---|------|---------|---------|
| 1 | 推荐了不兼容技术栈的场景 | 推荐Java场景给Go项目 | 技术栈标签过滤 |
| 2 | 阶段判断滞后 | 已进入开发仍推荐需求场景 | 多信号+实时判断 |
| 3 | 忽略团队规模 | 5人团队推荐企业级方案 | 团队规模权重 |
| 4 | 推荐序列不可执行 | 场景间有未满足的前置条件 | 依赖检查+前置推荐 |
| 5 | 不考虑已有模板 | 推荐用户已创建过的场景 | 去重+进阶版推荐 |
