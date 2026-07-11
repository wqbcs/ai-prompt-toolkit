# O4-4~5：ArkTS/ArkUI专项检查清单与OpenHarmony适配指南

> **迭代编号**：O4-4~5 | **维度**：赛事贴合度-鸿蒙专项 | **日期**：2026-07-11

---

## ArkTS/ArkUI专项检查清单

### 编码规范检查

- [ ] 文件命名：小写+短横线（如 `user-profile.ets`）
- [ ] 组件命名：大驼峰（如 `UserProfile`）
- [ ] 函数命名：小驼峰（如 `handleClick`）
- [ ] 常量命名：全大写+下划线（如 `MAX_RETRY_COUNT`）
- [ ] 严格模式：启用strictPropertyInitialization
- [ ] 禁止any类型：使用具体类型或泛型
- [ ] 禁止as类型断言：使用类型守卫

### 装饰器使用规范

- [ ] @State：仅用于组件内私有状态，简单类型优先
- [ ] @Prop：父→子单向传递，子组件不可修改
- [ ] @Link：需要双向绑定时使用，传递@State变量引用
- [ ] @Provide/@Consume：跨层级传递，避免prop drilling
- [ ] @Watch：监听状态变化，避免在回调中修改被监听状态
- [ ] @Observed：嵌套对象观测，配合@ObjectLink使用
- [ ] @Builder：抽取UI构建逻辑，避免build()过长
- [ ] @Extend：扩展原生组件样式，无状态逻辑

### 生命周期管理

- [ ] aboutToAppear：初始化数据，不发耗时请求
- [ ] aboutToDisappear：清理资源，取消定时器
- [ ] onPageShow：页面显示时刷新数据
- [ ] onPageHide：页面隐藏时暂停动画
- [ ] onBackPress：处理返回键，含确认对话框

### 内存泄漏检测

- [ ] 定时器在aboutToDisappear中清除
- [ ] 事件订阅在aboutToDisappear中取消
- [ ] Worker在aboutToDisappear中终止
- [ ] 文件句柄在aboutToDisappear中关闭
- [ ] 避免循环引用：组件不持有自身引用

---

## OpenHarmony适配指南

### API差异矩阵

| 能力 | HarmonyOS NEXT | OpenHarmony 5.x | 差异 |
|------|---------------|-----------------|------|
| 推送服务 | Push Kit | 无 | 需自建推送 |
| 地图服务 | Map Kit | 无 | 需集成第三方地图 |
| 支付服务 | Payment Kit | 无 | 需集成第三方支付 |
| 分享服务 | Share Kit | 部分支持 | 需自行实现 |
| 认证服务 | Account Kit | 无 | 需自建账户体系 |
| AI服务 | MindSpore Kit | 部分支持 | 能力有限 |

### 三方库替代方案

| HarmonyOS库 | OpenHarmony替代 | 说明 |
|-------------|----------------|------|
| @hms/push | 自建WebSocket推送 | 需自行实现 |
| @hms/map | AMAP/百度地图SDK | 需适配ohpm |
| @hms/analytics | 自建埋点方案 | 需自行实现 |
| @hms/ads | 自建广告系统 | 需自行实现 |

### 适配检查清单

- [ ] API调用使用兼容层封装
- [ ] 三方库有OpenHarmony替代方案
- [ ] 华为服务调用可降级处理
- [ ] 测试覆盖OpenHarmony目标设备
- [ ] ohpm依赖声明完整
