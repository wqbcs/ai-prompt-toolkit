# AI Prompt Toolkit

> AI提示词工业级工具链：条件编译、安全扫描、A/B测试、Prompt Linter

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-42.0.0-orange.svg)](CHANGELOG.md)

## 项目简介

**ai-prompt-toolkit** 是一个面向AI提示词工程的全生命周期工具链，提供从编写、质量检查、安全扫描、A/B测试到版本管理的完整解决方案。类似ESLint之于JavaScript，prompt-cli之于Prompt工程。

### 核心特性

| 功能 | CLI命令 | 描述 |
|------|---------|------|
| **Prompt Linter** | `prompt-cli lint` | 50条Lint规则(P001-P050)，涵盖结构/安全/性能/质量/Agent/RAG/多模态/lintlang/中文9大类 |
| **安全扫描** | `prompt-cli scan` | 注入检测(30条含中文)、PII隐私检测(10种)、供应链攻击检测、红队对抗(56+ Probe) |
| **Quality Gate** | `prompt-cli lint --gate` | CI模式Verdict门禁(PASS/WARN/FAIL)，退出码0/1/2 |
| **条件编译** | `prompt-cli compile` | 按模型/语言/行业条件编译提示词模板（类C预处理器语法） |
| **A/B测试** | `prompt-cli ab-test` | 贝叶斯统计(Thompson Sampling+SPRT)，18种LLM Provider支持 |
| **评估引擎** | `prompt-cli evaluate` | 62个评估维度(D01-D62)，快速/完整双模式 |
| **版本管理** | `prompt-cli version` | Git-like diff/rollback，版本历史追踪 |
| **模板市场** | `prompt-cli market` | REST API(FastAPI)，模板发布/评审/灰度发布 |
| **红队对抗** | `prompt-cli redteam` | 11种攻击探针(DAN/越狱/注入/幻觉/隐私等)，6种检测器 |
| **国际化** | `prompt-cli i18n` | LLM翻译+术语表+回退策略，支持中英日韩 |
| **Playground** | `prompt-cli playground` | WebSocket实时编辑器，浏览器UI |

### 差异化优势

- **全生命周期覆盖**：唯一覆盖 Lint→Security→Test→Version→Deploy 全链路的Prompt工具
- **零LLM调用Lint**：50条静态分析规则，无需消耗Token即可检测Prompt质量
- **18种LLM Provider**：支持OpenAI/Claude/DeepSeek/通义千问/智谱/华为盘古等国内外模型
- **中文优先**：15条中文注入检测规则、中文标点/Token/冗余特有Lint、人话翻译报错
- **PII+供应链防护**：10种隐私信息自动检测+脱敏、可疑URL/包名typosquat/资源注入检测
- **Quality Gate CI**：Verdict门禁(PASS/WARN/FAIL)，SARIF输出，GitHub Code Scanning集成
- **鸿蒙适配**：内置10个HarmonyOS场景模板，覆盖ArkTS UI/分布式/Stage模型

## 快速开始

### 安装

```bash
# 基础安装
pip install ai-prompt-toolkit

# 完整安装（含A/B测试+模板市场）
pip install "ai-prompt-toolkit[full]"

# 仅A/B测试
pip install "ai-prompt-toolkit[ab_test]"
```

### 基本使用

```bash
# Lint检查
prompt-cli lint -s my_prompt.md

# 安全扫描
prompt-cli scan -s my_prompt.md

# 条件编译
prompt-cli compile -s template.md -c context.json

# A/B测试
prompt-cli ab-test -c ab_config.yaml

# 版本管理
prompt-cli version diff my_prompt.md
prompt-cli version rollback my_prompt.md --rev 3

# 评估
prompt-cli evaluate -s my_prompt.md --mode full

# 红队对抗
prompt-cli redteam -s my_prompt.md --probe dan,jailbreak

# 交互式向导
prompt-cli wizard

# 健康检查
prompt-cli doctor
```

### Docker

