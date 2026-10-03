# Security Policy — AI Prompt Toolkit

本工具是**安全门禁工具**（检测 prompt 注入/PII/编码混淆等）。安全工具自身
必须示范安全响应流程——本文即该示范。

## 支持的版本

| 版本 | 安全修复支持 |
|---|---|
| 最新主版本（67.x） | ✅ 修复 |
| 上一主版本 | ⚠️ 仅 critical（升级建议） |
| 更早 | ❌ 请升级 |

## 报告漏洞（按严重度）

**Critical（先报告，后公开）**：

- 规则引擎可被恶意 prompt 文本 DoS（如灾难性回溯 ReDoS 触发 261 条规则
  挂起——尺子本身被尺子量到的对象打挂，最高优先）
- SARIF/JSON 输出注入（恶意文本逃逸为可执行内容）
- 基线文件篡改可静默绕过增量门禁
- 探针集（`data/golden_attacks.json`）投毒使双基线数字造假

**High**：waiver 机制绕过、SARIF region 定位伪造、依赖供应链风险。

### 报告渠道

1. **首选**：GitHub Security Advisories —
   `https://github.com/wqbcs/ai-prompt-toolkit/security/advisories/new`
   （私有渠道，不公开，不通知仓库 owner 之外的任何人）
2. 备选：`gwc0218@qq.com`（GPG 公钥待补——报告敏感内容请优先 advisory 渠道）

### SLA

| 严重度 | 首次响应 | 修复/缓解方案 |
|---|---|---|
| Critical | 48 小时 | 7 天 |
| High | 1 周 | 14 天（下版本） |
| Medium/Low | 2 周 | 评估后纳入 backlog |

## CVE 流程

确认的 Critical/High 漏洞走 GitHub Security Advisories 自动分配 CVE 流程：
修复 commit → advisory 发布 → README 安全公告行 → 双基线复跑（若涉及检测面）。

## 本项目自身威胁面（TH 系列，见 docs/planning/05 §5）

| # | 威胁 | 现行缓解 |
|---|---|---|
| TH1 | 探针集（尺子）投毒 | CODEOWNERS 双人 review（P3-13 建设中） |
| TH2 | 基线文件篡改绕过门禁 | 基线重存独立 commit 纪律 + hash 告警（P3-15） |
| TH4 | 规则投毒（假阴性） | 规则变更需带探针（探针先行流程） |
| TH6 | SARIF 输出注入 | JSON 序列化转义 + 回归测试（P3-14） |

## 安全相关的已知边界（非漏洞，诚实声明）

- 静态检测面不覆盖语义层攻击（创意越狱/对抗性改写）——见 README 适用域划分
- `gap-report` 度量防御**声明存在性**，非实际有效性
- 零 LLM 调用是特性也是边界：不存在的误报来自"模型理解"，只来自规则
