from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import ugettext as _

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


class File(models.Model):
    video = models.FileField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Record(models.Model):
    channel = models.ForeignKey('Channel', verbose_name=_('Kanal'))
    name = models.CharField(verbose_name=_('Kayıt Adı'), max_length=100)
    start_time = models.DateTimeField(verbose_name=_('Başlangıç'))
    time = models.TimeField(verbose_name=_('Süre'))

    file = models.ManyToManyField('File')

    status = models.PositiveSmallIntegerField(verbose_name=_('Durum'), choices=[
        (0, _('Zamanlandı')),
        (1, _('Başladı')),
        (2, _('İşleniyor')),
        (3, _('Başarılı')),
        (4, _('Zaman Aşımı')),
        (5, _('Hata'))
    ], default=0)

    log = models.TextField(verbose_name=_('Log'), null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Ekleniş'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Son Güncelleme'))

    def __str__(self):
        return str(self.name)


class Process(models.Model):
    record = models.OneToOneField('Record', verbose_name=_('Kayıt'))
    pid = models.PositiveSmallIntegerField(null=True, blank=True)

    cmd = models.TextField(verbose_name=_('Komut'), null=True, blank=True)
    log = models.TextField(verbose_name=_('Log'), null=True, blank=True)

    file = models.ForeignKey('File', null=True, blank=True)

    status = models.PositiveSmallIntegerField(verbose_name=_('Durum'), choices=[
        (0, _('Bekliyor')),
        (1, _('Çalışıyor')),
        (2, _('Başarılı')),
        (3, _('Sonlandırıldı')),
        (4, _('Hata'))
    ])

    start_time = models.DateTimeField(verbose_name=_('Başladı'), blank=True, null=True)
    end_time = models.DateTimeField(verbose_name=_('Bitti'), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)
