from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .models import Category, Channel, Schedule, Video


def delete_model(modeladmin, request, queryset):
    for obj in queryset:
        obj.delete()


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


class ScheduleAdminForm(forms.ModelForm):
    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']
        now = timezone.now()
        if start_time < now:
            raise forms.ValidationError(
                _('Start Time can not be before {time}').format(time=now.strftime('%d/%m/%Y %H:%M:%S')))

        return self.cleaned_data['start_time']


class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'channel', 'start_time', 'time', 'status']
    list_filter = ['status', 'channel']

    fieldsets = (
        (_('Record Informations'), {
            'fields': ('channel', 'name', 'start_time', 'time', 'file', 'status', 'created_at')
        }),
        (_('Resize'), {
            'fields': ('resize', 'foar')
        })
    )
    form = ScheduleAdminForm
    actions = [delete_model]

    readonly_fields = ('created_at', 'updated_at', 'status', 'file', 'user', 'queue')

    def get_changeform_initial_data(self, request):
        return {'time': '00:01:00', 'start_time': timezone.now(), 'channel': Channel.objects.all().first()}

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        obj.save()

    def delete_model(self, request, obj):
        obj.delete()


admin.site.register(Schedule, ScheduleAdmin)


class VideoAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'format', 'size']
    list_filter = ['format']
    readonly_fields = (
        'related_content_type', 'related_object_id', 'related', 'created_at', 'updated_at', 'attr',
        'format', 'name', 'file')

    actions = [delete_model]

    def delete_model(self, request, obj):
        obj.delete()


admin.site.register(Video, VideoAdmin)
