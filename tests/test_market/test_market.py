"""模板市场v2单元测试"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ai_prompt_toolkit.market.deploy import DeployManager
from ai_prompt_toolkit.market.review import ReviewPipeline
from ai_prompt_toolkit.market.service import MarketService
from ai_prompt_toolkit.market.types import (
    DeployPhase,
    LifecycleManager,
    Review,
    Template,
    TemplateStatus,
)


class TestLifecycleManager:
    def test_valid_transition(self):
        mgr = LifecycleManager()
        tpl = Template(id="t1", name="test", version="1.0", security_scan_passed=True)
        tpl = mgr.transition(tpl, TemplateStatus.REVIEW)
        assert tpl.status == TemplateStatus.REVIEW

    def test_invalid_transition(self):
        mgr = LifecycleManager()
        tpl = Template(id="t1", name="test", version="1.0", status=TemplateStatus.STABLE)
        with pytest.raises(ValueError, match="无效状态转换"):
            mgr.transition(tpl, TemplateStatus.DRAFT)

    def test_no_scan_no_publish(self):
        mgr = LifecycleManager()
        tpl = Template(id="t1", name="test", version="1.0", status=TemplateStatus.REVIEW, security_scan_passed=False)
        with pytest.raises(ValueError, match="安全扫描未通过"):
            mgr.transition(tpl, TemplateStatus.CANARY)

    def test_cannot_delete_review(self):
        mgr = LifecycleManager()
        tpl = Template(id="t1", name="test", version="1.0", status=TemplateStatus.REVIEW)
        assert not mgr.can_delete(tpl)

    def test_can_delete_draft(self):
        mgr = LifecycleManager()
        tpl = Template(id="t1", name="test", version="1.0", status=TemplateStatus.DRAFT)
        assert mgr.can_delete(tpl)


class TestReviewPipeline:
    def test_start_review(self):
        pipeline = ReviewPipeline()
        tpl = Template(id="t1", name="test", version="1.0", security_scan_passed=True)
        pipeline.start_review(tpl)
        assert tpl.status == TemplateStatus.REVIEW

    def test_gate_pass(self):
        pipeline = ReviewPipeline()
        tpl = Template(id="t1", name="test", version="1.0", security_scan_passed=True)
        pipeline.start_review(tpl)
        pipeline.submit_review("t1", Review(reviewer="alice", approved=True, score=4.5))
        gate = pipeline.check_gate(tpl)
        assert gate["passed"]

    def test_gate_fail_no_scan(self):
        pipeline = ReviewPipeline()
        tpl = Template(id="t1", name="test", version="1.0", security_scan_passed=False)
        gate = pipeline.check_gate(tpl)
        assert not gate["passed"]

    def test_gate_fail_low_score(self):
        pipeline = ReviewPipeline()
        tpl = Template(id="t1", name="test", version="1.0", security_scan_passed=True)
        pipeline.start_review(tpl)
        pipeline.submit_review("t1", Review(reviewer="bob", approved=True, score=2.0))
        gate = pipeline.check_gate(tpl)
        assert not gate["score_threshold"]


class TestDeployManager:
    def test_start_canary(self):
        dm = DeployManager()
        tpl = Template(id="t1", name="test", version="1.0", status=TemplateStatus.REVIEW, security_scan_passed=True)
        config = dm.start_canary(tpl, baseline_score=80.0)
        assert config.phase == DeployPhase.P5

    def test_promote(self):
        dm = DeployManager()
        tpl = Template(id="t1", name="test", version="1.0", status=TemplateStatus.REVIEW, security_scan_passed=True)
        config = dm.start_canary(tpl, baseline_score=80.0)
        assert config.phase == DeployPhase.P5
        tpl.status = TemplateStatus.CANARY
        config = dm.promote(tpl, canary_score=90.0)
        assert config.phase == DeployPhase.P25

    def test_auto_rollback(self):
        dm = DeployManager()
        tpl = Template(id="t1", name="test", version="1.0", status=TemplateStatus.REVIEW, security_scan_passed=True)
        config = dm.start_canary(tpl, baseline_score=100.0)
        tpl.status = TemplateStatus.CANARY
        config = dm.promote(tpl, canary_score=70.0)
        assert tpl.status == TemplateStatus.DRAFT


class TestMarketService:
    def test_submit_and_query(self):
        with tempfile.TemporaryDirectory() as td:
            svc = MarketService(data_dir=td)
            tpl = Template(id="svc-1", name="test", version="1.0")
            svc.submit(tpl)
            result = svc.query("svc-1")
            assert result is not None
            assert result.name == "test"

    def test_submit_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            svc = MarketService(data_dir=td)
            tpl = Template(id="dup-1", name="test", version="1.0")
            svc.submit(tpl)
            with pytest.raises(ValueError, match="已存在"):
                svc.submit(tpl)

    def test_full_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            svc = MarketService(data_dir=td)
            tpl = Template(id="life-1", name="lifecycle test", version="1.0", security_scan_passed=True)
            svc.submit(tpl)
            svc.start_review("life-1")
            svc.submit_review("life-1", Review(reviewer="alice", approved=True, score=4.5))
            config = svc.start_deploy("life-1", baseline_score=80.0)
            assert config.phase == DeployPhase.P5
            config = svc.promote_deploy("life-1", canary_score=90.0)
            status = svc.get_status("life-1")
            assert "deploy" in status
