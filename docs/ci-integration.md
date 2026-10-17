# CI 多平台集成（GitLab / Azure DevOps）

> P1-19 工件：GitHub 之外 CI 平台的复制即用门禁片段。
> 可移植性基础：SARIF 是 OASIS 标准（01 §9），CLI 退出码契约稳定
> （01 §3 不变量 5：**0=通过 / 1=警告(WARN, medium) / 2=门禁失败(FAIL, high/critical) / 3=执行层错误**，`--gate`/`--fail-on` 均走此契约）。
>
> 边界声明：本文件是发布前文档工件（P1-04 前置）；片段中 `pip install
> ai-prompt-toolkit` 需发布后可用。fork 仓冒烟（GitLab/Azure 各 1 次）
> 发布后执行，已登记 02 总板 P1-19。

## 命令面速查（本片段用到的选项）

| 选项 | 语义 |
|---|---|
| `prompt-cli lint -s <路径> --gate` | Quality Gate，按 verdict 决定退出码 |
| `--fail-on critical\|high\|medium` | 显式级别门禁：该级别及以上 findings>0 → 退出码 2 |
| `--new-from-rev <REV>` | git 原生增量：只 lint `<REV>` 后变更的文件（brownfield 免基线） |
| `--incremental --baseline <file>` | 基线增量：只计 NEW findings（与 `--new-from-rev` 互斥） |
| `--format sarif -o <file>` | SARIF 报告落盘（进 Code Scanning / Code Quality） |

## GitLab CI（`.gitlab-ci.yml`）

### 标准门禁

```yaml
prompt-lint:
  image: python:3.12-slim
  stage: test
  script:
    - pip install --no-cache-dir ai-prompt-toolkit
    - prompt-cli lint -s prompts/ --gate
  rules:
    - changes:
        - "prompts/**/*"
        - "**/*.md"
        - "**/*.prompt"
```

### MR 增量门禁（brownfield 推荐，免基线文件）

```yaml
prompt-lint-mr:
  image: python:3.12-slim
  stage: test
  script:
    - pip install --no-cache-dir ai-prompt-toolkit
    - |
      # CI_COMMIT_BEFORE_SHA 在部分 MR 为空（目标分支首推等）→ 空值回退全量
      if [ -n "$CI_COMMIT_BEFORE_SHA" ]; then
        prompt-cli lint -s . --new-from-rev "$CI_COMMIT_BEFORE_SHA" --gate
      else
        prompt-cli lint -s . --gate
      fi
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

### SARIF 进 GitLab Code Quality（GitLab ≥ 17.5 支持 SARIF 格式）

```yaml
prompt-lint:
  image: python:3.12-slim
  stage: test
  script:
    - pip install --no-cache-dir ai-prompt-toolkit
    - prompt-cli lint -s prompts/ --format sarif -o gl-code-quality.sarif
    - prompt-cli lint -s prompts/ --gate
  artifacts:
    reports:
      codequality: gl-code-quality.sarif
```

### air-gap / 内网变体（P1-03 落地后）

```yaml
prompt-lint:
  image: ghcr.io/<owner>/ai-prompt-toolkit:latest   # P1-03 落地后启用（06 §4 镜像命名/3-tag 策略; R319: 镜像名口径=ai-prompt-toolkit, 旧名 prompt-lint 废弃）
  stage: test
  script:
    - prompt-cli lint -s prompts/ --gate
```

内网 PyPI mirror 替代首行：`pip install -i <内网mirror> ai-prompt-toolkit`；
完全离线走 wheelhouse tarball / `docker save` 导入（06 §4 离线交付节）。

## Azure DevOps（YAML pipeline）

```yaml
stages:
  - stage: PromptLint
    displayName: 'Prompt Lint Gate'
    jobs:
      - job:
        pool:
          vmImage: ubuntu-latest
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.12'
          - script: |
              python -m pip install --no-cache-dir ai-prompt-toolkit
              prompt-cli lint -s prompts/ --format sarif -o prompt-lint.sarif
              prompt-cli lint -s prompts/ --gate
          - task: PublishBuildArtifacts@1
            inputs:
              PathtoPublish: prompt-lint.sarif
              ArtifactName: prompt-lint-sarif
```

SARIF 导入 Azure DevOps Code Analysis 的通道以官方文档为准；本片段先落
"门禁红绿 + SARIF 工件保留"两件事（不依赖额外 import 组件）。

## 与 GitHub 面的关系

GitHub 用户走 composite action（仓库根 `action.yml`，P1-01）或 pre-commit
（P1-02）；本文件只覆盖 GitHub 之外平台。检测内核、规则、退出码、SARIF
方言跨平台同一真源——同一 prompt 在任何平台裁决逐字节一致。
