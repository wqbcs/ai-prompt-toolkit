#!/bin/bash
# 华为云 CodeArts Buildkit 集成脚本
# 用法: 在CodeArts流水线的"执行Shell脚本"步骤中引用此文件

set -euo pipefail

echo "=== AI Prompt Toolkit — CodeArts Quality Gate ==="

# 安装工具链
pip install -e ".[full]" 2>/dev/null || pip install ai-prompt-toolkit[full]

PROMPT_DIR="${PROMPT_DIR:-prompts}"
GATE_MIN="${GATE_MIN:-60}"
EVAL_THRESHOLD="${EVAL_THRESHOLD:-6.0}"
FAIL_ON_CRITICAL="${FAIL_ON_CRITICAL:-true}"

EXIT_CODE=0

# 1. Lint检查
echo "--- Step 1: Prompt Lint ---"
if ! prompt-cli lint -t "$PROMPT_DIR" --gate --output lint-report.json; then
    echo "WARNING: Lint gate failed"
    EXIT_CODE=1
fi

# 2. 安全扫描
echo "--- Step 2: Security Scan ---"
if ! prompt-cli scan -t "$PROMPT_DIR" --output scan-report.json; then
    echo "WARNING: Security scan found issues"
    if [ "$FAIL_ON_CRITICAL" = "true" ]; then
        EXIT_CODE=2
    fi
fi

# 3. 质量评估
echo "--- Step 3: Quality Evaluate ---"
if ! prompt-cli evaluate -t "$PROMPT_DIR" --threshold "$EVAL_THRESHOLD" --save --output eval-report.json; then
    echo "WARNING: Quality below threshold"
    EXIT_CODE=3
fi

echo "=== Quality Gate Complete (exit: $EXIT_CODE) ==="
exit $EXIT_CODE
