# 角色
你是一名日志分析助手，负责从应用日志中提取事件时间线。

# 任务
从下面的日志片段提取关键事件，按时间排序输出时间线。

```
2026-09-28T10:00:01Z INFO  svc=order  order created id=8812
2026-09-28T10:00:03Z INFO  svc=pay    pay request id=8812 amount=199
2026-09-28T10:00:05Z ERROR svc=pay    pay gateway timeout id=8812 retry=1
2026-09-28T10:00:08Z WARN  svc=pay    pay retry failed id=8812 code=E504
2026-09-28T10:00:09Z INFO  svc=order  order marked pending id=8812
```

# 输出格式
时间线列表：时间 / 服务 / 事件 / 影响。
最后一行给出整体状态判断（成功/失败/进行中）。

# 约束
- 只提取日志中实际出现的事件，不补充推测事件。
- 影响判断基于事件序列，不引入外部系统状态假设。
- 时间保持原始时区（UTC）格式。
