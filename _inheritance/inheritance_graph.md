# 继承关系图谱

> **版本**: v1.0.0 | **日期**: 2026-07-12

---

## 一、InheritanceGraph数据结构

```typescript
interface InheritanceGraph {
  nodes: TemplateNode[];
  edges: InheritanceEdge[];
  last_updated: string;  // ISO 8601
}

interface TemplateNode {
  template_id: string;
  template_name: string;
  depth: number;             // 继承深度
  status: "active" | "deprecated" | "broken";
  broken_reason?: string;    // 链断裂原因
  child_count: number;       // 直接子模板数量
  last_modified: string;     // ISO 8601
}

interface InheritanceEdge {
  parent_id: string;
  child_id: string;
  override_fields: string[];   // 子模板覆盖的字段路径
  extension_fields: string[];  // 子模板新增的字段路径
  has_conflict: boolean;       // 是否存在冲突
  conflict_fields?: string[];  // 冲突字段
}
```

## 二、循环继承检测算法

### 2.1 DFS检测环

```
function detectCycle(graph, startNode):
    visited = Set()
    recursionStack = Set()

    function dfs(node):
        visited.add(node)
        recursionStack.add(node)

        for neighbor in graph.getNeighbors(node):
            if neighbor not in visited:
                if dfs(neighbor):
                    return true
            elif neighbor in recursionStack:
                return true  // 检测到环

        recursionStack.remove(node)
        return false

    return dfs(startNode)
```

### 2.2 检测示例

```
正常继承链: base → go-review → fin-go-review ✅ 无环

循环继承: A → B → C → A ❌ 检测到环
  - DFS从A开始: A→B→C→A（A在recursionStack中）
  - 报告: "检测到循环继承: A→B→C→A"
  - 处理: 拒绝创建继承关系
```

## 三、深度检测算法

### 3.1 深度计算

```
function calculateDepth(template_id, graph):
    depth = 0
    current = template_id

    while graph.getParent(current) != null:
        depth += 1
        current = graph.getParent(current)
        if depth > 5:
            return depth  // 超出限制
        if graph.getNode(current).status == "broken":
            return -1  // 链断裂

    return depth
```

### 3.2 深度限制

| 深度 | 状态 | 说明 |
|------|------|------|
| 0 | ✅ | 根模板，无继承 |
| 1 | ✅ | 一级继承 |
| 2 | ✅ | 二级继承 |
| 3 | ✅ | 三级继承 |
| 4 | ✅ | 四级继承 |
| 5 | ✅ | 最大允许深度 |
| 6+ | ❌ | 超出限制，拒绝创建 |

## 四、继承链断裂检测

### 4.1 断裂场景

| 场景 | 原因 | 检测方式 |
|------|------|----------|
| 父模板被删除 | 管理员删除了父模板 | 遍历edges，parent_id不在nodes中 |
| 父模板被废弃 | 父模板标记为deprecated | 遍历edges，parent_id对应status=deprecated |
| 存储损坏 | 模板文件损坏 | 读取模板文件时异常 |

### 4.2 断裂处理

```
当检测到继承链断裂时:
1. 将子模板标记为 status="broken"
2. 记录 broken_reason="父模板{parent_id}已删除/废弃"
3. 通知子模板的所有下游模板
4. 建议修复方案: 重新指定父模板或移除继承关系
```

## 五、继承关系图谱可视化

### 5.1 图谱示例

```
代码审查领域继承图谱:

base-code-review [depth=0, active]
├── go-code-review [depth=1, active]
│   ├── fin-go-review [depth=2, active]
│   └── devops-go-review [depth=2, active]
├── python-code-review [depth=1, active]
│   └── ml-python-review [depth=2, active]
└── java-code-review [depth=1, deprecated]  ← 废弃
    └── spring-java-review [depth=2, broken] ← 链断裂

架构设计领域继承图谱:

base-arch-design [depth=0, active]
├── microservice-arch [depth=1, active]
│   └── k8s-microservice [depth=2, active]
├── monolith-arch [depth=1, active]
└── serverless-arch [depth=1, active]
```

### 5.2 统计信息

| 指标 | 值 |
|------|-----|
| 总模板数 | 207 |
| 根模板数 | 45 |
| 继承模板数 | 162 |
| 最大深度 | 3 |
| 平均深度 | 1.6 |
| 循环继承 | 0 |
| 断裂链 | 1 |
