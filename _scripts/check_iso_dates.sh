#!/bin/bash
# ISO 8601日期格式校验与替换脚本
# 版本: v1.0.0
# 日期: 2026-07-12
# 用法: bash _scripts/check_iso_dates.sh [--fix]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FIX_MODE=false

if [ "$1" = "--fix" ]; then
    FIX_MODE=true
    echo "=== ISO 8601日期修复模式 ==="
else
    echo "=== ISO 8601日期校验模式 ==="
fi

ERROR_COUNT=0
FIX_COUNT=0

# 非ISO日期格式模式
# YYYY年MM月DD日 → YYYY-MM-DD
# YYYY/MM/DD → YYYY-MM-DD
# MM-DD-YYYY → YYYY-MM-DD
# DD/MM/YYYY → YYYY-MM-DD (谨慎处理)

check_dates() {
    local file="$1"
    local filename=$(basename "$file")

    # 检查中文日期格式: 2026年5月28日
    if grep -qE '[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日' "$file"; then
        echo "❌ 中文日期格式: $filename"
        ERROR_COUNT=$((ERROR_COUNT + 1))

        if [ "$FIX_MODE" = true ]; then
            # 替换中文日期为ISO格式
            sed -i -E 's/([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日/\1-\2-\3/g' "$file"
            # 补零: 2026-5-28 → 2026-05-28
            sed -i -E 's/([0-9]{4})-([0-9])-([0-9]{1,2})/\1-0\2-\3/g' "$file"
            sed -i -E 's/([0-9]{4})-([0-9]{2})-([0-9]) /\1-\2-0\3 /g' "$file"
            echo "   ✅ 已修复为ISO格式"
            FIX_COUNT=$((FIX_COUNT + 1))
        fi
    fi

    # 检查 YYYY/MM/DD 格式
    if grep -qE '[0-9]{4}/[0-9]{2}/[0-9]{2}' "$file"; then
        echo "⚠️  斜杠日期格式: $filename (可能为URL路径，需人工确认)"
    fi

    # 检查 updated_at 字段是否为ISO格式
    if grep -q "updated_at:" "$file"; then
        updated_at=$(grep "updated_at:" "$file" | head -1 | sed 's/.*updated_at:[[:space:]]*//' | tr -d '"'"'")
        if ! echo "$updated_at" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}'; then
            echo "❌ updated_at非ISO格式: $filename → '$updated_at'"
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
    fi
}

echo ""
echo "扫描所有Markdown文件..."
find "$PROJECT_DIR" -name "*.md" -type f | while read -r file; do
    check_dates "$file"
done

echo ""
echo "=== 检查完成 ==="
echo "错误数: $ERROR_COUNT"
if [ "$FIX_MODE" = true ]; then
    echo "修复数: $FIX_COUNT"
fi
