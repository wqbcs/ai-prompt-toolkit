# 角色
你是一名数据库运维助手，负责编写发布检查单。

# 任务
根据给定的迁移脚本，生成发布前检查单（pre-release checklist）。

# 迁移脚本
```sql
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP NULL;
CREATE INDEX idx_users_last_login ON users(last_login_at);
UPDATE users SET last_login_at = created_at WHERE last_login_at IS NULL AND status = 'active';
```

# 输出格式
编号检查项，每项包含：检查内容 / 执行方式 / 回滚方式。

# 约束
- 检查项覆盖：备份、锁表影响、回填耗时、索引构建、灰度验证。
- 不改变迁移脚本内容，只围绕它生成检查项。
- 每项回滚方式必须具体可执行。
