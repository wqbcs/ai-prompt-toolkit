# 调研2：Flutter/Dart跨平台开发提示词最佳实践

> **日期**：2026-07-11 | **版本**：v1.0

---

## 1. Flutter/Dart开发生态现状

### 1.1 核心技术栈（Flutter 3.44+）
- **Dart 3.x**：空安全、Records、Patterns、Sealed classes
- **Widget体系**：StatelessWidget/StatefulWidget/InheritedWidget
- **状态管理**：Provider/Riverpod/BLoC/GetX（Flutter Favorites推荐）
- **平台通道**：MethodChannel/EventChannel/BasicMessageChannel
- **Impeller渲染引擎**：替代Skia，提升渲染性能

### 1.2 架构模式
- **MVVM + Repository**：官方推荐架构指南
- **Clean Architecture**：Data Layer + Domain Layer + UI Layer
- **BLoC模式**：事件驱动+状态机
- **Riverpod 2.x**：声明式响应式状态管理

### 1.3 pub.dev关键包生态
- **状态管理**：flutter_bloc、hooks_riverpod、provider
- **网络**：dio、http
- **序列化**：json_serializable、freezed
- **路由**：go_router
- **本地存储**：shared_preferences、drift、hive
- **Firebase**：firebase_core、firebase_auth、cloud_firestore

### 1.4 提示词关键需求
1. **Widget开发规范**：const构造函数、Key使用、组件拆分粒度
2. **状态管理选型**：根据场景推荐Provider/Riverpod/BLoC
3. **平台通道最佳实践**：Platform Interface模式、插件开发规范
4. **性能优化**：RepaintBoundary、Isolate计算、懒加载
5. **发布部署**：多渠道打包、应用签名、商店发布

---

## 2. 对提示词体系的改进建议

1. 新增Flutter/Dart开发5场景提示词包（Widget开发/状态管理/平台通道/性能优化/发布部署）
2. 补充Dart编码规范专项提示词（空安全/Records/Patterns使用场景）
3. 增加跨平台适配检查清单（iOS/Android/Web/Desktop/嵌入式）
4. 设计Flutter开发者迁移指南（从React Native/SwiftUI/Android迁移）

---

## 3. 调研来源
- Flutter官方文档：https://docs.flutter.dev/
- Dart包仓库：https://pub.dev/
- Flutter Favorites：官方推荐高质量包列表
