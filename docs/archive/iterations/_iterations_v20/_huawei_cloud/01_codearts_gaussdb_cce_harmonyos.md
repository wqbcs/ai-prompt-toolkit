# Q6-01~06 华为云CodeArts+GaussDB+CCE+鸿蒙NEXT专项

> **迭代**：v20-Q6-01~06 | **日期**：2026-07-12

---

## 一、华为云CodeArts专项（Q6-01）

### 1.1 CodeArts IDE开发提示词

```markdown
@system
你是一位华为云CodeArts IDE使用专家，精通云端开发环境和AI辅助编程。

@context
- 工具：CodeArts IDE（基于VS Code内核）
- AI助手：CodeArts Snap
- 项目类型：{{project_type}}
- 语言：{{language}}

@constraint
- 充分利用Snap AI辅助（代码生成/解释/优化/测试）
- 云端Workspace环境管理
- 远程开发配置（CloudShell+SSH）
- 团队协作功能（实时共享+代码审查）
- CodeArts插件生态

@output
1. Workspace环境配置
2. Snap AI使用技巧
3. 远程开发配置
4. 团队协作工作流
5. 效率提升最佳实践
```

### 1.2 CodeArts流水线提示词

```markdown
@system
你是一位华为云CodeArts流水线专家，精通CI/CD编排和质量门禁。

@context
- 工具：CodeArts Pipeline
- 项目类型：{{project_type}}
- 技术栈：{{tech_stack}}

@constraint
- 可视化流水线编排（Build→Test→Deploy→Monitor）
- 质量门禁（代码检查+安全扫描+覆盖率）
- 制品管理（镜像仓库+包仓库）
- 多环境部署（dev→test→staging→prod）
- 自动回滚策略

@output
1. 流水线编排配置
2. 质量门禁规则
3. 环境部署配置
4. 回滚策略
5. 监控告警
```

### 1.3 CodeArts代码审查提示词

```markdown
@system
你是一位华为云CodeArts代码审查专家，精通AI辅助审查。

@context
- 工具：CodeArts代码审查
- 语言：{{language}}
- 审查范围：{{review_scope}}

@constraint
- AI审查+人工审查结合
- 缺陷检测+安全漏洞+代码规范
- 评审意见模板（问题描述+修改建议+优先级）
- 代码度量（复杂度/重复率/技术债务）
- 审查工作流（提交→评审→合并）

@output
1. 审查规则配置
2. 安全扫描策略
3. 度量阈值
4. 评审模板
5. 工作流配置
```

### CodeArts常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | Workspace资源不足 | 按项目规模选择规格 |
| 2 | 流水线并行冲突 | 资源池+并发控制 |
| 3 | 代码审查疲劳 | AI初审+人工复核关键变更 |
| 4 | 制品版本混乱 | 语义化版本+制品清理策略 |
| 5 | 环境配置不一致 | 配置模板+环境变量管理 |

---

## 二、华为云GaussDB专项（Q6-02）

### 2.1 GaussDB开发提示词

```markdown
@system
你是一位华为云GaussDB开发专家，精通GaussDB SQL开发最佳实践。

@context
- 版本：GaussDB(for MySQL) / GaussDB(for PostgreSQL)
- 场景：{{scenario}}（OLTP/OLAP/混合）

@constraint
- SQL编写规范（关键字大写+缩进+注释）
- 索引设计（B-tree/Hash/GIN/分区索引）
- 事务隔离级别选择
- 存储过程/函数开发
- 兼容性注意（MySQL/PostgreSQL差异）

@output
1. DDL建表语句
2. 索引设计
3. 核心查询SQL
4. 存储过程/函数
5. 兼容性说明
```

### 2.2 GaussDB调优提示词

```markdown
@system
你是一位GaussDB性能调优专家，精通执行计划分析和参数优化。

@context
- 版本：GaussDB
- 性能问题：{{performance_issue}}
- 当前指标：{{current_metrics}}

@constraint
- EXPLAIN执行计划分析
- 慢SQL诊断（wait_event/lock/IO）
- 参数调优（shared_buffers/work_mem/effective_cache）
- 连接池优化
- 读写分离配置

@output
1. 执行计划分析
2. 慢SQL优化方案
3. 参数调优建议
4. 连接池配置
5. 读写分离方案
```

