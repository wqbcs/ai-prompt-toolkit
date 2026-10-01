# UPPL语法分析器设计

> 版本：v1.0 | 日期：2026-05-29

---

## 1. AST节点类型

### 1.1 核心节点

| 节点类型 | 描述 | 子节点 |
|----------|------|--------|
| Program | 程序根节点 | imports[], declarations[] |
| ImportDecl | 导入声明 | module_path, items[] |
| PromptDecl | 提示词声明 | id, params[], body, constraints[], output_spec |
| ScenarioDecl | 场景声明 | id, prompt_ref, bindings{}, constraints[] |
| ConstraintDecl | 约束声明 | id, level, expression, message |
| OutputSpec | 输出规范 | format, schema?, validators[] |
| TypeDecl | 类型声明 | id, base_type, fields[] |
| EnumDecl | 枚举声明 | id, values[] |

### 1.2 表达式节点

| 节点类型 | 描述 | 子节点 |
|----------|------|--------|
| BinaryExpr | 二元表达式 | left, op, right |
| UnaryExpr | 一元表达式 | op, operand |
| CallExpr | 函数调用 | callee, args[] |
| MemberExpr | 成员访问 | object, property |
| PipeExpr | 管道表达式 | left, right |
| LambdaExpr | Lambda | params[], body |
| ConditionalExpr | 条件表达式 | condition, then, else |
| LiteralExpr | 字面量 | value, type |
| IdentifierExpr | 标识符 | name |
| TemplateExpr | 模板表达式 | parts[](text/variable) |

### 1.3 语句节点

| 节点类型 | 描述 | 子节点 |
|----------|------|--------|
| WhenStmt | 条件语句 | condition, body[] |
| ForEachStmt | 循环语句 | variable, iterable, body[] |
| EnsureStmt | 断言语句 | expression, message? |
| ReturnStmt | 返回语句 | expression |
| BlockStmt | 块语句 | statements[] |

## 2. 解析规则(EBNF风格)

```
program         ::= import_decl* declaration*

import_decl     ::= 'import' import_item (',' import_item)* 'from' STRING
import_item     ::= IDENTIFIER ('as' IDENTIFIER)?

declaration     ::= prompt_decl | scenario_decl | constraint_decl | type_decl | enum_decl

prompt_decl     ::= 'prompt' IDENTIFIER '(' param_list? ')' constraint_block? prompt_body output_spec?

param_list      ::= param (',' param)*
param           ::= IDENTIFIER ':' type_expr ('=' expression)?

type_expr       ::= 'string' | 'number' | 'boolean' | 'array' | 'object'
                  | IDENTIFIER              // 自定义类型
                  | type_expr '[' ']'       // 数组类型
                  | type_expr '|' type_expr // 联合类型

constraint_block ::= 'with' '{' constraint_item* '}'
constraint_item  ::= 'ensure' expression ('as' STRING)? ';'

prompt_body     ::= 'given' statement_list 'then' expression
                  | STRING                    // 简单模板

output_spec     ::= 'output' output_format output_schema? validator_list?
output_format   ::= 'text' | 'json' | 'markdown' | 'xml'
output_schema   ::= ':' type_expr
validator_list  ::= 'validate' '{' validator_item* '}'
validator_item  ::= IDENTIFIER ':' expression ';'

scenario_decl   ::= 'scenario' IDENTIFIER 'use' IDENTIFIER binding_block? constraint_block?
binding_block   ::= 'with' '{' binding_item* '}'
binding_item    ::= IDENTIFIER '=' expression ';'

constraint_decl ::= 'constraint' IDENTIFIER level_spec expression message_spec?
level_spec      ::= ':' ('error' | 'warn' | 'info')
message_spec    ::= 'as' STRING

statement       ::= when_stmt | for_each_stmt | ensure_stmt | return_stmt | expression_stmt
when_stmt       ::= 'when' expression '{' statement_list '}'
for_each_stmt   ::= 'for' 'each' IDENTIFIER 'in' expression '{' statement_list '}'
ensure_stmt     ::= 'ensure' expression ('as' STRING)? ';'
return_stmt     ::= 'return' expression ';'

expression      ::= pipe_expr
pipe_expr       ::= conditional_expr ('|>' pipe_expr)*
conditional_expr::= logical_or_expr ('if' expression 'else' conditional_expr)?
logical_or_expr ::= logical_and_expr ('||' logical_and_expr)*
logical_and_expr::= equality_expr ('&&' equality_expr)*
equality_expr   ::= comparison_expr (('==' | '!=') comparison_expr)*
comparison_expr ::= additive_expr (('>' | '<' | '>=' | '<=') additive_expr)*
additive_expr   ::= multiplicative_expr (('+' | '-') multiplicative_expr)*
multiplicative_expr ::= unary_expr (('*' | '/') unary_expr)*
unary_expr      ::= ('!' | '-') unary_expr | call_expr
call_expr       ::= primary_expr ('(' arg_list? ')')* ('.' IDENTIFIER)*
primary_expr    ::= STRING | NUMBER | BOOLEAN | IDENTIFIER
                  | '(' expression ')'
                  | lambda_expr
                  | template_expr
lambda_expr     ::= param_list? '=>' expression
template_expr   ::= '`' template_part* '`'
template_part   ::= TEXT | '${' expression '}'
```

