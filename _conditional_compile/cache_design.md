# 条件编译引擎与缓存设计

> **版本**: v1.0.0 | **日期**: 2026-07-12

---

## 一、条件指令解析器

### 1.1 解析流程

```
原始模板文本
    │
    ▼
词法分析器(Lexer) → Token流
    │
    ▼
语法分析器(Parser) → AST
    │
    ▼
副作用检测器 → AST(安全)
    │
    ▼
条件匹配器 → 编译结果
    │
    ▼
缓存层 → 最终输出
```

### 1.2 Token类型

| Token类型 | 格式 | 示例 |
|-----------|------|------|
| IF_OPEN | `{{#if ...}}` | `{{#if model == "gpt-4o"}}` |
| ELSE_IF | `{{#else if ...}}` | `{{#else if model == "claude"}}` |
| ELSE | `{{#else}}` | `{{#else}}` |
| IF_CLOSE | `{{/if}}` | `{{/if}}` |
| TEXT | 纯文本 | 任意非指令文本 |

### 1.3 AST节点

```typescript
interface ConditionalNode {
  type: "if" | "else_if" | "else" | "text";
  condition?: Condition;     // if/else_if节点有条件
  children?: ConditionalNode[];
  content?: string;          // text节点有内容
  line_start: number;
  line_end: number;
}

interface Condition {
  dimension: "model" | "language" | "industry";
  operator: "==" | "!=" | "in" | "not_in";
  value: string | string[];
  logical?: {
    operator: "&&" | "||";
    right: Condition;
  };
}
```

## 二、副作用检测器

### 2.1 检测规则

| 检测项 | 正则 | 严重度 |
|--------|------|--------|
| API调用 | `fetch\|axios\|http\|request\|ajax` | error |
| 文件操作 | `fs\.|writeFile\|readFile\|mkdir` | error |
| 随机函数 | `random\|Math\.random\|rand()` | error |
| 时间函数 | `now()\|Date\.now\|time()\|datetime` | warning |
| 全局变量 | `globalThis\|window\|process\.env` | warning |

### 2.2 检测流程

```
FOR each ConditionalNode in AST:
    IF node.type == "text":
        FOR each pattern in side_effect_patterns:
            IF pattern matches node.content:
                报告副作用检测结果
                IF severity == "error":
                    阻止编译
                ELIF severity == "warning":
                    标注警告，允许编译
```

## 三、编译条件匹配器

### 3.1 三维度求值

```typescript
interface CompilationContext {
  model: string;        // 当前编译的目标模型
  language: string;     // 当前编译的目标语言
  industry?: string;    // 当前编译的目标行业（可选）
}

function evaluateCondition(condition: Condition, context: CompilationContext): boolean {
  const dimensionValue = context[condition.dimension];

  switch (condition.operator) {
    case "==":
      return dimensionValue === condition.value;
    case "!=":
      return dimensionValue !== condition.value;
    case "in":
      return (condition.value as string[]).includes(dimensionValue);
    case "not_in":
      return !(condition.value as string[]).includes(dimensionValue);
  }

  if (condition.logical) {
    const leftResult = evaluateCondition(condition, context);
    const rightResult = evaluateCondition(condition.logical.right, context);
    return condition.logical.operator === "&&"
      ? leftResult && rightResult
      : leftResult || rightResult;
  }

  return false;
}
```

### 3.2 匹配流程

```
1. 解析模板为AST
2. 遍历AST，对每个条件节点执行evaluateCondition
3. 条件为true: 保留该分支内容
4. 条件为false: 忽略该分支内容
5. 无匹配分支且无else: 发出"编译结果为空"告警
6. 生成编译后文本
```

## 四、编译结果生成器

### 4.1 生成规则

```
FOR each node in AST (深度优先遍历):
    IF node.type == "text":
        追加 node.content 到输出
    ELIF node.type == "if":
        IF evaluateCondition(node.condition, context):
            递归处理 node.children
        ELSE:
            查找 else_if / else 分支
            IF 找到匹配的 else_if:
                递归处理其 children
            ELIF 找到 else:
                递归处理其 children
            ELSE:
                忽略整个条件块
```

## 五、LRU缓存层

### 5.1 缓存设计

```typescript
interface CacheEntry {
  key: string;           // SHA256(template_id + compilation_context)
  value: string;         // 编译后文本
  created_at: number;    // 创建时间戳
  ttl: number;           // 生存时间(ms)，默认86400000(24h)
  hit_count: number;     // 命中次数
  size_bytes: number;    // 缓存条目大小
}

interface LRUCache {
  max_entries: 1000;
  ttl_ms: 86400000;      // 24小时
  hit_rate_target: 0.80; // 命中率目标≥80%
  hit_latency_target_ms: 10; // 命中响应时间<10ms
}
```

### 5.2 缓存键计算

```
cache_key = SHA256(
  template_id + "|" +
  compilation_context.model + "|" +
  compilation_context.language + "|" +
  (compilation_context.industry || "") + "|" +
  template_content_hash  // 模板内容变化时缓存失效
)
```

### 5.3 缓存淘汰策略

```
当缓存条目数 > max_entries:
    淘汰最久未使用(LRU)的条目

当缓存条目 TTL过期:
    惰性删除（下次访问时检查TTL）

当模板内容变化:
    删除该模板的所有缓存条目（通过template_id前缀扫描）
```

### 5.4 缓存命中率目标

| 指标 | 目标 | 说明 |
|------|------|------|
| 命中率 | ≥ 80% | 相同模板+相同上下文的重复编译 |
| 命中延迟 | < 10ms | 缓存命中时的响应时间 |
| 未命中延迟 | < 200ms | 缓存未命中时的编译+缓存时间 |
| 内存占用 | ≤ 100MB | 1000条缓存的最大内存 |

## 六、compilation_context_schema.yaml

```yaml
# 条件编译上下文Schema
version: "1.0.0"

compilation_context:
  model:
    type: "string"
    required: true
    enum:
      - "gpt-4o"
      - "gpt-4o-mini"
      - "claude-3.5-sonnet"
      - "claude-3-haiku"
      - "qwen-max"
      - "qwen-plus"
      - "pangu-large"
      - "pangu-medium"
      - "deepseek-v3"
      - "glm-4"
    description: "目标AI模型ID"

  language:
    type: "string"
    required: true
    enum:
      - "zh"     # 中文
      - "en"     # 英文
      - "ja"     # 日文
      - "ko"     # 韩文
      - "fr"     # 法文
      - "de"     # 德文
      - "es"     # 西班牙文
      - "pt"     # 葡萄牙文
      - "ru"     # 俄文
      - "ar"     # 阿拉伯文
    description: "输出语言代码(ISO 639-1)"

  industry:
    type: "string"
    required: false
    enum:
      - "financial"       # 金融
      - "healthcare"      # 医疗
      - "education"       # 教育
      - "manufacturing"   # 制造
      - "government"      # 政府
      - "retail"          # 零售
      - "energy"          # 能源
      - "telecom"         # 电信
      - "logistics"       # 物流
      - "media"           # 媒体
    description: "目标行业代码"

  flags:
    type: "object"
    required: false
    properties:
      strict_compliance:
        type: "boolean"
        default: false
        description: "启用严格合规模式"
      verbose_output:
        type: "boolean"
        default: false
        description: "启用详细输出模式"
```
