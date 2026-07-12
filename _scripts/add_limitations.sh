#!/bin/bash
# 已知限制章节检查与补充脚本
# 版本: v1.0.0
# 日期: 2026-07-12
# 用法: bash _scripts/add_limitations.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCENARIOS_DIR="$PROJECT_DIR/_scenarios"
LIMITATION_SECTION="## 已知限制"
MISSING_COUNT=0
UPDATED_COUNT=0
TOTAL_COUNT=0

echo "=== 已知限制章节检查 ==="
echo "扫描目录: $SCENARIOS_DIR"
echo ""

find "$SCENARIOS_DIR" -name "*.md" -type f | while read -r file; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    filename=$(basename "$file")

    if ! grep -q "$LIMITATION_SECTION" "$file"; then
        echo "❌ 缺失已知限制: $filename"
        MISSING_COUNT=$((MISSING_COUNT + 1))

        # 自动追加已知限制章节
        cat >> "$file" << 'LIMITATION_EOF'

## 已知限制

1. **模型兼容性限制**: 部分提示词指令仅在特定模型上表现最佳，其他模型可能需要调整指令格式
2. **场景覆盖限制**: 当前场景模板基于通用实践编写，特定行业可能需要额外定制
3. **评估主观性**: LLM-as-Judge评估存在一定主观性，建议结合人工审核
LIMITATION_EOF

        echo "   ✅ 已自动补充3条已知限制"
        UPDATED_COUNT=$((UPDATED_COUNT + 1))
    else
        # 检查已知限制条目数
        limit_count=$(grep -c "^- \*\*" "$file" 2>/dev/null || grep -c "^[0-9]\+\." "$file" 2>/dev/null || echo "0")
        if [ "$limit_count" -lt 3 ]; then
            echo "⚠️  已知限制不足3条($limit_count条): $filename"
        else
            echo "✅ 已知限制完整($limit_count条): $filename"
        fi
    fi
done

echo ""
echo "=== 检查完成 ==="
echo "总场景模板: $TOTAL_COUNT"
echo "缺失已补充: $UPDATED_COUNT"