## 3. 语法分析器核心逻辑

```python
class UPPLParser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> Program:
        imports = []
        declarations = []
        while not self._at_end():
            if self._match(TokenType.KEYWORD, 'import'):
                imports.append(self._parse_import())
            else:
                declarations.append(self._parse_declaration())
        return Program(imports=imports, declarations=declarations)

    def _parse_declaration(self) -> ASTNode:
        if self._match(TokenType.KEYWORD, 'prompt'):
            return self._parse_prompt_decl()
        elif self._match(TokenType.KEYWORD, 'scenario'):
            return self._parse_scenario_decl()
        elif self._match(TokenType.KEYWORD, 'constraint'):
            return self._parse_constraint_decl()
        elif self._match(TokenType.KEYWORD, 'type'):
            return self._parse_type_decl()
        elif self._match(TokenType.KEYWORD, 'enum'):
            return self._parse_enum_decl()
        else:
            raise SyntaxError(f"Expected declaration, got {self._current()}")

    def _parse_prompt_decl(self) -> PromptDecl:
        name = self._expect(TokenType.IDENTIFIER).value
        params = []
        if self._match(TokenType.PUNCTUATION, '('):
            params = self._parse_param_list()
            self._expect(TokenType.PUNCTUATION, ')')
        constraints = []
        if self._match(TokenType.KEYWORD, 'with'):
            constraints = self._parse_constraint_block()
        body = self._parse_prompt_body()
        output = None
        if self._match(TokenType.KEYWORD, 'output'):
            output = self._parse_output_spec()
        return PromptDecl(id=name, params=params, body=body,
                         constraints=constraints, output_spec=output)

    def _parse_prompt_body(self):
        if self._match(TokenType.KEYWORD, 'given'):
            stmts = self._parse_statement_list()
            self._expect(TokenType.KEYWORD, 'then')
            expr = self._parse_expression()
            return PromptBody(given=stmts, then=expr)
        elif self._current().type == TokenType.STRING_LITERAL:
            return TemplateExpr(parts=[LiteralExpr(value=self._advance().value)])
        else:
            raise SyntaxError(f"Expected prompt body, got {self._current()}")

    def _parse_expression(self) -> Expr:
        return self._parse_pipe_expr()

    def _parse_pipe_expr(self) -> Expr:
        left = self._parse_conditional_expr()
        while self._match(TokenType.PIPE):
            right = self._parse_conditional_expr()
            left = PipeExpr(left=left, right=right)
        return left

    def _expect(self, type: TokenType, value: str = None) -> Token:
        token = self._current()
        if token.type != type or (value and token.value != value):
            raise SyntaxError(f"Expected {type}:{value}, got {token}")
        return self._advance()

    def _match(self, type: TokenType, value: str = None) -> bool:
        if self._current().type == type and (not value or self._current().value == value):
            self._advance()
            return True
        return False

    def _current(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else Token(TokenType.EOF, '', 0, 0)

    def _advance(self) -> Token:
        token = self._current()
        self.pos += 1
        return token

    def _at_end(self) -> bool:
        return self._current().type == TokenType.EOF
```
