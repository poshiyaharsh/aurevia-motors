#!/bin/sh
set -e

echo "[Aurevia Motors] Starting production deployment pipeline..."

# Run database migrations
echo "[Aurevia Motors] Applying database migrations..."
python manage.py migrate --noinput

# Collect static assets
echo "[Aurevia Motors] Collecting static assets..."
python manage.py collectstatic --noinput --clear

# Synchronize showcase catalog marques and coupons (idempotent)
echo "[Aurevia Motors] Synchronizing atelier catalog..."
python manage.py seed_marques
python manage.py seed_coupons

# Run production WSGI HTTP server
echo "[Aurevia Motors] Launching Gunicorn application server on port ${PORT:-8000}..."
exec gunicorn config.wsgi:application \
    --config gunicorn.conf.py \
    --bind 0.0.0.0:${PORT:-8000}
