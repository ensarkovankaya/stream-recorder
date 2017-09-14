import os
import random
import string

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from recorder.models import Category, Channel, Schedule, Video, VideoFormat, FOAR, Queue

User = get_user_model()


class VideoTestCase(TestCase):
    @staticmethod
    def generate_name():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    @staticmethod
    def create_video(**kwargs):
        try:
            return Video.objects.create(**kwargs)
        except Exception:
            raise

    def generate_email(self):
        return self.generate_name() + "@gmail.com"

    def create_user(self):
        return User.objects.create_user(username=self.generate_name(), email=self.generate_email(),
                                        password=self.generate_name())

    def test_create_video(self):
        v = self.create_video(name=self.generate_name())
        v.create_file()
        v.save()
        file = v.file.path

        # Check file extension
        self.assertTrue(str(file).endswith(VideoFormat.MP4.value))

        # Check file created.
        self.assertTrue(os.path.exists(file))

        # Check file size 0
        self.assertEqual(v.size(), 0)
        v.delete()

        # Check File deleted
        self.assertFalse(os.path.exists(file))

    def test_create_video_with_target(self):
        v = self.create_video(name=self.generate_name())
        user = self.create_user()
        v.set_related(user)
        v.save()


class ChannelCategoryTestCase(TestCase):
    @staticmethod
    def generate_name():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    @staticmethod
    def generate_url():
        return "http://www." + "".join(random.choices(string.ascii_lowercase, k=5)) + ".com/"

    @staticmethod
    def create_channel(**kwargs):
        return Channel.objects.create(**kwargs)

    @staticmethod
    def create_category(**kwargs):
        return Category.objects.create(**kwargs)

    def test_create_category(self):
        self.assertRaises(ValidationError, self.create_category)
        category = self.create_category(name=self.generate_name())
        self.assertEqual(category.channel_count(), 0)

    def test_create_channel(self):
        self.assertRaises(ValidationError, self.create_channel)
        self.assertRaises(ValidationError, self.create_channel, name=self.generate_name())
        self.create_channel(name=self.generate_name(), url=self.generate_url())

    def test_create_channel_with_category(self):
        category = self.create_category(name=self.generate_name())
        self.create_channel(name=self.generate_name(), url=self.generate_url(), category=category)

    def test_category_channel_count(self):
        category = self.create_category(name=self.generate_name())
        self.create_channel(name=self.generate_name(), url=self.generate_url(), category=category)
        self.create_channel(name=self.generate_name(), url=self.generate_url(), category=category)
        self.assertEqual(category.channel_count(), 2)


class ScheduleTestCase(TestCase):
    @staticmethod
    def generate_name():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    @staticmethod
    def generate_url():
        return "http://www." + "".join(random.choices(string.ascii_lowercase, k=5)) + ".com/"

    @staticmethod
    def create_channel(**kwargs):
        return Channel.objects.create(**kwargs)

    @staticmethod
    def create_category(**kwargs):
        return Category.objects.create(**kwargs)

    @staticmethod
    def create_schedule(**kwargs):
        return Schedule.objects.create(**kwargs)

    def generate_email(self):
        return self.generate_name() + "@gmail.com"

    def create_user(self):
        return User.objects.create_user(username=self.generate_name(), email=self.generate_email(),
                                        password=self.generate_name())

    def test_create_schedule(self):
        category = self.create_category(name=self.generate_name())
        channel = self.create_channel(name=self.generate_name(), url=self.generate_url(), category=category)

        start_time = timezone.now() + timezone.timedelta(seconds=10)
        time = "00:01:00"
        user = self.create_user()

        self.create_schedule(channel=channel, name=self.generate_name(), start_time=start_time, time=time,
                             user=user)

    def test_create_schedule_with_resize(self):
        category = self.create_category(name=self.generate_name())
        channel = self.create_channel(name=self.generate_name(), url=self.generate_url(), category=category)

        start_time = timezone.now() + timezone.timedelta(seconds=10)
        time = "00:01:00"
        user = self.create_user()
        resize = "1280x720"
        foar = FOAR.Increase
        self.create_schedule(channel=channel, name=self.generate_name(), start_time=start_time, time=time,
                             user=user, resize=resize, foar=foar)

    def test_delete_schedule(self):
        category = self.create_category(name=self.generate_name())
        channel = self.create_channel(name=self.generate_name(), url=self.generate_url(), category=category)

        start_time = timezone.now() + timezone.timedelta(seconds=10)
        time = "00:01:00"
        user = self.create_user()

        schedule = self.create_schedule(channel=channel, name=self.generate_name(), start_time=start_time, time=time,
                                        user=user)
        schedule.delete()
        self.assertFalse(Schedule.objects.all().filter(id=schedule.id).exists())

    def test_queue_deleted(self):
        category = self.create_category(name=self.generate_name())
        channel = self.create_channel(name=self.generate_name(), url=self.generate_url(), category=category)

        start_time = timezone.now() + timezone.timedelta(seconds=10)
        time = "00:01:00"
        user = self.create_user()

        schedule = self.create_schedule(channel=channel, name=self.generate_name(), start_time=start_time, time=time,
                                        user=user)
        queue = Queue.objects.get(id=schedule.queue.id)
        schedule.delete()
        self.assertFalse(Queue.objects.all().filter(id=queue.id).exists())
