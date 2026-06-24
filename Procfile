release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn exam_portal.wsgi --log-file -
