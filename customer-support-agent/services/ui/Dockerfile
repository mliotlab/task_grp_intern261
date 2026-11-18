# Build context: customer-support-agent/
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN pip install "streamlit>=1.38" "httpx>=0.27"
COPY services/ui ./ui
RUN useradd --create-home appuser
USER appuser
EXPOSE 8501
CMD ["streamlit", "run", "ui/chat_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
