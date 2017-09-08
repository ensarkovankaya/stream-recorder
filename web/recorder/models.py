import os
from enum import Enum
from logging import getLogger

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext as _

from ffmpeg.generator import Command
from ffmpeg.utils.base import ChoiceEnum
from ffmpeg.utils.codecs import Codec
from ffmpeg.utils.ffprobe import get_file_attributes
from ffmpeg.utils.filters import BitstreamChannelFilter, StreamSpecifier, ScaleFilter, FFmpegFilter
from ffmpeg.utils.log import LogLevel
from ffmpeg.utils.video import VIDEO_SIZES

User = getattr(settings, 'AUTH_USER_MODEL', get_user_model())
logger = getLogger('recorder.models')


class Category(models.Model):
    name = models.CharField(verbose_name=_('Category Name'), unique=True, max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    def channel_count(self):
        return Channel.objects.all().filter(category=self.id).count()

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")


class Channel(models.Model):
    name = models.CharField(verbose_name=_('Channel Name'), unique=True, max_length=100)
    url = models.URLField(verbose_name=_('URL'))
    category = models.ForeignKey('Category', null=True, blank=True, verbose_name=_('Category'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = _("Channel")
        verbose_name_plural = _("Channels")


class ScheduleStatus(ChoiceEnum):
    Scheduled = 0
    Processing = 1
    Completed = 2
    Canceled = -3
    TimeOut = -2
    Error = -1


class Schedule(models.Model):
    channel = models.ForeignKey('Channel', verbose_name=_('Channel'))
    name = models.CharField(verbose_name=_('Record Name'), max_length=100)
    start_time = models.DateTimeField(verbose_name=_('Start Time'))
    time = models.TimeField(verbose_name=_('Time'))

    status = models.SmallIntegerField(verbose_name=_('Status'), choices=[(s.value, _(s.name)) for s in ScheduleStatus],
                                      default=ScheduleStatus.Scheduled.value)

    file = models.ForeignKey('Video', null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Time'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Last Update Time'))

    def __str__(self):
        return str(self.name)

    def is_passed(self):
        return self.start_time <= timezone.now()

    def end_time(self):
        return self.start_time + timezone.timedelta(hours=self.time.hour, minutes=self.time.minute,
                                                    seconds=self.time.second)

    class Meta:
        verbose_name = _("Schedule")
        verbose_name_plural = _("Schedules")


class TaskTypes(ChoiceEnum):
    Record = 0
    Resize = 1
    AudioSync = 2


class Task(models.Model):
    schedule = models.OneToOneField(Schedule)
    type = models.SmallIntegerField(verbose_name=_("Type"), choices=[(t.value, _(t.name)) for t in TaskTypes])
    completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Time'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Last Update Time'))

    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")


class BaseTaskModel(models.Model):
    task = models.OneToOneField(Task)

    log = models.TextField(verbose_name=_('Log'), null=True, blank=True)
    pid = models.PositiveSmallIntegerField(null=True, blank=True)

    DEFAULT_STATUS = None  # Overwrite This
    STATUES = []  # Overwrite This
    status = models.SmallIntegerField(verbose_name=_('Status'), choices=STATUES,
                                      default=DEFAULT_STATUS)

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Time'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Last Update Time'))

    class Meta:
        abstract = True

    @staticmethod
    def _log_separator():
        "-" * 10 + " " + timezone.now().strftime('%d/%m/%Y %H:%M:%S') + " " + "-" * 10 + "\n"

    def add_log(self, msg: str, sep: bool = True, end: str = "\n", save: bool = True):
        if msg:
            log = self._log_separator() + str(msg) if sep else str(msg)
            self.log = self.log + end + log if self.log else log
            if save:
                self.save(update_fields=['log'])
        return self

    def command(self):
        """!Important: Overwrite this. This should generate command."""
        raise NotImplemented()


class RecordStatus(ChoiceEnum):
    Canceled = -2
    Error = -1
    Waiting = 0
    Recording = 1
    Completed = 2


