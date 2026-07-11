# SaaS行业术语表

> **版本**：v1.0.0
> **覆盖**：多租户架构、计费模型、SaaS运营、平台工程

---

| 序号 | 术语 | 英文 | 分类 | 定义 |
|------|------|------|------|------|
| 1 | 多租户 | Multi-Tenancy | 架构 | 单一软件实例服务多个客户(租户)，数据逻辑或物理隔离 |
| 2 | 租户隔离 | Tenant Isolation | 架构 | 确保不同租户数据/资源/配置互不可见的机制 |
| 3 | 行级隔离 | Row-Level Isolation | 架构 | 共享表+tenant_id列区分数据，最轻量隔离方式 |
| 4 | Schema隔离 | Schema-Level Isolation | 架构 | 共享数据库+独立Schema，中等隔离强度 |
| 5 | 库级隔离 | Database-Level Isolation | 架构 | 独立数据库，高隔离强度，适合敏感客户 |
| 6 | 租户上下文 | Tenant Context | 架构 | 请求处理链中自动传播的租户标识信息 |
| 7 | 按量计费 | Pay-As-You-Go | 计费 | 按实际使用量(API调用/存储/计算)计费 |
| 8 | 按席位计费 | Per-Seat Pricing | 计费 | 按活跃用户/授权账号数计费 |
| 9 | 预扣费 | Pre-Deduction | 计费 | 资源创建前预扣费用，创建成功后确认，失败回退 |
| 10 | 欠费处理 | Dunning | 计费 | 欠费后的分级处理：预警→限制→暂停→回收 |
| 11 | 按功能计费 | Feature-Based Pricing | 计费 | 按套餐/功能模块访问权限差异化计费 |
| 12 | 混合计费 | Hybrid Pricing | 计费 | 多种计费模型组合(基础费+按量+席位) |
| 13 | 功能开关 | Feature Flag/Toggle | 平台 | 运行时控制功能可用性的开关，支持租户级/全局级 |
| 14 | 租户配置 | Tenant Configuration | 平台 | 每租户独立的配置项(主题/字段/流程/规则) |
| 15 | 白标化 | White-Labeling | 平台 | 允许租户使用自有品牌/域名/外观的SaaS能力 |
| 16 | 租户上线 | Tenant Onboarding | 运营 | 新租户注册→环境初始化→数据导入→培训的全流程 |
| 17 | 租户注销 | Tenant Offboarding | 运营 | 租户退出→数据导出→数据删除→资源回收的全流程 |
| 18 | 被遗忘权 | Right to Be Forgotten | 合规 | GDPR赋予数据主体要求删除其个人数据的权利 |
| 19 | 数据驻留 | Data Residency | 合规 | 数据物理存储在特定地理区域的法律要求 |
| 20 | 密钥派生 | Key Derivation | 安全 | 从主密钥和租户ID派生每租户独立加密密钥(HKDF) |
| 21 | 密钥轮换 | Key Rotation | 安全 | 定期更换加密密钥，旧数据用版本化密钥解密 |
| 22 | 用量计量 | Usage Metering | 计费 | 精确采集和记录租户资源使用量的系统 |
| 23 | 账单对账 | Billing Reconciliation | 计费 | 用量记录与账单金额的一致性验证 |
| 24 | 计费异常 | Billing Anomaly | 计费 | 用量或费用偏离历史基线的异常情况 |
| 25 | 租户迁移 | Tenant Migration | 运营 | 租户在不同隔离级别/区域/版本间的数据迁移 |
| 26 | 差异化SLA | Tiered SLA | 运营 | 按套餐/价格提供不同等级的SLA保障 |
| 27 | 平台工程 | Platform Engineering | 技术 | 为SaaS开发团队提供自助式基础设施和工具的工程实践 |
| 28 | 自助服务 | Self-Service | 运营 | 租户无需人工介入即可完成开通/配置/扩容等操作 |
| 29 | 插件隔离 | Plugin Isolation | 安全 | 租户自定义插件在沙箱中运行，不影响平台稳定性 |
| 30 | 零停机升级 | Zero-Downtime Upgrade | 技术 | 平台升级不影响租户使用，通过蓝绿/滚动部署实现 |
