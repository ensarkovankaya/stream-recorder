from django.contrib import admin, messages
from command.models import Queue, Task, TaskStatus
from django.utils.translation import ugettext_lazy as _

def delete_model(modeladmin, request, queryset):
    for obj in queryset:
        obj.delete()


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ('id', 'line', 'depends', 'status', 'command')
    readonly_fields = ('id', 'line', 'depends', 'status', 'command')


class QueueAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'timer', 'created_at']
    list_filter = ['status']

    readonly_fields = ('status', 'tasks', 'started_at', 'ended_at', 'timer', 'created_at', 'updated_at')
    actions = [delete_model]
    inlines = [TaskInline]


admin.site.register(Queue, QueueAdmin)


def terminate_task(modeladmin, request, queryset):
    for q in queryset.filter(status=TaskStatus.Processing.value):
        q.set_status_terminated()
    return messages.success(request, _("Task(s) terminated."))


class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'queue', 'line', 'status', 'depends', 'created_at']
    list_filter = ['status', 'queue']

    readonly_fields = (
        'name', 'depends', 'stderr', 'stdout', 'pid', 'status', 'started_at', 'ended_at', 'created_at', 'updated_at',
        'command')

    actions = [delete_model, terminate_task]


admin.site.register(Task, TaskAdmin)
