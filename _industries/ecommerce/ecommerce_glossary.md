# 电商行业术语表

> **版本**：v1.0.0
> **覆盖**：电商平台运营、交易、促销、供应链

---

| 序号 | 术语 | 英文 | 分类 | 定义 |
|------|------|------|------|------|
| 1 | 秒杀 | Flash Sale | 促销 | 限时限量极低价销售，瞬时极高并发场景 |
| 2 | 库存预占 | Stock Pre-hold | 交易 | 下单时临时锁定库存，支付后确认扣减，超时释放 |
| 3 | 超卖 | Overselling | 交易 | 实际销售数量超过库存数量的异常 |
| 4 | TCC事务 | Try-Confirm-Cancel | 事务 | 分布式事务模式：预留→确认→取消三阶段 |
| 5 | Saga事务 | Saga Pattern | 事务 | 长事务模式：正向操作序列+反向补偿操作序列 |
| 6 | 本地消息表 | Local Message Table | 事务 | 可靠消息最终一致性方案：业务操作和消息记录在同一事务 |
| 7 | 对账 | Reconciliation | 交易 | 多系统间数据一致性比对，发现差异并处理 |
| 8 | 分库分表 | Sharding | 架构 | 按策略将数据分散到多个数据库/表，提升并发和存储能力 |
| 9 | 读写分离 | Read-Write Splitting | 架构 | 写操作走主库，读操作走从库，提升读并发能力 |
| 10 | 弹性伸缩 | Elastic Scaling | 架构 | 根据负载自动增减实例数(HPA/VPA) |
| 11 | 降级 | Degradation | 架构 | 高负载时关闭非核心功能，保障核心链路可用 |
| 12 | 熔断 | Circuit Breaker | 架构 | 下游异常率超阈值时自动断开，防止级联故障 |
| 13 | 限流 | Rate Limiting | 架构 | 限制单位时间请求数，保护系统不被过载 |
| 14 | 游标分页 | Cursor Pagination | 性能 | 基于游标(而非offset)的分页，避免深分页性能问题 |
| 15 | SKU | Stock Keeping Unit | 商品 | 最小库存单位，如红色XL码的某款衣服 |
| 16 | SPU | Standard Product Unit | 商品 | 标准商品单元，同一款商品(多SKU的抽象) |
| 17 | 促销叠加 | Promotion Stacking | 促销 | 多种促销(满减+折扣+优惠券)同时生效的规则 |
| 18 | 划线价 | Listed Price | 合规 | 商品原价展示，促销法要求真实且有依据 |
| 19 | 最低毛利保护 | Minimum Margin Protection | 促销 | 确保促销后售价不低于成本+最低毛利率 |
| 20 | 设备指纹 | Device Fingerprint | 风控 | 基于设备硬件/软件特征生成的唯一标识，用于防刷 |
| 21 | 延迟消息 | Delayed Message | 技术 | 延迟指定时间后投递的消息，用于超时未支付自动取消等 |
| 22 | 乐观锁 | Optimistic Lock | 技术 | 基于版本号的并发控制，更新时检查版本号是否变化 |
| 23 | 补接页 | Landing Page | 运营 | 营销活动入口页面，高并发+高转化率设计 |
| 24 | 转化率 | Conversion Rate | 运营 | 下单数/访客数，衡量营销效果的核心指标 |
| 25 | 客单价 | Average Order Value | 运营 | 总销售额/订单数，衡量消费水平 |
| 26 | 复购率 | Repurchase Rate | 运营 | 重复购买用户占比，衡量用户粘性 |
| 27 | 购物车 abandonment | Cart Abandonment Rate | 运营 | 加购未下单占比，衡量购物流程体验 |
| 28 | 全链路压测 | Full-Chain Stress Test | 性能 | 模拟真实用户完整购物链路的压测，验证全链路容量 |
| 29 | 大促预案 | Promotion Contingency Plan | 运维 | 大促活动的技术预案(容量/降级/回滚/应急) |
| 30 | 动态定价 | Dynamic Pricing | 运营 | 基于供需/竞争/时间等因素的实时价格调整 |
