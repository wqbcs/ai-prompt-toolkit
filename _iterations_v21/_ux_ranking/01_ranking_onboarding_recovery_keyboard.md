# R7-01 UX评分排行+新手引导+错误恢复+键盘导航

> **迭代**：v21-R7-01~06 | **日期**：2026-07-12

---

## 一、场景模板评分排行

### 排行算法

```typescript
interface ScenarioRanking {
  scenarioId: string
  compositeScore: number           // 综合评分
  components: {
    userRating: number             // 用户评分(5星制) 权重40%
    usageFrequency: number        // 使用频率(归一化) 权重25%
    effectivenessScore: number    // 效果评估(自动) 权重25%
    recencyBonus: number          // 新近度加分 权重10%
  }
  rank: number
  trend: 'rising' | 'stable' | 'declining'
  totalUsers: number
  avgRating: number
}

// 综合评分公式
// Score = 0.4*normalize(rating) + 0.25*normalize(usage) + 0.25*normalize(effectiveness) + 0.1*recencyBonus
```

### 排行维度

| 维度 | 说明 | 刷新频率 |
|------|------|---------|
| 综合排行 | 四维度加权 | 每日 |
| 用户评分排行 | 5星平均分 | 实时 |
| 使用频率排行 | 调用次数 | 每日 |
| 效果评估排行 | A/B测试胜率 | 每周 |
| 新秀排行 | 近30天新场景 | 每日 |
| 趋势排行 | 增长率 | 每周 |

### 排行展示

| 元素 | 说明 |
|------|------|
| 排名 | 数字+趋势箭头(↑↓→) |
| 场景名 | 名称+分类标签 |
| 评分 | 星级+人数 |
| 使用量 | 柱状图(7天) |
| 标签 | 热门/新品/推荐 |

---

## 二、新手引导流程

### 3步完成第一个场景

| 步骤 | 时间 | 内容 | 交互 |
|------|------|------|------|
| Step 1: 选择场景 | 30秒 | 展示Top5推荐场景+分类浏览 | 点击选择 |
| Step 2: 填写参数 | 2分钟 | 表单+示例+智能建议 | 填写+验证 |
| Step 3: 生成提示词 | 30秒 | 实时预览+一键复制 | 点击生成+复制 |

### 引导元素

| 元素 | 说明 |
|------|------|
| 进度条 | 顶部3步进度指示器 |
| 聚光灯 | 高亮当前操作区域 |
| 工具提示 | 悬浮解释每个字段含义 |
| 示例预填 | 一键填入示例数据 |
| 完成庆祝 | 动画+成就解锁 |

### 5分钟快速路径

```
首页 → [选择场景] → Python FastAPI → [填写参数] 
→ 项目名: my_api / 框架: FastAPI / 数据库: PostgreSQL 
→ [生成] → 预览+复制 → 完成! 🎉
```

### 15分钟深入路径

```
首页 → [浏览场景] → 选择2个场景 → [拖拽组合] 
→ 调整参数+预览 → [A/B测试] → 对比2个版本 
→ 选择最优 → 保存到我的模板 → 完成! 🎉
```

---

## 三、错误恢复

### 错误分类与恢复策略

| 错误类型 | 示例 | 自动恢复 | 手动恢复 |
|---------|------|---------|---------|
| 网络超时 | API调用超时 | 重试3次+指数退避 | 切换网络/降级模型 |
| Token超限 | 输出被截断 | 自动压缩+续写 | 减少输入/分段处理 |
| 格式错误 | 输出非预期格式 | 重试+格式约束 | 修改提示词+示例 |
| 安全拦截 | 内容被过滤 | 提示修改建议 | 调整约束条件 |
| 模型不可用 | API返回503 | 自动切换备用模型 | 手动选择模型 |
| 数据丢失 | 浏览器崩溃 | 自动保存恢复 | 从历史记录恢复 |

### 回退方案

```typescript
interface RecoveryPlan {
  errorType: string
  autoRecoveryAttempts: number
  autoRecoveryActions: RecoveryAction[]
  fallbackStrategy: 'retry' | 'degrade' | 'rollback' | 'manual'
  userMessage: string             // 用户友好的错误描述
  suggestedActions: string[]      // 用户可采取的行动
  preventFutureActions: string[]  // 预防措施
}

interface RecoveryAction {
  action: string
  parameters: Record<string, unknown>
  successCriteria: string
  nextActionIfFailed: string
}
```

### 自动保存机制

| 触发 | 保存内容 | 存储 |
|------|---------|------|
| 每次编辑 | 草稿内容 | localStorage |
| 30秒定时 | 全量状态 | IndexedDB |
| 生成前 | 输入参数 | 服务端 |
| 页面离开 | 全量状态 | localStorage |

---

## 四、键盘导航（Vim风格）

### 全局快捷键

| 快捷键 | 模式 | 功能 |
|--------|------|------|
| j / ↓ | Normal | 下移一项 |
| k / ↑ | Normal | 上移一项 |
| h / ← | Normal | 左侧面板 |
| l / → | Normal | 右侧面板 |
| gg | Normal | 跳到顶部 |
| G | Normal | 跳到底部 |
| / | Normal | 搜索模式 |
| : | Normal | 命令模式 |
| i | Normal | 进入编辑模式 |
| Esc | Insert | 回到Normal模式 |
| Enter | Normal | 打开/确认 |
| x | Normal | 删除 |
| y | Normal | 复制 |
| p | Normal | 粘贴 |
| u | Normal | 撤销 |
| Ctrl+r | Normal | 重做 |
| :w | Command | 保存 |
| :q | Command | 退出 |
| :help | Command | 帮助 |
| Tab | Normal | 切换面板焦点 |
| Ctrl+n | Normal | 新建场景 |
| Ctrl+s | Normal | 保存当前 |
| Ctrl+f | Normal | 搜索 |

### 模式切换

```
Normal模式 ←Esc→ Insert模式
    ↓:           ↑Enter
Command模式 ←Esc→
```

### 可访问性

| 特性 | 实现 |
|------|------|
| 屏幕阅读器 | ARIA标签+live region |
| 高对比度 | 3主题+系统跟随 |
| 字体缩放 | 100%-200%+ |
| 仅键盘 | 所有功能可通过键盘操作 |
| 焦点指示 | 明显焦点环+跳转顺序 |

---

## R7验收

| 功能 | 子功能 | 验证 |
|------|--------|------|
| 评分排行 | 6维度排行+算法+展示 | ✓ |
| 新手引导 | 3步流程+5分/15分路径 | ✓ |
| 错误恢复 | 6类错误+自动保存+回退 | ✓ |
| 键盘导航 | Vim风格+3模式+可访问性 | ✓ |

- [x] R7全部6次迭代完成
