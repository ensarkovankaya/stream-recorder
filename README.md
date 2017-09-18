# Stream Recorder

Django web app that records Streams.

Requirements:
 - ffmpeg : Use ffmpeg to record streams


## Docker
```
docker-compose build && docker-compose up
```

### ENV File
```
DJANGO_SECRET_KEY=  # Your Secret Key
DEBUG=false  # Change to True if not production
ALLOWED_HOSTS=example.com,www.example.com  # define allowed hosts with comma seperated
USE_SQLITE=false  # Use sqlite database

POSTGRES_DB=  # DB Name
POSTGRES_USER=  # DB User
POSTGRES_PASSWORD=  # DB Password
DB_SERVICE=postgres
DB_PORT=5432
```

## Build Manuel

```
# Install Requirements
pip install -r requirements.txt

# Make Migrations
python manage.py makemigrations recorder
python manage.py migrate

# Create User
python manage.py createsuperuser

# Run Server
python manage.py runserver

# Start Daemon which checks new Records every 5 seconds
python manage.py recorder -daemon start
```

## Channels

You can simply add channels from admin panel or command line. Channels can have categories.

```
# Adding Channel from command line
python manage.py channel -add channel --channel-name 'Channel Name' \
--channel-url 'http://stream-url' \
--category-name 'Category' --create-category  # This will create category if not exists

# Listing Channels
python manage.py channel -list channel

# Listing Categories
python manage.py channel -list category
```

## Records

Records are timely events which you specify a channel, a name and feature time. You can add records from admin panel.
For records to start at time Daemon must be running.

```
# Starting Daemon
python manage.py record -daemon start # You can use 'status', 'start', 'stop' or 'restart'

# Listing Records
# You filter by: all, scheluded, started, processing, succesful, canceled, timeout, error
python manage.py record -list all

# With multiple filter
python manage.py record -list scheluded started

# List will show limited amount of data (default 20) you can change it with --count flag
python manage.py record -list all --count 50
```

## Categories

Categories have no effect right now but its nice to have. You can see how many channels in one category and one place.