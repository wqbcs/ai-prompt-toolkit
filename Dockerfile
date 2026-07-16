FROM python:3.12-slim

LABEL org.opencontainers.image.title="ai-prompt-toolkit"
LABEL org.opencontainers.image.description="AI提示词体系工具链：条件编译、安全扫描、A/B测试、Prompt Linter"

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
COPY README.md ./

RUN pip install --no-cache-dir ".[full]"

ENTRYPOINT ["prompt-cli"]
CMD ["--help"]
