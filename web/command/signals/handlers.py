from ..models import Task
from django.dispatch import receiver
from django.db.models.signals import post_save

from logging import getLogger

logger = getLogger('task.signals.handlers')


@receiver(post_save, sender=Task)
def on_task_status_change(task: Task, created, **kwargs):
    if not created and task.queue:
        try:
            logger.debug("Task<%d>: Chec")
            task.queue.calculate_queue_status()
        except Exception:
            logger.exception("Task<%d>: Queue<%d> status can not calculated." % (task.id, task.queue.id))
