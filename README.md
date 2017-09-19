# Stream Recorder

Django web app that records Streams.

Requirements:
 - ffmpeg : Use ffmpeg to record streams

## Build

### Settings Enviroments

For development create .env_local file.

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

# (Optional) You can define admin username, email and password. Script will create if not exists.
ADMIN_USERNAME=
ADMIN_EMAIL=
ADMIN_PASSWORD=

# (Optional) You can add a channel. Script will create if not exists.
CHANNEL_NAME=
CHANNEL_URL=
CATEGORY=
```

### Docker
```
touch .env_local
docker-compose build

# For Development
# Development uses .env_local file.
docker-compose up  # This will use docker-compose.yml

# For Production
docker-compose up -f production.yml
```

### Manuel Build

```
# You should set environments first
# Install Requirements
pip install -r requirements.txt

# Make Migrations
python manage.py makemigrations
python manage.py migrate

# Create an Admin User
python manage.py createsuperuser

# Start Daemon
python manage.py daemon -start

# Run Server
python manage.py runserver

```

## Channels

Channels are stream sources that will record.

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

## Categories

Categories have no effect right now but its nice to have. You can see how many channels in a category from admin.

## Task

Tasks are commands will run in shell.

### Creating Simple Task

```
t = Task(command="echo 'Hello World'")  # Create a Task
t.run()

t.get_status_display()  # Check status
Completed

print(t.stdout)  # You can see output
Hello World

t.started_at  # When process started
t.ended_at  # When process ended
```

### Depending Tasks

Tasks can depends each other. Depending tasks will not run until dependence complete.

```
t1 = Task(command="echo 'Task 1'")
t2 = Task(command="echo 'Task 2'", depends=t1)

t2.run() # Will raise DependenceError
ERROR: Task dependence on Task<1> and task not completed.
```

## Queue

Queues are list of tasks that will run in order.

### Simple Queue

```
q = Queue.objects.create()

t1 = Task.objects.create(command="echo 'Task One'")
t2 = Task.objects.create(command="echo 'Task Two'")

q.add(t1, t2)
q.start()  # This will run first t1 than t2
```

### Dependence Task in Queue

If task depends another task when adding to the queue dependence will add first in queue.

```
t1 = Task.objects.create(command="echo 'Task One'")
t2 = Task.objects.create(command="echo 'Task Two'")
t3 = Task.objects.create(command="echo 'Task Three'", depends=t2)

q = Queue.objects.create()
q.add(t1, t3)

q.tasks()  # Returns in run order
[Task<1>, Task<2>, Task<3>]
```