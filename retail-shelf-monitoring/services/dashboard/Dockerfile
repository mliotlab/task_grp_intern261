# Build context: retail-shelf-monitoring/
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN pip install "streamlit>=1.38" "pandas>=2.2" "httpx>=0.27"
COPY services/dashboard ./dashboard
RUN useradd --create-home appuser
USER appuser
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
