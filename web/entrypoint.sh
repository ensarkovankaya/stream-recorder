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
        echo 'ENTRYPOINT: ADMIN_* variables not set.'
    fi
}

function add_channel {
    if [ ! -z "$CHANNEL_NAME" ] || [ ! -z "$CHANNEL_URL" ] || [ ! -z "$CATEGORY" ]; then
        echo 'ENTRYPOINT: Add Channel'
        python manage.py stream -add channel --channel-name "${CHANNEL_NAME}" --channel-url "${CHANNEL_URL}" --category-name "${CATEGORY}" --create-category
    else
        echo 'ENTRYPOINT: CHANNEL_* variables not set.'
    fi
}

function run {
    echo 'ENTRYPOINT: Starting server.'
    /usr/local/bin/gunicorn config.wsgi -b 0.0.0.0:8000
}

function daemon {
    if [ "$1" == 'start' ]; then
        echo 'ENTRYPOINT: Starting Daemon...'
        python manage.py daemon -start
    elif [ "$1" == 'restart' ]; then
        echo 'ENTRYPOINT: Restarting Daemon...'
        python manage.py daemon -restart
    elif [ "$1" == 'stop' ]; then
        echo 'ENTRYPOINT: Stopping Daemon...'
        python manage.py daemon -stop
    else
        echo 'ENTRYPOINT: Unknown Command:' $1
    fi
}

if [ "$1" == "bash" ]; then
    exec bash
elif [ "$1" == "-run" ]; then
    run
elif [ "$1" == "-prod" ]; then
    makemigrations
    migrate
    collectstatic
    daemon restart
    run
    daemon stop
fi