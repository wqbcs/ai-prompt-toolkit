# CI/CD工作流模板 v1.0

> **版本**：v1.0 | **日期**：2026-05-29

---

## 1. GitHub Actions工作流

### 1.1 提示词自动评估

```yaml
name: Prompt Evaluation
on:
  pull_request:
    paths: ['**/*.prompt']
  push:
    branches: [main]
    paths: ['**/*.prompt']

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Prompt Engineer CLI
        run: |
          npm install -g prompt-engineer-cli
          prompt-engineer init --config .promptrc
      
      - name: Lint Prompts
        run: |
          prompt-engineer lint --principles 28 --anti-patterns 28
          # 检测28种反模式+28条原则合规
      
      - name: Run Gate Checks
        run: |
          prompt-engineer guard --gates 17 --strict
          # 执行17项门禁，--strict表示任一失败则阻断
      
      - name: Evaluate Quality (22 Dimensions)
        run: |
          prompt-engineer evaluate \
            --dimensions 22 \
            --threshold 20.00 \
            --models gpt-4-turbo,claude-3-opus,qwen-max \
            --output evaluation-report.json
      
      - name: Regression Test
        run: |
          prompt-engineer regression \
            --baseline .evaluations/baseline.json \
            --max-degradation 0.0
            # 0退化容忍(满分守护)
      
      - name: Stress Test
        run: |
          prompt-engineer stress \
            --model-switch \
            --input-anomaly \
            --concurrent \
            --version-conflict
      
      - name: Check Score Maintenance
        run: |
          prompt-engineer score-check \
            --current evaluation-report.json \
            --baseline .evaluations/baseline_v12.json \
            --must-maintain-perfect
            # 满分守护：不得低于20.00
      
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: evaluation-report
          path: evaluation-report.json
      
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const report = require('./evaluation-report.json');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 提示词评估报告\n${formatReport(report)}`
            });
```

### 1.2 提示词自动发布

```yaml
name: Prompt Publish
on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Version Validation
        run: |
          prompt-engineer version-check \
            --semantic \
            --no-skip \
            --changelog-required
      
      - name: Full Evaluation
        run: |
          prompt-engineer evaluate --full --dimensions 22
      
      - name: Compatibility Check
        run: |
          prompt-engineer compat \
            --backward \
            --versions v11.0.0,v12.0.0
      
      - name: Publish to Market
        run: |
          prompt-engineer publish \
            --market v2 \
            --token ${{ secrets.MARKET_TOKEN }}
      
      - name: Update Documentation
        run: |
          prompt-engineer docs \
            --changelog \
            --manual \
            --api-reference
      
      - name: Notify Community
        run: |
          prompt-engineer notify \
            --channels slack,discord,email
```

---

## 2. GitLab CI工作流

### 2.1 提示词质量门禁

```yaml
stages:
  - lint
  - evaluate
  - guard
  - publish

prompt-lint:
  stage: lint
  image: node:20
  script:
    - npm install -g prompt-engineer-cli
    - prompt-engineer lint --principles 28 --anti-patterns 28
  rules:
    - changes: ["**/*.prompt"]

prompt-evaluate:
  stage: evaluate
  image: node:20
  script:
    - prompt-engineer evaluate --dimensions 22 --threshold 20.00
    - prompt-engineer regression --max-degradation 0.0
  artifacts:
    reports:
      metrics: evaluation-metrics.txt
    paths:
      - evaluation-report.json

prompt-guard:
  stage: guard
  image: node:20
  script:
    - prompt-engineer guard --gates 17 --strict
    - prompt-engineer score-check --must-maintain-perfect
  needs: ["prompt-evaluate"]

prompt-publish:
  stage: publish
  image: node:20
  script:
    - prompt-engineer publish --market v2
  rules:
    - if: $CI_COMMIT_TAG
  needs: ["prompt-guard"]
  when: manual
```

---

## 3. 满分守护CI配置

```yaml
name: Score Guardian
on:
  push:
    branches: ['**']

jobs:
  guardian:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Pre-evaluation
        run: |
          CURRENT=$(prompt-engineer score --format json)
          echo "current_score=$CURRENT" >> $GITHUB_ENV
      
      - name: Apply Changes
        run: |
          # 变更已通过PR合并，此处验证
          prompt-engineer apply --dry-run
      
      - name: Post-evaluation
        run: |
          NEW=$(prompt-engineer score --format json)
          echo "new_score=$NEW" >> $GITHUB_ENV
      
      - name: Score Comparison
        run: |
          python3 guardian_check.py \
            --current ${{ env.current_score }} \
            --new ${{ env.new_score }} \
            --min-score 20.00 \
            --max-std-dev 0.00
      
      - name: Auto-Rollback on Degradation
        if: failure()
        run: |
          git revert HEAD --no-edit
          git push origin HEAD
          # 自动回退到上一满分版本
```

---

## 4. IDE集成配置

### 4.1 pre-commit钩子

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/prompt-engineer/pre-commit
    rev: v1.0.0
    hooks:
      - id: prompt-lint
        args: ['--principles', '28', '--anti-patterns', '28']
      - id: prompt-format
        args: ['--style', 'canonical']
      - id: prompt-guard
        args: ['--gates', '17', '--strict']
```
