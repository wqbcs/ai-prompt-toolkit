# O5-4~5：Dart编码规范专项与跨平台适配检查清单

> **迭代编号**：O5-4~5 | **维度**：赛事贴合度-Flutter专项 | **日期**：2026-07-11

---

## Dart编码规范专项提示词

### 空安全规范

- [ ] 所有公共API使用空安全类型
- [ ] 避免使用!强制解包（使用?.或??替代）
- [ ] late仅用于确定延迟初始化的场景
- [ ] Nullable返回值使用Option模式处理
- [ ] 集合操作使用whereType<T>()而非cast<T>()

### Dart 3.x现代特性

| 特性 | 用途 | 示例 |
|------|------|------|
| Records | 轻量级数据聚合 | `(String, int) pair = ('hello', 42)` |
| Patterns | 解构与模式匹配 | `if (json case {'name': String name}) ...` |
| Sealed classes | 有限类型层次 | `sealed class Result {}` |
| Class modifiers | 访问控制 | `final class`, `interface class` |
| When表达式 | 穷尽匹配 | `when (result) { Success() => ... }` |

### 代码风格

```dart
// 好的写法
final users = await repository.getUsers();
final names = users.map((u) => u.name).toList();

// 避免
var users = await repository.getUsers();
List<String> names = [];
for (var u in users) {
  names.add(u.name);
}
```

---

## 跨平台适配检查清单

### iOS适配

- [ ] Info.plist权限声明完整
- [ ] Cupertino风格组件适配
- [ ] SafeArea处理刘海/圆角
- [ ] iOS返回手势支持
- [ ] App Transport Security配置
- [ ] Universal Links配置
- [ ] TestFlight测试

### Android适配

- [ ] AndroidManifest权限声明
- [ ] Material风格组件适配
- [ ] 系统导航栏沉浸式
- [ ] 返回键处理(WillPopScope)
- [ ] App Links配置
- [ ] 多窗口/分屏支持
- [ ] ProGuard规则配置

### Web适配

- [ ] 响应式布局（Breakpoints）
- [ ] SEO元数据配置
- [ ] PWA支持（manifest+service worker）
- [ ] URL路由策略（path/hash）
- [ ] CORS代理配置
- [ ] Web渲染器选择（CanvasKit/HTML）
- [ ] WASM编译支持

### Desktop适配

- [ ] 窗口大小与最小尺寸
- [ ] 键盘快捷键支持
- [ ] 鼠标右键菜单
- [ ] 文件拖放
- [ ] 系统托盘（如需要）
- [ ] 原生窗口标题栏定制
