import os
import signal
import subprocess
import time
from datetime import datetime
from logging import getLogger

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from command.errors import CommandError, DependenceError, ProcessError, StatusError, TaskError
from command.utils import pid_exists

from ffmpeg.utils import ChoiceEnum

logger = getLogger("task.models")


class TaskStatus(ChoiceEnum):
    Canceled = -3
    Terminated = -2
    Error = -1
    Created = 0
    Processing = 2
    Completed = 3


class QueueStatus(ChoiceEnum):
    Timeout = -3
    Stopped = -2
    Error = -1
    Created = 0
    Processing = 1
    Completed = 2


class Task(models.Model):
    queue = models.ForeignKey('Queue', null=True, blank=True, on_delete=models.CASCADE)
    line = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=15, null=True, blank=True)
    depends = models.ForeignKey('Task', null=True, blank=True)
    timeout = models.TimeField(null=True, blank=True)

    stderr = models.TextField(verbose_name=_('StdErr'), null=True, blank=True)
    stdout = models.TextField(verbose_name=_('StdOut'), null=True, blank=True)
    pid = models.PositiveSmallIntegerField(null=True, blank=True)

    status = models.SmallIntegerField(verbose_name=_('Status'), choices=TaskStatus.choices(),
                                      default=int(TaskStatus.Created))

    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Task Started'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Task Ended'))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Time'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Last Update Time'))

    command = models.TextField()

    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        app_label = "command"
        ordering = ('line',)

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return "Task<%d>" % self.id

    def get_status(self):
        # Return status as TaskStatus Object
        return TaskStatus.__members__.get(self.status)

    def _get_self(self):
        try:
            return Task.objects.get(id=self.id)
        except Task.DoesNotExist:
            logger.exception("Task<%d>: Object not found in database." % self.id)
            raise
        except Exception:
            logger.exception("Task<%d>: Error while get self." % self.id)
            raise

    def _add_stderr(self):
        err: bytes = self.ps.stderr.readline()
        if err:
            self.stderr = self.stderr + err.decode('utf-8') if self.stderr else err.decode('utf-8')
            self.save(update_fields=['stderr'])

    def _add_stdout(self):
        try:
            if self.ps.stdout.readable():
                out: bytes = self.ps.stdout.readline()
                if out:
                    self.stdout = self.stdout + out.decode('utf-8') if self.stdout else out.decode('utf-8')
                    self.save(update_fields=['stdout'])
        except Exception:
            logger.exception("Stdout can not saved.")

    def _set_status(self, stat: TaskStatus):
        if self.status == stat:
            logger.warning("Task<%d>: Status already %s can not change." % (self.id, stat.name))
            return

        try:
            logger.debug("Task<%d>: Status changing %s to %s." % (self.id, self.get_status_display(), stat.name))
            self.status = int(stat)
            self.save(update_fields=['status'])
        except Exception:
            logger.exception("Status can not changed.")
            raise

    def set_status_terminated(self):
        self._set_status(TaskStatus.Terminated)

    def set_status_error(self):
        self._set_status(TaskStatus.Error)

    def set_status_processing(self):
        self._set_status(TaskStatus.Processing)

    def set_status_completed(self):
        self._set_status(TaskStatus.Completed)

    def _is_process_allive(self):
        return (self.ps.poll() is None) if self.ps else False

    def _is_task_terminated(self):
        return self._get_self().status == TaskStatus.Terminated

    def is_timeout(self):
        return datetime.combine(self.started_at, self.timeout) > timezone.now()

    def _save_process_stderr(self):
        """Read process stderr output and saves it to the model logs."""
        try:
            logger.debug("Task<%d>: Saving process stderr." % self.id)
            # Save Console Output
            self.stderr = "".join([l.decode('utf-8') for l in self.ps.stderr.readlines()])
            self.save(update_fields=['stderr'])
        except Exception:
            logger.exception("Task<%d>: Saving stderr failed." % self.id)

    def _save_process_stdout(self):
        try:
            out = "".join([l.decode('utf-8') for l in self.ps.stdout.readlines()])
            if out:
                self.stdout = self.stdout + out if self.stdout else out
                self.save(update_fields=['stdout'])
        except Exception:
            logger.exception("Stdout can not saved.")

    def _set_start_time(self):
        try:
            self.started_at = timezone.now()
            self.save(update_fields=['started_at'])
        except Exception:
            logger.exception("Start time can not saved.")
            raise

    def _set_end_time(self):
        try:
            self.ended_at = timezone.now()
            self.save(update_fields=['ended_at'])
        except Exception:
            logger.exception("End time can not saved.")
            raise

    def _start_process(self):
        logger.debug("Running Command: %s" % self.command)
        try:
            self.ps = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.set_status_processing()
        except subprocess.SubprocessError:
            self.set_status_error()
            logger.exception("Task<%d>: Process could not started" % self.id)
            raise

        try:
            # Save Pid
            self.pid = self.ps.pid
            self.save(update_fields=['pid'])
        except Exception:
            logger.exception("Task<%d>: Pid can not saved" % self.id)
            raise

    def _terminate_process(self):
        if not self.ps:
            logger.warning("Task<%d>: ps not found, process can not terminated." % self.id)
            return

        try:
            logger.debug("Task<%d>: Terminating process..." % self.id)
            self.ps.terminate()
        except Exception:
            logger.exception("Task<%d>: Process can not terminated." % self.id)

    def _loop(self):

        if not self.ps:
            logger.error("Task<%d>: Loop method called but process not found." % self.id)
            raise ValueError("Process not found")

        start_time = timezone.now()
        error = False
        while self._is_process_allive():
            passed = (timezone.now() - start_time).total_seconds()
            if self.timeout and self.is_timeout():
                error = True
                logger.error("Task<%d>: Process react Timeout." % self.id)
                self._terminate_process()
                self.terminate()
                self.set_status_terminated()
                break

            # Do Every 10 seconds
            if int(passed) % 10 == 0:
                if self._is_task_terminated():  # Check Task is terminated
                    error = True
                    logger.warning("Task<%d>: Terminated by user." % self.id)
                    self._terminate_process()
                    self.terminate()
                    break
                logger.debug("Task<{id}>: Working for {seconds} seconds".format(id=self.id, seconds=int(passed)))
            time.sleep(1)  # Wait

        if not error:
            self.set_status_completed()

    def _run(self):
        """!IMPORTANT: This method should not call directly, call 'run' method instead"""
        self._start_process()
        self._set_start_time()
        self._loop()
        self._set_end_time()

        if self.ps.returncode == 0:
            self._save_process_stdout()
        else:
            self.set_status_error()
            self._save_process_stderr()
        return self

    def _can_run(self):
        if self.status == TaskStatus.Completed:
            raise StatusError("Task<%d>: Can not run already completed." % self.id)
        elif self.status == TaskStatus.Terminated or self.status == TaskStatus.Error:
            raise StatusError(
                "Task<%d>: Can not run Terminated or Error for rerun first call `clear` method." % self.id)
        elif self.status == TaskStatus.Processing:
            raise StatusError("Task<%d>: Can not run already started call `terminate` method for cancel." % self.id)

    def run(self, check=False):
        if self.depends and self.depends.status != TaskStatus.Completed:
            raise DependenceError("Task dependence on Task<%d> and task not completed." % self.depends.id)

        if (self.command is None) or (self.command == ""):
            raise CommandError("Task<%d>: Command is not set." % self.id)

        self._can_run()

        try:
            self._run()
            if check and (self.status == TaskStatus.Error or self.status == TaskStatus.Terminated):
                raise ProcessError("Process exit with error.")
        except Exception as err:
            raise ProcessError(err)

    def terminate(self):
        """Terminate the process if allive"""
        if pid_exists(self.pid):
            try:
                while True:
                    os.kill(self.pid, signal.SIGTERM)
                    time.sleep(0.1)
            except OSError as err:
                err = str(err)

                if err.find('No such process') > 0:
                    logger.debug("Task<%d>: Terminated, pid %d." % (self.id, self.pid))
                    self.set_status_terminated()
                else:
                    logger.exception("Task<%d> can not terminated." % self.id)

    def print(self):
        for k, v in self.__dict__.items():
            print("%s: %s" % (k, v))


