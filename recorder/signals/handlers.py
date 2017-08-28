from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings

from ..models import Record, Process


def make_log(message):
    return timezone.now().strftime('%d/%m/%Y %H:%M:%S') + " - " + message


@receiver(post_save, sender=Record)
def on_create_record(instance: Record, created: bool, **kwargs):
    if created:
        try:
            Process.objects.create(
                record=instance,
                status=0,
            )
            instance.log = make_log("Process created")
            instance.save()
        except Exception as err:
            raise err


@receiver(post_delete, sender=Record)
def on_delete_record(instance: Record, **kwargs):
    processes = Process.objects.all().filter(record=instance, status__in=[0, 1])
    for p in processes:
        p.log = str(p.log) + "\n" + make_log("Record deleted.") if p.log else make_log("Record deleted.")
        p.status = 3
        p.save()
