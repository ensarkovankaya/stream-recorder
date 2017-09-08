from django import forms
from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import ugettext as _

from .models import Category, Channel


class ChannelInline(admin.TabularInline):
    model = Channel
    extra = 0


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    fields = ('name',)
    inlines = [ChannelInline]


admin.site.register(Category, CategoryAdmin)


class ChannelAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category']
    fields = ('name', 'url', 'category')
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(Channel, ChannelAdmin)


class RecordAdminForm(forms.ModelForm):
    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']
        now = timezone.now()
        if start_time < now:
            raise forms.ValidationError(
                _('Başlangıç zamanı {time} önce olamaz.').format(time=now.strftime('%d/%m/%Y %H:%M:%S')))

        return self.cleaned_data['start_time']


def terminate_records(modeladmin, request, queryset):
    if queryset.exclude(status__in=[0, 1, 2]).exists():
        return messages.error(request, _("Sadece Başlamış veya İşlelen durumlardaki kayıtlar durdurlabilir."))
    queryset.update(terminate=True, status=4)
    return messages.success(request, _("Kayıtlar durdurldu."))

terminate_records.short_description = 'Seçili kayıtları durdur'


def reschedule_records(modeladmin, request, queryset):
    if queryset.exclude(status__in=[5,6]).exists():
        return messages.error(request, _("Sadece İptal edilen veya Hatalı kayıtlar yeniden zamanlanabilir."))

    not_passed = queryset.filter(start_time__gte=timezone.now())
    not_passed.update(status=0, terminate=False)

    if not_passed.count() != queryset.count():
        return messages.warning(request, _("Bütün kayıtlar tekrar zamanlamadı."))
    return messages.success(request, _("Kayıtlar tekrar zamanladı."))


reschedule_records.short_description = 'Seçili kayıtları tekrar zamanla'


