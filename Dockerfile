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

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/version')" || exit 1

CMD ["uvicorn", "ai_prompt_toolkit.playground.server:app", "--host", "0.0.0.0", "--port", "8080"]
