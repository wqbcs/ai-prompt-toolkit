# 沙箱实现方案

> 版本：v1.0 | 日期：2026-05-29

---

## 1. 沙箱架构

```
┌───────────────────────────────────────────────┐
│                Sandbox Shell                   │
├───────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │ Process     │  │ Resource    │  │Network │ │
│  │ Isolation   │  │ Limiter     │  │Filter  │ │
│  └─────────────┘  └─────────────┘  └────────┘ │
├───────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │ Output      │  │ Filesystem  │  │Signal  │ │
│  │ Filter      │  │ Sandbox     │  │Handler │ │
│  └─────────────┘  └─────────────┘  └────────┘ │
└───────────────────────────────────────────────┘
```

## 2. 沙箱配置

```python
from dataclasses import dataclass

@dataclass
class SandboxConfig:
    # 进程隔离
    isolated_process: bool = True
    user_namespace: bool = True        # Linux user namespace
    pid_namespace: bool = True         # PID namespace
    mount_namespace: bool = True       # Mount namespace

    # 资源限制
    max_memory_mb: int = 512           # 最大内存
    max_cpu_percent: float = 80.0      # 最大CPU使用率
    max_execution_time_ms: int = 30000 # 最大执行时间
    max_output_size_kb: int = 1024     # 最大输出大小
    max_file_descriptors: int = 64     # 最大文件描述符数

    # 网络白名单
    network_whitelist: list[str] = None  # 允许的网络访问
    network_deny_all: bool = True      # 默认拒绝所有网络

    # 输出过滤
    output_filter_patterns: list[str] = None  # 输出过滤正则
    sanitize_html: bool = True         # HTML消毒
    sanitize_code: bool = False        # 代码消毒(默认关)

    # 文件系统
    read_only_paths: list[str] = None  # 只读路径
    writable_paths: list[str] = None   # 可写路径
    temp_dir: str = "/tmp/sandbox"     # 临时目录

    # 审计
    audit_log: bool = True             # 审计日志
    audit_log_path: str = "/var/log/sandbox/audit.log"
```

## 3. SandboxExecutor实现

```python
import subprocess
import tempfile
import signal
import resource
import re
import json
import os
from typing import Callable, Optional

class SandboxExecutor:
    def __init__(self, config: SandboxConfig):
        self.config = config
        self._audit_log = []

    def execute(self, prompt: str, llm: Callable) -> str:
        audit_entry = {
            "action": "execute",
            "timestamp": self._now(),
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
        }

        try:
            # 1. 预检查：输入验证
            self._validate_input(prompt)

            # 2. 创建隔离环境
            with self._create_sandbox_env() as env:
                # 3. 执行LLM调用(受资源限制)
                raw_output = self._execute_with_limits(
                    lambda: llm(prompt), env
                )

            # 4. 输出过滤
            filtered_output = self._filter_output(raw_output)

            # 5. 审计记录
            audit_entry["status"] = "success"
            audit_entry["output_size"] = len(filtered_output)
            self._audit(audit_entry)

            return filtered_output

        except SandboxViolation as e:
            audit_entry["status"] = "violation"
            audit_entry["violation"] = str(e)
            self._audit(audit_entry)
            raise
        except Exception as e:
            audit_entry["status"] = "error"
            audit_entry["error"] = str(e)
            self._audit(audit_entry)
            raise

    def _validate_input(self, prompt: str) -> None:
        if len(prompt) > 100000:
            raise SandboxViolation("Input exceeds maximum size")
        dangerous = [r"__import__", r"eval\(", r"exec\(", r"subprocess",
                     r"os\.system", r"rm\s+-rf"]
        for pattern in dangerous:
            if re.search(pattern, prompt):
                raise SandboxViolation(f"Dangerous pattern detected: {pattern}")

    def _execute_with_limits(self, fn: Callable, env: dict) -> str:
        import threading
        result = [None]
        error = [None]

        def worker():
            try:
                result[0] = fn()
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=self.config.max_execution_time_ms / 1000.0)

        if thread.is_alive():
            raise SandboxTimeout("Execution timed out")
        if error[0]:
            raise error[0]

        output = str(result[0])
        if len(output) > self.config.max_output_size_kb * 1024:
            raise SandboxViolation("Output exceeds maximum size")
        return output

    def _filter_output(self, output: str) -> str:
        if self.config.output_filter_patterns:
            for pattern in self.config.output_filter_patterns:
                output = re.sub(pattern, "[FILTERED]", output)
        if self.config.sanitize_html:
            output = self._sanitize_html(output)
        return output

    def _sanitize_html(self, text: str) -> str:
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'on\w+="[^"]*"', '', text, flags=re.IGNORECASE)
        return text

    @contextmanager
    def _create_sandbox_env(self):
        env = {}
        if self.config.audit_log:
            env["AUDIT_LOG"] = self.config.audit_log_path
        yield env

    def _audit(self, entry: dict) -> None:
        if self.config.audit_log:
            self._audit_log.append(entry)

    @staticmethod
    def _now() -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()


class SandboxViolation(Exception):
    pass

class SandboxTimeout(SandboxViolation):
    pass
```

## 4. 网络白名单过滤

```python
class NetworkFilter:
    def __init__(self, whitelist: list[str], deny_all: bool = True):
        self.whitelist = [self._parse_url(u) for u in (whitelist or [])]
        self.deny_all = deny_all

    def is_allowed(self, url: str) -> bool:
        if self.deny_all and not self.whitelist:
            return False
        parsed = self._parse_url(url)
        for allowed in self.whitelist:
            if parsed["host"].endswith(allowed["host"]):
                return True
        return False

    def _parse_url(self, url: str) -> dict:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return {"host": parsed.hostname or url, "port": parsed.port}
```

## 5. 安全等级

| 等级 | 配置 | 适用场景 |
|------|------|---------|
| STRICT | 隔离进程+512MB内存+30s超时+无网络+输出过滤 | 生产环境 |
| MODERATE | 隔离进程+1GB内存+60s超时+白名单网络 | 开发环境 |
| PERMISSIVE | 无隔离+2GB内存+300s超时+全网络 | 测试环境 |
