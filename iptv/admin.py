from django.contrib import admin
from .models import Category, Channel, Record, Process


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


class RecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'channel', 'start_time', 'end_time', 'status']
    list_filter = ['status', 'channel']
    fields = ('channel', 'name', 'status', 'start_time', 'end_time', 'file')
    readonly_fields = ('created_at', 'updated_at', 'status')

    def save_model(self, request, obj, form, change):
        print(change)
        obj.status = 0
        obj.save()

admin.site.register(Record, RecordAdmin)


class ProcessAdmin(admin.ModelAdmin):
    list_display = ['id', 'record', 'pid', 'status']
    list_filter = ['status']
    fields = ('record', 'pid', 'status', 'cmd', 'log')
    readonly_fields = ('created_at', 'updated_at', 'status', 'record', 'pid', 'cmd', 'log')


admin.site.register(Process, ProcessAdmin)
