#!/bin/bash
# 外部链接快照存档脚本
# 版本: v1.0.0
# 日期: 2026-07-12
# 用法: bash _scripts/archive_external_links.sh [--check]
# 依赖: curl, jq

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CHECK_ONLY=false

if [ "$1" = "--check" ]; then
    CHECK_ONLY=true
fi

echo "=== 外部链接快照存档 ==="

EXTERNAL_LINK_COUNT=0
ARCHIVED_COUNT=0
NO_ARCHIVE_COUNT=0

# Wayback Machine API
WAYBACK_API="https://archive.org/wayback/available"

# 提取所有外部链接
extract_links() {
    find "$PROJECT_DIR" -name "*.md" -type f -exec grep -oP 'https?://[^\s\)\]>"]+' {} \; | sort -u
}

check_archive() {
    local url="$1"
    local encoded_url=$(echo "$url" | curl -s -o /dev/null -w '%{url_effective}' --data-urlencode "url=$url" "" 2>/dev/null || echo "$url")

    local response=$(curl -s "${WAYBACK_API}?url=${url}" 2>/dev/null || echo '{}')

    if echo "$response" | jq -e '.archived_snapshots.closest' >/dev/null 2>&1; then
        local archive_url=$(echo "$response" | jq -r '.archived_snapshots.closest.url')
        echo "$archive_url"
    else
        echo ""
    fi
}

echo "扫描外部链接..."
links=$(extract_links)
EXTERNAL_LINK_COUNT=$(echo "$links" | grep -c "." || echo "0")

echo "发现 $EXTERNAL_LINK_COUNT 个外部链接"

if [ "$CHECK_ONLY" = true ]; then
    echo ""
    echo "仅检查模式，不修改文件"
    echo "链接列表:"
    echo "$links" | head -20
    if [ "$EXTERNAL_LINK_COUNT" -gt 20 ]; then
        echo "... (共$EXTERNAL_LINK_COUNT个)"
    fi
    exit 0
fi

echo ""
echo "注意: 完整存档需要逐个查询Wayback Machine API"
echo "建议: 对新增链接在提交时添加存档标注"
echo ""
echo "存档格式规范:"
echo "  [原文链接](url) [存档](archive-url)"
echo "  [原文链接](url) [无存档]"
echo ""
echo "=== 检查完成 ==="
