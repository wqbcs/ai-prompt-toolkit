# MITRE ATLAS × OWASP LLM Top 10 × 本项目规则映射表（R213-P1-6）

> 用途: 规则/探针新增与评审时的对标依据；`--owasp-report` 的扩展参考
> 口径: ATLAS 技术编号经 2026-09 联网核实（MITRE ATLAS 2026.07/2026.08 版发布说明）；
> 规则名/编号为 `get_all_rules()` 实测值（2026-09-30 核对; R215 于 2026-10-01 联网复核
> T0051.000/T0054 编号）；未核实的条目明确标注

## 三方映射表

| ATLAS 技术 | OWASP LLM 2025 | 本项目规则 / 探针 | 覆盖判定 |
|---|---|---|---|
| AML.T0051.000 Direct Prompt Injection | LLM01 | P161 模板注入 / P022 注入标记 / P029 变量未转义 / P021 编码混淆 / P177 Base64混淆注入 / **P258 伪系统标签（R215-B2）** / golden攻击集68探针 / mcp-lint description层 | 覆盖（静态面） |
| AML.T0051.001 Indirect Prompt Injection | LLM01 | P035/P036/P037 RAG检索族 / P038-P040 多模态族 / **P257（R213-B5 新增）** | 部分→R213补强 |
| AML.T0051.002 Triggered Injection | LLM01 | P163 越狱防护 + redteam jailbreak 探针 | 部分（触发式需运行时） |
| AML.T0053 AI Agent Tool Invocation（2026.07 由 LLM Plugin Compromise 更名） | LLM06 | P031 工具约束 / P033 上下文边界 / P034 审批机制 / MCP-104 免审批 / MCP-107 链式路由 | 覆盖（配置面） |
| AML.T0054 LLM Jailbreak | LLM01 | P163 / **P259 人格切换复合面（R215-B2）** + redteam 越狱探针 | 覆盖（静态面） |
| AML.T0056 Extract LLM System Prompt（原名 LLM Meta Prompt Extraction） | LLM07 | P164 指令提取防护 / P165 侧信道 / canary token 注入+检测 | 覆盖 |
| AML.T0057 LLM Data Leakage | LLM02 | P051 硬编码凭据 / PII检测器12类 / P201-P205 数据合规族 / P241 最小化 / P243 保留策略 | 覆盖 |
| AML.T0059 Erode Dataset Integrity | LLM04 | P223 数据溯源链 | 部分（数据管道运行时面超出静态lint范围） |
| AML.T0060 Publish Hallucinated Entities | LLM09 | P036 RAG幻觉检测提示 / P203 AI输出标识 | 部分 |
| AML.T0062 Discover LLM Hallucinations | LLM09 | （无静态规则 — 幻觉验证是运行时能力） | **缺口（记录, 不实现）** |
| AML.T0066 Retrieval Content Crafting | LLM08 | P035 检索源验证 / P037 引用标注 | 覆盖（静态面） |
| AML.T0085 Data from AI Services | LLM08 | P035-P037 RAG族 | 部分 |
| AML.T0086 Exfiltration via AI Agent Tool Invocation | LLM02/LLM06 | P031/P034 / MCP-105 凭据透传 / MCP-107 | 覆盖（配置面） |
| AML.T0088 Generate Deepfakes | LLM05 | P038-P040 多模态声明族 / P131 多模态输入声明 | 部分 |
| AML.T0010 ML Supply Chain Compromise（.002 Data / .003 Model） | LLM03 | P221 模型来源 / P222 依赖审计 / P224 版本锁定 / P225 签名 / MCP-106 未固定版本 | 覆盖 |
| AML.T0020 Training Data Poisoning（2026.08 由 Publish Poisoned Datasets 更名） | LLM04 | P223 数据溯源 | 部分 |
| AML.T0115 Publish Poisoned AI Artifacts（2026.08 合并原 T0019+T0058；.000 Datasets / .001 Models） | LLM03/LLM04 | P221 来源验证 / P224 版本锁定 / P225 供应链签名 / **MCP-109/110 rug pull 基线漂移（R227, description sha256 已批准基线+漂移告警, Microsoft 官方点名面）** | 覆盖（静态面） |
| AML.T0092 Manipulate User LLM Chat History | LLM01 | P161/P164 指令保护 | 部分（会话级上下文操纵需运行时） |
| AML.T0093 Prompt Infiltration via Public-Facing Application | LLM01 | mcp-lint description层 / P022 | 覆盖 |
| AML.T0094 Delay Execution of LLM Instructions | LLM01 | （无规则） | **缺口（记录, 候选）** |
| AML.T0015 Evade AI Model | LLM01 | P021 编码混淆 / P152 输出编码转义 / P177 Base64 / **P260 编码混淆注入面（R215-B2, 5子pattern）** / **P261 不可见字符交错/BiDi反转面（R217, 3子pattern, 信源ATR-2026-00276）** / **MCP-108 MCP description 隐藏通道（R227, C0/ANSI/C1/Unicode Tags）** / redteam 编码探针9条（badchars/encoding_base64/encoding_binary/encoding_bypass/encoding_hex/encoding_rot13/encoding_unicode/glitch_zerowidth/chinese_encoding_injection; R217 命名对齐统一注册表实测） | 覆盖 |
| AML.T0035 Create Proxy ML Model | — | （无 — 运行时建模能力） | **缺口（记录, 不实现）** |
| RAG Poisoning / False RAG Entry Injection / Gather RAG-Indexed Targets / RAG Credential Harvesting（2025-03 后新增, 编号以官方矩阵为准） | LLM08 | P035-P037 + **P257（R213-B5）** | 部分→R213补强 |

## OWASP LLM Top 10 (2025) 汇总覆盖

| OWASP | 覆盖状态 |
|---|---|
| LLM01 Prompt Injection | 强（多层: 规则/探针/mcp-lint/P257/P258/P259/P260/P261） |
| LLM02 Sensitive Information Disclosure | 强 |
| LLM03 Supply Chain | 强 |
| LLM04 Data & Model Poisoning | 中（静态面覆盖, 数据管道运行时面声明为范围外） |
| LLM05 Improper Output Handling | 中 |
| LLM06 Excessive Agency | 强（Agent规则族+MCP配置面） |
| LLM07 System Prompt Leakage | 强（P164/P165+canary） |
| LLM08 Vector & Embedding Weaknesses | 中→P257补强 |
| LLM09 Misinformation | 弱（静态lint的天然边界, 缺口已记录） |
| LLM10 Unbounded Consumption | 弱（成本面由 health-score 成本档位部分覆盖, 无专用规则） |

## 使用纪律

1. 新增规则/探针在文档与注释中引用对应 ATLAS 编号（可追溯性）
2. "缺口（记录, 不实现）"= 对抗性审查判定为超出静态 prompt lint 定位的能力 —
   不实现是范围纪律, 不是遗漏；如未来产品定位变化再重评
3. 本表随 ATLAS/OWASP 版本更新而更新（更新时重新联网核实编号, 禁止凭记忆改编号）
