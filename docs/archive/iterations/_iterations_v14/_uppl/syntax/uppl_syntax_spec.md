# UPPL(Universal Prompt Programming Language)语法规范

> 版本：v14.0.0 | 日期：2026-05-29 | 规范编号：PE-UPPL-SYNTAX-001

---

## 1. 设计哲学

UPPL是声明式与命令式混合的提示词编程语言：
- **声明式**：描述"要什么"(场景/约束/输出)
- **命令式**：描述"怎么做"(步骤/分支/循环)
- **编译性**：可编译到自然语言/JSON/Agent指令

---

## 2. EBNF语法规范

### 2.1 顶层结构
```ebnf
program        ::= module_decl (statement)*
module_decl    ::= 'module' IDENT '(' version_spec ')' ';'
version_spec   ::= 'version' STRING
statement      ::= import_decl
               | scene_decl
               | constraint_decl
               | output_decl
               | check_decl
               | step_decl
               | branch_decl
               | loop_decl
               | expr_statement
```

### 2.2 场景声明(声明式)
```ebnf
scene_decl     ::= 'scene' IDENT '{' scene_body '}'
scene_body     ::= (role_decl | task_decl | context_decl)*
role_decl      ::= 'role' ':' STRING ';'
task_decl      ::= 'task' ':' STRING ';'
context_decl   ::= 'context' IDENT ':' type_expr '=' expr ';'
```

### 2.3 约束声明(声明式)
```ebnf
constraint_decl ::= 'constraint' IDENT '{' constraint_body '}'
constraint_body ::= (must_decl | must_not_decl | prefer_decl)*
must_decl      ::= 'must' ':' expr ';'
must_not_decl  ::= 'must_not' ':' expr ';'
prefer_decl    ::= 'prefer' ':' expr ';'
```

### 2.4 输出声明(声明式)
```ebnf
output_decl    ::= 'output' '{' output_body '}'
output_body    ::= format_decl schema_decl? example_decl*
format_decl    ::= 'format' ':' ('json' | 'yaml' | 'markdown' | 'text' | IDENT) ';'
schema_decl    ::= 'schema' ':' type_expr ';'
example_decl   ::= 'example' STRING '=>' STRING ';'
```

### 2.5 检查项声明(声明式)
```ebnf
check_decl     ::= 'check' IDENT '{' check_body '}'
check_body     ::= (assert_decl | verify_decl | measure_decl)*
assert_decl    ::= 'assert' ':' expr ('=>' STRING)? ';'
verify_decl    ::= 'verify' ':' expr ';'
measure_decl   ::= 'measure' IDENT ':' expr ';'
```

### 2.6 步骤声明(命令式)
```ebnf
step_decl      ::= 'step' IDENT '{' step_body '}'
step_body      ::= (action_decl | call_decl | assign_decl)*
action_decl    ::= 'action' ':' STRING ';'
call_decl      ::= 'call' IDENT '(' arg_list? ')' ';'
assign_decl    ::= IDENT '=' expr ';'
```

### 2.7 分支与循环(命令式)
```ebnf
branch_decl    ::= 'if' expr 'then' '{' statement* '}' ('else' '{' statement* '}')?
loop_decl      ::= 'for' IDENT 'in' expr '{' statement* '}'
               | 'while' expr '{' statement* '}'
               | 'repeat' '{' statement* '}' 'until' expr
```

### 2.8 表达式
```ebnf
expr           ::= literal
               | IDENT
               | expr '.' IDENT
               | expr '(' arg_list? ')'
               | expr op expr
               | 'not' expr
               | '(' expr ')'
               | list_expr
               | dict_expr

literal        ::= STRING | NUMBER | BOOL | 'null'
list_expr      ::= '[' (expr (',' expr)*)? ']'
dict_expr      ::= '{' (STRING ':' expr (',' STRING ':' expr)*)? '}'
arg_list       ::= expr (',' expr)*
op             ::= '+' | '-' | '*' | '/' | '==' | '!=' | '<' | '>' | '<=' | '>='
               | 'and' | 'or' | 'contains' | 'matches'
type_expr      ::= 'string' | 'number' | 'bool' | 'list' '<' type_expr '>'
               | 'dict' '<' STRING ':' type_expr '>'
               | IDENT       // 自定义类型
```

---

## 3. 保留关键字

```
module version import scene role task context
constraint must must_not prefer
output format schema example
check assert verify measure
step action call
if then else for in while repeat until
string number bool list dict null
true false not and or contains matches
```

---

## 4. 注释
```uppl
// 单行注释
/* 多行注释 */
```

---

## 5. UPPL示例(代码审查场景)

```uppl
module CodeReview(version "2.0.0");

import SecurityChecks;
import QualityMetrics;

scene CodeReviewScene {
  role: "资深代码审查专家";
  task: "对代码变更进行全维度审查";
  context code: string;
  context language: string;
  context diff: string;
  context author: string;
}

constraint SecurityConstraint {
  must: SecurityChecks.no_sql_injection(code);
  must: SecurityChecks.no_hardcoded_secrets(code);
  must_not: code.contains("eval(") or code.contains("exec(");
  prefer: SecurityChecks.input_validation_present(code);
}

constraint QualityConstraint {
  must: QualityMetrics.complexity(code) <= 20;
  must: QualityMetrics.test_coverage(code) >= 0.8;
  prefer: QualityMetrics.naming_convention(code) == "consistent";
}

output {
  format: json;
  schema: CodeReviewOutput;
  example: "def add(a,b): return a+b" => 
    '{"security": "pass", "quality": {"complexity": 2, "coverage": 0.9}}';
}

check SecurityCheck {
  assert: SecurityConstraint.satisfied => "安全检查通过";
  verify: no_vulnerabilities_found;
  measure security_score: SecurityChecks.score(code);
}

check QualityCheck {
  assert: QualityConstraint.satisfied => "质量检查通过";
  verify: no_major_issues_found;
  measure quality_score: QualityMetrics.score(code);
}

step Analyze {
  action: "分析代码变更范围和影响";
  call SecurityCheck();
  call QualityCheck();
}

step GenerateReport {
  action: "生成审查报告";
  call format_output(security_score, quality_score);
}
```
