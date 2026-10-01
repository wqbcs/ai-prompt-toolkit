# 社区贡献指南

> 版本：v16.0.0 | 新贡献者必读

---

## 1. 快速开始(10分钟内)

### 1.1 环境准备

```bash
# 1. Fork并克隆仓库
git clone https://github.com/your-org/prompt-system.git
cd prompt-system

# 2. 安装依赖
pip install -r requirements.txt  # Python SDK
npm install                       # TypeScript SDK

# 3. 验证开发环境
make dev-verify  # 应输出: ✓ Environment ready

# 4. 运行测试
make test  # 应全部通过
```

### 1.2 找到你的首个Issue

```
标签筛选：
- good-first-issue：适合新手
- help-wanted：需要帮助
- i18n：翻译相关
- documentation：文档改进
- performance：性能优化
```

## 2. 贡献类型

| 类型 | 难度 | 预期时间 | 示例 |
|------|------|---------|------|
| 文档修正 | 简单 | 1-2小时 | 修复拼写/补充示例 |
| 翻译贡献 | 简单 | 2-4小时/场景 | 新语言场景翻译 |
| Bug修复 | 中等 | 4-8小时 | 修复已知Bug |
| 功能增强 | 中等 | 1-3天 | 新增场景/优化现有 |
| 新场景 | 较难 | 3-5天 | 设计+实现+测试完整场景 |
| 性能优化 | 较难 | 2-5天 | 性能基准+优化+验证 |
| 架构改进 | 困难 | 1-2周 | 重构+迁移+兼容性 |

## 3. PR提交流程

### 3.1 分支命名

```
feature/S<id>-<描述>    # 新功能
fix/S<id>-<描述>        # Bug修复
docs/S<id>-<描述>       # 文档
i18n/S<id>-<语言>       # 翻译
perf/S<id>-<描述>       # 性能
```

### 3.2 PR模板

```markdown
## 变更类型
- [ ] Feature / [ ] Fix / [ ] Docs / [ ] i18n / [ ] Perf

## 关联Issue
Fixes #

## 变更描述
<详细描述>

## 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动验证

## 检查清单
- [ ] 代码规范
- [ ] 无硬编码字符串(i18n)
- [ ] 文档已更新
- [ ] CHANGELOG已更新
```

### 3.3 Commit消息规范

```
<type>(<scope>): <subject>

type: feat|fix|docs|i18n|perf|refactor|test|chore
scope: scenario|sdk|runtime|i18n|ecosystem|security
subject: 简明描述(50字内)
```

## 4. 代码规范

### 4.1 通用规范
- 缩进：2空格(不使用Tab)
- 行宽：100字符
- 编码：UTF-8无BOM
- 换行：LF(不使用CRLF)

### 4.2 提示词规范
- 每场景单一职责(P1)
- 输出必须符合Schema(P2)
- 约束在指令前声明(P3)
- 提供输入→输出示例(P4)

## 5. Review标准

| 检查项 | 要求 |
|--------|------|
| 正确性 | 逻辑正确，输出符合Schema |
| 安全性 | 无注入风险，无敏感信息泄露 |
| 性能 | 无明显性能退化 |
| 可读性 | 代码清晰，命名合理 |
| 测试 | 覆盖关键路径 |
| 文档 | 公开API有文档 |
| i18n | 无硬编码可翻译字符串 |