class Queue(models.Model):
    status = models.SmallIntegerField(verbose_name=_('Status'), choices=QueueStatus.choices(),
                                      default=int(QueueStatus.Created))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Task Started'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Task Ended'))

    timer = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Time'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Last Update Time'))

    class Meta:
        verbose_name = _("Queue")
        verbose_name_plural = _("Queues")

    def __repr__(self):
        return "<Queue: %d>" % self.id

    def __str__(self):
        return str(self.id)

    def calculate_queue_status(self):
        if self.tasks().filter(status=TaskStatus.Error.value).exists():
            self.set_status_error()
        elif self.tasks().filter(status=TaskStatus.Completed.value).count() == self.tasks().count():
            self.set_status_completed()
        elif self.tasks().filter(status=TaskStatus.Processing.value).exists():
            self.set_status_processing()

    def tasks(self):
        """Returns tasks"""
        return Task.objects.all().filter(queue=self)

    def _set_start_time(self):
        try:
            self.started_at = timezone.now()
            self.save(update_fields=['started_at'])
        except Exception:
            logger.exception("Queue<%d>: Start time can not saved." % self.id)
            raise

    def _set_end_time(self):
        try:
            self.ended_at = timezone.now()
            self.save(update_fields=['ended_at'])
        except Exception:
            logger.exception("Queue<%d>: End time can not saved." % self.id)
            raise

    def _set_status(self, stat: QueueStatus):
        if self.status == stat:
            return

        try:
            logger.debug("Queue<%d>: Status changing %s to %s." % (self.id, self.get_status_display(), stat.name))
            self.status = int(stat)
            self.save(update_fields=['status'])
        except Exception:
            logger.exception("Status can not changed.")
            raise

    def set_status_stopped(self):
        self._set_status(QueueStatus.Stopped)

    def set_status_processing(self):
        self._set_status(QueueStatus.Processing)

    def set_status_completed(self):
        self._set_status(QueueStatus.Completed)

    def set_status_error(self):
        self._set_status(QueueStatus.Error)

    def _get_self(self):
        try:
            return Queue.objects.get(id=self.id)
        except Queue.DoesNotExist:
            logger.exception("Queue<%d>: Object not found in database." % self.id)
            raise
        except Exception:
            logger.exception("Queue<%d>: Error while get self." % self.id)
            raise

    def _loop(self):
        for task in self.tasks():
            try:
                if task.status != TaskStatus.Created:
                    logger.warning(
                        "Queue<%d>: Passing, Task<%d> status %s." % (self.id, task.id, task.get_status_display()))
                    continue

                if task.depends and task.depends.status != TaskStatus.Completed:
                    logger.warning(
                        "Queue<%d>: Task<%d> dependence Task<%d> not completed." % (self.id, task.id, task.depends.id))
                    continue

                try:
                    logger.info("Queue<%d>: Starting Task<%d>." % (self.id, task.id))
                    task.run()
                    logger.info("Queue<%d>: Completed Task<%d>" % (self.id, task.id))
                except ProcessError:
                    logger.exception("Queue<%d>: Task<%d>: Process exit with error" % (self.id, task.id))
                except DependenceError:
                    logger.exception("Queue<%d>: Task<%d>: Task error" % (self.id, task.id))
                    raise
                except TaskError:
                    logger.exception("Queue<%d>: Task<%d>: Task error" % (self.id, task.id))

            except Exception:
                self.set_status_error()
                raise

    def start(self):
        if self.tasks().count() == 0:
            logger.warning("Queue<%d>: There is no task to run." % self.id)
            return

        logger.debug("Queue<%d>: Starting..." % self.id)
        self.set_status_processing()
        self._set_start_time()
        self._loop()
        self._set_end_time()
        logger.debug("Queue<%d>: End." % self.id)

    def stop(self):
        for task in self.tasks().filter(status=TaskStatus.Processing):
            try:
                task.set_status_terminated()
            except Exception:
                logger.exception("Task could not stopped: %s" % task.id)
        self.set_status_stopped()

    def next_line(self):
        return self.tasks().count() + 1

    def add(self, task: Task):
        if self.status != QueueStatus.Created:
            raise StatusError("Queue<%d>: Status not valid to add Task<%d>." % (self.id, task.id))

        if task.depends:
            self.add(Task.objects.get(id=task.depends.id))

        if self.tasks().filter(id=task.id).exists():
            logger.warning("Queue<%d>: Task<%d> already in queue." % (self.id, task.id))
        else:
            try:
                task.line = self.next_line()
                task.queue = self
                task.save()
            except Exception:
                logger.exception("Queue<%d>: Task<%d> can not added." % (self.id, task.id))
                raise
