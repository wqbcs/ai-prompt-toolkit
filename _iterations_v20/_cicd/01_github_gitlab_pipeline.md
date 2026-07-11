# Q1-06 CI/CD模板（GitHub Actions + GitLab CI）

> **迭代**：v20-Q1-06 | **日期**：2026-07-12

---

## 一、GitHub Actions完整流水线

### 1.1 提示词质量检查流水线

```yaml
name: Prompt Quality Pipeline

on:
  push:
    branches: [main, develop]
    paths:
      - 'prompts/**'
      - 'templates/**'
  pull_request:
    branches: [main, develop]
    paths:
      - 'prompts/**'
      - 'templates/**'

env:
  PROMPT_VERSION: "1.0.0"
  NODE_VERSION: "20"

jobs:
  lint:
    name: 提示词语法检查
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - name: 安装依赖
        run: npm ci
      - name: 提示词语法检查
        run: |
          npx prompt-ide lint prompts/ \
            --format json \
            --output lint-report.json \
            --max-warnings 0 \
            --max-errors 0
      - name: 上传检查报告
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: lint-report
          path: lint-report.json

  validate:
    name: 提示词模板验证
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: 验证模板格式
        run: |
          npx prompt-ide validate templates/ \
            --check-variables \
            --check-directives \
            --check-references \
            --strict
      - name: 验证变量完整性
        run: |
          npx prompt-ide check-vars templates/ \
            --no-undefined-vars \
            --no-unused-vars \
            --consistent-naming snake_case

  security:
    name: 安全扫描
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: 提示词安全检查
        run: |
          npx prompt-ide security-scan prompts/ \
            --check-pii \
            --check-secrets \
            --check-injection \
            --severity-threshold high

  performance:
    name: 性能基准测试
    runs-on: ubuntu-latest
    needs: [lint, validate]
    steps:
      - uses: actions/checkout@v4
      - name: Token消耗基准
        run: |
          npx prompt-ide benchmark prompts/ \
            --models gpt-4o,claude-3.5-sonnet,qwen-max \
            --max-tokens 4096 \
            --output benchmark-report.json
      - name: 性能回归检测
        run: |
          npx prompt-ide regression-check \
            --baseline main \
            --threshold 10%
      - name: 上传基准报告
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-report
          path: benchmark-report.json

  test:
    name: 提示词执行测试
    runs-on: ubuntu-latest
    needs: [lint, validate]
    strategy:
      matrix:
        model: [gpt-4o, gpt-4o-mini, claude-3.5-sonnet, qwen-max]
    steps:
      - uses: actions/checkout@v4
      - name: 执行提示词测试
        env:
          API_KEY: ${{ secrets.LLM_API_KEY }}
        run: |
          npx prompt-ide test prompts/ \
            --model ${{ matrix.model }} \
            --timeout 30s \
            --retry 3 \
            --output test-results-${{ matrix.model }}.json
      - name: 上传测试结果
        uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ matrix.model }}
          path: test-results-${{ matrix.model }}.json

  quality-gate:
    name: 质量门禁
    runs-on: ubuntu-latest
    needs: [lint, validate, security, performance, test]
    if: always()
    steps:
      - uses: actions/checkout@v4
      - name: 质量门禁检查
        run: |
          npx prompt-ide quality-gate \
            --lint-passed ${{ needs.lint.result == 'success' }} \
            --validate-passed ${{ needs.validate.result == 'success' }} \
            --security-passed ${{ needs.security.result == 'success' }} \
            --performance-passed ${{ needs.performance.result == 'success' }} \
            --test-passed ${{ needs.test.result == 'success' }} \
            --min-score 21.00 \
            --max-std-dev 0.10

  publish:
    name: 发布提示词包
    runs-on: ubuntu-latest
    needs: [quality-gate]
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      - uses: actions/checkout@v4
      - name: 构建发布包
        run: |
          npx prompt-ide build \
            --version ${{ github.ref_name }} \
            --output dist/
      - name: 发布
        run: |
          npx prompt-ide publish dist/ \
            --registry ${{ secrets.REGISTRY_URL }} \
            --token ${{ secrets.REGISTRY_TOKEN }}
      - name: 生成Release Notes
        run: |
          npx prompt-ide release-notes \
            --from ${{ github.event.before }} \
            --to ${{ github.sha }} \
            --output RELEASE_NOTES.md
      - name: 创建GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          body_path: RELEASE_NOTES.md
          files: dist/*
```

