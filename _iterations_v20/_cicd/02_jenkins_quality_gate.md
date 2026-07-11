# Q1-07 Jenkins模板+质量门禁+环境管理

> **迭代**：v20-Q1-07 | **日期**：2026-07-12

---

## 一、Jenkins Pipeline完整模板

### 1.1 Jenkinsfile

```groovy
pipeline {
  agent any

  environment {
    PROMPT_VERSION = ''
    NPM_REGISTRY = credentials('npm-registry-url')
    REGISTRY_TOKEN = credentials('registry-token')
    LLM_API_KEY = credentials('llm-api-key')
  }

  options {
    timeout(time: 30, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '20'))
    disableConcurrentBuilds()
  }

  stages {
    stage('初始化') {
      steps {
        script {
          PROMPT_VERSION = sh(returnStdout: true, script: 'git describe --tags --always').trim()
          echo "提示词版本: ${PROMPT_VERSION}"
        }
        sh 'npm ci'
      }
    }

    stage('语法检查') {
      steps {
        sh '''
          npx prompt-ide lint prompts/ \
            --format json \
            --output lint-report.json \
            --max-warnings 0 \
            --max-errors 0
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'lint-report.json', allowEmptyArchive: true
        }
      }
    }

    stage('模板验证') {
      parallel {
        stage('格式验证') {
          steps {
            sh '''
              npx prompt-ide validate templates/ \
                --check-variables \
                --check-directives \
                --check-references \
                --strict
            '''
          }
        }
        stage('变量完整性') {
          steps {
            sh '''
              npx prompt-ide check-vars templates/ \
                --no-undefined-vars \
                --no-unused-vars \
                --consistent-naming snake_case
            '''
          }
        }
      }
    }

    stage('安全扫描') {
      steps {
        sh '''
          npx prompt-ide security-scan prompts/ \
            --check-pii \
            --check-secrets \
            --check-injection \
            --severity-threshold high
        '''
      }
    }

    stage('性能基准') {
      steps {
        sh '''
          npx prompt-ide benchmark prompts/ \
            --models gpt-4o,claude-3.5-sonnet,qwen-max \
            --max-tokens 4096 \
            --output benchmark-report.json
        '''
        sh '''
          npx prompt-ide regression-check \
            --baseline origin/main \
            --threshold 10%
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'benchmark-report.json', allowEmptyArchive: true
        }
      }
    }

    stage('执行测试') {
      matrix {
        axes {
          axis {
            name 'MODEL'
            values 'gpt-4o', 'gpt-4o-mini', 'claude-3.5-sonnet', 'qwen-max'
          }
        }
        stages {
          stage('测试') {
            steps {
              sh """
                npx prompt-ide test prompts/ \
                  --model ${MODEL} \
                  --timeout 30s \
                  --retry 3 \
                  --output test-results-${MODEL}.json
              """
            }
          }
        }
      }
    }

    stage('质量门禁') {
      steps {
        sh '''
          npx prompt-ide quality-gate \
            --min-score 21.00 \
            --max-std-dev 0.10 \
            --check-all-passed
        '''
      }
    }

    stage('构建发布包') {
      when {
        buildingTag()
      }
      steps {
        sh '''
          npx prompt-ide build \
            --version ${PROMPT_VERSION} \
            --output dist/
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'dist/**', allowEmptyArchive: true
        }
      }
    }

    stage('发布') {
      when {
        buildingTag()
      }
      steps {
        sh '''
          npx prompt-ide publish dist/ \
            --registry ${NPM_REGISTRY} \
            --token ${REGISTRY_TOKEN}
        '''
      }
    }
  }

  post {
    success {
      echo '提示词CI/CD流水线执行成功'
    }
    failure {
      echo '提示词CI/CD流水线执行失败'
      mail(
        to: 'team@example.com',
        subject: "提示词CI/CD失败: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
        body: "流水线执行失败，请检查: ${env.BUILD_URL}"
      )
    }
    always {
      cleanWs()
    }
  }
}
```

---

## 二、质量门禁详细定义

### 2.1 质量门禁规则

| 门禁项 | 阈值 | 级别 | 动作 |
|--------|------|------|------|
| 语法检查 | 0 error, 0 warning | 阻断 | 不通过则阻止合并 |
| 模板验证 | 100%通过 | 阻断 | 变量/指令/引用完整性 |
| 安全扫描 | 0 high/critical | 阻断 | PII/Secret/注入检测 |
| Token基准 | 不超基线10% | 警告 | Token消耗回归检测 |
| 延迟基准 | 不超基线20% | 警告 | P99延迟回归检测 |
| 均分 | ≥21.00 | 阻断 | 维度评分最低要求 |
| 标准差 | ≤0.10 | 阻断 | 维度均衡性要求 |
| 测试通过率 | 100% | 阻断 | 所有模型测试通过 |
| 兼容性 | 全模型兼容 | 阻断 | 多模型输出一致性 |

