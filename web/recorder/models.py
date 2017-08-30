from logging import getLogger

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.core.files.base import ContentFile

User = getattr(settings, 'AUTH_USER_MODEL', get_user_model())
logger = getLogger('recorder.models')


class Category(models.Model):
    name = models.CharField(verbose_name=_('Kategori Adı'), unique=True, max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    def channel_count(self):
        return Channel.objects.all().filter(category=self.id).count()

    class Meta:
        verbose_name = _("Kategori")
        verbose_name_plural = _("Kategoriler")


class Channel(models.Model):
    name = models.CharField(verbose_name=_('Kanal Adı'), unique=True, max_length=100)
    url = models.URLField(verbose_name=_('URL'))
    category = models.ForeignKey('Category', null=True, blank=True, verbose_name=_('Kategori'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = _("Kanal")
        verbose_name_plural = _("Kanallar")


RECORD_STATUSES = [
    (0, _('Zamanlandı')),
    (1, _('Başladı')),
    (2, _('İşleniyor')),
    (3, _('Başarılı')),
    (4, _('İptal Edildi')),
    (5, _('Zaman Aşımı')),
    (6, _('Hata'))
]


class Record(models.Model):
    channel = models.ForeignKey('Channel', verbose_name=_('Kanal'))
    name = models.CharField(verbose_name=_('Kayıt Adı'), max_length=100)
    start_time = models.DateTimeField(verbose_name=_('Başlangıç'))
    time = models.TimeField(verbose_name=_('Süre'))
    terminate = models.BooleanField(default=False, verbose_name=_("İptal Et"))

    file = models.FileField(verbose_name=_('Dosya'), upload_to='videos/', null=True, blank=True)

    status = models.PositiveSmallIntegerField(verbose_name=_('Durum'), choices=RECORD_STATUSES, default=0)

    log = models.TextField(verbose_name=_('Log'), null=True, blank=True)
    pid = models.PositiveSmallIntegerField(null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)

    record_started = models.DateTimeField(null=True, blank=True)
    record_ended = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Ekleniş'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Son Güncelleme'))

    def __str__(self):
        return str(self.name)

    def add_log(self, msg):
        log = "-" * 10 + " " + \
              timezone.now().strftime('%d/%m/%Y %H:%M:%S') + \
              " " + "-" * 10 + "\n" + str(msg)
        self.log = self.log + "\n" + log if self.log else log
        self.save()

    def is_passed(self):
        return self.start_time <= timezone.now()

    def generate_file_name(self, ext):
        return self.start_time.strftime("%Y-%m-%d_%H-%M-%S") + "_" + str(self.name) + "." + str(ext)

    def create_file(self):
        if not self.file:
            self.file.save(self.generate_file_name('mp4'), ContentFile(''), save=False)

    def generate_record_command(self):
        self.create_file()
        return "ffmpeg -i '" + str(self.channel.url) + \
            "' -y -c copy -bsf:a aac_adtstoasc -t " + \
               str(self.time) + " " + self.file.path

    def delete(self, **kwargs):
        if self.file:
            self.file.delete()
        super(Record, self).delete(**kwargs)

    class Meta:
        verbose_name = _("Kayıt")
        verbose_name_plural = _("Kayıtlar")