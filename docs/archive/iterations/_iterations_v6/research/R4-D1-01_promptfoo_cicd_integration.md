# 调研报告：Promptfoo CI/CD集成方式

> **调研编号**：R4-D1-01
> **日期**：2026-05-29
> **调研方向**：Promptfoo最新版本和CI/CD集成方式

---

## 一、Promptfoo当前状态

### 1.1 版本与生态
- **最新状态**：Promptfoo已被OpenAI收购，成为OpenAI生态一部分
- **GitHub Stars**：21.7k+
- **支持提供者**：60+（OpenAI/Anthropic/Google/Ollama/自定义Python/JS）
- **核心能力**：评估(Evals)+红队测试(Red Teaming)+护栏(Guardrails)+代码扫描(Code Scanning)+MCP代理

### 1.2 核心产品矩阵
| 产品 | 功能 | 适用场景 |
|------|------|----------|
| Evaluations | 提示词/模型/RAG评估 | CI/CD门禁 |
| Red Teaming | 安全漏洞主动发现 | 注入防御验证 |
| Guardrails | 实时越狱/对抗防御 | 生产运行时防护 |
| Code Scanning | IDE/CI中LLM漏洞扫描 | 开发期安全 |
| MCP Proxy | MCP通信安全代理 | Agent系统防护 |

---

## 二、CI/CD集成方式

### 2.1 GitHub Actions集成

```yaml
name: 'Prompt Evaluation'
on:
  pull_request:
    paths:
      - 'prompts/**'
jobs:
  evaluate:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - name: Set up promptfoo cache
        uses: actions/cache@v4
        with:
          path: ~/.cache/promptfoo
          key: ${{ runner.os }}-promptfoo-v1
      - name: Run promptfoo evaluation
        uses: promptfoo/promptfoo-action@v1
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          prompts: 'prompts/**/*.json'
          config: 'prompts/promptfooconfig.yaml'
          cache-path: ~/.cache/promptfoo
```

### 2.2 配置文件格式(promptfooconfig.yaml)

```yaml
description: "AI提示词体系v6.0评估"
prompts:
  - file://prompts/01_requirement_analysis.json
providers:
  - openai:chat:gpt-4-turbo
  - anthropic:messages:claude-3-opus
  - google:gemini-pro
tests:
  - vars:
      input: "测试输入"
    assert:
      - type: contains
        value: "期望输出"
      - type: llm-rubric
        value: "质量评估标准"
      - type: latency
        threshold: 3000
```

### 2.3 支持的断言类型
- **contains/icontains**: 输出包含指定内容
- **llm-rubric**: LLM评分(核心)
- **latency**: 延迟阈值
- **cost**: 成本阈值
- **javascript/python**: 自定义脚本断言
- **similar**: 语义相似度
- **regex**: 正则匹配

---

## 三、对本体系的集成方案

### 3.1 体系适配配置

```yaml
# _evaluations_v6/promptfoo/promptfooconfig.yaml
description: "AI提示词体系v6.0全量评估"
prompts:
  - file://../../01_需求分析与产品规划提示词.md
  - file://../../02_架构设计与技术选型提示词.md
  # ... 12个核心文档
providers:
  - openai:chat:gpt-4-turbo
  - anthropic:messages:claude-3-opus
  - google:gemini-pro
  - ollama:chat:deepseek-v3
defaultTest:
  assert:
    - type: llm-rubric
      value: "输出必须结构化、准确、完整"
    - type: latency
      threshold: 10000
```

### 3.2 与现有LLM-as-Judge的关系
- **互补关系**：Promptfoo负责自动化CI/CD门禁，LLM-as-Judge负责深度质量评估
- **数据共享**：Promptfoo评估结果可作为Dashboard数据源
- **红队测试**：Promptfoo Red Teaming可用于注入防御v2.0验证

---

## 四、调研结论

1. Promptfoo已具备工业级CI/CD集成能力，支持GitHub Actions/GitLab CI/Jenkins等
2. Red Teaming功能可直接用于Prompt注入防御v2.0验证
3. Guardrails功能可作为生产运行时防护层
4. 建议采用Promptfoo作为评估工业化基础设施
5. 评估配置采用YAML格式，与体系现有接口定义格式一致