### 2.2 质量门禁配置

```yaml
# quality-gate.yml
gates:
  - name: syntax-check
    level: blocking
    rules:
      - metric: lint_errors
        operator: eq
        threshold: 0
      - metric: lint_warnings
        operator: eq
        threshold: 0

  - name: template-validation
    level: blocking
    rules:
      - metric: undefined_variables
        operator: eq
        threshold: 0
      - metric: unused_variables
        operator: eq
        threshold: 0
      - metric: broken_references
        operator: eq
        threshold: 0

  - name: security-scan
    level: blocking
    rules:
      - metric: high_severity_issues
        operator: eq
        threshold: 0
      - metric: critical_severity_issues
        operator: eq
        threshold: 0

  - name: performance-benchmark
    level: warning
    rules:
      - metric: token_regression_percent
        operator: lte
        threshold: 10
      - metric: latency_regression_percent
        operator: lte
        threshold: 20

  - name: dimension-score
    level: blocking
    rules:
      - metric: average_score
        operator: gte
        threshold: 21.00
      - metric: standard_deviation
        operator: lte
        threshold: 0.10

  - name: test-coverage
    level: blocking
    rules:
      - metric: test_pass_rate
        operator: eq
        threshold: 100
      - metric: model_compatibility
        operator: eq
        threshold: 100
```

---

## 三、环境管理策略

### 3.1 环境提升流程

```
dev → test → staging → prod
 ↓      ↓       ↓        ↓
自动    自动     手动审批   手动审批+灰度
```

### 3.2 环境配置对比

| 配置项 | dev | test | staging | prod |
|--------|-----|------|---------|------|
| 模型 | gpt-4o-mini | gpt-4o | gpt-4o | gpt-4o |
| temperature | 0.7 | 0.3 | 0.2 | 0.1 |
| max_tokens | 2048 | 4096 | 4096 | 4096 |
| 超时 | 30s | 60s | 60s | 120s |
| 日志级别 | debug | info | warn | error |
| 均分要求 | 19.00 | 20.00 | 20.50 | 21.00 |
| 标准差要求 | 0.50 | 0.20 | 0.10 | 0.05 |
| 自动部署 | push即部署 | PR合并即部署 | 手动审批 | 灰度→全量 |
| 回滚策略 | 自动回滚 | 自动回滚 | 手动回滚 | 手动回滚 |
| 监控 | 基础 | 标准 | 完整 | 完整+告警 |

### 3.3 灰度发布配置

```yaml
# canary-release.yml
strategy:
  type: canary
  steps:
    - setWeight: 10
      pause:
        duration: 5m
    - setWeight: 30
      pause:
        duration: 10m
    - setWeight: 50
      pause:
        duration: 15m
    - setWeight: 100
  analysis:
    metrics:
      - name: error_rate
        provider: prometheus
        query: "rate(http_errors_total{job='prompt-api'}[5m]) / rate(http_requests_total{job='prompt-api'}[5m])"
        threshold: 0.01
      - name: latency_p99
        provider: prometheus
        query: "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job='prompt-api'}[5m]))"
        threshold: 5.0
      - name: token_regression
        provider: custom
        query: "prompt_token_regression_ratio"
        threshold: 1.1
    rollback:
      automatic: true
      action: rollback
```

---

## 四、Q1总结

### Q1交付物清单

| # | 迭代 | 交付物 | 状态 |
|---|------|--------|------|
| 1 | Q1-01 | VS Code扩展架构设计 | ✓ |
| 2 | Q1-02 | 语法高亮（TextMate+3主题+语义Token） | ✓ |
| 3 | Q1-03 | 代码补全+10代码片段+Hover | ✓ |
| 4 | Q1-04 | 预览面板+Debug Adapter | ✓ |
| 5 | Q1-05 | JetBrains插件设计 | ✓ |
| 6 | Q1-06 | GitHub Actions+GitLab CI | ✓ |
| 7 | Q1-07 | Jenkins+质量门禁+环境管理 | ✓ |

---

## 五、验收项

- [x] Jenkins Declarative Pipeline完整模板
- [x] 8个Stage定义（初始化/语法/验证/安全/性能/测试/门禁/发布）
- [x] 多模型并行测试矩阵
- [x] 质量门禁6类规则（语法/验证/安全/性能/评分/测试）
- [x] 环境管理4级配置（dev/test/staging/prod）
- [x] 灰度发布策略（10%→30%→50%→100%）
- [x] 自动回滚配置
- [x] Q1全部7次迭代完成