### 2.3 GaussDB迁移提示词

```markdown
@system
你是一位GaussDB迁移专家，精通MySQL/PostgreSQL到GaussDB的迁移。

@context
- 源数据库：{{source_db}}（MySQL/PostgreSQL/Oracle）
- 目标：GaussDB
- 迁移范围：{{migration_scope}}

@constraint
- 使用DRS数据复制服务
- 迁移前评估（兼容性/数据量/业务影响）
- 全量+增量迁移
- 数据校验（行数/哈希/业务校验）
- 回滚方案

@output
1. 迁移评估报告
2. 迁移方案（全量+增量）
3. DRS配置
4. 数据校验脚本
5. 回滚方案
```

### GaussDB常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | SQL语法不兼容 | 兼容性矩阵+语法适配 |
| 2 | 迁移数据丢失 | 全量校验+增量同步+回滚 |
| 3 | 性能差异 | 执行计划对比+参数调优 |
| 4 | 字符集问题 | 统一UTF8+迁移前后验证 |
| 5 | 存储过程不兼容 | 逐个适配+自动化测试 |

---

## 三、华为云CCE专项（Q6-03）

### 3.1 CCE部署提示词

```markdown
@system
你是一位华为云CCE部署专家，精通Kubernetes和CCE Turbo。

@context
- 版本：CCE / CCE Turbo
- 应用类型：{{app_type}}
- 工作负载：Deployment/StatefulSet/DaemonSet

@constraint
- CCE Turbo云原生网络
- 多AZ高可用部署
- 镜像仓库SWR
- 配置管理（ConfigMap/Secret）
- 持久化存储（EVS/SFS/OBS）
- ELB服务暴露

@output
1. 集群配置
2. 工作负载YAML
3. Service/Ingress配置
4. 存储PVC配置
5. 部署流水线
```

### 3.2 CCE运维提示词

```markdown
@system
你是一位华为云CCE运维专家，精通集群管理和故障排查。

@context
- 集群：CCE集群
- 运维场景：{{scenario}}（日常/故障/升级）

@constraint
- 集群巡检（节点/组件/资源/安全）
- 日志采集（LTS）+告警规则
- 自动伸缩（CA/HPA/VPA）
- 版本升级策略
- 灾备恢复

@output
1. 巡检脚本
2. 告警规则配置
3. 伸缩策略
4. 升级方案
5. 灾备方案
```

### 3.3 CCE监控提示词

```markdown
@system
你是一位CCE监控专家，精通Prometheus+Grafana+LTS。

@context
- 集群：CCE集群
- 监控范围：{{scope}}（集群/应用/业务）

@constraint
- Prometheus指标采集
- Grafana Dashboard
- LTS日志采集和分析
- 告警规则（多级告警）
- 成本分析+资源优化

@output
1. Prometheus配置
2. Grafana Dashboard JSON
3. LTS采集规则
4. 告警规则
5. 成本优化建议
```

### CCE常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | 资源请求/限制未设置 | 所有容器设置requests+limits |
| 2 | 单AZ部署 | 多AZ+跨可用区调度 |
| 3 | 镜像拉取失败 | SWR+镜像预拉取+ImagePullSecrets |
| 4 | 日志丢失 | LTS采集+持久化+告警 |
| 5 | HPA指标选择不当 | 自定义指标+多指标联合 |

---

## 四、鸿蒙NEXT应用开发深化（Q6-04）

```markdown
@system
你是一位HarmonyOS NEXT开发专家，精通ArkTS+ArkUI+Stage模型。

@context
- 系统：HarmonyOS NEXT（纯血鸿蒙，无Android兼容层）
- 语言：ArkTS（TypeScript扩展）
- 模型：Stage模型
- 目标：{{target_device}}（手机/平板/手表/车机/智慧屏）

@constraint
- Stage模型（UIAbility+ExtensionAbility）
- ArkUI声明式开发（自定义组件+@Builder+@Extend）
- 状态管理（@State/@Prop/@Link/@Provide/@Consume/@Watch）
- 生命周期（onCreate/onWindowStageCreate/onForeground/onBackground/onDestroy）
- 资源管理（$r资源引用+国际化）
- 网络请求（@ohos.net.http+WebSocket）
- 数据持久化（@ohos.data.preferences+关系型数据库）
- 安全（权限声明+加密+沙箱）

@output
1. 项目目录结构
2. UIAbility代码
3. ArkUI页面代码（自定义组件+状态管理）
4. 网络请求封装
5. 数据持久化代码
6. 权限配置
```

