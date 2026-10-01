# O5-6~7：Flutter赛事专项与开发者迁移指南

> **迭代编号**：O5-6~7 | **维度**：赛事贴合度-Flutter专项 | **日期**：2026-07-11

---

## OSC 2026 Flutter赛道专项提示词

### 赛事关键要求
1. 使用Flutter/Dart跨平台开发
2. 适配至少2个平台（Android+iOS优先）
3. 体现鸿蒙/HarmonyOS适配能力
4. 性能优化达标
5. 开源协议合规

### 赛事评分维度映射

| 评分维度 | 提示词场景 | 覆盖率 |
|---------|-----------|--------|
| 跨平台能力 | Widget+平台通道 | 95% |
| 代码质量 | Dart编码规范+状态管理 | 90% |
| 用户体验 | UI开发+性能优化 | 90% |
| 鸿蒙适配 | 平台通道+ohos插件 | 75% |
| 性能表现 | 性能优化场景 | 85% |

---

## Flutter开发者迁移指南

### 从React Native迁移

| React Native | Flutter | 说明 |
|-------------|---------|------|
| JSX | Widget树 | 声明式UI |
| useState | @State (StatefulWidget) | 本地状态 |
| useContext | InheritedWidget/Provider | 跨组件 |
| useEffect | initState/dispose | 副作用 |
| Redux | Riverpod/BLoC | 全局状态 |
| StyleSheet.create | Widget属性 | 样式 |
| FlatList | ListView.builder | 列表 |
| Navigation | Navigator/GoRouter | 路由 |
| AsyncStorage | shared_preferences | 本地存储 |
| Native Modules | Platform Channels | 原生交互 |

### 从Android原生迁移

| Android | Flutter | 说明 |
|---------|---------|------|
| XML Layout | Widget树 | 声明式 |
| ViewModel | Riverpod/BLoC | 状态管理 |
| LiveData | Stream/ValueNotifier | 响应式 |
| Room | drift/sqflite | 数据库 |
| Retrofit | dio/http | 网络请求 |
| Glide/Coil | cached_network_image | 图片加载 |
| Hilt/Dagger | get_it/injectable | 依赖注入 |
| Gradle | pubspec.yaml | 构建配置 |
| R8/ProGuard | --obfuscate | 代码混淆 |

### 从iOS原生迁移

| iOS | Flutter | 说明 |
|-----|---------|------|
| SwiftUI | Widget | 声明式UI |
| UIKit | Widget | 命令式迁移 |
| Combine | Stream/RxDart | 响应式 |
| CoreData | drift | 数据库 |
| URLSession | dio/http | 网络请求 |
| Kingfisher | cached_network_image | 图片加载 |
| Swinject | get_it | 依赖注入 |
| SPM/CocoaPods | pubspec.yaml | 包管理 |
