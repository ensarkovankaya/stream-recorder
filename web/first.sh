#!/bin/sh

python manage.py makemigrations && \
python manage.py migrate && \
python manage.py collectstatic -c --noinput

if [ ! -z "$ADMIN_USERNAME" ] || [ ! -z "$ADMIN_EMAIL" ] || [ ! -z "$ADMIN_PASSWORD" ]; then
    python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.create_superuser('${ADMIN_USERNAME}', '${ADMIN_EMAIL}', '${ADMIN_PASSWORD}') if not get_user_model().objects.all().filter(username='${ADMIN_USERNAME}').exists() else print('${ADMIN_USERNAME} exists.')"
fi

if [ ! -z "$CHANNEL_NAME" ] || [ ! -z "$CHANNEL_URL" ] || [ ! -z "$CATEGORY" ]; then
    python manage.py iptv -add channel --channel-name "${CHANNEL_NAME}" --channel-url "${CHANNEL_URL}" --category-name "${CATEGORY}" --create-category
fi

python manage.py test && \
python manage.py daemon -restart && python manage.py daemon -status