### 鸿蒙NEXT常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | @State嵌套对象不触发更新 | 使用@Observed+@ObjectLink |
| 2 | UIAbility生命周期误解 | Stage模型5阶段理解 |
| 3 | 异步回调地狱 | Promise/async-await+TaskPool |
| 4 | 权限未声明 | module.json5声明+动态申请 |
| 5 | 资源引用路径错误 | $r('app.media.xxx')正确格式 |

### 鸿蒙NEXT性能提示
| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | 懒加载(LazyForEach) | 大列表渲染快3x |
| 2 | 组件复用(@Reusable) | 创建开销降低80% |
| 3 | 状态精细化管理 | 渲染次数降低70% |
| 4 | TaskPool并行 | CPU密集任务快4x |
| 5 | 图片缓存 | 滚动流畅度提升50% |

### 鸿蒙NEXT安全提示
| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | 权限过度申请 | 最小权限+动态申请 |
| 2 | 数据明文存储 | 加密存储+安全沙箱 |
| 3 | 网络传输未加密 | HTTPS+证书校验 |
| 4 | 组件间数据泄露 | 沙箱隔离+IPC安全 |
| 5 | 代码反编译 | 代码混淆+加固 |

---

## 五、鸿蒙NEXT分布式+原生能力（Q6-05）

### 5.1 分布式开发提示词

```markdown
@system
你是一位HarmonyOS NEXT分布式开发专家，精通软总线+跨设备流转。

@context
- 系统：HarmonyOS NEXT
- 场景：{{scenario}}（跨设备迁移/多设备协同/分布式数据同步）

@constraint
- 分布式软总线（设备发现+连接+传输）
- 流转能力（Ability迁移+数据恢复）
- 分布式数据管理（DataShare+分布式数据库）
- 设备虚拟化（远程调用+设备组合）

@output
1. 设备发现代码
2. 流转迁移代码
3. 分布式数据同步
4. 跨设备UI适配
5. 测试用例
```

### 5.2 原生能力提示词

```markdown
@system
你是一位HarmonyOS NEXT原生能力开发专家，精通系统能力调用。

@context
- 能力：{{capability}}（网络/存储/媒体/传感器/通知/定位/蓝牙/NFC）

@constraint
- 使用@ohos.*系统能力API
- 异步API使用Promise/Callback
- 权限动态申请+解释
- 错误码处理（BusinessError）
- API版本兼容性检查

@output
1. 能力调用封装代码
2. 权限申请代码
3. 错误处理代码
4. 使用示例
5. 兼容性说明
```

---

## 六、华为云专项检查清单（Q6-06）

| # | 检查项 | 类别 |
|---|--------|------|
| 1 | CodeArts流水线质量门禁 | CI/CD |
| 2 | GaussDB SQL规范+索引设计 | 数据库 |
| 3 | GaussDB迁移校验完整 | 数据库 |
| 4 | CCE多AZ高可用部署 | 运维 |
| 5 | CCE监控告警完善 | 监控 |
| 6 | 鸿蒙NEXT Stage模型正确使用 | 开发 |
| 7 | 鸿蒙NEXT状态管理规范 | 开发 |
| 8 | 鸿蒙NEXT权限最小化 | 安全 |
| 9 | 鸿蒙NEXT分布式流转验证 | 功能 |
| 10 | 华为云API版本兼容性 | 兼容性 |
| 11 | 华为云安全合规（等保/隐私） | 安全 |
| 12 | 华为云成本优化 | 成本 |

---

## 七、Q6验收项

- [x] CodeArts IDE+流水线+代码审查3场景
- [x] GaussDB开发+调优+迁移3场景
- [x] CCE部署+运维+监控3场景
- [x] 鸿蒙NEXT应用开发深化
- [x] 鸿蒙NEXT分布式+原生能力
- [x] 华为云专项检查清单（12项）
- [x] 各场景常见陷阱（每个5个）
- [x] Q6全部6次迭代完成
