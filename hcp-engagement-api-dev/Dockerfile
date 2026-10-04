FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so code changes don't invalidate the pip layer
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user; the app writes rotating logs to /app/logs
RUN useradd --create-home --uid 10001 appuser && mkdir -p logs && chown -R appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=4)" || exit 1

# One worker on purpose: socket sessions, stream state and rate limits live in process
# memory. Threads give concurrency; simple-websocket provides the WebSocket transport.
CMD ["gunicorn", "--worker-class", "gthread", "--workers", "1", "--threads", "100", \
     "--timeout", "120", "--bind", "0.0.0.0:5000", "app:app"]
