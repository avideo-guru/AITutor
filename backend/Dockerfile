FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cloud Run injects $PORT (defaults to 8080). Honor it — a hardcoded port
# fails health checks if the platform ever changes the default. Shell form +
# `exec` so uvicorn is PID 1 and receives Cloud Run's SIGTERM for graceful
# shutdown (drains in-flight SSE streams instead of being killed).
EXPOSE 8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
