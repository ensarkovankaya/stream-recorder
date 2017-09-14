#!/bin/sh
USERNAME="admin"
EMAIL="admin@admin.com"
PASSWORD="12345"

python manage.py makemigrations && \
python manage.py migrate && \
python manage.py collectstatic --clear --noinput && \
python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.create_superuser('${USERNAME}', '${EMAIL}', '${PASSWORD}')"