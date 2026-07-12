---
version: "1.0.0"
author: "AI提示词体系"
updated_at: "2026-07-12"
category: tooling
---

# Prompt Linter 引擎简介

## 定位

Prompt Linter 是一个静态检查提示词质量的工具，参考 ESLint（JavaScript）和 Ruff（Python）的架构设计，为提示词工程提供可配置、可扩展的规则化检查能力。

## 核心目标

1. **质量门禁**：在提示词进入生产环境前自动检查，拦截结构性缺陷、安全风险和性能浪费
2. **标准化**：建立提示词质量基线，团队协作时统一标准，减少主观判断
3. **持续改进**：通过规则迭代和配置调优，持续提升提示词质量

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│                    Prompt Linter                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  Parser  │───▶│  Linter  │───▶│ Reporter │      │
│  │  解析器   │    │  检查器   │    │  报告器   │      │
│  └──────────┘    └──────────┘    └──────────┘      │
│       │               │               │             │
│       ▼               ▼               ▼             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  AST /   │    │  Rules   │    │  Output  │      │
│  │  结构树   │    │  规则集   │    │  输出格式  │      │
│  └──────────┘    └──────────┘    └──────────┘      │
│                       │                             │
│                       ▼                             │
│                 ┌──────────┐                        │
│                 │  Config  │                        │
│                 │  配置文件  │                        │
│                 └──────────┘                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 核心模块

| 模块 | 职责 | 类比 |
|------|------|------|
| **Parser** | 解析提示词文本为结构化AST（角色/指令/示例/约束等节点） | ESLint的 Espree |
| **Linter** | 遍历AST节点，应用启用的规则进行检查 | ESLint的 Linter |
| **Rules** | 可插拔的规则集，每条规则独立检测特定问题 | ESLint的 Rules |
| **Config** | YAML配置文件，控制规则启用/禁用/严重级别/忽略模式 | ESLint的 .eslintrc |
| **Reporter** | 格式化检查结果输出（终端/JSON/Markdown） | ESLint的 Formatters |

## 工作流程

```
1. 读取配置文件 (_linter/config.yaml)
2. 加载启用的规则集
3. 解析提示词文本为结构化AST
4. 遍历AST节点，逐条规则执行检查
5. 收集检查结果（问题列表）
6. 按严重级别和规则分类排序
7. 输出检查报告（终端高亮 / JSON / Markdown）
8. 返回退出码（0=通过, 1=警告, 2=错误）
```

## 规则分类

| 类别 | 范围 | 规则数 |
|------|------|--------|
| 结构类 (P001-P005) | 提示词必需元素完整性 | 5 |
| 安全类 (P006-P010) | 敏感信息泄露、注入风险 | 5 |
| 性能类 (P011-P015) | Token效率、冗余检测 | 5 |
| 质量类 (P016-P020) | 歧义、矛盾、评估标准 | 5 |

## 严重级别

| 级别 | 含义 | 退出码影响 |
|------|------|-----------|
| `error` | 必须修复，否则提示词不可用 | 导致检查失败 |
| `warning` | 建议修复，可能影响效果 | 不导致检查失败 |
| `info` | 优化建议，可选修复 | 不导致检查失败 |

## 集成方式

### CLI 使用

```bash
# 检查单个提示词文件
prompt-linter check prompt.md

# 检查目录下所有提示词
prompt-linter check ./_scenarios/

# 使用自定义配置
prompt-linter check --config ./_linter/config.yaml prompt.md

# 输出JSON格式
prompt-linter check --format json prompt.md
```

### CI/CD 集成

```yaml
# GitHub Actions 示例
- name: Prompt Lint
  run: prompt-linter check ./prompts/ --max-warnings 0
```

### IDE 集成

- VSCode 扩展：实时高亮提示词问题
- 保存时自动检查：`editor.formatOnSave` + Linter 扩展

## 输出示例

```
prompt.md
  P002  warning  缺失输出格式定义    第15行
  P006  error    检测到API密钥模式    第23行
  P011  warning  Token浪费: 重复指令   第8行
  P017  error    矛盾指令: "简洁"vs"详细" 第12行/第28行

✖ 4 problems (2 errors, 2 warnings)
```

## 与现有体系的关系

- **_scenarios/**：Linter 检查的主要目标文件
- **_schemas/**：提供提示词结构定义，Linter 可参考 Schema 约束
- **_evaluations/**：Linter 是静态检查，Evaluations 是动态评估，两者互补
- **_security/**：安全类规则（P006-P010）参考 _security/ 体系
