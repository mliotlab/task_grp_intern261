# Build context: retail-shelf-monitoring/
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# WITH_ML=1 installs CPU-only PyTorch + Ultralytics (~1 GB). CI builds with WITH_ML=0 for speed.
ARG WITH_ML=1
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*
RUN if [ "$WITH_ML" = "1" ]; then \
      pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    fi

COPY pyproject.toml README.md ./
COPY shelfmon ./shelfmon
COPY services ./services
RUN if [ "$WITH_ML" = "1" ]; then pip install ".[ml]"; else pip install .; fi

RUN useradd --create-home appuser && mkdir -p var/images models && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
