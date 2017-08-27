from django.db import models
from django.utils.translation import ugettext as _
from django.contrib.auth import get_user_model
from django.conf import settings
User = getattr(settings, 'AUTH_USER_MODEL', get_user_model())

class Category(models.Model):
    name = models.CharField(verbose_name=_('Kategori Adı'), unique=True, max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class Channel(models.Model):
    name = models.CharField(verbose_name=_('Kanal Adı'), unique=True, max_length=100)
    url = models.URLField(verbose_name=_('URL'))
    category = models.ForeignKey('Category', null=True, blank=True, verbose_name=_('Kategori'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class Record(models.Model):

    channel = models.ForeignKey('Channel', verbose_name=_('Kanal'))
    name = models.CharField(verbose_name=_('Kayıt Adı'), max_length=100)
    start_time = models.DateTimeField(verbose_name=_('Başlangıç'))
    end_time = models.DateTimeField(verbose_name=_('Bitiş'))

    file = models.FileField(verbose_name=_('Video Dosyası'), upload_to='videos/', null=True, blank=True)

    status = models.PositiveSmallIntegerField(verbose_name=_('Durum'), choices=[
        (0, _('Zamanlandı')),
        (1, _('Başladı')),
        (2, _('İşleniyor')),
        (3, _('Başarılı')),
        (4, _('Zaman Aşımı')),
        (5, _('Hata'))
    ], default=0)

    scheduled = models.BooleanField(default=False)
    started = models.BooleanField(default=False)
    processing = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    error = models.BooleanField(default=False)
    timeout = models.BooleanField(default=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    def save(self, **kwargs):
        if self.end_time < self.start_time:
            raise ValueError(_('Bitiş zamanı Başlangıç zamanından sonra olmalıdır.'))
        return super(Record, self).save(**kwargs)

class Process(models.Model):

    record = models.OneToOneField('Record', verbose_name=_('Kayıt'))
    pid = models.PositiveSmallIntegerField()

    cmd = models.TextField(verbose_name=_('Komut'))
    log = models.TextField(verbose_name=_('Log'))

    status = models.PositiveSmallIntegerField(verbose_name=_('Durum'), choices=[
        (0, _('Bekliyor')),
        (1, _('Çalışıyor')),
        (2, _('Başarılı')),
        (3, _('Hata'))
    ])

    waiting = models.BooleanField(default=False)
    running = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    error = models.BooleanField(default=False)

    start_time = models.DateTimeField(verbose_name=_('Başladı'), auto_now_add=True)
    end_time = models.DateTimeField(verbose_name=_('Bitti'), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)

