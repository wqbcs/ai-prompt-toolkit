# O2-1：多人协同编辑协议 - CRDT冲突解决

> **迭代编号**：O2-1 | **维度**：功能增添-AI协作 | **日期**：2026-07-11

---

## CRDT协同编辑协议

### 1. 数据模型

```typescript
interface PromptDocument {
  id: string
  version: number
  content: CRDTText
  metadata: DocumentMetadata
  operations: Operation[]
}

interface CRDTText {
  chars: Map<string, CharRecord>  // charId → CharRecord
  clock: VectorClock
}

interface CharRecord {
  id: CharID          // [replicaId, sequenceNum]
  value: string       // 字符内容
  left: CharID | null // 左邻居ID
  right: CharID | null // 右邻居ID
  deleted: boolean    // 逻辑删除标记
  originLeft: CharID | null  // 插入时的左邻居
  originRight: CharID | null // 插入时的右邻居
}

type CharID = [string, number]
type VectorClock = Map<string, number>
```

### 2. 操作类型

```typescript
type Operation = 
  | InsertOp
  | DeleteOp
  | FormatOp
  | MetaOp

interface InsertOp {
  type: 'insert'
  charId: CharID
  value: string
  leftId: CharID | null
  rightId: CharID | null
  originLeft: CharID | null
  originRight: CharID | null
}

interface DeleteOp {
  type: 'delete'
  charId: CharID
  timestamp: number
}
```

### 3. 冲突解决策略

**RGA（Replicated Growable Array）算法**：
1. 并发插入冲突：按originLeft/originRight关系排序，相同则按replicaId排序
2. 并发删除：逻辑删除，保留字符记录
3. 格式冲突：Last-Writer-Wins，按时间戳+replicaId排序

### 4. 同步协议

```
客户端A修改 → 本地应用 → 广播Operation → 客户端B接收 → 逆向转换 → 应用
```

- 每次操作附带VectorClock
- 接收方根据VectorClock确定操作顺序
- 缺失的操作请求重发
