"""Parser单元测试——AST构建、嵌套>3、未闭合检测。"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.compiler.lexer import Lexer
from ai_prompt_toolkit.compiler.parser import NestingError, ParseError, Parser
from ai_prompt_toolkit.compiler.types import ASTNode, Condition, NodeType, Token, TokenKind


class TestASTConstruction:
    def test_simple_text(self):
        tokens = Lexer("Hello").tokenize()
        ast = Parser(tokens).parse()
        assert ast.type == NodeType.BLOCK
        assert len(ast.children) == 1
        assert ast.children[0].type == NodeType.TEXT
        assert ast.children[0].value == "Hello"

    def test_simple_conditional(self):
        tokens = Lexer("{{#if model == gpt-4}}A{{/if}}").tokenize()
        ast = Parser(tokens).parse()
        assert ast.type == NodeType.BLOCK
        assert len(ast.children) == 1
        cond = ast.children[0]
        assert cond.type == NodeType.CONDITIONAL
        assert cond.condition is not None
        assert cond.condition.dimension == "model"
        assert cond.condition.operator == "=="
        assert cond.condition.value == "gpt-4"

    def test_conditional_with_else(self):
        tokens = Lexer("{{#if model == gpt-4}}A{{else}}B{{/if}}").tokenize()
        ast = Parser(tokens).parse()
        cond = ast.children[0]
        assert cond.type == NodeType.CONDITIONAL
        children = cond.children
        assert len(children) >= 2
        assert children[0].type == NodeType.TEXT
        assert children[0].value == "A"

    def test_else_if_chain(self):
        tokens = Lexer(
            "{{#if model == gpt-4}}A{{#else if model == claude}}B{{else}}C{{/if}}"
        ).tokenize()
        ast = Parser(tokens).parse()
        cond = ast.children[0]
        assert cond.type == NodeType.CONDITIONAL
        conditionals = [c for c in cond.children if c.type == NodeType.CONDITIONAL]
        assert len(conditionals) >= 1

    def test_multiple_conditionals(self):
        source = "{{#if model == gpt-4}}A{{/if}} text {{#if language == zh}}B{{/if}}"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        conditionals = [c for c in ast.children if c.type == NodeType.CONDITIONAL]
        assert len(conditionals) == 2


class TestConditionParsing:
    def test_equality(self):
        tokens = Lexer("{{#if model == gpt-4}}X{{/if}}").tokenize()
        ast = Parser(tokens).parse()
        cond = ast.children[0].condition
        assert cond.dimension == "model"
        assert cond.operator == "=="
        assert cond.value == "gpt-4"

    def test_inequality(self):
        tokens = Lexer("{{#if model != gpt-4}}X{{/if}}").tokenize()
        ast = Parser(tokens).parse()
        cond = ast.children[0].condition
        assert cond.operator == "!="

    def test_in_operator(self):
        tokens = Lexer("{{#if model in gpt-4,claude}}X{{/if}}").tokenize()
        ast = Parser(tokens).parse()
        cond = ast.children[0].condition
        assert cond.operator == "in"
        assert cond.value == ["gpt-4", "claude"]

    def test_not_in_operator(self):
        tokens = Lexer("{{#if model not_in gpt-4}}X{{/if}}").tokenize()
        ast = Parser(tokens).parse()
        cond = ast.children[0].condition
        assert cond.operator == "not_in"

    def test_logical_and(self):
        tokens = Lexer("{{#if model == gpt-4 && language == zh}}X{{/if}}").tokenize()
        ast = Parser(tokens).parse()
        cond = ast.children[0].condition
        assert cond.logical == "&&"
        assert cond.right is not None
        assert cond.right.dimension == "language"

    def test_logical_or(self):
        tokens = Lexer("{{#if model == gpt-4 || model == claude}}X{{/if}}").tokenize()
        ast = Parser(tokens).parse()
        cond = ast.children[0].condition
        assert cond.logical == "||"


class TestNestingDepth:
    def test_nesting_depth_1(self):
        source = "{{#if a == 1}}X{{/if}}"
        ast = Parser(Lexer(source).tokenize()).parse()
        assert ast.children[0].type == NodeType.CONDITIONAL

    def test_nesting_depth_2(self):
        source = "{{#if a == 1}}{{#if b == 2}}X{{/if}}{{/if}}"
        ast = Parser(Lexer(source).tokenize()).parse()
        assert ast.children[0].type == NodeType.CONDITIONAL

    def test_nesting_depth_3(self):
        source = "{{#if a == 1}}{{#if b == 2}}{{#if c == 3}}X{{/if}}{{/if}}{{/if}}"
        ast = Parser(Lexer(source).tokenize()).parse()
        assert ast.children[0].type == NodeType.CONDITIONAL

    def test_nesting_exceeds_3(self):
        source = "{{#if a == 1}}{{#if b == 2}}{{#if c == 3}}{{#if d == 4}}X{{/if}}{{/if}}{{/if}}{{/if}}"
        with pytest.raises(NestingError) as exc_info:
            Parser(Lexer(source).tokenize()).parse()
        assert exc_info.value.depth == 4


class TestUnclosedDetection:
    def test_unclosed_if(self):
        source = "{{#if model == gpt-4}}Hello"
        with pytest.raises(ParseError) as exc_info:
            Parser(Lexer(source).tokenize()).parse()
        assert "未闭合" in str(exc_info.value)

    def test_unclosed_nested(self):
        source = "{{#if a == 1}}{{#if b == 2}}X{{/if}}"
        with pytest.raises(ParseError):
            Parser(Lexer(source).tokenize()).parse()

    def test_properly_closed(self):
        source = "{{#if model == gpt-4}}Hello{{/if}}"
        ast = Parser(Lexer(source).tokenize()).parse()
        assert ast.type == NodeType.BLOCK
