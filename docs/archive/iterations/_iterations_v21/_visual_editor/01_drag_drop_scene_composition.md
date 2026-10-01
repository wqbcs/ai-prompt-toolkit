# R1-01 提示词可视化编辑器-拖拽式场景组合

> **迭代**：v21-R1-01 | **日期**：2026-07-12

---

## 一、可视化编辑器架构

### 核心概念

```
┌─────────────────────────────────────────────┐
│            可视化编辑器 (Visual Editor)        │
├─────────┬──────────┬──────────┬──────────────┤
│ 组件面板 │ 画布区域  │ 属性面板  │ 实时预览      │
│         │          │          │              │
│ [场景]  │ ┌──┐     │ 场景名:  │ # 输出预览    │
│ [陷阱]  │ │S1├─┐   │ xxx      │              │
│ [性能]  │ └──┘ │   │ 陷阱: 5  │ 1. xxx       │
│ [安全]  │ ┌──┐ ↓   │ 性能: 5  │ 2. xxx       │
│ [输出]  │ │S2├─┐   │ 安全: 5  │ 3. xxx       │
│         │ └──┘ │   │          │              │
│ [前置]  │ ┌──┐ ↓   │ [应用]   │ [刷新]       │
│ [扩展]  │ │S3├─┘   │ [重置]   │              │
│         │ └──┘     │          │              │
└─────────┴──────────┴──────────┴──────────────┘
```

### 组件类型定义

```typescript
interface VisualEditorComponent {
  id: string
  type: 'scenario' | 'trap' | 'performance' | 'security' | 'output' | 'prerequisite' | 'extension'
  label: string
  icon: string
  category: string
  draggable: boolean
  configurable: boolean
  defaultConfig: Record<string, unknown>
}

interface VisualEditorNode {
  id: string
  componentId: string
  position: { x: number; y: number }
  config: Record<string, unknown>
  connections: {
    input: string[]
    output: string[]
  }
}

interface VisualEditorEdge {
  id: string
  source: string
  target: string
  type: 'sequence' | 'parallel' | 'conditional'
  condition?: string
  label?: string
}
```

## 二、拖拽式场景组合

### 6种组合模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| 顺序组合 | 场景1→场景2→场景3 | 逐步深化型提示词 |
| 并行组合 | 场景1∥场景2∥场景3 | 多视角对比型提示词 |
| 条件组合 | IF条件→场景A/场景B | 分支选择型提示词 |
| 循环组合 | REPEAT N次→场景 | 迭代优化型提示词 |
| 嵌套组合 | 场景包含子场景 | 层级结构型提示词 |
| 混合组合 | 上述任意组合 | 复杂提示词 |

### 拖拽交互设计

| 操作 | 手势 | 效果 |
|------|------|------|
| 添加组件 | 从面板拖到画布 | 创建新节点 |
| 删除组件 | 右键→删除/拖到回收站 | 删除节点+连线 |
| 连接组件 | 从输出端口拖到输入端口 | 创建连线 |
| 断开连接 | 点击连线→Delete | 删除连线 |
| 移动组件 | 拖拽节点 | 更新位置 |
| 复制组件 | Ctrl+拖拽 | 克隆节点+配置 |
| 批量选择 | 框选/Shift+点击 | 多节点操作 |

### 场景模板库

```typescript
interface ScenarioTemplate {
  id: string
  name: string
  category: 'python' | 'frontend' | 'database' | 'microservice' | 'huawei_cloud' | 'agent' | 'rag' | 'mlops' | 'security'
  description: string
  prerequisites: string[]
  components: VisualEditorComponent[]
  defaultLayout: 'horizontal' | 'vertical' | 'grid'
  estimatedTokens: number
}
```

## 三、实时预览引擎

### 预览策略

| 触发 | 延迟 | 范围 |
|------|------|------|
| 节点配置变更 | 300ms防抖 | 仅变更节点 |
| 连线变更 | 500ms防抖 | 受影响路径 |
| 模板加载 | 即时 | 全量 |
| 手动刷新 | 即时 | 全量 |

### 预览输出格式

```markdown
# {场景组合标题}

## 前置知识
- {来自前置知识节点}

## 场景1: {名称}
{场景内容}

## 常见陷阱
{来自陷阱节点}

## 性能提示
{来自性能节点}

## 安全提示
{来自安全节点}

## 请输出
{来自输出节点}

## 扩展阅读
{来自扩展阅读节点}
```

## 四、验收项

- [x] 可视化编辑器架构设计（4面板布局）
- [x] 6种拖拽组合模式定义
- [x] 7种拖拽交互操作设计
- [x] 场景模板库数据结构
- [x] 实时预览引擎（3种触发策略+输出格式）
