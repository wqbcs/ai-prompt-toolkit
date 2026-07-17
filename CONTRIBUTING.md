# 贡献指南

感谢你对 ai-prompt-toolkit 的关注！欢迎参与项目贡献。

## 快速开始

```bash
# 1. Fork & Clone
git clone https://github.com/YOUR_USERNAME/ai-prompt-toolkit.git
cd ai-prompt-toolkit

# 2. 安装开发依赖
pip install -e ".[dev]"

# 3. 运行测试
pytest tests/ -v

# 4. 代码格式化
black src/ tests/
isort src/ tests/
```

## 贡献流程

1. **创建Issue** - 描述问题或功能需求
2. **Fork仓库** - 在你的账户下创建分支
3. **开发** - 在feature分支上开发
4. **测试** - 确保所有测试通过，新增功能需有对应测试
5. **提交PR** - 描述变更内容和原因

## 代码规范

- Python 3.10+ 语法
- 类型注解：所有公开API必须有类型注解
- 文档字符串：所有公开函数/类必须有docstring
- 测试覆盖：新增功能必须包含测试
- 代码格式：使用 black + isort

## 提交信息格式

```
feat: 简短描述
fix: 简短描述
docs: 简短描述
refactor: 简短描述
test: 简短描述
```

## 添加Lint规则

1. 在 `src/ai_prompt_toolkit/linter/rules_pXXX_pYYY.py` 中定义规则
2. 实现检测函数 `check_pXXX(text: str) -> Finding | None`
3. 注册到 `_RULE_MAP`
4. 在 `rules.py` 中导入并添加到 `_CHECKERS_EXTENDED`
5. 编写测试

## 报告Bug

请使用 GitHub Issues，包含：
- 复现步骤
- 期望行为
- 实际行为
- 环境信息（Python版本、OS等）

## 许可

贡献的代码将采用 MIT 许可证。
