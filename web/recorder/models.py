import os
from logging import getLogger

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator, MinLengthValidator, URLValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from command.models import Queue
from ffmpeg.utils.base import ChoiceEnum
from ffmpeg.utils.ffprobe import get_file_attributes
from ffmpeg.utils.filters import FOAR
from ffmpeg.utils.video import VIDEO_SIZES

User = getattr(settings, 'AUTH_USER_MODEL', get_user_model())
logger = getLogger('recorder.models')


class Category(models.Model):
    name = models.CharField(verbose_name=_('Category Name'), unique=True, max_length=100,
                            validators=[MinLengthValidator(2)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    def channel_count(self):
        return Channel.objects.all().filter(category=self.id).count()

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        app_label = "recorder"

    def save(self, **kwargs):
        self.full_clean()
        return super(Category, self).save(**kwargs)


class Channel(models.Model):
    name = models.CharField(verbose_name=_('Channel Name'), unique=True, max_length=100,
                            validators=[MinLengthValidator(2)])
    url = models.URLField(verbose_name=_('URL'), validators=[URLValidator])
    category = models.ForeignKey('Category', null=True, blank=True, verbose_name=_('Category'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = _("Channel")
        verbose_name_plural = _("Channels")

    def save(self, **kwargs):
        self.full_clean()
        return super(Channel, self).save(**kwargs)


class ScheduleStatus(ChoiceEnum):
    Scheduled = 0
    Processing = 1
    Completed = 2
    Canceled = -3
    TimeOut = -2
    Error = -1


class Schedule(models.Model):
    channel = models.ForeignKey('Channel', verbose_name=_('Channel'))
    name = models.CharField(verbose_name=_('Record Name'), max_length=100, validators=[MinLengthValidator(2)])
    start_time = models.DateTimeField(verbose_name=_('Start Time'))
    time = models.TimeField(verbose_name=_('Time'))

    status = models.SmallIntegerField(verbose_name=_('Status'), choices=[(s.value, _(s.name)) for s in ScheduleStatus],
                                      default=int(ScheduleStatus.Scheduled))

    file = models.FileField(verbose_name=_("Video"), null=True, blank=True)

    # Resize Task
    resize = models.CharField(max_length=10, choices=VIDEO_SIZES, null=True, blank=True, verbose_name=_("Resize"))
    foar = models.CharField(verbose_name=_("Force Original Aspect Ratio"), max_length=10, choices=FOAR.choices(),
                            default=FOAR.Disable)

    queue = models.OneToOneField(Queue, null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Time'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Last Update Time'))

    def __str__(self):
        return str(self.name)

    def get_foar(self) -> FOAR:
        return FOAR.__members__.get(self.get_foar_display())

    def is_passed(self) -> bool:
        return self.start_time <= timezone.now()

    def end_time(self):
        return self.start_time + timezone.timedelta(hours=self.time.hour, minutes=self.time.minute,
                                                    seconds=self.time.second)

    class Meta:
        verbose_name = _("Schedule")
        verbose_name_plural = _("Schedules")

    def save(self, **kwargs):
        self.full_clean()
        return super(Schedule, self).save(**kwargs)

    def delete(self, **kwargs):
        if self.queue:
            self.queue.delete()
        return super(Schedule, self).delete(**kwargs)

    def _set_status(self, stat: ScheduleStatus):
        if self.status == stat:
            logger.warning("Schedule<%d>: Status already %s can not change." % (self.id, stat.name))
            return

        try:
            logger.exception("Schedule<%d>: Changing status %s to %s" % (self.id, self.get_status_display(), stat.name))
            self.status = stat.value
            self.save(update_fields=['status'])
        except Exception:
            logger.exception("Schedule<%d>: can not change status to %s" % stat.name)
            raise

    def set_status_scheduled(self):
        self._set_status(ScheduleStatus.Scheduled)

    def set_status_processing(self):
        self._set_status(ScheduleStatus.Processing)

    def set_status_completed(self):
        self._set_status(ScheduleStatus.Completed)

    def set_status_canceled(self):
        self._set_status(ScheduleStatus.Canceled)

    def set_status_timeout(self):
        self._set_status(ScheduleStatus.TimeOut)

    def set_status_error(self):
        self._set_status(ScheduleStatus.Error)


class VideoFormat(ChoiceEnum):
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    FLV = "flv"


class Video(models.Model):
    related_content_type = models.ForeignKey(ContentType, blank=True, null=True)
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    related = GenericForeignKey('related_content_type', 'related_object_id')

    name = models.CharField(max_length=100, verbose_name=_("Video Name"), validators=[MinLengthValidator(1)])
    file = models.FileField(verbose_name=_("Video File"), upload_to="videos/",
                            validators=[FileExtensionValidator(VideoFormat.values())])

    format = models.CharField(max_length=5, verbose_name=_("File Format"), default=VideoFormat.MP4.value,
                              choices=VideoFormat.choices())

    attr = JSONField(verbose_name=_("Attributes"), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Create Time"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last Update"))

    def size(self) -> int:
        return int(self.file.size)

    def set_related(self, obj):
        try:
            self.related_content_type = ContentType.objects.get_for_model(obj)
            self.related_object_id = obj.pk
            self.save()
            return self
        except Exception:
            logger.exception("Video<%d>: Set target failed." % self.id)
            raise

    @staticmethod
    def get_object_by_related(obj):
        related_content_type = ContentType.objects.get_for_model(obj)
        related_object_id = obj.pk
        return Video.objects.all().filter(related_content_type=related_content_type,
                                          related_object_id=related_object_id)

    def save_file_attributes(self):
        if not self.file:
            raise ValueError("File is not set yet.")

        self.attr = get_file_attributes(self.file.path)
        self.save(update_fields=['attr'])

    def create_file(self):
        try:
            """Creates empty file as placeholder so can use `file.path` attribute"""
            self.format = self.format
            self.file.save("%s.%s" % (self.name, self.format), ContentFile(''), save=True)
            return self
        except Exception:
            logger.exception("Video<%d>: Create file failed." % self.id)
            raise

    def delete(self, **kwargs):
        if self.file and os.path.exists(self.file.path):
            try:
                os.remove(self.file.path)
            except Exception:
                logger.exception("Video<%d> File could not deleted: %s" % (self.id, self.file.path))
        return super(Video, self).delete(**kwargs)

    def save(self, **kwargs):
        self.full_clean(exclude=['file'])
        return super(Video, self).save(**kwargs)

    class Meta:
        verbose_name = _("Video")
        verbose_name_plural = _("Videos")
