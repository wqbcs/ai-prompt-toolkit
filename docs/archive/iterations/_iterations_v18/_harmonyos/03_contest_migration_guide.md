# O4-6~7：鸿蒙赛事专项提示词与迁移指南

> **迭代编号**：O4-6~7 | **维度**：赛事贴合度-鸿蒙专项 | **日期**：2026-07-11

---

## OSC 2026 鸿蒙赛道专项提示词

### 赛事关键要求
1. 使用HarmonyOS NEXT / OpenHarmony开发
2. ArkTS/ArkUI声明式开发范式
3. 体现分布式能力
4. 适配多设备形态
5. 开源协议合规

### 赛事评分维度映射

| 评分维度 | 提示词场景 | 覆盖率 |
|---------|-----------|--------|
| 技术创新 | 分布式能力开发 | 95% |
| 代码质量 | ArkTS编码规范+性能优化 | 90% |
| 用户体验 | ArkUI界面开发 | 90% |
| 安全合规 | 安全合规检查 | 85% |
| 生态适配 | OpenHarmony适配 | 80% |

---

## 开发者迁移指南

### 从Android迁移

| Android概念 | HarmonyOS对应 | 说明 |
|-------------|--------------|------|
| Activity | UIAbility | 页面容器 |
| Service | ExtensionAbility | 后台服务 |
| BroadcastReceiver | CommonEvent | 事件通知 |
| ContentProvider | DataShareExtension | 数据共享 |
| Fragment | 自定义@Component | UI组件 |
| ViewModel | @State/@Link | 状态管理 |
| RecyclerView | List/Grid+LazyForEach | 列表渲染 |
| Retrofit | @ohos/axios | 网络请求 |
| Room | @ohos/data-relational | 数据库 |
| Hilt | 系统无DI框架 | 需自建 |

### 从iOS/SwiftUI迁移

| SwiftUI概念 | ArkUI对应 | 说明 |
|-------------|----------|------|
| @State | @State | 相同 |
| @Binding | @Link | 双向绑定 |
| @ObservedObject | @Observed+@ObjectLink | 观测对象 |
| @EnvironmentObject | @Provide+@Consume | 环境注入 |
|NavigationView | NavRouter | 导航 |
| List | List+LazyForEach | 列表 |
| URLSession | @ohos/axios | 网络请求 |
| Core Data | @ohos/data-relational | 数据库 |

### 从Flutter迁移

| Flutter概念 | ArkUI对应 | 说明 |
|-------------|----------|------|
| StatefulWidget | @Component+@State | 有状态组件 |
| Provider/Riverpod | @Provide/@Consume | 状态管理 |
| Navigator | NavRouter | 导航 |
| ListView.builder | List+LazyForEach | 列表 |
| Platform Channel | NAPI | 原生交互 |
| pub.dev | ohpm | 包管理 |
