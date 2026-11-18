# Build context: customer-support-agent/
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY support_agent ./support_agent
COPY services ./services
COPY scripts ./scripts
RUN pip install . \
 && useradd --create-home appuser && mkdir -p var && chown -R appuser /app
USER appuser

# Synthetic orders are generated at build time; no real customer data is ever used.
RUN python scripts/generate_orders.py --n 100 --seed 42 --out var/orders.json

EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"
CMD ["uvicorn", "services.order_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
