# Backend: Flask API

Flask + Flask-RESTX API for the HCP Engagement platform. See the [root README](../README.md) for the full setup, architecture and API reference.

## Run locally (Python 3.11)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set GROQ_API_KEY, SECRET_KEY, JWT_SECRET_KEY
python3 app.py         # http://localhost:5000, Swagger UI at /docs/
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite runs offline: Groq is replaced by a local fake server that streams server-sent events (both chunked and connection-delimited), and PubMed is stubbed.

## Layout

| Path | Purpose |
|---|---|
| `app.py` | API, auth, Groq/PubMed integration, Socket.IO streaming |
| `tests/` | Automated pytest suite |
| `scripts/` | Manual smoke checks against a running server (`python3 scripts/test_api.py`) |
| `Dockerfile` | Production image (Gunicorn, non-root, health check) |
