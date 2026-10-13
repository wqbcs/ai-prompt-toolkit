# OWASP LLM Top 10 防御缺口报告

生成: 2026-10-13T10:19:49.635523 · 文件数: 26 · 平均缺口率(存在性): 25% · 平均声明质量: 33%(质量缺口 67%)

> 双口径(均静态文本面, 非实际有效性, 运行时防护不在检测域): **存在性**=每风险命中任一防御面即视为声明了; **质量**=每风险命中防御面数/总面数(多面=声明越全, 薄声明=低分)。

## 每风险防御缺口(存在性) × 声明质量

| 风险 | 名称 | 缺声明文件 | 存在性占比 | 声明质量 | 映射Lint规则 |
|---|---|---|---|---|---|
| LLM01 | Prompt Injection | 0/26 | 0% | 50% | 72条(P006, P007, P010, P031…) |
| LLM02 | Sensitive Information Disclosure | 0/26 | 0% | 48% | 37条(P006, P009, P024, P041…) |
| LLM03 | Excessive Agency | 10/26 | 38% | 37% | 65条(P008, P030, P041, P042…) |
| LLM04 | Supply Chain | 12/26 | 46% | 29% | 15条(P024, P047, P048, P049…) |
| LLM05 | Data and Model Poisoning | 0/26 | 0% | 36% | 18条(P029, P035, P036, P037…) |
| LLM06 | Unbounded Consumption | 17/26 | 65% | 7% | 13条(P004, P011, P012, P013…) |
| LLM07 | Misinformation | 0/26 | 0% | 47% | 49条(P015, P016, P017, P018…) |
| LLM08 | Hidden Context Exposure | 0/26 | 0% | 25% | 19条(P006, P009, P024, P041…) |
| LLM09 | Vector and Embedding Weaknesses | 25/26 | 96% | 3% | 12条(P035, P036, P037, P039…) |
| LLM10 | Improper Output Handling | 0/26 | 0% | 49% | 18条(P007, P008, P031, P032…) |

**最大缺口风险(存在性)**: LLM09 Vector and Embedding Weaknesses (96% 文件缺防御声明)  **最薄风险(质量)**: LLM09 Vector and Embedding Weaknesses (平均声明质量 3%)

## 每文件分级

| 文件 | 缺口(存在性) | 声明质量 | 缺哪些风险 | 分级 |
|---|---|---|---|---|
| edu-course-designer.md | 4/10 | 26% | LLM03, LLM04, LLM06, LLM09 | high |
| gov-policy-advisor.md | 4/10 | 26% | LLM03, LLM04, LLM06, LLM09 | high |
| pangu-multimodal.md | 4/10 | 28% | LLM03, LLM04, LLM06, LLM09 | high |
| pangu-nlp-assistant.md | 4/10 | 28% | LLM03, LLM04, LLM06, LLM09 | high |
| pangu-scientific.md | 4/10 | 30% | LLM03, LLM04, LLM06, LLM09 | high |
| deepseek-r1-reasoning.md | 3/10 | 22% | LLM03, LLM04, LLM09 | medium |
| financial-risk-analyzer.md | 3/10 | 34% | LLM04, LLM06, LLM09 | medium |
| mfg-quality-inspector.md | 3/10 | 32% | LLM04, LLM06, LLM09 | medium |
| pangu-cv.md | 3/10 | 34% | LLM03, LLM04, LLM09 | medium |
| translator-pro.md | 3/10 | 25% | LLM03, LLM06, LLM09 | medium |
| customer-service.md | 2/10 | 31% | LLM04, LLM09 | medium |
| general-assistant.md | 2/10 | 33% | LLM04, LLM09 | medium |
| harmonyos-arkts-codegen.md | 2/10 | 35% | LLM06, LLM09 | medium |
| harmonyos-dev.md | 2/10 | 35% | LLM06, LLM09 | medium |
| harmonyos-distributed.md | 2/10 | 39% | LLM06, LLM09 | medium |
| harmonyos-performance.md | 2/10 | 37% | LLM06, LLM09 | medium |
| harmonyos-security-audit.md | 2/10 | 39% | LLM06, LLM09 | medium |
| harmonyos-stage-model.md | 2/10 | 37% | LLM06, LLM09 | medium |
| huawei-modelarts-deploy.md | 2/10 | 38% | LLM06, LLM09 | medium |
| mcp-server-dev.md | 2/10 | 35% | LLM06, LLM09 | medium |
| pangu-prediction.md | 2/10 | 36% | LLM03, LLM09 | medium |
| rag-assistant.md | 2/10 | 37% | LLM03, LLM04 | medium |
| security-auditor.md | 2/10 | 35% | LLM06, LLM09 | medium |
| code-reviewer.md | 1/10 | 37% | LLM09 | low |
| huawei-cloud-assistant.md | 1/10 | 37% | LLM09 | low |
| huawei-cloud-deploy.md | 1/10 | 37% | LLM09 | low |

## 修复建议(按最大缺口风险)

- **LLM09 Vector and Embedding Weaknesses** (96% 文件缺): 向量数据库访问控制，实施嵌入相似度阈值过滤
- **LLM06 Unbounded Consumption** (65% 文件缺): 实施速率限制和Token消耗监控，防止资源/成本耗尽
- **LLM04 Supply Chain** (46% 文件缺): 验证第三方包名真实性，使用官方源和签名校验；校验 promoted model artifact 真实性