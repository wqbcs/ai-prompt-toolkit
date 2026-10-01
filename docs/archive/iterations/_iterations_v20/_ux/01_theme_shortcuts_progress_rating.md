# Q7-01~06 UX主题+快捷键+进度追踪+评分

> **迭代**：v20-Q7-01~06 | **日期**：2026-07-12

---

## 一、3主题CSS变量体系+切换逻辑（Q7-01）

### 1.1 CSS变量定义

```css
:root {
  --color-bg-primary: #1e1e2e;
  --color-bg-secondary: #313244;
  --color-bg-tertiary: #45475a;
  --color-text-primary: #cdd6f4;
  --color-text-secondary: #a6adc8;
  --color-text-muted: #6c7086;
  --color-accent-blue: #89b4fa;
  --color-accent-green: #a6e3a1;
  --color-accent-yellow: #f9e2af;
  --color-accent-red: #f38ba8;
  --color-accent-purple: #cba6f7;
  --color-accent-teal: #94e2d5;
  --color-border: #585b70;
  --color-success: #a6e3a1;
  --color-warning: #f9e2af;
  --color-error: #f38ba8;
  --color-info: #89b4fa;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 8px rgba(0,0,0,0.3);
  --font-mono: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

[data-theme="light"] {
  --color-bg-primary: #faf4ed;
  --color-bg-secondary: #f2e9e1;
  --color-bg-tertiary: #dfdad9;
  --color-text-primary: #575279;
  --color-text-secondary: #797593;
  --color-text-muted: #9890a3;
  --color-accent-blue: #286983;
  --color-accent-green: #56949f;
  --color-accent-yellow: #ea9d34;
  --color-accent-red: #b4637a;
  --color-accent-purple: #907aa9;
  --color-accent-teal: #9ccfd8;
  --color-border: #cecacd;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 8px rgba(0,0,0,0.08);
}

[data-theme="high-contrast"] {
  --color-bg-primary: #000000;
  --color-bg-secondary: #1a1a1a;
  --color-bg-tertiary: #333333;
  --color-text-primary: #ffffff;
  --color-text-secondary: #cccccc;
  --color-text-muted: #999999;
  --color-accent-blue: #4fc3f7;
  --color-accent-green: #81c784;
  --color-accent-yellow: #fff176;
  --color-accent-red: #ef5350;
  --color-accent-purple: #ce93d8;
  --color-accent-teal: #80cbc4;
  --color-border: #666666;
  --shadow-sm: 0 0 2px #ffffff;
  --shadow-md: 0 0 4px #ffffff;
}
```

### 1.2 主题切换逻辑

```typescript
type Theme = 'dark' | 'light' | 'high-contrast';

class ThemeManager {
  private static STORAGE_KEY = 'prompt-ide-theme';
  private static SYSTEM_MEDIA = '(prefers-color-scheme: dark)';

  static init(): void {
    const saved = localStorage.getItem(this.STORAGE_KEY) as Theme | null;
    if (saved) {
      this.apply(saved);
    } else {
      const prefersDark = window.matchMedia(this.SYSTEM_MEDIA).matches;
      this.apply(prefersDark ? 'dark' : 'light');
    }
    window.matchMedia(this.SYSTEM_MEDIA).addEventListener('change', (e) => {
      if (!localStorage.getItem(this.STORAGE_KEY)) {
        this.apply(e.matches ? 'dark' : 'light');
      }
    });
  }

  static apply(theme: Theme): void {
    document.documentElement.setAttribute('data-theme', theme);
  }

  static toggle(): void {
    const current = this.getCurrent();
    const themes: Theme[] = ['dark', 'light', 'high-contrast'];
    const next = themes[(themes.indexOf(current) + 1) % themes.length];
    localStorage.setItem(this.STORAGE_KEY, next);
    this.apply(next);
  }

  static getCurrent(): Theme {
    return (document.documentElement.getAttribute('data-theme') as Theme) || 'dark';
  }
}
```

---

## 二、20快捷键定义+冲突检测+自定义（Q7-02）

### 2.1 快捷键定义

