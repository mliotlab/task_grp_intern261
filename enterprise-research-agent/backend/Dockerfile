# One image for the API service and both workers (different commands in docker-compose.yml).
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY workers ./workers
RUN pip install ".[ingest,llm]"

COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts

RUN useradd --create-home appuser && mkdir -p var/uploads && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
