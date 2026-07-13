---
version: 3.0.0
author: AI提示词体系
updated_at: '2026-07-13'
tags:
- harmonyos
- arkts
- ui-component
- declarative-ui
applicable_models:
- gpt-4o
- claude-3.5-sonnet
- qwen-max
- pangu-large
inheritance:
  enabled: false
locale: zh-CN
i18n_status: untranslated
market_status: draft
lint_score: 65.0
lint_last_checked: '2026-07-13T05:35:03Z'
---
# 鸿蒙ArkTS UI组件开发场景模板

## 概述

鸿蒙（HarmonyOS）ArkUI声明式开发范式使用ArkTS语言，基于`@Component`装饰器和声明式UI描述构建界面。本模板覆盖ArkTS组件开发的核心场景，帮助开发者规避ArkUI开发中的常见陷阱并编写高性能、适配多设备的UI组件。

---

## 一、常见陷阱（5项）

### 陷阱1：@State滥用导致全量刷新

- `@State`修饰的变量变化会触发组件全量刷新，大量`@State`变量导致性能急剧下降
- 将整个数据对象标记为`@State`，仅修改其中一个属性也会触发整个组件树重新渲染
- 在ListItem中使用`@State`管理选中状态，列表滚动时出现卡顿
- **规避**：使用`@Prop`向下传递只读数据、`@Link`双向绑定、`@ObjectLink`+`@Observed`实现细粒度观察；列表场景使用`@ObjectLink`避免全量刷新

### 陷阱2：LazyForEach数据源未实现IDataSource

- `LazyForEach`要求数据源实现`IDataSource`接口，直接传入数组导致懒加载失效变为全量加载
- 数据更新后未调用`notifyDataReload()`/`notifyDataChange()`，UI不刷新
- keyGenerator返回重复key，导致列表渲染异常
- **规避**：严格实现`IDataSource`接口的`totalCount()`/`getData()`/`registerDataChangeListener()`方法；数据变更时正确通知监听器；确保keyGenerator返回唯一稳定key

### 陷阱3：自定义组件生命周期误用

- 在`aboutToAppear`中执行耗时操作阻塞UI渲染，页面白屏
- 在`aboutToDisappear`中清理资源但子组件已销毁，访问子组件引用崩溃
- `onPageShow`/`onPageHide`与`aboutToAppear`/`aboutToDisappear`混淆使用
- **规避**：耗时操作放在`onAppear`回调或异步执行；资源清理在`aboutToDisappear`中只清理本组件资源；理解页面级vs组件级生命周期差异

### 陷阱4：@Builder函数性能陷阱

- `@Builder`函数内部访问外部变量触发不必要的重新调用
- 在`@Builder`中使用`if`条件渲染而非`@Conditional`，导致渲染性能差异
- `@Builder`函数参数传递大对象，每次调用都创建副本
- **规避**：使用`@LocalBuilder`避免按引用传递开销；`@Builder`函数参数使用`wrapBuilder`缓存；条件渲染优先使用三目运算符或`@Conditional`

### 陷阱5：多设备适配硬编码尺寸

- 使用固定px值（如`width(360)`），在不同设备上布局错乱
- 仅在代码中处理手机和平板两种尺寸，折叠屏和智慧屏适配缺失
- 未使用`vp`/`fp`单位导致不同DPI设备上显示差异大
- **规避**：使用`vp`/`fp`自适应单位；通过`@StorageProp`读取设备规格动态计算布局；使用`Grid`/`Flex`等自适应容器；利用`breakpointSystem`断点系统

---

## 二、提示词模板

{{#if model == gpt-4o}}
### GPT-4o优化版

你是一位鸿蒙ArkUI高级开发专家，精通ArkTS声明式UI开发范式。请帮我开发以下ArkTS组件：

**需求**：[描述具体组件需求]

**开发规范**：
1. 使用`@Component`装饰器定义组件，合理选择状态管理装饰器（`@State`/`@Prop`/`@Link`/`@ObjectLink`）
2. 列表场景必须使用`LazyForEach`+`IDataSource`实现懒加载
3. 布局使用`vp`/`fp`单位，禁止硬编码px值
4. 遵循ArkUI组件生命周期最佳实践
5. 提供完整的组件代码+使用示例

{{else}}
### 通用版

你是一位鸿蒙ArkUI开发专家。请帮我开发以下ArkTS组件：

**需求**：[描述具体组件需求]

**开发要求**：
1. 使用`@Component`装饰器，合理选择状态管理
2. 列表使用懒加载，避免全量刷新
3. 布局使用自适应单位
4. 遵循生命周期最佳实践

{{/if}}

---

## 三、代码示例

```typescript
@Component
export struct ProductList {
  @State products: Product[] = []
  private dataSource: ProductDataSource = new ProductDataSource([])

  aboutToAppear() {
    this.loadProducts()
  }

  build() {
    Column() {
      List() {
        LazyForEach(this.dataSource, (item: Product) => {
          ListItem() {
            ProductItem({ product: item })
          }
        }, (item: Product) => item.id.toString())
      }
      .width('100%')
      .layoutWeight(1)
    }
  }
}

class ProductDataSource implements IDataSource {
  private data: Product[] = []
  private listeners: DataChangeListener[] = []

  constructor(data: Product[]) { this.data = data }

  totalCount(): number { return this.data.length }
  getData(index: number): Product { return this.data[index] }

  registerDataChangeListener(listener: DataChangeListener): void {
    this.listeners.push(listener)
  }

  unregisterDataChangeListener(listener: DataChangeListener): void {
    this.listeners = this.listeners.filter(l => l !== listener)
  }

  notifyDataReload(): void {
    this.listeners.forEach(l => l.onDataReloaded())
  }
}
```

---

## 四、测试要点

1. 组件渲染性能：LazyForEach列表滚动帧率≥55fps
2. 状态管理：@State/@Prop/@Link数据变更正确触发UI更新
3. 多设备适配：手机/平板/折叠屏布局正确
4. 生命周期：aboutToAppear/aboutToDisappear资源正确管理
5. 内存泄漏：组件销毁后无残留引用