class RecordTask(BaseTaskModel):
    output = models.ForeignKey('Video', related_name="recordtask_output")

    STATUES = [(s.value, _(s.name)) for s in RecordStatus]
    DEFAULT_STATUS = RecordStatus.Waiting.value

    class Meta:
        verbose_name = _("Record")
        verbose_name_plural = _("Records")

    def command(self):
        try:
            input = self.task.schedule.channel.url

            output: Video = Video.objects.get_or_create(target_object_id=self.id,
                                                        target_content_type=ContentType.objects.get_for_model(self))
            output.create_file()

            cmd = Command({"input": input, "output": output.file.path, "loglevel": LogLevel.Error.value,
                           "duration": self.task.schedule.time})
            cmd.add_codec(Codec(data={"copy": True, "stream": StreamSpecifier.Video.value}))

            cmd.add_filter(
                BitstreamChannelFilter({"stream": StreamSpecifier.Audio.value, "filters": FFmpegFilter.aac_adtstoasc})
            )
            cmd.validate()
        except Exception as err:
            logger.exception("Command can not created.")
            raise err

        return cmd.generate()


class ResizeStatus(ChoiceEnum):
    Canceled = -2
    Error = -1
    Started = 0
    Ended = 1


class ResizeTask(BaseTaskModel):
    input = models.ForeignKey('Video', related_name="resizetask_input")
    output = models.ForeignKey('Video', related_name="resizetask_output")

    scale = models.CharField(max_length=10, choices=VIDEO_SIZES)
    kar = models.BooleanField(default=False, verbose_name=_("Keep Aspect Ratio"))

    STATUES = [(s.value, _(s.name)) for s in ResizeStatus]
    DEFAULT_STATUS = ResizeStatus.Started.value

    class Meta:
        verbose_name = _("Resize")
        verbose_name_plural = _("Resize")

    def command(self):
        """
        :return: ffmpeg -i {input} -filter:v scale={scale} {output}
        """
        try:
            output: Video = Video.objects.get_or_create(target_object_id=self.id,
                                                        target_content_type=ContentType.objects.get_for_model(self))
            output.create_file()
            cmd = Command(data={"input": self.input.file.path, "output": output.file.path})
            width, height = self.scale.split('x')
            cmd.add_filter(
                ScaleFilter(data={"width": int(width), "height": int(height), "stream": StreamSpecifier.Video.value}))
            cmd.validate()
        except Exception as err:
            logger.exception("Command can not created.")
            raise err
        return cmd.generate()


class VideoFormat(ChoiceEnum):
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    FLV = "flv"


class Video(models.Model):
    target_content_type = models.ForeignKey(ContentType, related_name='video_target', blank=True, null=True)
    target_object_id = models.CharField(max_length=255, blank=True, null=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')

    name = models.CharField(max_length=100, verbose_name=_("Video Name"))
    file = models.FileField(verbose_name=_("Video File"), upload_to="videos/")

    format = models.CharField(max_length=5, verbose_name=_("File Format"), default=VideoFormat.MP4.value,
                              choices=[(f.value, f.name) for f in VideoFormat])

    size = models.IntegerField(default=0, verbose_name=_("File Size"))
    attr = JSONField(verbose_name=_("Attributes"), null=True, blank=True)

    is_empty = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Create Time"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last Update"))

    def save_file_attributes(self):
        if not self.file:
            raise ValueError("File is not set yet.")

        self.attr = get_file_attributes(self.file.path)
        self.save(update_fields=['attr'])

    def create_file(self, ext: VideoFormat = None):
        """Creates empty file as placeholder so can use `file.path` attribute"""
        self.is_empty = True
        self.size = 0
        self.format = ext.value if ext else self.format
        self.file.save(self.name + "." + self.format, ContentFile(''), save=False)
        self.save(update_fields=['is_empty', 'file', 'size', 'format'])

    def delete(self, **kwargs):
        if self.file:
            try:
                os.remove(self.file.path)
            except Exception:
                logger.exception("File could not deleted: %s" % self.file.path)
        super(Video, self).delete(**kwargs)

    class Meta:
        verbose_name = _("Video")
        verbose_name_plural = _("Videos")
