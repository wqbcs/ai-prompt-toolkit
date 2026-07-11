# UPPL编译器规范与语言参考手册

> 版本：v14.0.0 | 日期：2026-05-29

---

## 1. 编译器架构

```
UPPL Source → Lexer → Token Stream → Parser → AST → 
  Semantic Analyzer → Typed AST → 
  Optimizer → Optimized AST → 
  Code Generator → Target (NL/JSON/Agent)
```

### 1.1 编译阶段
| 阶段 | 输入 | 输出 | 职责 |
|------|------|------|------|
| 词法分析 | 源码字符串 | Token流 | 分词+过滤注释 |
| 语法分析 | Token流 | AST | 构建抽象语法树 |
| 语义分析 | AST | 类型化AST | 类型检查+作用域解析 |
| 优化 | 类型化AST | 优化AST | 死代码消除+约束简化 |
| 代码生成 | 优化AST | 目标代码 | 生成NL/JSON/Agent |

### 1.2 错误处理
| 级别 | 示例 | 行为 |
|------|------|------|
| Error | 类型不匹配 | 编译失败+诊断 |
| Warning | 未使用变量 | 继续+警告 |
| Info | 可优化提示 | 继续+提示 |

---

## 2. UPPL语言参考手册

### 2.1 模块声明
```uppl
module ModuleName(version "x.y.z");
```

### 2.2 导入
```uppl
import ModuleName;                    // 全导入
import ModuleName.{Item1, Item2};     // 选择导入
import ModuleName as Alias;           // 别名导入
```

### 2.3 场景
```uppl
scene SceneName {
  role: "角色描述";
  task: "任务描述";
  context name: type = default_value;  // 可选默认值
  context name: type;                  // 必需
}
```

### 2.4 约束
```uppl
constraint ConstraintName {
  must: expr;              // 必须满足(违反=error)
  must_not: expr;          // 必须不满足(违反=error)
  prefer: expr;            // 优选(违反=warning)
  priority: number;        // 1-10，默认5
}
```

### 2.5 输出
```uppl
output {
  format: json;                    // 输出格式
  schema: OutputSchemaType;        // Schema类型
  example: "input" => "output";    // 示例
}
```

### 2.6 检查项
```uppl
check CheckName {
  assert: expr => "通过消息";       // 断言
  verify: expr;                      // 验证
  measure name: expr;                // 度量
}
```

### 2.7 步骤(命令式)
```uppl
step StepName {
  action: "动作描述";
  call FunctionName(args);          // 调用
  var = expr;                       // 赋值
}
```

### 2.8 控制流(命令式)
```uppl
if expr then { ... } else { ... }
for item in collection { ... }
while expr { ... }
repeat { ... } until expr
```

---

## 3. 内置函数

| 函数 | 签名 | 说明 |
|------|------|------|
| len | (list/dict) → number | 长度 |
| contains | (string, string) → bool | 包含 |
| matches | (string, regex) → bool | 正则匹配 |
| starts_with | (string, string) → bool | 前缀 |
| upper/lower | (string) → string | 大小写 |
| filter | (list, predicate) → list | 过滤 |
| map | (list, function) → list | 映射 |
| reduce | (list, function, init) → any | 归约 |
| sort | (list, key?) → list | 排序 |
| unique | (list) → list | 去重 |
| merge | (dict, dict) → dict | 合并 |
| weighted_score | (Constraint) → number | 约束加权分数 |

---

## 4. 与运行时集成

UPPL编译器输出可被提示词运行时直接加载：
```
UPPL源码 → 编译器 → JSON规范 → 运行时加载 → 执行
```

运行时提供UPPL执行环境：
- 加载：从.uppl文件或URN加载
- 解析：UPPL Parser编译到AST
- 验证：类型检查+约束验证
- 执行：步骤序列执行+约束检查
- 监控：度量收集+断言检查
