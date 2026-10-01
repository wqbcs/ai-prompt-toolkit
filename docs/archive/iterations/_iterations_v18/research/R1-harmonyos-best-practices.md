# 调研1：鸿蒙(HarmonyOS)开发最佳实践与ArkUI/ArkTS提示词需求

> **日期**：2026-07-11 | **版本**：v1.0

---

## 1. HarmonyOS开发生态现状

### 1.1 核心技术栈
- **ArkTS**：华为自研的TypeScript超集语言，支持声明式UI开发
- **ArkUI**：声明式UI框架，基于eTS(extended TypeScript)
- **ArkCompiler**：方舟编译器，支持多语言统一编译
- **分布式能力**：分布式数据管理、分布式任务调度、分布式文件系统

### 1.2 开发范式
- **Stage模型**（推荐）：AbilityStage + UIAbility + ExtensionAbility
- **FA模型**（旧版）：Feature Ability + Particle Ability
- **声明式UI**：@Component + @Builder + @Extend装饰器模式

### 1.3 提示词关键需求
1. **ArkTS语法特性提示**：@State/@Prop/@Link/@Provide/@Consume装饰器使用场景
2. **组件生命周期管理**：aboutToAppear/aboutToDisappear/onPageShow/onPageHide
3. **分布式能力调用**：分布式数据同步、设备发现、任务迁移
4. **性能优化模式**：LazyForEach、组件复用、按需加载
5. **安全合规要求**：权限声明、数据分类分级、隐私保护

### 1.4 OpenHarmony适配要点
- OpenHarmony 5.x API与HarmonyOS NEXT的差异
- 三方库兼容性（ohpm包管理）
- 设备适配（手机/平板/手表/车机/智慧屏）

---

## 2. 对提示词体系的改进建议

1. 新增鸿蒙开发5场景提示词包（应用开发/ArkUI界面/分布式能力/性能优化/安全合规）
2. 补充ArkTS专项检查清单（装饰器使用规范/生命周期管理/内存泄漏检测）
3. 增加OpenHarmony适配指南（API差异矩阵/三方库替代方案）
4. 设计鸿蒙开发者快速入门路径（从Android/iOS/Flutter迁移）

---

## 3. 调研来源
- 华为开发者文档中心：https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/
- OpenHarmony Gitee仓库：https://gitee.com/openharmony（当前系统升级中，基于历史认知补充）
