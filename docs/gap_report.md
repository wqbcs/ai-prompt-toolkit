# OWASP LLM Top 10 防御缺口报告

生成: 2026-10-02T12:28:17.925971 · 文件数: 26 · 平均缺口率: 86%

> 口径: 度量**防御声明/意图存在性**(静态文本面), 非实际有效性; 运行时防护不在检测域。

## 每风险防御缺口(缺声明的文件占比)

| 风险 | 名称 | 缺声明文件 | 占比 | 映射Lint规则 |
|---|---|---|---|---|
| LLM01 | Prompt Injection | 24/26 | 92% | 72条(P006, P007, P010, P031…) |
| LLM02 | Sensitive Information Disclosure | 18/26 | 69% | 37条(P006, P009, P024, P041…) |
| LLM03 | Supply Chain Vulnerabilities | 24/26 | 92% | 15条(P024, P047, P048, P049…) |
| LLM04 | Data and Model Poisoning | 24/26 | 92% | 18条(P029, P035, P036, P037…) |
| LLM05 | Improper Output Handling | 25/26 | 96% | 18条(P007, P008, P031, P032…) |
| LLM06 | Excessive Agency | 20/26 | 77% | 65条(P008, P030, P041, P042…) |
| LLM07 | System Prompt Leakage | 26/26 | 100% | 19条(P006, P009, P024, P041…) |
| LLM08 | Vector and Embedding Weaknesses | 26/26 | 100% | 12条(P035, P036, P037, P039…) |
| LLM09 | Misinformation | 14/26 | 54% | 49条(P015, P016, P017, P018…) |
| LLM10 | Unbounded Consumption | 22/26 | 85% | 13条(P004, P011, P012, P013…) |

**最大缺口风险**: LLM07 System Prompt Leakage (100% 文件缺防御声明)

## 每文件分级

| 文件 | 缺口 | 缺哪些风险 | 分级 |
|---|---|---|---|
| deepseek-r1-reasoning.md | 10/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| edu-course-designer.md | 10/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| harmonyos-arkts-codegen.md | 10/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| harmonyos-dev.md | 10/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| mcp-server-dev.md | 10/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| mfg-quality-inspector.md | 10/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| gov-policy-advisor.md | 9/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM10 | critical |
| harmonyos-performance.md | 9/10 | LLM01, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| harmonyos-stage-model.md | 9/10 | LLM01, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| huawei-cloud-assistant.md | 9/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM07, LLM08, LLM09, LLM10 | critical |
| pangu-multimodal.md | 9/10 | LLM01, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| pangu-nlp-assistant.md | 9/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM10 | critical |
| rag-assistant.md | 9/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM10 | critical |
| translator-pro.md | 9/10 | LLM01, LLM02, LLM04, LLM05, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| customer-service.md | 8/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM07, LLM08, LLM10 | critical |
| financial-risk-analyzer.md | 8/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM07, LLM08, LLM10 | critical |
| general-assistant.md | 8/10 | LLM01, LLM02, LLM03, LLM05, LLM06, LLM07, LLM08, LLM10 | critical |
| harmonyos-distributed.md | 8/10 | LLM01, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM10 | critical |
| huawei-cloud-deploy.md | 8/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM07, LLM08, LLM09 | critical |
| huawei-modelarts-deploy.md | 8/10 | LLM01, LLM02, LLM03, LLM04, LLM05, LLM07, LLM08, LLM10 | critical |
| pangu-scientific.md | 8/10 | LLM01, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM10 | critical |
| security-auditor.md | 8/10 | LLM02, LLM03, LLM04, LLM06, LLM07, LLM08, LLM09, LLM10 | critical |
| code-reviewer.md | 7/10 | LLM01, LLM02, LLM03, LLM05, LLM07, LLM08, LLM09 | critical |
| harmonyos-security-audit.md | 7/10 | LLM03, LLM04, LLM05, LLM06, LLM07, LLM08, LLM10 | critical |
| pangu-cv.md | 7/10 | LLM01, LLM03, LLM04, LLM05, LLM06, LLM07, LLM08 | critical |
| pangu-prediction.md | 6/10 | LLM01, LLM04, LLM05, LLM06, LLM07, LLM08 | critical |

## 修复建议(按最大缺口风险)

- **LLM07 System Prompt Leakage** (100% 文件缺): 系统提示词分段存储，添加Canary Token泄露检测
- **LLM08 Vector and Embedding Weaknesses** (100% 文件缺): 向量数据库访问控制，实施嵌入相似度阈值过滤
- **LLM05 Improper Output Handling** (96% 文件缺): 对LLM输出进行编码转义，防止XSS/注入二次攻击