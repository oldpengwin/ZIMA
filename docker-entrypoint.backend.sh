#!/bin/sh
# Entrypoint for the backend container: run pending migrations before the
# app starts serving traffic, instead of expecting whoever deploys this to
# remember to run `alembic upgrade head` by hand. Fails loudly (non-zero
# exit, container won't come up) if migrations fail — starting the API
# against a schema it doesn't match is worse than not starting at all.
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting API server..."
exec gunicorn src.main:app \
    --workers "${GUNICORN_WORKERS:-4}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${API_PORT:-8000}" \
    --access-logfile - \
    --error-logfile -
