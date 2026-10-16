FROM python:3.12-slim AS base

LABEL org.opencontainers.image.title="ai-prompt-toolkit"
LABEL org.opencontainers.image.description="AI提示词体系工具链：条件编译、安全扫描、A/B测试、Prompt Linter"

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
COPY README.md ./

RUN pip install --no-cache-dir ".[full]"

ENTRYPOINT ["prompt-cli"]
CMD ["--help"]

FROM base AS playground

# R306 深审 M-1: base 阶段 ENTRYPOINT ["prompt-cli"] 被继承后与下方 CMD
# 组合为 `prompt-cli uvicorn ...`(无此子命令), 裸 `docker run` 必坏且
# HEALTHCHECK 恒 unhealthy; CI smoke 显式传参恰好绕开。清空继承的
# ENTRYPOINT, 默认运行=启动 Playground 服务。
ENTRYPOINT []

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/version')" || exit 1

CMD ["uvicorn", "ai_prompt_toolkit.playground.server:app", "--host", "0.0.0.0", "--port", "8080"]
