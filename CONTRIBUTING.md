# 贡献指南 — AI Prompt Toolkit

本仓库是**确定性 LLM 提示词静态门禁**（prompt 的 ESLint）。
核心不变量（贡献前必读，违反即退回）：

1. **楔子**：每次裁决逐字节一致 + 零 LLM 成本 + <100ms/文件 + 离线可跑
2. **探针先行**：无探针支撑的规则 = 噪音，不合入
3. **棘轮只收紧**：mypy 基线（=0）/ 误报基线（1%）/ 漏检基线（5%）不得抬升
4. **反清单**（docs/planning/02 总板"不做什么"）：不往门禁路径加 LLM 调用、
   不批量给模板塞声明骗规则、不为凑数加规则/维度/Provider

行为准则见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 快速开始

```bash
# 1. Fork & Clone
git clone https://github.com/YOUR_USERNAME/ai-prompt-toolkit.git
cd ai-prompt-toolkit

# 2. 安装开发依赖（Python 3.10+）
pip install -e ".[dev]"

# 3. 运行测试
pytest tests/ -q -k "not slow"

# 4. 代码格式化 + Lint
ruff format src/ tests/
ruff check src/ tests/

# 5. 收口前全链门禁（29 步，独立退出码，禁管道）
python scripts/release_gate.py
```

## 贡献流程

1. **创建 Issue** — 描述问题或功能需求（安全漏洞走私有渠道，见 SECURITY.md）
2. **Fork 仓库** — 在你的账户下创建分支（`feat/xxx`, `fix/xxx`, `docs/xxx`）
3. **开发** — 按下方纪律提交
4. **测试** — 确保所有测试通过，新增功能需有对应测试
5. **提交 PR** — 描述变更内容和原因

## 代码规范