```bash
docker build -t prompt-cli .
docker run --rm prompt-cli lint -s /app/my_prompt.md
```

## 项目架构

```
src/ai_prompt_toolkit/
├── cli.py              # CLI兼容层
├── cli_core.py         # CLI实际实现(20+命令)
├── linter/             # Prompt Linter引擎
│   ├── linter.py       # Lint核心引擎
│   ├── rules.py        # P001-P020规则
│   ├── rules_p021_p030.py  # P021-P030规则
│   ├── rules_p031_p040.py  # P031-P040 Agent/RAG/多模态
│   ├── rules_p041_p050.py  # P041-P050 lintlang参考+中文特有
│   ├── quality_gate.py # Verdict-based Quality Gate
│   ├── friendly_descriptions.py  # 人话翻译
│   ├── fixer.py        # 自动修复
│   └── lsp_server.py   # LSP协议服务
├── security/           # 安全扫描引擎
│   ├── scanner.py      # 扫描编排器
│   ├── injection_detector.py  # 注入检测(15条)
│   ├── zh_injection_rules.py  # 中文注入(15条)
│   ├── pii_detector.py # PII隐私检测(10种)
│   ├── supply_chain_detector.py  # 供应链检测
│   ├── scorer.py       # CVSS-like安全评分
│   └── inheritance_auditor.py  # 继承审计
├── compiler/           # 条件编译引擎
├── redteam/            # 红队对抗引擎(11种探针)
├── ab_test/            # A/B测试引擎(18种Provider)
├── i18n/               # 国际化引擎
├── market/             # 模板市场(FastAPI)
├── evaluator.py        # 评估引擎(62维度)
├── version_store.py    # 版本管理(Git-like)
├── playground/         # Playground UI
└── onboarding/         # 交互式向导
```

### 全生命周期流程图

```
编写 → Lint(50规则) → Security Scan(30+检测) → Quality Gate(CI) → A/B Test → Deploy
  │         │                    │                      │              │          │
  └─ compile ─┘           PII/供应链检测          PASS/WARN/FAIL    18种Provider  模板市场
```

## 场景模板

内置51个行业场景模板：

- **可观测性** (5个)：分布式追踪/指标监控/日志聚合
- **混沌工程** (5个)：网络/资源/依赖/数据混沌
- **GitOps** (5个)：ArgoCD/Flux/IaC/配置/安全
- **平台工程** (5个)：IDP/自助服务/编排/可组合性
- **鸿蒙** (10个)：ArkTS UI/分布式/性能/安全/Stage模型
- **华为云** (18个)：DEH/BMS/AS/ELB/CCE/ModelArts等
- **信创** (3个)：鲲鹏/昇腾/openEuler

## VSCode插件

项目包含VSCode扩展 `vscode-prompt-lint/`，提供：

- 实时Lint诊断(50条规则)
- 保存时自动检查
- 安全扫描集成(30条含中文注入)
- PII隐私检测
- Quality Gate检查
- Front Matter验证
- 严重级别覆盖配置

详见 [vscode-prompt-lint/README.md](vscode-prompt-lint/README.md)

## CI/CD集成

```yaml
# GitHub Actions示例 - Quality Gate
- name: Prompt Lint with Quality Gate
  run: prompt-cli lint -t ./prompts/ --gate

# SARIF输出 - GitHub Code Scanning
- name: Prompt Lint (SARIF)
  run: prompt-cli lint -t ./prompts/ --format sarif --output results.sarif

- name: Prompt Security Scan
  run: prompt-cli scan -t ./prompts/
```

项目内置3个GitHub Actions Workflow：
- `quality-gate.yml` - 质量门禁
- `prompt-lint.yml` - Prompt Lint
- `prompt-quality-gate.yml` - Prompt质量门禁

## 开发

```bash
# 开发环境
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 代码格式化
black src/ tests/
isort src/ tests/
```

## 许可证

MIT License

## 链接

- [变更日志](CHANGELOG.md)
- [术语表](_glossary.md)
- [适配矩阵](_adaptation_matrix.md)
