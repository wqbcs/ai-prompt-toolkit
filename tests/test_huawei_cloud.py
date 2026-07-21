"""huawei_cloud模块测试 — 华为云IAM/OBS/LTS深度集成"""

from __future__ import annotations

import os
import pytest

from ai_prompt_toolkit.huawei_cloud import (
    IAMCredential, OBSConfig, LTSConfig,
    AuditLogEntry, HuaweiCloudService, sign_request,
)


class TestIAMCredential:
    def test_from_env_missing(self):
        old = {k: os.environ.pop(k, None) for k in ["HW_ACCESS_KEY_ID", "HW_SECRET_ACCESS_KEY"]}
        try:
            cred = IAMCredential.from_env()
            assert cred.access_key_id == ""
            assert cred.is_valid() is False
        finally:
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v

    def test_is_valid_with_keys(self):
        cred = IAMCredential(access_key_id="AK123", secret_access_key="SK456")
        assert cred.is_valid() is True

    def test_default_region(self):
        cred = IAMCredential()
        assert cred.region == "cn-north-4"


class TestSignRequest:
    def test_sign_adds_headers(self):
        cred = IAMCredential(
            access_key_id="AKTEST", secret_access_key="SKTEST",
            region="cn-north-4",
        )
        headers = {"Content-Type": "application/json"}
        signed = sign_request("POST", "https://obs.cn-north-4.myhuaweicloud.com/bucket/key",
                              headers, "{}", cred)
        assert "Authorization" in signed
        assert "SDK-HMAC-SHA256" in signed["Authorization"]
        assert "X-Sdk-Date" in signed

    def test_sign_with_security_token(self):
        cred = IAMCredential(
            access_key_id="AK", secret_access_key="SK",
            security_token="TOKEN123", region="cn-north-4",
        )
        headers = {}
        signed = sign_request("GET", "https://example.com/api", headers, "", cred)
        assert "X-Security-Token" in signed
        assert signed["X-Security-Token"] == "TOKEN123"


class TestOBSConfig:
    def test_from_env_defaults(self):
        config = OBSConfig.from_env()
        assert config.region == "cn-north-4"
        assert config.prefix == "ai-prompt-toolkit/"

    def test_is_valid_without_bucket(self):
        config = OBSConfig()
        assert config.is_valid() is False

    def test_is_valid_with_bucket(self):
        config = OBSConfig(bucket_name="test-bucket", endpoint="obs.cn-north-4.myhuaweicloud.com")
        assert config.is_valid() is True


class TestLTSConfig:
    def test_from_env_defaults(self):
        config = LTSConfig.from_env()
        assert config.region == "cn-north-4"

    def test_is_valid_without_ids(self):
        config = LTSConfig()
        assert config.is_valid() is False

    def test_is_valid_with_ids(self):
        config = LTSConfig(log_group_id="group1", log_stream_id="stream1")
        assert config.is_valid() is True


class TestAuditLogEntry:
    def test_to_dict(self):
        entry = AuditLogEntry(
            action="lint.run", resource_type="template",
            resource_id="test.md", user="cli",
        )
        d = entry.to_dict()
        assert d["action"] == "lint.run"
        assert d["resource_type"] == "template"

    def test_to_lts_format(self):
        entry = AuditLogEntry(action="test")
        lts = entry.to_lts_format()
        assert "timestamp" in lts
        assert "content" in lts


class TestHuaweiCloudService:
    def test_is_configured_false(self):
        svc = HuaweiCloudService()
        assert svc.is_configured() is False

    def test_audit_log_creates_entry(self):
        svc = HuaweiCloudService()
        entry = svc.audit_log("lint.run", "template", "test.md")
        assert entry.action == "lint.run"
        assert len(svc._audit_buffer) == 1

    def test_audit_buffer_auto_flush(self):
        svc = HuaweiCloudService()
        for i in range(10):
            svc.audit_log(f"action.{i}")
        assert len(svc._audit_buffer) == 0

    def test_upload_to_obs_not_configured(self):
        svc = HuaweiCloudService()
        result = svc.upload_to_obs("test.md", "content")
        assert result is False

    def test_download_from_obs_not_configured(self):
        svc = HuaweiCloudService()
        result = svc.download_from_obs("test.md")
        assert result is None

    def test_get_service_status(self):
        svc = HuaweiCloudService()
        status = svc.get_service_status()
        assert "iam_configured" in status
        assert "obs_configured" in status
        assert "lts_configured" in status
        assert "region" in status