- **Python 3.10+** 语法
- **类型注解**：所有公开 API 必须有类型注解（mypy 棘轮基线=0，禁抬）
- **文档字符串**：所有公开函数/类必须有 docstring
- **测试覆盖**：新增功能必须包含测试
- **代码格式**：`ruff format` + `ruff check`（版本 0.17.0 钉死，勿升级）
- **提交信息**：遵循 [Conventional Commits](https://www.conventionalcommits.org/)

```
feat: 简短描述
fix: 简短描述
docs: 简短描述
refactor: 简短描述
test: 简短描述
```

工具链版本钉死（ruff 0.17.0 / mypy 2.4.0，真源=pyproject.toml [dev] + ci/dep_snapshot.json）——门禁行为随上游发版漂移
是本项目 R223 四连红的根因，升级需独立 PR 论证。

## 新增 Lint 规则（探针先行流程）

这是本仓库最核心的贡献路径，顺序不可颠倒：

1. **先写探针**（`src/ai_prompt_toolkit/data/golden_attacks.json` + 干净样本集）
   - 每条新规则 ≥2 TP（攻击形态命中）+ ≥2 TN（干净样本不误报，
     优先结构复杂样本：嵌套 JSON/多轮对话/代码混排——FP 痛点实证见
     docs/planning/12 §1.7）
   - 探针 = 尺子。探针错，规则就是自嗨
2. **再写规则**（`src/ai_prompt_toolkit/linter/rules_pXXX_pYYY.py`）
   - 必须有 OWASP LLM Top 10 或内部类别映射
   - severity 分级有据：critical=直接可利用 / high=显著风险 /
     medium=最佳实践 / low=风格
   - 消息文案含"下一步"（修复建议 or `prompt-cli explain Pxxx`）
3. **验证双基线不回归**：

   ```bash
   python scripts/check_false_positives.py --fail-above 0.01
   python scripts/check_miss_rate.py --fail-above 0.05
   ```

4. **全链收口**：`python scripts/release_gate.py`（29 步全绿才提交）

### 规则落地位置（10 步，探针先行流程的具体落点）

1. 创建 `src/ai_prompt_toolkit/linter/rules_pXXX_pYYY.py`
2. 定义 `_RULES_PXXX_PYYY` 列表，包含 `LintRule` 对象
3. 通过 `_RULE_MAP[r.rule_id] = r` 注册到全局
4. 实现 check 函数 `check_pXXX(text: str) -> Finding | list[Finding]`
5. 在 `rules.py` 中 import check 并添加到 `_CHECKERS_EXTENDED`
6. 在 `owasp_mapping.py` 的 `_OWASP_RULE_MAPPING` 添加 OWASP 映射
7. 在 `fixer.py` 的 `AUTO_FIXABLE_RULES` 添加（如可自动修复）
8. 在 `linter.py` 的 `_get_fix_action` 添加修复逻辑（如可自动修复）
9. **更新测试断言中的 Lint 规则数量**
10. 编写测试 `tests/test_rXX.py`（TP+TN 探针各 ≥2）

### Lint 规则类别

| 类别 | 规则范围 | 说明 |
|------|----------|------|
| structure | P001-P030 | Prompt 结构基础规则 |
| security | P031-P100 | 安全防护规则 |
| quality | P101-P130 | 质量评估规则 |
| privacy | P131-P150 | 隐私合规规则 |
| advanced_security | P151-P165 | 高级安全规则 |
| output_safety | P166-P170 | 输出安全规则 |
| harmonyos | P171-P175 | 鸿蒙 NEXT API 规则 |
| injection | P176-P180 | 注入攻击检测规则 |
| operations | P181-P185 | Prompt 运维规则（版本/依赖/隔离/降级/灰度） |
| harmonyos_v15 | P186-P190 | 鸿蒙 NEXT API 15 规则（ArkUI/NAPI/沙箱 2.0/HSP/元服务） |
| agent_security | P191-P195 | AI Agent 安全规则（权限/工具约束/CoT 隔离/协调/记忆） |

> P196–P271 后续规则族（如 P269 混排 / P270 中文 agent 配置注入 / P271 多模态输入门）
> 见 [docs/rules.md](docs/rules.md) 全量清单。

### 其他扩展点

- **添加 Probe**：`redteam/probes/` 创建模块，继承 `BaseProbe` 实现
  `generate_inputs()`，自动发现机制（`_discover_probes`）自动注册
- **添加 Provider**：`ab_test/providers/` 创建模块，继承 `BaseProvider`
  实现 `invoke()`（async）和 `validate()`，自动发现机制自动注册
- **添加评估维度**：`evaluator.py` 的 `_DIMENSIONS` 列表添加维度字典，
  更新测试断言中的维度数量。权重预设 7 个（default/security-heavy/
  quality-balanced/performance-first/harmonyos-strict/redteam-ready/
  cost-efficient），`evaluate --preset` 使用
- **添加 MCP 工具**：`mcp_server.py` 的 `_handle_tools_list` 添加工具定义
  + 实现 `_tool_xxx(args) -> dict` + `_get_tool_dispatch` 添加映射
  （tools list 和 dispatch 必须同步，启动时自动校验）
- **添加华为云 FunctionGraph 模板**：`huawei_cloud/fg_template.py` 的
  `_TEMPLATES` 添加代码模板字符串 + `_TEMPLATE_META` 添加元数据 +
  `FGTemplateType` 枚举添加新类型（MCP 工具自动支持
  fg_template_list 和 fg_template_generate）

## 测试纪律

- 单元：`tests/test_rXXX_*.py`（R 编号 = 轮次，新贡献沿用递增）
- e2e 真子进程：`tests/e2e/`（涉及进程边界/stdio/exit code 必须真子进程，
  CliRunner 绿 ≠ 真 CLI 绿——R222 click stdin 类型漂移实证）
- 测试数只增不减；删测试需在 PR 说明理由

## 版本与发布

版本号三处同步：`pyproject.toml` / `ai_prompt_toolkit/__init__.py` /
README 徽章。升版后的固定顺序（漏跑曾两次致 CI 红）：

```
版本3处 + README 徽章 → python scripts/gen_rules_doc.py（非--check）
→ python scripts/sync_readme_metrics.py → python scripts/gen_operating_curve.py（非--check）
→ python scripts/sync_badges.py → python scripts/check_version_consistency.py → commit
```

语义化版本策略：规则新增=minor / bugfix=patch / 行为变更=major。

## 提交纪律

- **门禁链禁管道**：`release_gate.py | tail` 会吞退出码造成假绿
  （R224 事故）。直接 `python scripts/release_gate.py`
- **基线重存独立 commit**：`baselines/` 变更必须单独提交并说明理由
  （增量门禁的尺子，混入功能提交=审计盲区）
- **门禁自身变更必须自测**：`.github/workflows/ scripts/ baselines/ ci/`
  的变更在 CI paths 过滤内，push 后必须轮询确认 run 出现且绿
  （16a57a5 无 run 教训）
- 探针集（`src/ai_prompt_toolkit/data/golden_*`）/ 规则文件 / workflow / 基线 = 尺子面，
  变更需双人 review（`.github/CODEOWNERS`，R242-P3-13 已落；分支保护
  启用=仓库管理员操作，见 00 交接文档 §4）

## 安全规范

- **禁止提交** API Key/密码/token 等敏感信息
- 所有用户输入必须经过安全检查
- 新增安全规则需同步更新 OWASP 映射
- 安全相关变更需标注 `[SECURITY]` 前缀

## 报告 Bug

请使用 GitHub Issues（bug 模板已内置 `--version` 与复现命令字段），包含：
- 复现步骤（精确到可复制粘贴的命令）
- 期望行为 / 实际行为
- 环境信息（Python 版本、OS、安装方式）
- 误报类 bug 请附 `prompt-cli baseline` 输出与干净样本——
  误报是双基线棘轮守护的一等公民缺陷

## 许可

贡献的代码遵循 MIT 许可证。
