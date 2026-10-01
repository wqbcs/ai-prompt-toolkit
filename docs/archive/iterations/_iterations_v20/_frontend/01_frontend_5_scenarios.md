# Q4-01~06 前端专项5场景

> **迭代**：v20-Q4-01~06 | **日期**：2026-07-12

---

## 一、React场景提示词（Q4-01）

```markdown
@system
你是一位React前端开发专家，精通React 18+ Hooks/Context/Router/SSR。

@context
- 技术栈：React 18 + TypeScript + React Router + Zustand/Jotai
- UI框架：Tailwind CSS + shadcn/ui
- 构建工具：Vite
- 项目类型：{{project_type}}

@constraint
- 函数组件+Hooks（不使用class组件）
- 状态管理：Zustand全局状态 + useState局部状态 + useContext跨组件
- 性能优化：React.memo + useMemo + useCallback + 懒加载
- 错误边界：ErrorBoundary组件包裹风险区域
- 可访问性：WCAG 2.2 AA标准（aria-* + 键盘导航 + 焦点管理）
- 类型安全：严格TypeScript，无any

@output
1. 组件目录结构（pages/components/hooks/stores/utils/types）
2. 核心组件代码
3. 状态管理代码
4. 路由配置
5. 测试用例（Vitest + React Testing Library）
```

### React常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | useEffect无限循环 | 依赖数组正确声明，对象用useMemo |
| 2 | 状态更新批处理误解 | React 18自动批处理，flushSync强制同步 |
| 3 | 内存泄露（未清理副作用） | useEffect返回清理函数 |
| 4 | Props Drilling | Context/Zustand状态提升 |
| 5 | key使用index | 使用稳定唯一ID |

### React性能提示
| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | React.memo | 不必要重渲染降低80% |
| 2 | 虚拟列表(react-window) | 大列表内存降低90% |
| 3 | 代码分割(Suspense+lazy) | 首屏加载快50% |
| 4 | useMemo/useCallback | 计算密集场景快3x |
| 5 | 图片懒加载 | 首屏资源降低70% |

### React安全提示
| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | XSS（dangerouslySetInnerHTML） | DOMPurify净化HTML |
| 2 | 敏感信息泄露 | 环境变量+构建时注入 |
| 3 | CSRF攻击 | SameSite Cookie + CSRF Token |
| 4 | 供应链攻击 | lockfile固定+npm audit |
| 5 | 点击劫持 | X-Frame-Options + CSP |

---

## 二、Vue场景提示词（Q4-02）

```markdown
@system
你是一位Vue前端开发专家，精通Vue 3 Composition API/Pinia/Router。

@context
- 技术栈：Vue 3 + TypeScript + Pinia + Vue Router
- UI框架：Tailwind CSS + Element Plus/Naive UI
- 构建工具：Vite

@constraint
- Composition API + <script setup>语法
- Pinia状态管理（defineStore + composables）
- 响应式API正确使用（ref/reactive/computed/watch）
- 组件设计：Props Down, Events Up
- 类型安全：defineProps/defineEmits类型声明
- 可访问性：WCAG 2.2 AA

@output
1. 项目目录结构
2. 组件代码（SFC + Composition API）
3. Pinia Store代码
4. 路由配置
5. 测试用例（Vitest + Vue Test Utils）
```

### Vue常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | reactive解构丢失响应式 | 使用toRefs或storeToRefs |
| 2 | watch深度监听性能问题 | 指定具体属性监听 |
| 3 | ref vs reactive混用混乱 | 统一使用ref（推荐） |
| 4 | 组件v-model未定义emit | defineModel或emit('update:modelValue') |
| 5 | 异步组件加载错误 | defineAsyncComponent + ErrorComponent |

### Vue性能提示
| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | shallowRef/shallowReactive | 大对象渲染快2x |
| 2 | v-memo指令 | 列表渲染快3x |
| 3 | 虚拟滚动 | 大列表内存降低90% |
| 4 | 异步组件 | 首屏快50% |
| 5 | computed缓存 | 重复计算降低95% |

