# Build context: customer-support-agent/
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY support_agent ./support_agent
COPY services ./services
RUN pip install ".[llm]"

COPY configs ./configs
COPY prompts ./prompts
COPY kb ./kb

RUN useradd --create-home appuser && mkdir -p var && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "services.chat_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
