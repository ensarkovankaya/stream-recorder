from datetime import datetime
from logging import getLogger

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from command.models import Queue, Task, QueueStatus

from ffmpeg.generator import Codec, Command, LogLevel
from ffmpeg.utils.filters import BitstreamChannelFilter, FFmpegFilter, FOAR, ScaleFilter, StreamSpecifier

from recorder.models import Schedule, Video, ScheduleStatus
from recorder.utils import generate_random_string

logger = getLogger('recorder.signals.handlers')


def generate_record_command(input: str, output: str, duration: str, overwrite: bool = True) -> Command:
    """Returns: ffmpeg -i 'INPUT' -y -c copy -bsf:a aac_adtstoasc -t DURATION OUTPUT"""
    data = {'input': input, 'output': output, 'loglevel': LogLevel.Error, 'overwrite': overwrite,
            'duration': duration}
    try:
        cmd = Command(**data)
        cmd.add_codec(Codec(copy=True))
        cmd.add_filter(
            BitstreamChannelFilter(stream=StreamSpecifier.Audio, filters=[FFmpegFilter.aac_adtstoasc]))
        logger.debug("Record command generated: %s" % cmd.generate())
        return cmd.generate()
    except Exception:
        logger.exception("Record Command can not generated.\nData: %s" % data)
        raise


def generate_resize_command(input: str, output: str, width: int, height: int, foar: FOAR,
                            overwrite: bool = True) -> Command:
    data = {'input': input, 'output': output, 'width': width, 'height': height, 'foar': foar, 'overwrite': overwrite}

    try:
        cmd = Command(input=input, output=output, overwrite=True)
        cmd.add_filter(ScaleFilter(width=width, height=height, foar=foar))
        logger.debug("Resize command generated: %s" % cmd.generate(True))
        return cmd.generate()
    except Exception:
        logger.exception("Resize Command can not generated.\nData: %s" % data)
        raise


def create_video_file(task: Task) -> Video:
    try:
        v = Video(name=generate_random_string(8))
        v.set_related(task)
        v.create_file()
        v.save()
        return v
    except Exception:
        logger.exception("Video file can not created for Task<%d>." % task.id)
        raise


def create_recod_task(schedule: Schedule) -> (Task, Video):
    try:
        timeout = timezone.timedelta(hours=schedule.time.hour, minutes=schedule.time.minute + 1,
                                     seconds=schedule.time.second)
        task = Task.objects.create(timeout=str(timeout))
        output_file = create_video_file(task)

        task.command = generate_record_command(input=schedule.channel.url, output=output_file.file.path,
                                               duration=str(schedule.time))
        task.save(update_fields=['command'])
        logger.info("Record task created for Schedule<%d>" % schedule.id)
    except Exception:
        logger.exception("Create Record Task failed.")
        raise
    return task, output_file


def create_resize_task(schedule: Schedule, file: Video, dependence: Task = None) -> (Task, Video):
    try:

        task = Task.objects.create(depends=dependence)
        output_file: Video = create_video_file(task)
        width, height = schedule.resize.split('x')
        task.command = generate_resize_command(input=file.file.path, output=output_file.file.path, width=int(width),
                                               height=int(height), foar=schedule.get_foar())
        task.save(update_fields=['command'])
        logger.info("Resize task created for Schedule<%d>" % schedule.id)
    except Exception:
        logger.exception("Create Resize Task failed.")
        raise
    return task, output_file


def create_instance_queue(sch: Schedule):
    queue = Queue.objects.create(timer=sch.start_time)
    record_task, record_file = create_recod_task(sch)
    queue.add(record_task)

    if sch.resize:
        resize_task, resize_file = create_resize_task(schedule=sch, file=record_file, dependence=record_task)
        queue.add(resize_task)
    return queue


@receiver(post_save, sender=Schedule)
def on_schedule_save(instance: Schedule, created, **kwargs):
    if created:
        try:
            # Create Tasks
            instance.queue = create_instance_queue(instance)
            instance.save(update_fields=['queue'])
        except Exception:
            logger.exception("Queue can not created for Schedule<%d>." % instance.id)
            raise


@receiver(post_save, sender=Queue)
def on_queue_status_change(instance: Queue, created, **kwargs):
    if not created:
        s: Schedule or None = Schedule.objects.all().filter(queue=instance).first()
        if s:
            if instance.status == QueueStatus.Timeout:
                s.set_status_timeout()
            elif instance.status == QueueStatus.Error:
                s.set_status_error()
            elif instance.status == QueueStatus.Processing:
                s.set_status_processing()
            elif instance.status == QueueStatus.Completed:
                s.set_status_completed()
                try:
                    v: Video = Video.get_object_by_related(instance.tasks().last()).first()
                    s.file = v.file
                    s.save()
                except Exception:
                    logger.exception("Schedule<%d> status can not change Completed" % s.id)
                    raise

