#!/usr/bin/env bash
set -e

function migrate {
    echo 'ENTRYPOINT: Migrate'
    python manage.py migrate
}

function makemigrations {
    echo 'ENTRYPOINT: Makemigrations'
    python manage.py makemigrations
}

function collectstatic {
    echo 'ENTRYPOINT: Collecting Static Files'
    python manage.py collectstatic -c --noinput
}

function clear {
    echo 'ENTRYPOINT: Clearing...'
    if [ -d "logs" ]; then
        echo 'ENTRYPOINT: Clearing Log Files...'
        rm logs/*.log
    fi

    if [ -d media/* ]; then
        echo 'ENTRYPOINT: Clearing Media Files...'
        rm -r media/*
    fi

    if [ -d static/* ]; then
        echo 'ENTRYPOINT: Clearing Static Files...'
        rm -r static/*
    fi

    if [ -d ".daemon.lock" ]; then
        rm .daemon.lock
    fi

    if [ -d ".daemon.pid" ]; then
        rm .daemon.pid
    fi

    echo 'ENTRYPOINT: Clearing migrations.'
    rm */migrations/0*
    echo 'ENTRYPOINT: Clear Done.'
}

function add_admin {
    if [ ! -z "$ADMIN_USERNAME" ] || [ ! -z "$ADMIN_EMAIL" ] || [ ! -z "$ADMIN_PASSWORD" ]; then
        echo 'ENTRYPOINT: Add Admin.'
        python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.create_superuser('${ADMIN_USERNAME}', '${ADMIN_EMAIL}', '${ADMIN_PASSWORD}') if not get_user_model().objects.all().filter(username='${ADMIN_USERNAME}').exists() else print('${ADMIN_USERNAME} exists.')"
    else
        echo 'ENTRYPOINT: ADMIN_* variables not set.' && exit 1
    fi
}

function add_channel {
    if [ ! -z "$CHANNEL_NAME" ] || [ ! -z "$CHANNEL_URL" ] || [ ! -z "$CATEGORY" ]; then
        echo 'ENTRYPOINT: Add Channel'
        python manage.py stream -add channel --channel-name "${CHANNEL_NAME}" --channel-url "${CHANNEL_URL}" --category-name "${CATEGORY}" --create-category
    else
        echo 'ENTRYPOINT: CHANNEL_* variables not set.' && exit 1
    fi
}

function run {
    echo 'ENTRYPOINT: Starting server.'
    /usr/local/bin/gunicorn config.wsgi -b 0.0.0.0:8000
}

function daemon {
    echo 'ENTRYPOINT: Restarting Daemon.'
    python manage.py daemon -restart
}

while getopts "cahsmirdf" opt "$@"; do
    case "${opt}" in
        c) clear;;
        a) add_admin;;
        h) add_channel;;
        s) collectstatic;;
        m) makemigrations;;
        i) migrate;;
        r) run;;
        d) daemon;;
        f) clear && makemigrations && migrate && collectstatic && add_admin && add_channel && daemon && run;;
        \?) exit 1;;
        :) echo "ENTRYPOINT: Option -$OPTARG requires an argument." >&2 && exit 1;;
    esac
done