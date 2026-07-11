# 平台集成接口 v1.0

> **版本**：v1.0 | **日期**：2026-05-29

---

## 1. HuggingFace集成

### 1.1 模型中心集成

```yaml
huggingface_integration:
  model_hub:
    - 功能: 提示词模板随模型发布
    - 格式: model_card中包含recommended_prompt_template
    - 接口: |
        POST /api/models/{model_id}/prompt-template
        {
          "template": "提示词模板内容",
          "version": "1.0.0",
          "compatibility": ["v12.0.0+"],
          "dimensions": {"score": 20.00}
        }
  
  inference_api:
    - 功能: 通过Inference API执行提示词
    - 接口: |
        POST /api/models/{model_id}/completion
        Headers: Authorization: Bearer {HF_TOKEN}
        Body: {
          "prompt": "从.prompt文件加载",
          "parameters": {"temperature": 0.1, "max_tokens": 4096},
          "options": {"guard_checks": true}
        }
  
  spaces:
    - 功能: 部署提示词Playground为HF Space
    - 模板: Gradio+prompt-engineer-sdk
    - 自动部署: GitHub Actions→HF Spaces
```

### 1.2 Dataset集成

```yaml
dataset_integration:
  prompt_dataset:
    - 格式: |
        {
          "prompt": "...",
          "category": "code_review",
          "industry": "financial",
          "model_compatibility": [...],
          "quality_score": {"22d": 20.00},
          "examples": [...]
        }
    - 发布: 发布为HF Dataset供社区使用
    - 版本: 语义化版本+评估报告
```

---

## 2. ModelArts集成(华为云)

### 2.1 模型适配

```yaml
modelarts_integration:
  model_deployment:
    - 功能: 提示词随ModelArts模型部署
    - 接口: |
        POST /v2/{project_id}/deployments
        {
          "model_id": "华为云模型ID",
          "prompt_config": {
            "template": "从.prompt文件加载",
            "adaptation_layer": "modelarts-specific",
            "guard_checks": ["owasp", "compliance", "injection"]
          }
        }
  
  evaluation:
    - 功能: 使用ModelArts评测框架评估提示词
    - 接口: |
        POST /v2/{project_id}/evaluations
        {
          "prompt_file": ".prompt文件路径",
          "dimensions": 22,
          "models": ["pangu", "yi", "chatglm"],
          "dataset": "评测数据集"
        }
  
  workflow:
    - 功能: ModelArts工作流编排
    - 模板: 提示词开发→评估→部署→监控
  
  mlf_low:
    - 功能: MLFlow实验追踪
    - 集成: 提示词版本+评估指标+模型适配记录
```

### 2.2 华为云特有模型适配

```yaml
huawei_models:
  pangu_large:
    capability: {reasoning: 0.85, tool: 0.7, structured: 0.9, chinese: 0.95}
    adaptation: "中文优化适配层+华为合规约束"
  yi_large:
    capability: {reasoning: 0.9, tool: 0.8, structured: 0.85, chinese: 0.9}
    adaptation: "推理增强适配层"
  chatglm:
    capability: {reasoning: 0.8, tool: 0.6, structured: 0.8, chinese: 0.95}
    adaptation: "对话优化适配层"
```

---

## 3. JetBrains集成

### 3.1 IntelliJ IDEA插件

```yaml
jetbrains_integration:
  plugin_id: com.prompt-engineer.intellij
  features:
    - prompt_language: ".prompt文件语法高亮+补全"
    - lint: "28反模式实时检测"
    - snippets: "5层结构+28原则片段"
    - preview: "侧边预览面板"
    - evaluation: "内建评估框架"
    - refactor: "提示词重构(提取模板+内联变量)"
    - navigation: "引用导航(Go to Definition/Find Usages)"
    - diff: "提示词Diff视图"
    - debug: "断点调试+变量检查+执行追踪"
  
  compatible_products:
    - IntelliJ IDEA
    - PyCharm
    - WebStorm
    - GoLand
    - RustRover
```

---

## 4. 通用API接口

### 4.1 提示词执行API

```yaml
execution_api:
  endpoint: POST /api/v1/execute
  request:
    prompt_file: ".prompt文件路径或内联内容"
    variables: {"language": "python", "industry": "financial"}
    model: "gpt-4-turbo"  # 可选，默认使用文件中指定的模型
    options:
      guard_checks: true   # 执行门禁检查
      evaluate: true       # 执行质量评估
      stress_test: false   # 执行应力测试
      max_tokens: 4096
      temperature: 0.1
  response:
    output: "AI输出"
    evaluation: {"score": 20.00, "dimensions": {...}}
    guard_result: {"passed": true, "failures": []}
    tokens: {"input": 500, "output": 2000}
    latency_ms: 1200
```

### 4.2 提示词市场API

```yaml
market_api:
  search: GET /api/v1/market/search?q=code+review&industry=financial&sort=rating
  install: POST /api/v1/market/install/{package_id}
  publish: POST /api/v1/market/publish
  rate: POST /api/v1/market/rate/{package_id}
  review: POST /api/v1/market/review/{package_id}
```
