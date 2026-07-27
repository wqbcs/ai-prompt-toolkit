# 贡献指南 | Contributing Guide

感谢你对 **ai-prompt-toolkit** 的贡献兴趣！

## 快速开始

```bash
# 1. Fork & Clone
git clone https://github.com/YOUR_USERNAME/ai-prompt-toolkit.git
cd ai-prompt-toolkit

# 2. 安装开发依赖
pip install -e ".[dev]"

# 3. 运行测试
pytest tests/ -v

# 4. 代码格式化 + Lint
ruff format src/ tests/
ruff check src/ tests/
```

## 贡献流程

1. **创建Issue** — 描述问题或功能需求
2. **Fork仓库** — 在你的账户下创建分支
3. **开发** — 在feature分支上开发(`feat/xxx`, `fix/xxx`, `docs/xxx`)
4. **测试** — 确保所有测试通过，新增功能需有对应测试
5. **提交PR** — 描述变更内容和原因

## 代码规范

- **Python 3.10+** 语法
- **类型注解**：所有公开API必须有类型注解
- **文档字符串**：所有公开函数/类必须有docstring
- **测试覆盖**：新增功能必须包含测试
- **代码格式**：使用 `ruff format` + `ruff check`
- **提交信息**：遵循 [Conventional Commits](https://www.conventionalcommits.org/)

```
feat: 简短描述
fix: 简短描述
docs: 简短描述
refactor: 简短描述
test: 简短描述
```

## 添加Lint规则

1. 创建 `src/ai_prompt_toolkit/linter/rules_pXXX_pYYY.py`
2. 定义 `_RULES_PXXX_PYYY` 列表，包含 `LintRule` 对象
3. 通过 `_RULE_MAP[r.rule_id] = r` 注册到全局
4. 实现 check 函数 `check_pXXX(text: str) -> Finding | None`
5. 在 `rules.py` 中 import check 并添加到 `_CHECKERS_EXTENDED`
6. 在 `owasp_mapping.py` 的 `_OWASP_RULE_MAPPING` 添加 OWASP 映射
7. 在 `fixer.py` 的 `AUTO_FIXABLE_RULES` 添加(如可自动修复)
8. 在 `linter.py` 的 `_get_fix_action` 添加修复逻辑(如可自动修复)
9. **更新测试断言中的Lint规则数量**
10. 编写测试 `tests/test_rXX.py`

## 添加Probe

1. 在 `redteam/probes/` 创建模块
2. 继承 `BaseProbe`，实现 `generate_inputs()` 方法
3. 自动发现机制(`_?discover_probes`)会自动注册

## 添加Provider

1. 在 `ab_test/providers/` 创建模块
2. 继承 `BaseProvider`，实现 `generate()` 和 `parse_response()` 方法
3. 自动发现机制会自动注册

## 添加评估维度

1. 在 `evaluator.py` 的 `_DIMENSIONS` 列表添加维度字典
2. 更新测试断言中的维度数量

## 添加MCP工具

1. 在 `mcp_server.py` 的 `_handle_tools_list` 添加工具定义
2. 实现工具处理函数 `_tool_xxx(args) -> dict`
3. 在 `_get_tool_dispatch` 添加 dispatch 映射
4. tools list 和 dispatch 必须同步

## 安全规范

- **禁止提交** API Key/密码/token等敏感信息
- 所有用户输入必须经过安全检查
- 新增安全规则需同步更新OWASP映射
- 安全相关变更需标注 `[SECURITY]` 前缀

## 报告Bug

请使用 GitHub Issues，包含：
- 复现步骤
- 期望行为
- 实际行为
- 环境信息（Python版本、OS等）

## 许可

贡献的代码遵循 MIT 许可证。
