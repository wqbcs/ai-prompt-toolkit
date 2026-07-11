# O2-3：评论与批注系统

> **迭代编号**：O2-3 | **维度**：功能增添-AI协作 | **日期**：2026-07-11

---

## 评论与批注系统

### 1. 评论模型

```typescript
interface Comment {
  id: string
  documentId: string
  version: number
  range: TextRange        // 评论范围
  content: string          // 评论内容
  author: UserInfo
  type: CommentType
  status: CommentStatus
  replies: Comment[]
  reactions: Reaction[]
  createdAt: string
  updatedAt: string
  resolvedAt?: string
}

type CommentType = 
  | 'suggestion'   // 建议修改
  | 'question'     // 疑问
  | 'issue'        // 问题
  | 'approval'     // 认可
  | 'ai-review'    // AI审查意见

type CommentStatus = 'open' | 'resolved' | 'dismissed'

interface TextRange {
  startLine: number
  startCol: number
  endLine: number
  endCol: number
  selectedText: string
}
```

### 2. 批注类型

| 批注 | 图标 | 用途 |
|------|------|------|
| 💡 建议 | 建议修改措辞/结构 |
| ❓ 疑问 | 对内容不理解 |
| ⚠️ 问题 | 发现错误/矛盾 |
| ✅ 认可 | 同意当前表述 |
| 🤖 AI审查 | AI自动审查意见 |

### 3. 评论线程

```
评论 → 回复1 → 回复2（解决）→ [标记已解决]
     → 回复3（新问题）→ [重新打开]
```

### 4. AI辅助评论

- 自动检测潜在问题并生成AI审查意见
- 根据评论历史学习团队偏好
- 建议评论的回复内容
- 自动将重复性评论转化为检查清单项
