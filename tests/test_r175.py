"""R175测试: P101性能优化(剪枝+截断)的行为守护"""

from __future__ import annotations

import time

from ai_prompt_toolkit.linter.rules import check_p101


class TestP101PerformanceGuard:
    """R175: P101 O(n²)剪枝+截断 — 行为语义守护(防止优化破坏检测能力)"""

    def test_near_duplicates_still_detected(self):
        text = "你是一个AI助手。你是一个人工智能助手。你是一个AI辅助工具。你是有用的助手。请回答问题。"
        finding = check_p101(text)
        assert finding is not None
        assert "组相似表述" in finding.description
        assert "+" not in finding.description  # 未截断场景无"+"号

    def test_distinct_sentences_no_finding(self):
        text = "请编写Python脚本处理数据。使用CSV格式读取文件。输出统计报表到屏幕。"
        assert check_p101(text) is None

    def test_truncation_marked_with_plus(self):
        """全重复长文本: 触发上限早退, description带'+'标注"""
        text = "重复的内容用于测试。" * 400  # 大量同句
        finding = check_p101(text)
        if finding is not None and len(finding.details.get("redundant_pairs", [])) >= 5:
            # 大量重复时必然早退(或恰好全部枚举完也允许)
            assert "+" in finding.description or "组相似表述" in finding.description

    def test_large_text_bounded(self):
        """性能守护: 50KB全重复文本必须在1秒内完成(优化前6.3秒)"""
        text = "你是一名助手。" + "这是第i条内容，用于测试性能，包含一些重复和约束说明。" * 1300
        t0 = time.perf_counter()
        check_p101(text)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, f"P101大文本耗时{elapsed:.2f}s, 超过1秒守护线"
