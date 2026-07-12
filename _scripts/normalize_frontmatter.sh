#!/bin/bash
# YAML Front Matter规范化脚本
# 版本: v1.0.0
# 日期: 2026-07-12
# 用法: bash _scripts/normalize_frontmatter.sh [--fix]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FIX_MODE=false

if [ "$1" = "--fix" ]; then
    FIX_MODE=true
    echo "=== Front Matter修复模式 ==="
else
    echo "=== Front Matter校验模式 ==="
fi

# 6个必需字段
REQUIRED_FIELDS=("version" "author" "updated_at" "tags" "applicable_models" "inheritance")

MISSING_COUNT=0
FIX_COUNT=0
TOTAL_COUNT=0

check_frontmatter() {
    local file="$1"
    local filename=$(basename "$file")
    TOTAL_COUNT=$((TOTAL_COUNT + 1))

    # 检查是否有YAML Front Matter
    if ! head -1 "$file" | grep -q "^---"; then
        echo "❌ 缺失Front Matter: $filename"
        MISSING_COUNT=$((MISSING_COUNT + 1))

        if [ "$FIX_MODE" = true ]; then
            local today=$(date +%Y-%m-%d)
            # 在文件开头插入Front Matter
            sed -i "1i---\nversion: \"1.0.0\"\nauthor: \"AI提示词体系\"\nupdated_at: \"${today}\"\ntags: []\napplicable_models: [gpt-4o, claude-3.5-sonnet, qwen-max, pangu-large]\ninheritance:\n  enabled: false\n---" "$file"
            echo "   ✅ 已自动添加Front Matter"
            FIX_COUNT=$((FIX_COUNT + 1))
        fi
        return
    fi

    # 检查各必需字段
    local has_all=true
    for field in "${REQUIRED_FIELDS[@]}"; do
        if ! grep -q "^${field}:" "$file"; then
            echo "⚠️  缺失字段 '${field}': $filename"
            has_all=false
            MISSING_COUNT=$((MISSING_COUNT + 1))
        fi
    done

    if [ "$has_all" = true ]; then
        echo "✅ Front Matter完整: $filename"
    fi

    # 检查标签规范化（小写、中划线连接）
    if grep -q "^tags:" "$file"; then
        local tags_line=$(grep "^tags:" "$file")
        if echo "$tags_line" | grep -qE '[A-Z]'; then
            echo "⚠️  标签含大写字母: $filename → 建议统一为小写"
        fi
        if echo "$tags_line" | grep -qE '_'; then
            echo "⚠️  标签含下划线: $filename → 建议使用中划线"
        fi
    fi
}

echo "扫描场景模板..."
find "$PROJECT_DIR/_scenarios" -name "*.md" -type f 2>/dev/null | while read -r file; do
    check_frontmatter "$file"
done

echo ""
echo "=== 检查完成 ==="
echo "总模板数: $TOTAL_COUNT"
echo "缺失项数: $MISSING_COUNT"
if [ "$FIX_MODE" = true ]; then
    echo "修复数: $FIX_COUNT"
fi
