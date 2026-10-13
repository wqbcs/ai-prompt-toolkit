# OWASP LLM Top 10 防御缺口报告

生成: 2026-10-13T08:58:54.049823 · 文件数: 26 · 平均缺口率: 25%

> 口径: 度量**防御声明/意图存在性**(静态文本面), 非实际有效性; 运行时防护不在检测域。

## 每风险防御缺口(缺声明的文件占比)

| 风险 | 名称 | 缺声明文件 | 占比 | 映射Lint规则 |
|---|---|---|---|---|
| LLM01 | Prompt Injection | 0/26 | 0% | 72条(P006, P007, P010, P031…) |
| LLM02 | Sensitive Information Disclosure | 0/26 | 0% | 37条(P006, P009, P024, P041…) |
| LLM03 | Excessive Agency | 10/26 | 38% | 65条(P008, P030, P041, P042…) |
| LLM04 | Supply Chain | 12/26 | 46% | 15条(P024, P047, P048, P049…) |
| LLM05 | Data and Model Poisoning | 0/26 | 0% | 18条(P029, P035, P036, P037…) |
| LLM06 | Unbounded Consumption | 17/26 | 65% | 13条(P004, P011, P012, P013…) |
| LLM07 | Misinformation | 0/26 | 0% | 49条(P015, P016, P017, P018…) |
| LLM08 | Hidden Context Exposure | 0/26 | 0% | 19条(P006, P009, P024, P041…) |
| LLM09 | Vector and Embedding Weaknesses | 25/26 | 96% | 12条(P035, P036, P037, P039…) |
| LLM10 | Improper Output Handling | 1/26 | 4% | 18条(P007, P008, P031, P032…) |

**最大缺口风险**: LLM09 Vector and Embedding Weaknesses (96% 文件缺防御声明)

## 每文件分级

| 文件 | 缺口 | 缺哪些风险 | 分级 |
|---|---|---|---|
| deepseek-r1-reasoning.md | 4/10 | LLM03, LLM04, LLM09, LLM10 | high |
| edu-course-designer.md | 4/10 | LLM03, LLM04, LLM06, LLM09 | high |
| gov-policy-advisor.md | 4/10 | LLM03, LLM04, LLM06, LLM09 | high |
| pangu-multimodal.md | 4/10 | LLM03, LLM04, LLM06, LLM09 | high |
| pangu-nlp-assistant.md | 4/10 | LLM03, LLM04, LLM06, LLM09 | high |
| pangu-scientific.md | 4/10 | LLM03, LLM04, LLM06, LLM09 | high |
| financial-risk-analyzer.md | 3/10 | LLM04, LLM06, LLM09 | medium |
| mfg-quality-inspector.md | 3/10 | LLM04, LLM06, LLM09 | medium |
| pangu-cv.md | 3/10 | LLM03, LLM04, LLM09 | medium |
| translator-pro.md | 3/10 | LLM03, LLM06, LLM09 | medium |
| customer-service.md | 2/10 | LLM04, LLM09 | medium |
| general-assistant.md | 2/10 | LLM04, LLM09 | medium |
| harmonyos-arkts-codegen.md | 2/10 | LLM06, LLM09 | medium |
| harmonyos-dev.md | 2/10 | LLM06, LLM09 | medium |
| harmonyos-distributed.md | 2/10 | LLM06, LLM09 | medium |
| harmonyos-performance.md | 2/10 | LLM06, LLM09 | medium |
| harmonyos-security-audit.md | 2/10 | LLM06, LLM09 | medium |
| harmonyos-stage-model.md | 2/10 | LLM06, LLM09 | medium |
| huawei-modelarts-deploy.md | 2/10 | LLM06, LLM09 | medium |
| mcp-server-dev.md | 2/10 | LLM06, LLM09 | medium |
| pangu-prediction.md | 2/10 | LLM03, LLM09 | medium |
| rag-assistant.md | 2/10 | LLM03, LLM04 | medium |
| security-auditor.md | 2/10 | LLM06, LLM09 | medium |
| code-reviewer.md | 1/10 | LLM09 | low |
| huawei-cloud-assistant.md | 1/10 | LLM09 | low |
| huawei-cloud-deploy.md | 1/10 | LLM09 | low |

## 修复建议(按最大缺口风险)

- **LLM09 Vector and Embedding Weaknesses** (96% 文件缺): 向量数据库访问控制，实施嵌入相似度阈值过滤
- **LLM06 Unbounded Consumption** (65% 文件缺): 实施速率限制和Token消耗监控，防止资源/成本耗尽
- **LLM04 Supply Chain** (46% 文件缺): 验证第三方包名真实性，使用官方源和签名校验；校验 promoted model artifact 真实性