web: python manage.py runserver 0.0.0.0:8218
worker: celery -A myweb worker -l info
beat: celery -A myweb beat -l info