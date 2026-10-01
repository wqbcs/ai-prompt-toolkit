# O2-5：实时协作通信协议

> **迭代编号**：O2-5 | **维度**：功能增添-AI协作 | **日期**：2026-07-11

---

## WebSocket通信协议

### 1. 消息格式

```typescript
interface CollabMessage {
  type: MessageType
  roomId: string
  sender: string
  payload: any
  timestamp: number
  seqNum: number
}

type MessageType = 
  | 'join'          // 加入房间
  | 'leave'         // 离开房间
  | 'sync'          // 全量同步
  | 'operation'     // CRDT操作
  | 'cursor'        // 光标位置
  | 'selection'     // 选区
  | 'comment'       // 评论
  | 'presence'      // 在线状态
  | 'heartbeat'     // 心跳
```

### 2. 连接生命周期

```
1. 客户端连接WebSocket
2. 发送join消息（含文档ID+用户信息）
3. 服务端返回sync消息（完整文档状态）
4. 客户端应用sync，进入编辑状态
5. 编辑操作通过operation消息广播
6. 定期发送heartbeat保持连接
7. 断开时发送leave消息
```

### 3. 断线重连

- 本地操作缓存：断线期间的操作保存在本地
- 重连后发送缓冲操作
- 服务端根据VectorClock合并
- 超时未重连自动释放锁

### 4. 性能优化

- 操作压缩：连续单字符插入合并为批量插入
- 增量同步：只传输diff
- 防抖：100ms内操作合并发送
- 离线支持：IndexedDB本地持久化
