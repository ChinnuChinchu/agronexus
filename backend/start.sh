#!/bin/sh
set -e

python -m scripts.wait_for_db

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