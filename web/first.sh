#!/bin/sh
USERNAME=""
EMAIL=""
PASSWORD=""
CHANNEL_NAME=""
CHANNEL_URL=""
CATEGORY=""

python manage.py makemigrations && \
python manage.py migrate && \
python manage.py collectstatic -c --noinput && \
python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.create_superuser('${USERNAME}', '${EMAIL}', '${PASSWORD}') if not get_user_model().objects.all().filter(username='${USERNAME}').exists() else print('${USERNAME} exists.')" && \
python manage.py iptv -add channel --channel-name "${CHANNEL_NAME}" --channel-url "${CHANNEL_URL}" --category-name "${CATEGORY}" --create-category && \
python manage.py test && \
python manage.py daemon -restart && python manage.py daemon -status