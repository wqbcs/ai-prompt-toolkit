# D1-D5 发布操作清单（点击级指南）

> 定位：00_交接文档 §4 决策项的操作指南。D 编号以 **00 §4 为权威**
> （06 §11 的旧编号已漂移——其 D4"Action 名"不在权威表内，marketplace 名称
> 确认降为 P1-01 发布后验收子项）。本清单只覆盖用户侧操作；仓库侧准备
> （release.yml / 打包配置 / 门禁链）已全部就绪。
>
> 状态基线（2026-10-14 实测）：
> - `pypi.org/pypi/ai-prompt-toolkit/json` → **404 = 项目未创建、包名未被占用**
> - 最新 tag `v67.25.0`，当前版本 `67.34.80`（未发布）
> - `release.yml`：tag `v*` 触发 → 3 作业链：release-build（sdist+wheel）→
>   pypi-publish（trusted publishing，OIDC，零 API token）→ docker-publish（ghcr 双通道，R289）

## 发布前 30 秒自检

```bash
git status --short        # 必须干净（或仅有有意携带的改动）
git log --oneline -3      # 确认收口 commit 在 HEAD
```

可选：`gitleaks detect`（或 `git log -S "token"` 抽查）确认历史无凭据泄漏。
`marketing/` 已在 .gitignore（不进历史）。

## D1 · 仓库转公开（~1 分钟）

1. GitHub → 仓库页 → **Settings**
2. 左侧 **General** → 底部 **Danger Zone**
3. **Change repository visibility** → **Make public** → 输入仓库名确认

解锁：P0-03 → P0-04/P1 全采用漏斗。

## D2 · PyPI 包名确认（0 分钟）

2026-10-14 实测 `ai-prompt-toolkit` **未被占用**——直接确认使用原包名。
（若决策前被他人抢注，改 `ai-prompt-toolkit-cli`；模块名 `ai_prompt_toolkit` 不变。）

## D3 · PyPI 项目 + trusted publishing（~5 分钟）

1. pypi.org → 登录 → **Projects** → **Publish a project** → 创建 `ai-prompt-toolkit`
2. 项目 **Settings** → **Publishing** → **Add integration** →
   - Type: **OpenID Connect**
   - Owner: **GitHub** → `wqbcs/ai-prompt-toolkit`
   - Environment: `pypi`
3. GitHub 侧先建 environment（顺序不能反，否则第 2 步选不到）：
   仓库 **Settings** → **Environments** → **New environment** → 名称 `pypi`

无 API token——GH Actions 以 OIDC 身份代签（`release.yml` 已配 `permissions: id-token: write`）。

## D4 · 按 P0 序列推进（无操作）

确认"是"即可（P0-01→P0-06 已全绿，P0-03/04 待 D1/D3 解除）。

## D5 · 启用分支保护（~2 分钟）

1. GitHub → 仓库 **Settings** → **Branches**
2. **Add branch protection rule** → 分支 `main`
3. 勾选：
   - **Require status checks to pass before merging** → 选 `prompt-quality-gate`、`test`
   - **Require pull request reviews before merging** → 1 名 reviewer（`.github/CODEOWNERS` 已落盘，尺子类文件自动匹配双人 review 面）
4. Save

解锁：P3-13 制度面强制化（无分支保护时 ownership 仅展示不强制）。

## 发布执行（D1-D5 全绿后）

```bash
git tag v67.34.80          # 若本轮收口已升版，用新版本号
git push origin v67.34.80  # 触发 release.yml → PyPI + ghcr 双通道（R289：docker-publish 在 pypi-publish 后）
```

**发版后 30 分钟验证**（06 §1 纪律）：

```bash
pip index versions ai-prompt-toolkit        # 版本号出现
python -m venv /tmp/pypi-smoke && /tmp/pypi-smoke/bin/pip install ai-prompt-toolkit
/tmp/pypi-smoke/bin/prompt-cli --version
/tmp/pypi-smoke/bin/prompt-cli baseline     # 必须输出 0.00%/0.82% 当前双基线
/tmp/pypi-smoke/bin/prompt-cli lint -s src/ai_prompt_toolkit/templates/   # 必须出 finding
docker pull ghcr.io/wqbcs/ai-prompt-toolkit:67.34.80   # R289 双通道镜像（若升版改新版本号）
docker run --rm ghcr.io/wqbcs/ai-prompt-toolkit:67.34.80 --version
```

## 发布后触发器（登记在 02 总板，按信号逐个执行）

| 触发器 | 动作 | 板项 |
|---|---|---|
| 发布完成 | `uvx prompt-cli` 实测（1 轮内） | R242-X3 |
| 发布完成 | docker pull 冒烟（双通道实测；CI 已内置 docker run baseline） | P1-03 |
| 发布完成 | P1-19 GitLab/Azure snippet fork 仓冒烟各 1 次 | P1-19 |
| 发布完成 | P1-20 MCP ≥1 客户端实连 + registry 收录 | P1-20 |
| 首次发布后 | Homebrew tap 启用 | P1-21 |
| 发布后 | README 英文首屏（ICP-① 英文优先） | P1-07 |
| M1 验收 | CI 连续 14 天双绿（计时自 R225，已满足）+ PyPI 可装 + 公开 | M1 |
