# 上线前一次性动作清单（P0-04 · PyPI trusted publishing + GitHub 侧公开面）

> **用途**：上线（tag 推送触发 release.yml 发布链）前，用户侧需完成的全部一次性动作——
> 共 6 项（必填 4 + 社交预览图 1 + ruleset 可选 1），全部复制即用，约 10 分钟。完成后告知 agent「配置完成」，
> 即进入发布轮（升版 → commit → tag → PyPI + ghcr 双通道）。
>
> **为什么是 trusted publishing**：GitHub Actions 用 OIDC（JWT 短期凭据）向 PyPI 自证
> 身份，**零长期 API token**——没有可泄露的凭据，符合仓库供应链安全纪律。

---

## A. PyPI 侧（1 步）

> **机制说明（R342 · 2026-10-26 官网实证）**：个人账号**官网没有「创建（空）项目」入口**——
> 旧「先建项目占名、再配 trusted publisher」两步流程在官网已不存在
> （仅组织账号可在 org 后台创建空项目）。
> 官方流程 = **pending trusted publisher**（<https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/>）：
> 在**账号级** Publishing 页配置并指定要创建的项目名，首次 OIDC 发布自动创建项目，
> 并自动转为正式 publisher（此后无需任何再配置）。

### 步骤 1：配置 Pending Trusted Publisher（账号级，首次发布自动建项目）

1. 打开 <https://pypi.org/manage/account/>（未注册则先注册；用你打算长期维护的账号）
2. 左侧边栏 **Publishing**（账号级页面 <https://pypi.org/manage/account/publishing/>，
   **不是**项目后台——项目尚不存在）→ **Add new trusted publisher**
3. 表单比项目后台**多一个项目名字段**，五元组按下表逐字填：

   | 字段 | 值 | 依据 |
   |---|---|---|
   | PyPI 项目名 | `ai-prompt-toolkit` | 与 `pyproject.toml` `[project] name` 逐字一致（含连字符）；**必须与元数据名一致，不一致 = 首发布 400**（官方 troubleshooting） |
   | Repository owner | `wqbcs` | GitHub 仓库 owner |
   | Repository name | `ai-prompt-toolkit` | GitHub 仓库名 |
   | Workflow filename | `release.yml` | `.github/workflows/release.yml`（**文件名，不是工作流显示名** "Release to PyPI"） |
   | Workflow environment | `pypi` | release.yml `pypi-publish` 作业的 `environment: pypi`（release.yml:107） |

4. **提交前核对名称可用**：<https://pypi.org/project/ai-prompt-toolkit/> 显示 404 = 可用。
   ⚠️ **pending publisher 在首次发布前不创建项目、不预留名称**（官方文档 Important 条款）：
   若名称先被他人占用，该 pending publisher **失效**，须重新配置
5. 保存后 PyPI 会显示一段 `-----BEGIN PUBLIC KEY-----` 公钥——**不用粘贴到任何地方**
   （GitHub 端 OIDC 凭据自动匹配），仅作留档。
6. **不要创建 PyPI API token**（账号管理 API tokens 页）——本流程完全走 OIDC，
   无 token = 无泄露面。

> 首次发布成功（tag 推送 → release.yml）后项目自动创建、pending publisher 自动转为
> 正式 publisher；届时可在项目后台 <https://pypi.org/manage/project/ai-prompt-toolkit/publishing/>
> 查看状态（无需任何动作）。

---

## B. GitHub 侧（3 项必填 + 1 项可选）

### 步骤 2：创建 `pypi` 环境（必须，否则发布作业红）

`release.yml` 的 `pypi-publish` 作业引用 `environment: pypi`（release.yml:107）——
环境不存在时作业直接失败（GitHub 不自动创建环境）。

1. 仓库 **Settings → Environments → New environment**
2. 名称填 **`pypi`**（逐字一致）
3. 其余选项保持默认即可（trusted publishing 不需要 environment secrets）

### 步骤 3：设置仓库 Description（复制即用）

仓库 **Settings → General → About** → Description（≤350 字符）：

