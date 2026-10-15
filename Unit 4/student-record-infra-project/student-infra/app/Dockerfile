FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 DB_PATH=/data/students.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN useradd -m -u 1000 appuser && mkdir -p /data && chown -R appuser:appuser /app /data
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:8080", "app:app"]