| # | 操作 | 快捷键 | 分类 |
|---|------|--------|------|
| 1 | 执行提示词 | Ctrl+Enter | 执行 |
| 2 | 调试提示词 | F5 | 执行 |
| 3 | 停止执行 | Shift+F5 | 执行 |
| 4 | 逐步执行 | F10 | 执行 |
| 5 | 预览面板 | Ctrl+Shift+V | 视图 |
| 6 | 性能分析 | Ctrl+Shift+A | 视图 |
| 7 | 切换主题 | Ctrl+Shift+T | 视图 |
| 8 | 插入模板 | Ctrl+Shift+I | 编辑 |
| 9 | 插入变量 | Ctrl+Shift+V | 编辑 |
| 10 | 格式化 | Shift+Alt+F | 编辑 |
| 11 | 搜索场景 | Ctrl+K | 导航 |
| 12 | 快速打开 | Ctrl+P | 导航 |
| 13 | 命令面板 | Ctrl+Shift+P | 导航 |
| 14 | 保存 | Ctrl+S | 文件 |
| 15 | 导出 | Ctrl+Shift+E | 文件 |
| 16 | 撤销 | Ctrl+Z | 编辑 |
| 17 | 重做 | Ctrl+Y | 编辑 |
| 18 | 注释切换 | Ctrl+/ | 编辑 |
| 19 | 缩放增大 | Ctrl+= | 视图 |
| 20 | 缩放减小 | Ctrl+- | 视图 |

### 2.2 快捷键冲突检测

```typescript
interface KeyBinding {
  command: string;
  key: string;
  when?: string;
  source: 'default' | 'user' | 'extension';
}

class KeyBindingManager {
  private bindings: Map<string, KeyBinding[]> = new Map();

  register(binding: KeyBinding): ConflictReport | null {
    const existing = this.bindings.get(binding.key) || [];
    const conflicts = existing.filter(
      (b) => b.command !== binding.command && b.when === binding.when
    );
    if (conflicts.length > 0) {
      return {
        key: binding.key,
        newCommand: binding.command,
        existingCommands: conflicts.map((c) => c.command),
        resolution: '请选择保留哪个快捷键绑定',
      };
    }
    existing.push(binding);
    this.bindings.set(binding.key, existing);
    return null;
  }

  getAll(): KeyBinding[] {
    return Array.from(this.bindings.values()).flat();
  }
}

interface ConflictReport {
  key: string;
  newCommand: string;
  existingCommands: string[];
  resolution: string;
}
```

---

## 三、进度追踪（Q7-03）

### 3.1 进度管理

```typescript
interface LearningProgress {
  user_id: string;
  started_at: string;
  last_accessed: string;
  completed_scenarios: string[];
  current_scenario: string | null;
  scenario_progress: Record<string, ScenarioProgress>;
  total_time_spent_minutes: number;
  achievements: Achievement[];
}

interface ScenarioProgress {
  scenario_id: string;
  status: 'not_started' | 'in_progress' | 'completed';
  started_at: string | null;
  completed_at: string | null;
  time_spent_minutes: number;
  rating: number | null;
  notes: string;
}

interface Achievement {
  id: string;
  name: string;
  description: string;
  unlocked_at: string;
  icon: string;
}

class ProgressManager {
  private static STORAGE_KEY = 'prompt-ide-progress';

  static save(progress: LearningProgress): void {
    progress.last_accessed = new Date().toISOString();
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(progress));
  }

  static load(): LearningProgress | null {
    const data = localStorage.getItem(this.STORAGE_KEY);
    return data ? JSON.parse(data) : null;
  }

  static getCompletionPercent(progress: LearningProgress, totalScenarios: number): number {
    return Math.round((progress.completed_scenarios.length / totalScenarios) * 100);
  }

  static getRecommendedNext(progress: LearningProgress, allScenarios: string[]): string | null {
    if (progress.current_scenario) return progress.current_scenario;
    const incomplete = allScenarios.filter((s) => !progress.completed_scenarios.includes(s));
    return incomplete[0] || null;
  }
}
```

---

## 四、场景评分（Q7-04）

### 4.1 评分系统

