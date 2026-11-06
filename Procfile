web: gunicorn config.wsgi:application --config gunicorn.conf.py --bind 0.0.0.0:$PORT
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py seed_marques && python manage.py seed_coupons
