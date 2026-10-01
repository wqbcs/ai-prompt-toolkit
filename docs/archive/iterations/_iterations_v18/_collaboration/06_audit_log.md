# O2-6：协作历史与审计日志

> **迭代编号**：O2-6 | **维度**：功能增添-AI协作 | **日期**：2026-07-11

---

## 审计日志模型

```typescript
interface AuditLog {
  id: string
  documentId: string
  action: AuditAction
  actor: UserInfo
  timestamp: string
  details: AuditDetails
  ipAddress: string
  userAgent: string
}

type AuditAction = 
  | 'view' | 'edit' | 'delete' | 'restore'
  | 'comment_add' | 'comment_resolve' | 'comment_dismiss'
  | 'review_submit' | 'review_approve' | 'review_reject'
  | 'publish' | 'rollback' | 'lock' | 'unlock'
  | 'permission_change' | 'member_add' | 'member_remove'
```

### 活动时间线

```
2026-07-11 10:00  张三 创建文档
2026-07-11 10:15  李四 加入编辑
2026-07-11 10:30  张三 编辑"架构设计"段落
2026-07-11 10:35  AI助手 审查建议(3条)
2026-07-11 10:40  李四 评论"建议补充性能指标"
2026-07-11 11:00  张三 解决评论
2026-07-11 11:15  李四 提交审核
2026-07-11 11:30  王五 审核通过
2026-07-11 11:35  王五 发布v18.0.0
```

### 数据保留策略
- 操作日志：永久保留
- CRDT操作历史：保留最近1000个版本
- 评论：永久保留（已解决评论90天后归档）
- 审计日志：永久保留
