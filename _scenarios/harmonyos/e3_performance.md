---
version: 3.0.0
author: AI提示词体系
updated_at: '2026-07-13'
tags:
- harmonyos
- performance
- memory
- arkts-optimizer
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
lint_score: 55.0
lint_last_checked: '2026-07-13T05:35:03Z'
---
# 鸿蒙ArkTS性能优化场景模板

## 概述

鸿蒙应用性能优化是用户体验的关键，涵盖渲染性能、内存管理、启动速度、包体积等多个维度。本模板系统覆盖ArkTS应用性能优化场景，帮助开发者定位和解决性能瓶颈。

---

## 一、常见陷阱（5项）

### 陷阱1：组件渲染性能未分级优化

- 所有列表使用`ForEach`而非`LazyForEach`，万级数据列表首屏渲染耗时超3秒
- 复杂组件未使用`@Reusable`装饰器复用，频繁创建/销毁导致GC压力
- `@Watch`回调中执行耗时计算阻塞UI线程
- **规避**：长列表使用`LazyForEach`+`IDataSource`；可复用组件标记`@Reusable`；`@Watch`回调中仅做轻量标记，耗时计算延迟到`aboutToAppear`或异步处理

### 陷阱2：内存泄漏未有效监控

- 定时器/事件监听在`aboutToDisappear`中未清理，组件销毁后回调仍执行
- 闭包引用组件实例，导致整个组件树无法GC
- `@State`持有大对象引用但不再使用，未主动释放
- **规避**：组件销毁时清理所有定时器/监听器；避免闭包直接捕获`this`，使用弱引用或解绑；大对象用完后置null或使用`@Local`替代`@State`

### 陷阱3：启动链路过长

- `EntryAbility.onCreate`中同步加载大量数据，冷启动耗时超2秒
- `Index`页面`aboutToAppear`中初始化所有子模块，首帧渲染延迟
- 未使用`TaskPool`并行化初始化任务
- **规避**：将数据加载延迟到首帧渲染后；使用`TaskPool`并行初始化独立模块；实现分阶段初始化（核心→次要→后台）

### 陷阱4：图片资源未优化

- 加载原始分辨率图片（如4000x3000），实际显示仅200x150，内存浪费严重
- 未使用`PixelMap`进行图片解码控制，所有图片全量解码
- SVG/矢量图标用PNG替代，包体积和渲染性能双损
- **规避**：使用`image.Format`指定采样率降低解码分辨率；小图标使用SVG/VectorDrawable；图片缓存使用`ImageCache`统一管理

### 陷阱5：线程模型误用

- 在主线程执行CPU密集计算（如JSON解析100KB+数据），UI卡死
- `TaskPool`任务间通过`@State`共享数据导致线程安全问题
- `Worker`通信序列化大对象，通信耗时超过计算耗时
- **规避**：CPU密集任务使用`TaskPool`执行；`TaskPool`任务间通过`Struct`传值而非共享引用；大对象使用`SharedArrayBuffer`零拷贝传递

---

## 二、提示词模板

{{#if model == gpt-4o}}
### GPT-4o优化版

你是鸿蒙ArkTS性能优化专家，拥有丰富的HarmonyOS应用调优经验。请帮我优化以下性能问题：

**问题现象**：[描述具体性能问题]
**性能指标**：[目标指标，如首屏<1s、列表滚动>55fps]

**优化方向**：
1. 渲染优化：组件状态管理精细化、LazyForEach懒加载、@Reusable复用
2. 内存优化：泄漏检测、大对象释放、图片采样率控制
3. 启动优化：延迟加载、TaskPool并行、分阶段初始化
4. 线程优化：CPU密集任务TaskPool化、SharedArrayBuffer零拷贝
5. 包体积：动态加载、资源压缩、SVG替代PNG

请提供具体的优化方案+代码修改+性能对比数据。

{{else}}
### 通用版

你是鸿蒙性能优化专家。请帮我优化以下性能问题：

**问题**：[描述问题]

**优化方向**：渲染/内存/启动/线程/包体积

{{/if}}

---

## 三、代码示例

```typescript
import taskpool from '@ohos.taskpool';

@Reusable
@Component
struct OptimizedListItem {
  @ObjectLink item: ListItemData

  build() {
    Row() {
      Image(this.item.icon)
        .width(48)
        .height(48)
        .objectFit(ImageFit.Cover)
        .alt($r('app.media.placeholder'))
      Column() {
        Text(this.item.title).fontSize(16).fontWeight(FontWeight.Medium)
        Text(this.item.subtitle).fontSize(12).fontColor('#999999')
      }.layoutWeight(1).alignItems(HorizontalAlign.Start)
    }.width('100%').padding(12)
  }
}

@Concurrent
function heavyCalculation(data: number[]): number {
  return data.reduce((sum, val) => sum + Math.sqrt(val), 0)
}

async function runParallelCalc() {
  const task = new taskpool.Task(heavyCalculation, [1, 4, 9, 16, 25, 36])
  const result = await taskpool.execute(task)
  console.info(`Calculation result: ${result}`)
}
```

---

## 四、测试要点

1. 首屏渲染时间：冷启动<1.5s，热启动<0.5s
2. 列表滚动帧率：1000项列表≥55fps
3. 内存峰值：页面切换后内存回落>80%
4. 图片内存：缩略图解码内存≤显示尺寸*4bytes
5. CPU占用：后台态CPU占用<1%
