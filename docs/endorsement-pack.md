# P5-14 背书素材包（R354 E4 交付物）

> 状态：**素材就绪, 提交动作=用户侧**（会话无 GitHub/OWASP 账号权限, 不代提交）。
> 纪律：本文件所有数字与仓库 README/基线文件一致（机器可复现口径）；提交前
> 若数字随版本变化, 以 `prompt-cli baseline` 实测为准更新本文。
> 生成: R354 (2026-10-30, v67.34.134)

## 0. 复制即用素材（公共部分）

**仓库**: https://github.com/wqbcs/ai-prompt-toolkit
**PyPI**: `ai-prompt-toolkit`（已发布）· **npm**: `ai-prompt-toolkit` · **ghcr**: `ghcr.io/wqbcs/ai-prompt-toolkit`
**一句话定位（中）**: 确定性的 LLM prompt 静态门禁——零 LLM、裁决逐字节一致、<100ms/文件、SARIF/CI 原生, 双基线（误报率/漏检率）一条命令自证。
**One-liner (EN)**: Deterministic static gate for LLM prompts — zero LLM, byte-identical verdicts, <100ms/file, SARIF/CI-native, with a one-command self-proof dual baseline.
**核心数字（2026-10-30 口径, `prompt-cli baseline` 一条命令复现）**:
- 271 条 lint 规则（196 可自动修复）/ 130 评估维度 / 73 MCP 工具
- 708 条 golden 攻击探针, 漏检率 **0.00%**（棘轮阈值 5%, 只收紧不放松）
- 60 个干净样本, 误报率 **0.81%**（棘轮阈值 1%）
- 过防御锚点：NotInject 339 hard-benign 独立 holdout, 安全族误杀率 **6.78%**（首点 33.92% 逐批修复至破 10% 阈值以下, 时间序列公开）
- OWASP LLM Top 10 (2026) + MITRE ATLAS + 等保 2.0 三标准映射
- MIT License, Python 3.10+, 零核心第三方依赖
- 零安装试用: `pipx run --spec ai-prompt-toolkit prompt-cli lint <file>`（2026-10-30 实测 uvx 通道全程 6.8s）
- 自证命令: `pip install ai-prompt-toolkit && prompt-cli baseline`

## 1. OWASP LLM Top 10 工具/资源清单申请文本

> 提交路径：OWASP GenAI Security Project 资源页（genai.owasp.org）提交入口,
> 或其 GitHub 仓库 open issue 附下列文本。提交人=用户侧账号。

**Title**: ai-prompt-toolkit — Deterministic static gate for LLM prompts (CI-gate layer, zero LLM)

**Body**:

> ai-prompt-toolkit (https://github.com/wqbcs/ai-prompt-toolkit) is a deterministic
> static-analysis gate for LLM prompts and agent prompt artifacts. It runs 271 static
> rules (196 auto-fixable) plus a 5-layer security scan, red-team probes, and 130-dimension
> evaluation, with full OWASP LLM Top 10 (2026 edition) + MITRE ATLAS + MLPS 2.0
> (等保 2.0) mapping and SARIF output for CI.
>
> Positioning: CI-gate layer of a layered LLM defense — deterministic, zero-LLM,
> offline, byte-identical verdicts (<100ms/file). Complementary to, not a substitute
> for, runtime protection (e.g. LLM Guard class) and LLM-based evaluation (e.g.
> promptfoo); a coexistence workflow is documented in the repo.
>
> Reproducible quality claims (one command, any machine):
> `pip install ai-prompt-toolkit && prompt-cli baseline`
> — miss rate 0.00% on 708 golden attack probes; false-positive rate 0.81% on 60
> clean prompts; over-defense 6.78% on the NotInject 339 hard-benign holdout
> (ACL 2025), with public time series (ratchet: tighten-only) and a machine-generated
> known-misses ledger.
>
> License: MIT. Package: PyPI `ai-prompt-toolkit` (also npm/ghcr).

## 2. Awesome 清单 PR 条目（三条候选, R351 调研登记）

> 提交路径：各仓库 GitHub open PR（按各清单 CONTRIBUTING 格式微调）。提交人=用户侧。

### 2.1 tldrsec（AI/LLM 安全面）

```markdown
- [ai-prompt-toolkit](https://github.com/wqbcs/ai-prompt-toolkit) — Deterministic static gate for LLM prompts: 271 rules, OWASP LLM Top 10 (2026) mapping, SARIF/CI-native, zero LLM, byte-identical verdicts, one-command reproducible dual baseline (0.00% miss @708 probes / 0.81% FP @60 clean). MIT, Python.
```

### 2.2 muellerberndt（安全工具面）

```markdown
- [ai-prompt-toolkit](https://github.com/wqbcs/ai-prompt-toolkit) — static lint/scan gate for prompt files and agent configs; injection detection (incl. 18 Chinese rules), OWASP LLM Top 10 (2026) + MITRE ATLAS mapping, SARIF output, CI gate with incremental mode. MIT, Python.
```

### 2.3 mukundakatta（LLM 工程/工具面）

```markdown
- [ai-prompt-toolkit](https://github.com/wqbcs/ai-prompt-toolkit) — prompt linting + security scanning + 130-dimension evaluation + red-team probes for LLM prompts; deterministic (zero LLM), <100ms/file, SARIF/JSON, MCP server (73 tools), Chinese-first. MIT, Python.
```

## 3. promptfoo 生态共存页建议

> 现状：本仓库已有 `docs/promptfoo-coexistence.md`（双轨 workflow：PR 静态层
> `prompt-cli lint --gate` + PR 后/nightly promptfoo eval 行为层）。建议动作
> （用户侧, 任选其一）：
>
> ① 在 promptfoo 仓库 community/docs 区 open discussion：提议在 "interoperability /
> static analysis" 面登记 ai-prompt-toolkit 作为静态门禁互补层（引用本仓库共存文档
> URL）；
> ② 若 promptfoo 维护活跃, 提交 PR 在其 docs 的 "related tools" 面加一行
> （正文复用本文 §0 一句话定位 EN 版）。
>
> 注意：不做任何"替代 promptfoo"表述——共存叙事=双方采用面都扩大。

## 4. 提交顺序建议（低摩擦优先）

1. 三 awesome 清单 PR（模板化, 5 分钟/条, 被拒损失=0）
2. OWASP GenAI 资源页提交（官方背书面, 周期长）
3. promptfoo 共存 discussion（生态面, 视维护活跃度）

> 诚实边界：截至 R354 收口, 以上提交均未执行（用户侧动作）；02 总板 P5-14 行
> 状态在用户确认提交后回写。