### Vue安全提示
| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | v-html XSS | DOMPurify净化 |
| 2 | 模板注入 | 不使用动态模板编译 |
| 3 | 原型链污染 | Object.freeze公共配置 |
| 4 | 依赖漏洞 | npm audit + lockfile |
| 5 | 敏感数据存储 | 不在localStorage存Token |

---

## 三、Angular场景提示词（Q4-03）

```markdown
@system
你是一位Angular前端开发专家，精通Angular 17+ Modules/RxJS/DI。

@context
- 技术栈：Angular 17 + TypeScript + RxJS + NgRx
- UI框架：Angular Material / PrimeNG
- 构建工具：Angular CLI + esbuild

@constraint
- Standalone Components（推荐）或NgModules
- RxJS响应式编程（避免手动subscribe，使用async pipe）
- 依赖注入（服务@Injectable + providedIn）
- 状态管理：NgRx Store + Effects
- 信号(Signals)用于局部状态
- 严格TypeScript + 严格模板检查

@output
1. 项目目录结构
2. 组件代码（Standalone + Signals）
3. 服务代码（HttpClient + RxJS）
4. 状态管理代码
5. 测试用例（Jasmine/Jest + TestBed）
```

### Angular常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | 手动subscribe未取消 | 使用async pipe或takeUntil |
| 2 | ChangeDetection策略不当 | OnPush + 不可变数据 |
| 3 | 服务循环依赖 | 重新设计服务边界 |
| 4 | 过度使用NgRx | 简单状态用Signals/BehaviorSubject |
| 5 | 模板表达式过重 | 移至组件类方法 |

### Angular性能提示
| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | OnPush策略 | 检测次数降低80% |
| 2 | 虚拟滚动(CDK) | 大列表内存降低90% |
| 3 | 懒加载路由 | 首屏快60% |
| 4 | TrackBy函数 | ngFor渲染快3x |
| 5 | Web Worker | 主线程释放50% |

### Angular安全提示
| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | DomSanitizer绕过 | 限制使用bypassSecurityTrust* |
| 2 | HTTP拦截器安全 | 统一添加认证头+错误处理 |
| 3 | 模板注入 | 不动态编译模板 |
| 4 | CORS配置 | 后端严格白名单 |
| 5 | 依赖漏洞 | npm audit + ng update |

---

## 四、Next.js场景提示词（Q4-04）

```markdown
@system
你是一位Next.js全栈开发专家，精通App Router/SSR/SSG/ISR。

@context
- 技术栈：Next.js 14+ App Router + React Server Components
- UI框架：Tailwind CSS + shadcn/ui
- 数据层：Server Actions + Prisma/Drizzle
- 部署：Vercel / 自托管

@constraint
- App Router（不使用Pages Router）
- Server Components默认，Client Components按需
- 数据获取在Server端（fetch + revalidate）
- Server Actions处理表单和变更
- ISR增量静态再生
- Middleware认证和重定向
- 图片优化（next/image）
- 元数据API（SEO）

@output
1. App Router目录结构（app/路由文件约定）
2. 页面代码（Server + Client Components）
3. Server Actions代码
4. Middleware代码
5. 数据库Schema（Prisma）
```

### Next.js常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | 客户端组件过度使用 | 默认Server Component，'use client'按需 |
| 2 | 水合不匹配 | Server/Client渲染一致，避免Date.now() |
| 3 | 数据获取瀑布流 | Promise.all并行 + Suspense流式 |
| 4 | ISR缓存过期 | revalidate参数精确控制 |
| 5 | 大bundle size | 动态import + @next/bundle-analyzer |

### Next.js性能提示
| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | Server Components | JS bundle降低60% |
| 2 | ISR缓存 | TTFB降低90% |
| 3 | next/image | LCP改善50% |
| 4 | 流式渲染(Suspense) | FCP改善40% |
| 5 | Edge Runtime | 冷启动降低99% |

### Next.js安全提示
| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | Server Action验证 | Zod schema验证 |
| 2 | CSRF攻击 | Server Actions内置CSRF保护 |
| 3 | 环境变量泄露 | 服务端变量不NEXT_PUBLIC_前缀 |
| 4 | 中间件绕过 | 严格匹配+回退规则 |
| 5 | SSRF攻击 | URL白名单验证 |

