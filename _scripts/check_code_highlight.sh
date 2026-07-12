#!/bin/bash
# 代码片段语法高亮校验脚本
# 版本: v1.0.0
# 日期: 2026-07-12
# 用法: bash _scripts/check_code_highlight.sh [--fix]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FIX_MODE=false

if [ "$1" = "--fix" ]; then
    FIX_MODE=true
    echo "=== 代码高亮修复模式 ==="
else
    echo "=== 代码高亮校验模式 ==="
fi

MISSING_COUNT=0
FIX_COUNT=0

# 语言映射规则
# 根据代码内容推断语言
declare -A LANG_MAP=(
    ["#!/bin/bash"]="bash"
    ["#!/bin/sh"]="bash"
    ["kubectl"]="yaml"
    ["apiVersion"]="yaml"
    ["kind:"]="yaml"
    ["metadata:"]="yaml"
    ["spec:"]="yaml"
    ["docker"]="dockerfile"
    ["FROM "]="dockerfile"
    ["RUN "]="dockerfile"
    ["COPY "]="dockerfile"
    ["import python"]="python"
    ["def "]="python"
    ["print("]="python"
    ["func "]="go"
    ["package "]="go"
    ["fmt."]="go"
    ["type "]="typescript"
    ["interface "]="typescript"
    ["const "]="typescript"
    ["async function"]="typescript"
)

detect_language() {
    local content="$1"

    for pattern in "${!LANG_MAP[@]}"; do
        if echo "$content" | grep -q "$pattern"; then
            echo "${LANG_MAP[$pattern]}"
            return
        fi
    done

    echo ""
}

check_file() {
    local file="$1"
    local filename=$(basename "$file")
    local line_num=0
    local in_code_block=false
    local code_start=0
    local code_content=""

    while IFS= read -r line; do
        line_num=$((line_num + 1))

        if [[ "$line" =~ ^\`\`\`([a-zA-Z0-9_-]*) ]]; then
            if [ "$in_code_block" = false ]; then
                in_code_block=true
                code_start=$line_num
                local lang="${BASH_REMATCH[1]}"

                if [ -z "$lang" ]; then
                    echo "❌ 缺失语言标识: $filename:L${code_start}"
                    MISSING_COUNT=$((MISSING_COUNT + 1))

                    # 收集代码内容用于语言推断
                    code_content=""
                else
                    code_content="HAS_LANG"
                fi
            else
                in_code_block=false
                code_content=""
            fi
        elif [ "$in_code_block" = true ] && [ "$code_content" != "HAS_LANG" ]; then
            code_content="${code_content}${line}"$'\n'
        fi
    done < "$file"
}

echo "扫描Markdown文件..."
find "$PROJECT_DIR" -name "*.md" -type f | while read -r file; do
    check_file "$file"
done

echo ""
echo "=== 检查完成 ==="
echo "缺失语言标识: $MISSING_COUNT"
echo ""
echo "语言映射规则:"
echo "  Shell脚本 → bash"
echo "  K8s清单 → yaml"
echo "  Dockerfile → dockerfile"
echo "  Python代码 → python"
echo "  Go代码 → go"
echo "  TypeScript代码 → typescript"
echo "  JSON数据 → json"