```
Deterministic LLM prompt security & quality gate (prompt's ESLint): zero LLM cost, byte-level reproducible verdicts, SARIF/CI-native, OWASP LLM Top 10 2026 mapped. Python CLI · GitHub Action · MCP · VS Code · Docker
```

> 说明：不含规则数等会随版本漂移的数字（公开面数字漂移是 R260/R329 同族治理面）；
> 搜索关键词由 Topics 承担（步骤 4）。

### 步骤 4：设置 Topics（复制即用）

仓库 **Settings → General → About** → Topics（空格分隔，11 个）：

```
prompt-security llm prompt-engineering prompt-injection static-analysis linter ci-gate owasp-llm sarif mcp ai-safety
```

> 与 `pyproject.toml` `[project] keywords` 同源（PyPI 搜索面/GitHub 搜索面一致）；
> 增删 keyword 时两处同改。

### 步骤 5（可选）：Branch Protection Ruleset

P0-02 剩余项（API 403 需管理员侧）：仓库 **Settings → Rulesets → Create ruleset**：
作用于 `main`，勾 **Require a pull request before merging** + 状态检查
（Prompt CI 的 test 作业）。不阻塞上线（个人仓库现状可发布），属治理加固。

> **Homepage**（About 页可选字段）：先留空或填仓库 URL；若未来上 MkDocs 文档站
> （P5-12）再改指站点。

### 步骤 6：上传社交预览图（分享面封面）

聊天软件（Slack/Discord/微信）/ 浏览器粘贴仓库链接时的 unfurl 封面——
此前分享面是裸的（无 social preview）。图片已生成：**`assets/social_preview.png`**
（1280×640，品牌盾+对勾 motif，仅不变量文案、无计数数字 = 防漂移）。
上传：仓库 **Settings → General → About → Social preview**，选该文件。

---

## C. 命名映射表（P5-13 · 单一真源）

| 面 | 名称 | 真源位置 |
|---|---|---|
| PyPI 包 | `ai-prompt-toolkit` | `pyproject.toml` `[project] name` |
| Python 模块 | `ai_prompt_toolkit` | `src/ai_prompt_toolkit/` |
| CLI 入口（主/别名） | `prompt-cli` / `prompt` | `[project] scripts` |
| GitHub Action | `wqbcs/ai-prompt-toolkit@action/v1` | 根 `action.yml`（P1-01；tag 命名空间 `action/v*` 防撞发布触发 `v*`） |
| Docker 镜像 | `ghcr.io/wqbcs/ai-prompt-toolkit`（3 tag：latest/全版本/主版本） | `release.yml` docker-publish 作业 |
| MCP 入口 | `prompt-cli mcp`（73 工具） | console scripts（P1-18） |
| LSP 入口 | `prompt-cli lsp`（`[lsp]` extra） | `lsp_server.py`（P5-16） |
| npm 包装器 | 未发布（P1-04，依赖 P0-04） | — |

> 品牌/logo：`assets/logo.svg` + `assets/favicon.svg`（纯矢量单真源，P5-13 R326 落）；
> 四处 logo diff=0 与 PyPI 页面截图存档 = 发布后动作（P5-13 剩余）。

---

## D. 仓库侧已就位（无需任何动作）

`release.yml` 发布链（触发器：推送 `v*` tag）：

```
release-test      全量 pytest（−slow 面，与 CI 3.12 lane 逐字同命令）+ linter 覆盖率棘轮 ≥90%
  → release-gate  tag↔pyproject 版本硬断言（漂移即拒发）
                  + gen_rules_doc --check + release_gate --skip 1,2（全链）
  → release-build python -m build + twine check + dist 工件
  → pypi-publish  environment: pypi + permissions: id-token: write
                  pypa/gh-action-pypi-publish@release/v1（无密码 = OIDC 通道）
  → docker-publish lockstep（PyPI 成功后才发 ghcr + docker run baseline smoke）
```

