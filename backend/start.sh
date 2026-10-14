#!/bin/sh
set -e

echo "Waiting for the database..."
tries=0
until python -c "from sqlalchemy import create_engine; from app.core.config import settings; create_engine(settings.DATABASE_URL).connect().close()" 2>/dev/null; do
  tries=$((tries + 1))
  if [ "$tries" -ge 30 ]; then
    echo "The database is not reachable. Giving up."
    exit 1
  fi
  sleep 2
done

echo "Applying database migrations..."
alembic upgrade head

echo "Seeding the crop catalog..."
python -m app.db.seed

if [ "${RUN_NETWORK_PROBE:-0}" = "1" ]; then
  echo "Running the network probe..."
  python -m scripts.net_probe || true
fi

echo "Starting the API on port ${PORT:-8000}..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips='*'
  