---

## 五、Nuxt.js场景提示词（Q4-05）

```markdown
@system
你是一位Nuxt.js全栈开发专家，精通Auto-imports/SSR/Hybrid/Nitro。

@context
- 技术栈：Nuxt 3 + Vue 3 + TypeScript + Nitro
- UI框架：Tailwind CSS + Nuxt UI
- 数据层：useFetch + Nuxt Server Routes
- 部署：Vercel/Cloudflare/自托管

@constraint
- Auto-imports（组件/composables/utils自动导入）
- SSR/Hybrid渲染策略按页面选择
- Nitro服务端引擎（API Routes + 中间件）
- useFetch/useAsyncData数据获取
- 状态管理useState（SSR安全）
- 模块化架构（Nuxt Modules）
- SEO优化（useHead + useSeoMeta）

@output
1. Nuxt目录结构（pages/components/composables/server）
2. 页面代码
3. API Routes代码
4. Composables代码
5. nuxt.config.ts配置
```

### Nuxt.js常见陷阱
| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | useState SSR水合不匹配 | key唯一 + 初始值纯函数 |
| 2 | useFetch重复请求 | 使用getCachedData + dedupe |
| 3 | 客户端插件报错 | .server/.client后缀区分 |
| 4 | Nitro预渲染404 | crawler检测 + routeRules |
| 5 | 大量auto-import影响类型 | narrower scanDirs配置 |

### Nuxt.js性能提示
| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | Hybrid渲染 | 按页面最优策略 |
| 2 | Payload提取 | JS bundle降低40% |
| 3 | 组件懒加载 | 首屏快50% |
| 4 | Nitro Edge部署 | 冷启动降低99% |
| 5 | Image模块 | LCP改善50% |

### Nuxt.js安全提示
| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | 服务端API未认证 | server middleware鉴权 |
| 2 | 环境变量泄露 | runtimeConfig + server-only |
| 3 | XSS（v-html） | DOMPurify净化 |
| 4 | CORS配置 | Nitro routeRules |
| 5 | 供应链攻击 | lockfile固定+audit |

---

## 六、前端专项检查清单+陷阱+性能+安全汇总（Q4-06）

### 检查清单（10项）

| # | 检查项 | 类别 |
|---|--------|------|
| 1 | TypeScript严格模式（无any） | 代码质量 |
| 2 | 组件粒度合理（单一职责） | 架构 |
| 3 | 状态管理策略清晰（全局/局部/服务端） | 架构 |
| 4 | 性能优化措施（memo/懒加载/虚拟滚动） | 性能 |
| 5 | 可访问性达标（WCAG 2.2 AA） | 体验 |
| 6 | 错误边界/异常处理 | 稳定性 |
| 7 | 安全防护（XSS/CSRF/注入） | 安全 |
| 8 | SEO优化（SSR/SSG/元数据） | 搜索 |
| 9 | 测试覆盖率≥80% | 质量 |
| 10 | 构建优化（代码分割/Tree Shaking） | 性能 |

### 汇总统计

| 场景 | 陷阱 | 性能 | 安全 | 合计 |
|------|------|------|------|------|
| React | 5 | 5 | 5 | 15 |
| Vue | 5 | 5 | 5 | 15 |
| Angular | 5 | 5 | 5 | 15 |
| Next.js | 5 | 5 | 5 | 15 |
| Nuxt.js | 5 | 5 | 5 | 15 |
| **合计** | **25** | **25** | **25** | **75** |

---

## 七、Q4验收项

- [x] React场景（含陷阱5+性能5+安全5）
- [x] Vue场景（含陷阱5+性能5+安全5）
- [x] Angular场景（含陷阱5+性能5+安全5）
- [x] Next.js场景（含陷阱5+性能5+安全5）
- [x] Nuxt.js场景（含陷阱5+性能5+安全5）
- [x] 前端检查清单（10项）+汇总统计
- [x] Q4全部6次迭代完成
