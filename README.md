# IPTV Recorder

IPTV Recorder Django web app that record IPTV Broadcasts.

Requirements:
 - ffmpeg


## Build

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
```
