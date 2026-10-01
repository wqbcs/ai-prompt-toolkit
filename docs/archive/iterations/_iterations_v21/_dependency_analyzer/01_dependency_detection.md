# R2-01 提示词依赖分析器-场景依赖检测

> **迭代**：v21-R2-01 | **日期**：2026-07-12

---

## 一、依赖分析器架构

### 核心概念

```typescript
interface PromptDependencyGraph {
  nodes: DependencyNode[]
  edges: DependencyEdge[]
  cycles: DependencyCycle[]
  orphans: string[]             // 孤立节点(无依赖无被依赖)
  clusters: DependencyCluster[] // 依赖集群
}

interface DependencyNode {
  id: string
  type: 'scenario' | 'template' | 'variable' | 'checklist' | 'glossary' | 'workflow'
  name: string
  version: string
  category: string
  metadata: Record<string, unknown>
}

interface DependencyEdge {
  source: string
  target: string
  type: 'requires' | 'extends' | 'includes' | 'references' | 'conflicts'
  strength: 'hard' | 'soft'      // hard=必须满足 soft=可选
  description: string
}

interface DependencyCycle {
  nodes: string[]
  edges: DependencyEdge[]
  severity: 'error' | 'warning'
  suggestion: string
}

interface DependencyCluster {
  id: string
  name: string
  nodes: string[]
  cohesion: number               // 内聚度0-1
  coupling: number               // 耦合度0-1
}
```

## 二、5种依赖类型

| 类型 | 说明 | 示例 |
|------|------|------|
| requires | 必须依赖 | FastAPI场景→Python基础场景 |
| extends | 扩展依赖 | 华为云DWS场景→数据库基础场景 |
| includes | 包含依赖 | 完整审查→代码风格+安全+性能检查 |
| references | 引用依赖 | 场景→术语表/检查清单 |
| conflicts | 冲突标记 | React场景↔Vue场景互斥 |

## 三、循环依赖检测

### 检测算法

```
1. 构建有向图 G(V, E)
2. DFS遍历，维护访问栈
3. 遇到栈中节点→发现环
4. 记录环路径+严重等级
5. 生成解环建议
```

### 解环策略

| 策略 | 说明 | 适用 |
|------|------|------|
| 断开弱依赖 | 移除soft类型边 | 循环含soft依赖 |
| 提取公共层 | 将循环部分提取为独立节点 | 多节点循环 |
| 延迟加载 | 运行时动态解析 | 可接受的循环 |
| 事件驱动 | 改requires为事件通知 | 异步场景 |

## 四、影响范围分析

### 变更影响评估

```typescript
interface ImpactAnalysis {
  changedNode: string
  changeType: 'added' | 'modified' | 'removed' | 'deprecated'
  directImpact: ImpactDetail[]
  transitiveImpact: ImpactDetail[]
  totalAffected: number
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  recommendedActions: string[]
}

interface ImpactDetail {
  node: string
  path: string[]                // 影响路径
  impactType: 'breaking' | 'behavioral' | 'performance' | 'cosmetic'
  description: string
  autoFixable: boolean
}
```

### 影响等级分类

| 等级 | 变更类型 | 影响范围 | 动作 |
|------|---------|---------|------|
| critical | 删除核心场景 | 全局 | 阻止+告警 |
| high | 修改requires依赖 | 直接+间接 | 审批+测试 |
| medium | 修改extends依赖 | 直接 | 通知+验证 |
| low | 修改references | 仅直接 | 记录+检查 |

## 五、验收项

- [x] 依赖图数据结构（6种节点+5种边）
- [x] 循环依赖检测算法+4种解环策略
- [x] 影响范围分析（4级风险+4种影响类型）
- [x] 依赖集群分析（内聚度+耦合度）
