---
version: 3.0.0
author: AI提示词体系
updated_at: '2026-07-18'
tags:
- huawei-cloud
- modelarts
- pangu
- llm
applicable_models:
- pangu-large
- qwen-max
- gpt-4o
inheritance:
  enabled: false
locale: zh-CN
i18n_status: untranslated
market_status: draft
lint_score: 0
lint_last_checked: '2026-07-18T00:00:00Z'
template_type: prompt
---
# 华为云ModelArts盘古大模型应用开发场景模板

## 概述

华为云ModelArts平台提供盘古大模型(Pangu)的推理服务、微调能力和AI应用开发套件。本模板覆盖基于盘古大模型的应用开发核心场景，帮助开发者高效构建企业级AI应用。

---

## 一、常见陷阱（5项）

### 陷阱1：Prompt未适配盘古模型的中文偏好

- 盘古大模型对中文Prompt的理解优于英文，但开发者习惯性使用英文Prompt
- 中文分词边界与GPT系列不同，直接翻译英文Prompt效果下降
- 未利用盘古的角色扮演和指令遵循偏好
- **规避**：使用中文编写Prompt，注意中文语法和表达的自然性；利用盘古的角色设定能力增强指令遵循

### 陷阱2：ModelArts推理接口调用不当

- 未使用连接池导致频繁建连，推理延迟增加3-5倍
- 请求超时设置过短，长文本生成频繁超时
- 未实现重试机制，偶发网络异常导致整个流程失败
- **规避**：使用连接池管理HTTP连接，设置合理的超时(30-60秒)，实现指数退避重试

### 陷阱3：微调数据质量不达标

- 微调数据量不足(<100条)导致模型欠拟合
- 数据标签不一致(同一输入多种标签)导致模型混乱
- 未做数据脱敏，训练数据包含PII信息
- **规避**：确保微调数据>=500条，标签一致性>95%，训练前进行数据清洗和脱敏

### 陷阱4：推理结果后处理缺失

- 直接使用原始输出未做格式校验，下游系统解析异常
- 未处理模型幻觉输出，将错误信息当作事实
- 缺少内容安全过滤，可能输出不当内容
- **规避**：实现输出格式校验和异常兜底，添加事实性检查层，接入内容安全审核

### 陷阱5：成本控制缺失

- 未监控Token消耗，单次调用成本失控
- 缓存策略缺失，重复请求浪费资源
- 未使用流式输出，大段文本生成时用户体验差
- **规避**：实现Token用量监控和预算告警，添加语义缓存层，使用SSE流式输出

---

## 二、最佳实践模板

### 场景1：基于盘古大模型的企业知识库问答

```
你是华为云ModelArts盘古大模型应用开发专家。

## 角色
你是一位精通盘古大模型API和RAG架构的AI应用架构师。

## 任务
请为以下企业知识库设计基于盘古大模型的问答系统：
[企业知识库描述]

## 约束
- 使用ModelArts推理服务，模型选择pangu-large
- 实现RAG架构：检索→重排→生成
- 中文Prompt优先
- 输出必须标注信息来源和置信度
- 如果检索结果不包含答案，明确回答"知识库中未找到相关信息"
- 推理结果需通过内容安全审核
- 单次推理Token消耗控制在2000以内

## 输出格式
请以JSON格式输出：
{
  "architecture": {"retrieval": "...", "reranker": "...", "generation": "..."},
  "prompt_template": "...",
  "safety_config": {"content_filter": true},
  "cost_estimate": {"tokens_per_call": 1500}
}

## 示例
输入：公司IT运维知识库，5000篇故障处理文档
输出：{"architecture": {"retrieval": "Elasticsearch+向量检索", "reranker": "bge-reranker-large", "generation": "pangu-large + RAG Prompt"}, "prompt_template": "根据以下检索内容回答问题，如果检索内容不包含答案请说明：\n{context}\n\n问题：{question}", "safety_config": {"content_filter": true}, "cost_estimate": {"tokens_per_call": 1200}}
```

---

## 四、质量检查清单

- [ ] 是否使用中文Prompt适配盘古模型
- [ ] 是否实现推理接口的重试和超时机制
- [ ] 微调数据是否经过质量检查和脱敏
- [ ] 推理结果是否有格式校验和幻觉检测
- [ ] 是否实现Token消耗监控和预算控制
- [ ] 是否使用流式输出提升用户体验
- [ ] 是否接入内容安全审核