关键锚点（机器可查，防本文漂移）：
- 触发：`on: push: tags: ['v*']`（release.yml:8-9）
- OIDC：`environment: pypi`（release.yml:107）+ `id-token: write`（release.yml:109）
- 版本断言：`refs/tags/v$TAG` 必须 == `pyproject.toml` 的 `project.version`（release.yml:62-69）
- 包坐标：`ai-prompt-toolkit`，`requires-python >=3.10`，console scripts `prompt-cli`/`prompt`

---

## E. 完成后：agent 侧动作（用户回「配置完成」即开始）

1. **升版**（收口门禁序，禁跳步）：版本 3 处（`pyproject.toml` +
   `src/ai_prompt_toolkit/__init__.py` + README 徽章）当前版本 → 下一 patch
   → `gen_rules_doc.py`（非 --check）→ `sync_readme_metrics.py` →
   `gen_operating_curve.py`（非 --check）→ `sync_badges.py` → `check_version_consistency.py`
2. **CHANGELOG + 板行回写 + commit/push**（02 总板 P0-04 行状态更新）
3. **推 tag** `v<新版本>` → release.yml 自动触发整链
4. **观测**：CI 可会话内经匿名公开 API 实查（仓库已公开）——盯
   release-test → release-gate → pypi-publish → docker-publish 全绿
5. **验收**（P0-04 验收标准，全过才算收口）：
   - `pip download ai-prompt-toolkit` 成功
   - 干净 venv 冒烟：`prompt-cli --help` + `prompt-cli baseline` + `prompt-cli lint`
   - PyPI 页面在线（<https://pypi.org/project/ai-prompt-toolkit/>）
   - ghcr 3 tag 存在（latest/全版本/主版本）
   - P0-01~P0-06 全清 → **S1「可信」阶段成立**

---

## F. 常见坑（历史踩点留痕）

| 坑 | 后果 | 防法 |
|---|---|---|
| pending publisher 项目名与 pyproject 元数据不一致 | 首发布 400 "Non-user identities cannot create new projects" | 逐字 `ai-prompt-toolkit`（含连字符）；若已发生，按官方 troubleshooting 删除错建项目并以正确名重建 pending publisher |
| `ai-prompt-toolkit` 名称先被他人占用 | pending publisher 失效，首次发布失败 | 发布前核对 404 = 可用（步骤 1 第 4 项）；pending publisher 首次发布前不预留名称（官方文档） |
| `pypi` 环境未创建 | pypi-publish 作业红（environment not found） | 步骤 2 先于 tag 推送 |
| Workflow environment 填错（如 `production`/留空） | OIDC audience 不匹配，作业红 | 逐字 `pypi`，对照 release.yml:107 |
| Workflow filename 填显示名 `Release to PyPI` | PyPI 侧找不到 workflow，授权不生效 | 填文件名 `release.yml` |
| tag 忘 `v` 前缀或版本与 pyproject 不一致 | release-gate 版本断言拒发（**特性不是故障**） | tag 永远 `v<pyproject version>` |
| 未升版直接推 tag 试跑 | 版本已发布过 → PyPI 拒收且**版本无法静默撤回** | 发布不可逆是设计事实——test+gate 前置链为此存在；未验收完不推 tag |
| Description 写死规则数等数字 | 每加规则必漂移（R260/R329 同族） | 步骤 4 文本无数字；数字由徽章/README 承载 |
| PyPI 账号被锁/换号 | 发布链红且无法自愈 | 用长期维护账号；PyPI 项目可加多 owner |

---

## G. 状态（R342 · 2026-10-26 修正）

- 仓库侧：✅ 就位（release.yml 全链 + P5-13 发布元数据顶配 + 06 §4 双通道设计 + 命名映射表 §C）
- 用户侧：⬜ A 节 1 步（pending publisher）+ B 节 3 项必填（步骤 5 可选）+ 步骤 6 社交预览图待执行——全部复制即用
- R342 修正：旧 A 节「创建 PyPI 项目（占名）」步骤失效——官网实证个人账号无创建项目入口，
  机制改 pending publisher（官方文档 + 2026-10-26 实查）
- 完成后：agent 侧 §E 五步收口 P0-04 → S1 可信阶段成立
