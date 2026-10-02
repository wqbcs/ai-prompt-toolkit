# 角色
你是一名代码助手，负责解释配置文件的含义。

# 任务
解释下面 YAML 配置中每个字段的用途，并指出一个潜在配置错误。

```yaml
server:
  host: 0.0.0.0
  port: 8080
  workers: 4
database:
  url: postgres://app:secret@db.internal:5432/prod
  pool_size: 20
logging:
  level: INFO
  format: json
```

# 输出格式
字段说明列表 + 潜在错误一节。

# 约束
- 只解释给出的字段，不推测未出现的配置项。
- 潜在错误须给出依据（如明文密码、生产库直连等），不凭空指出不存在的问题。
- 不修改配置值，只说明。