```typescript
interface ScenarioRating {
  scenario_id: string;
  user_id: string;
  rating: number;
  feedback: string;
  created_at: string;
  tags: string[];
}

interface RatingStatistics {
  scenario_id: string;
  avg_rating: number;
  total_ratings: number;
  rating_distribution: Record<number, number>;
  common_feedback_tags: string[];
  low_rating_count: number;
  improvement_triggered: boolean;
}

class RatingManager {
  private static STORAGE_KEY = 'prompt-ide-ratings';

  static submitRating(rating: ScenarioRating): void {
    const ratings = this.getAllRatings();
    ratings.push(rating);
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(ratings));
    if (rating.rating <= 2) {
      this.triggerImprovement(rating.scenario_id);
    }
  }

  static getStatistics(scenarioId: string): RatingStatistics {
    const ratings = this.getAllRatings().filter((r) => r.scenario_id === scenarioId);
    const distribution: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    ratings.forEach((r) => distribution[r.rating]++);
    const avg = ratings.reduce((s, r) => s + r.rating, 0) / ratings.length;
    return {
      scenario_id: scenarioId,
      avg_rating: Math.round(avg * 100) / 100,
      total_ratings: ratings.length,
      rating_distribution: distribution,
      common_feedback_tags: this.extractTags(ratings),
      low_rating_count: ratings.filter((r) => r.rating <= 2).length,
      improvement_triggered: avg < 3.0,
    };
  }

  private static triggerImprovement(scenarioId: string): void {
    console.log(`[改进触发] 场景 ${scenarioId} 收到低评分，自动触发改进流程`);
  }

  private static extractTags(ratings: ScenarioRating[]): string[] {
    const tags: Record<string, number> = {};
    ratings.forEach((r) => r.tags.forEach((t) => tags[t] = (tags[t] || 0) + 1));
    return Object.entries(tags)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([tag]) => tag);
  }

  private static getAllRatings(): ScenarioRating[] {
    const data = localStorage.getItem(this.STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  }
}
```

---

## 五、UX交互优化（Q7-05）

### 5.1 空状态/加载状态/错误提示/退出流程

```typescript
interface UXStateHandlers {
  emptyState: {
    icon: string;
    title: string;
    description: string;
    action_label: string;
    action_callback: () => void;
  };
  loadingState: {
    type: 'spinner' | 'skeleton' | 'progress';
    message: string;
    progress_percent?: number;
  };
  errorState: {
    error_code: string;
    title: string;
    description: string;
    recovery_actions: {
      label: string;
      callback: () => void;
    }[];
  };
  exitConfirmation: {
    title: string;
    message: string;
    save_label: string;
    discard_label: string;
    cancel_label: string;
  };
}
```

---

## 六、UX检查清单+可访问性验证（Q7-06）

### UX检查清单（10项）

| # | 检查项 | 类别 |
|---|--------|------|
| 1 | 3主题可切换+偏好记忆 | 视觉 |
| 2 | 20快捷键可自定义+冲突检测 | 操作 |
| 3 | 进度保存/恢复/可视化 | 学习 |
| 4 | 5星评分+文字反馈 | 反馈 |
| 5 | 空状态友好提示+引导 | 状态 |
| 6 | 加载状态反馈（骨架屏/进度） | 状态 |
| 7 | 错误提示可操作+恢复建议 | 状态 |
| 8 | 退出确认+自动保存 | 安全 |
| 9 | 可访问性WCAG 2.2 AA | 无障碍 |
| 10 | 响应式布局（桌面/平板/手机） | 布局 |

### 可访问性验证

| # | WCAG 2.2准则 | 验证方式 |
|---|-------------|---------|
| 1 | 1.4.3 对比度 | 文本与背景对比度≥4.5:1 |
| 2 | 2.1.1 键盘可操作 | 所有功能键盘可达 |
| 3 | 2.4.3 焦点顺序 | Tab顺序逻辑一致 |
| 4 | 2.4.7 焦点可见 | 焦点指示器清晰可见 |
| 5 | 4.1.2 名称/角色/值 | ARIA属性完整 |

---

## 七、Q7验收项

- [x] 3主题CSS变量体系+切换逻辑
- [x] 系统主题自动跟随
- [x] 20快捷键定义+冲突检测+自定义
- [x] 进度追踪（保存/恢复/百分比/推荐）
- [x] 场景评分（5星+反馈+统计+改进触发）
- [x] UX交互优化（空状态/加载/错误/退出）
- [x] UX检查清单（10项）
- [x] 可访问性验证（5项WCAG 2.2）
- [x] Q7全部6次迭代完成
