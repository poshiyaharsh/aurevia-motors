#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "[Render Build] Installing Python dependencies..."
pip install -r requirements.txt

echo "[Render Build] Applying database migrations..."
python manage.py migrate --noinput

echo "[Render Build] Collecting and compressing static assets..."
python manage.py collectstatic --noinput --clear

echo "[Render Build] Synchronizing official marques and vouchers..."
python manage.py seed_marques
python manage.py seed_coupons

echo "[Render Build] Seeding 24 flagship hypercars with real studio photography..."
python manage.py seed_vehicles

# Optional auto-creation of administrator if environment variables are provided
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "[Render Build] Creating/verifying administrator account..."
    python manage.py createsuperuser --noinput || true
fi

echo "[Render Build] Build completed successfully!"
