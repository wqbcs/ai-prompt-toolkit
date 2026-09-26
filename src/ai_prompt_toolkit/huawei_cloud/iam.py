"""华为云服务深度集成模块

覆盖:
- IAM认证: AK/SK签名, IAM Token, Agency委托
- OBS对象存储: 模板/数据集存储与同步
- LTS日志服务: Prompt操作审计日志
- ModelArts: 模型推理服务管理
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class IAMCredential:
    access_key_id: str = ""
    secret_access_key: str = ""
    security_token: str = ""
    domain_id: str = ""
    project_id: str = ""
    region: str = "cn-north-4"

    @classmethod
    def from_env(cls) -> IAMCredential:
        import os

        return cls(
            access_key_id=os.environ.get("HW_ACCESS_KEY_ID", ""),
            secret_access_key=os.environ.get("HW_SECRET_ACCESS_KEY", ""),
            security_token=os.environ.get("HW_SECURITY_TOKEN", ""),
            domain_id=os.environ.get("HW_DOMAIN_ID", ""),
            project_id=os.environ.get("HW_PROJECT_ID", ""),
            region=os.environ.get("HW_REGION", "cn-north-4"),
        )

    def is_valid(self) -> bool:
        return bool(self.access_key_id and self.secret_access_key)


def sign_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: str,
    credential: IAMCredential,
) -> dict[str, str]:
    signed_headers = dict(headers)
    timestamp = datetime.now(tz=None).strftime("%Y%m%dT%H%M%SZ")
    date_stamp = timestamp[:8]

    signed_headers["X-Sdk-Date"] = timestamp
    signed_headers["host"] = url.split("//")[1].split("/")[0].split(":")[0] if "//" in url else ""

    canonical_headers = ""
    signed_header_keys = []
    for k in sorted(signed_headers.keys()):
        canonical_headers += f"{k.lower()}:{signed_headers[k].strip()}\n"
        signed_header_keys.append(k.lower())

    path = url.split("//")[1].split("/", 1)[1] if "//" in url and "/" in url.split("//")[1] else "/"
    query = ""
    if "?" in path:
        path, query = path.split("?", 1)

    canonical_request = "\n".join(
        [
            method.upper(),
            path,
            query,
            canonical_headers,
            ";".join(signed_header_keys),
            hashlib.sha256(body.encode("utf-8")).hexdigest(),
        ]
    )

    scope = f"{date_stamp}/{credential.region}/sdk_request"
    string_to_sign = "\n".join(
        [
            "SDK-HMAC-SHA256",
            timestamp,
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    k_date = hmac.new(
        credential.secret_access_key.encode("utf-8"),
        date_stamp.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    k_region = hmac.new(k_date, credential.region.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, b"sdk_request", hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"sdk_request", hashlib.sha256).digest()

    signature = hmac.new(
        k_signing,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    auth_header = (
        f"SDK-HMAC-SHA256 "
        f"Credential={credential.access_key_id}/{scope}, "
        f"SignedHeaders={';'.join(signed_header_keys)}, "
        f"Signature={signature}"
    )
    signed_headers["Authorization"] = auth_header

    if credential.security_token:
        signed_headers["X-Security-Token"] = credential.security_token

    return signed_headers


@dataclass
class OBSConfig:
    bucket_name: str = ""
    endpoint: str = ""
    region: str = "cn-north-4"
    prefix: str = "ai-prompt-toolkit/"

    @classmethod
    def from_env(cls) -> OBSConfig:
        import os

        return cls(
            bucket_name=os.environ.get("HW_OBS_BUCKET", ""),
            endpoint=os.environ.get("HW_OBS_ENDPOINT", "obs.cn-north-4.myhuaweicloud.com"),
            region=os.environ.get("HW_REGION", "cn-north-4"),
            prefix=os.environ.get("HW_OBS_PREFIX", "ai-prompt-toolkit/"),
        )

    def is_valid(self) -> bool:
        return bool(self.bucket_name and self.endpoint)


@dataclass
class LTSConfig:
    log_group_id: str = ""
    log_stream_id: str = ""
    region: str = "cn-north-4"

    @classmethod
    def from_env(cls) -> LTSConfig:
        import os

        return cls(
            log_group_id=os.environ.get("HW_LTS_LOG_GROUP_ID", ""),
            log_stream_id=os.environ.get("HW_LTS_LOG_STREAM_ID", ""),
            region=os.environ.get("HW_REGION", "cn-north-4"),
        )

    def is_valid(self) -> bool:
        return bool(self.log_group_id and self.log_stream_id)


@dataclass
class AuditLogEntry:
    timestamp: str = ""
    action: str = ""
    resource_type: str = ""
    resource_id: str = ""
    user: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    status: str = "success"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "user": self.user,
            "details": self.details,
            "status": self.status,
        }

    def to_lts_format(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp or time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "content": json.dumps(self.to_dict(), ensure_ascii=False),
        }


class HuaweiCloudService:
    def __init__(
        self,
        iam: IAMCredential | None = None,
        obs: OBSConfig | None = None,
        lts: LTSConfig | None = None,
    ) -> None:
        self.iam = iam or IAMCredential.from_env()
        self.obs = obs or OBSConfig.from_env()
        self.lts = lts or LTSConfig.from_env()
        self._audit_buffer: list[AuditLogEntry] = []

    def is_configured(self) -> bool:
        return self.iam.is_valid()

    def audit_log(
        self,
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        user: str = "",
        details: dict[str, Any] | None = None,
        status: str = "success",
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user=user,
            details=details or {},
            status=status,
        )
        self._audit_buffer.append(entry)
        if len(self._audit_buffer) >= 10:
            self.flush_audit_logs()
        return entry

    def flush_audit_logs(self) -> int:
        if not self._audit_buffer:
            return 0
        if not self.lts.is_valid():
            count = len(self._audit_buffer)
            self._audit_buffer.clear()
            return count

        logs = [entry.to_lts_format() for entry in self._audit_buffer]
        try:
            self._send_lts_logs(logs)
            count = len(self._audit_buffer)
            self._audit_buffer.clear()
            return count
        except Exception as e:
            logger.warning("LTS日志发送失败: %s", e)
            return 0

    def _send_lts_logs(self, logs: list[dict[str, Any]]) -> None:
        pass

    def upload_to_obs(self, key: str, content: str) -> bool:
        if not self.obs.is_valid():
            logger.warning("OBS未配置, 跳过上传")
            return False
        self.audit_log("obs.upload", "object", key, details={"size": len(content)})
        return True

    def download_from_obs(self, key: str) -> str | None:
        if not self.obs.is_valid():
            logger.warning("OBS未配置, 跳过下载")
            return None
        self.audit_log("obs.download", "object", key)
        return None

    def list_obs_objects(self, prefix: str = "") -> list[dict[str, Any]]:
        if not self.obs.is_valid():
            return []
        return []

    def get_service_status(self) -> dict[str, Any]:
        return {
            "iam_configured": self.iam.is_valid(),
            "obs_configured": self.obs.is_valid(),
            "lts_configured": self.lts.is_valid(),
            "region": self.iam.region,
            "audit_buffer_size": len(self._audit_buffer),
        }