---

## 二、GitLab CI完整流水线

### 2.1 .gitlab-ci.yml

```yaml
stages:
  - lint
  - validate
  - security
  - performance
  - test
  - quality-gate
  - publish

variables:
  PROMPT_VERSION: "1.0.0"
  NPM_REGISTRY: "https://registry.npmjs.org"

.lint:
  stage: lint
  image: node:20-alpine
  before_script:
    - npm ci
  script:
    - npx prompt-ide lint prompts/ --format json --output lint-report.json --max-warnings 0 --max-errors 0
  artifacts:
    paths:
      - lint-report.json
    when: always

prompt-lint:
  extends: .lint

template-validate:
  stage: validate
  image: node:20-alpine
  before_script:
    - npm ci
  script:
    - npx prompt-ide validate templates/ --check-variables --check-directives --check-references --strict
    - npx prompt-ide check-vars templates/ --no-undefined-vars --no-unused-vars --consistent-naming snake_case

security-scan:
  stage: security
  image: node:20-alpine
  before_script:
    - npm ci
  script:
    - npx prompt-ide security-scan prompts/ --check-pii --check-secrets --check-injection --severity-threshold high

performance-benchmark:
  stage: performance
  image: node:20-alpine
  needs: [prompt-lint, template-validate]
  before_script:
    - npm ci
  script:
    - npx prompt-ide benchmark prompts/ --models gpt-4o,claude-3.5-sonnet,qwen-max --max-tokens 4096 --output benchmark-report.json
    - npx prompt-ide regression-check --baseline main --threshold 10%
  artifacts:
    paths:
      - benchmark-report.json

prompt-test:
  stage: test
  image: node:20-alpine
  needs: [prompt-lint, template-validate]
  parallel:
    matrix:
      - MODEL: [gpt-4o, gpt-4o-mini, claude-3.5-sonnet, qwen-max]
  before_script:
    - npm ci
  script:
    - npx prompt-ide test prompts/ --model $MODEL --timeout 30s --retry 3 --output test-results-$MODEL.json
  artifacts:
    paths:
      - test-results-$MODEL.json

quality-gate:
  stage: quality-gate
  image: node:20-alpine
  needs: [prompt-lint, template-validate, security-scan, performance-benchmark, prompt-test]
  when: always
  before_script:
    - npm ci
  script:
    - npx prompt-ide quality-gate --min-score 21.00 --max-std-dev 0.10

publish:
  stage: publish
  image: node:20-alpine
  needs: [quality-gate]
  only:
    - tags
  before_script:
    - npm ci
  script:
    - npx prompt-ide build --version $CI_COMMIT_TAG --output dist/
    - npx prompt-ide publish dist/ --registry $NPM_REGISTRY
    - npx prompt-ide release-notes --from $CI_COMMIT_BEFORE_SHA --to $CI_COMMIT_SHA --output RELEASE_NOTES.md
  artifacts:
    paths:
      - dist/
      - RELEASE_NOTES.md
```

---

## 三、环境管理

### 3.1 多环境配置

```yaml
# environments/dev.yml
model: gpt-4o-mini
temperature: 0.7
max_tokens: 2048
timeout: 30s
log_level: debug
quality_gate:
  min_score: 19.00
  max_std_dev: 0.50

# environments/test.yml
model: gpt-4o
temperature: 0.3
max_tokens: 4096
timeout: 60s
log_level: info
quality_gate:
  min_score: 20.00
  max_std_dev: 0.20

# environments/staging.yml
model: gpt-4o
temperature: 0.2
max_tokens: 4096
timeout: 60s
log_level: warn
quality_gate:
  min_score: 20.50
  max_std_dev: 0.10

# environments/prod.yml
model: gpt-4o
temperature: 0.1
max_tokens: 4096
timeout: 120s
log_level: error
quality_gate:
  min_score: 21.00
  max_std_dev: 0.05
```

---

## 四、验收项

- [x] GitHub Actions完整流水线（7个Job：lint/validate/security/performance/test/quality-gate/publish）
- [x] GitLab CI完整流水线（7个Stage，对应GitHub Actions）
- [x] 多模型并行测试矩阵
- [x] 质量门禁（均分/标准差/安全/性能）
- [x] 多环境配置（dev/test/staging/prod）
- [x] 发布工作流（构建+发布+Release Notes）
- [x] 产物管理（lint报告/基准报告/测试结果）
