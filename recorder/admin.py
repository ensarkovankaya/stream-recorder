from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import ugettext as _

from .models import Category, Channel, Record


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


class RecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'channel', 'start_time', 'time', 'status']
    list_filter = ['status', 'channel']
    fields = ('channel', 'name', 'status', 'start_time', 'time', 'file', 'log', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', 'status', 'file', 'user', 'log', 'pid', 'cmd')

    form = RecordAdminForm

    def get_changeform_initial_data(self, request):
        return {'time': '01:00:00', 'start_time': timezone.now(), 'channel': Channel.objects.all().first()}

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()


admin.site.register(Record, RecordAdmin)
