import os
import signal
import sys
import time
from logging import getLogger
from threading import Thread

from django.conf import settings
from django.core.management.base import OutputWrapper
from django.core.management.color import color_style, no_style
from django.utils import timezone

from .base.emrah import Daemon as BaseDaemon
from .models import Queue, QueueStatus

logger = getLogger('task.Daemon')
_runfile = os.path.join(settings.BASE_DIR, '.daemon.lock')
_pidfile = os.path.join(settings.BASE_DIR, '.daemon.pid')


class QueueThread(Thread):
    def __init__(self, id: int, *args, **kwargs):
        self.id = id
        super(QueueThread, self).__init__(daemon=True, *args, **kwargs)

    def get_queue(self) -> Queue:
        try:
            return Queue.objects.get(id=self.id)
        except Queue.DoesNotExist:
            logger.exception("Queue<%d> not found." % self.id)
            raise
        except Exception:
            logger.exception("Queue<%d> can not get." % self.id)
            raise

    def run(self):
        q = self.get_queue()
        q.start()


class DaemonError(Exception):
    pass


class DaemonRunning(DaemonError):
    pass


class DaemonNotRunning(DaemonError):
    pass


class Daemon(BaseDaemon):
    def __init__(self, wait=2, threshold=4, stdout=None, stderr=None, no_color=False):
        """Task Daemon: Gets task and execute them.

        :arg wait : How many seconds should wait before check new records again. This should be lower than threshold
        :arg threshold :
        """
        self.wait = wait
        self.threshold = threshold
        self.threads = []
        self.queues = []
        self.stdout = OutputWrapper(stdout or sys.stdout)
        self.stderr = OutputWrapper(stderr or sys.stderr)
        if no_color:
            self.style = no_style()
        else:
            self.style = color_style()
            self.stderr.style_func = self.style.ERROR

        super(Daemon, self).__init__(name="Daemon", pidfile=_pidfile, runfile=_runfile, stoptimeout=10, debug=1)

    def start(self):
        # Check daemon is running
        pid = self.__getpid()
        if pid:
            logger.warning("Daemon: Already Running, can not start.")
            raise DaemonRunning()

        # Start Daemon
        logger.info("Daemon: Started.")
        self.daemonize()
        self.run()

    def stop(self):
        # Check alive daemon if not exists already
        pid = self.__getpid()
        if not pid:
            logger.warning("Daemon: Not Running, can not stop.")
            raise DaemonNotRunning()

        self.stdout.write(self.style.WARNING("Trying to stop..."))
        self.__cleanstop(pid)

        try:
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            err = str(err)

            if err.find('No such process') > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                raise DaemonError(err)

    def is_running(self):
        """Checks daemon is running"""
        return os.path.exists(self.runfile)

    @staticmethod
    def _is_queue_time_came(q: Queue):
        return q.timer <= timezone.now()

    def start_queue(self, q: Queue):
        if not self._is_queue_time_came(q):
            return

        logger.debug("Daemon: Start Queue<%d>" % q.id)
        try:
            thread = QueueThread(q.id)
            thread.start()
            self.threads.append(thread)
        except Exception:
            logger.exception("Daemon: Start Queue<%d> failed." % q.id)
            try:
                q.set_status_error()
            except:
                logger.exception("Daemon: Queue<%d> status can not set error." % q.id)

    def queue_timeout(self, q: Queue):
        try:
            logger.warning("Queue<%d> timeout, changing status." % q.id)
            q.status = QueueStatus.Timeout.value
            q.save()
        except Exception:
            logger.exception("Queue<%d> status can not changed to Timeout." % q.id)

    @staticmethod
    def get_queues(stat: QueueStatus):
        return Queue.objects.all().filter(status=stat.value).order_by('timer')

    def _add_queue_list(self, q: Queue):
        if q.id not in self.queues:
            logger.debug("Daemon: Queue<%d> is adding to the queues." % q.id)
            self.queues.append(q.id)
        else:
            logger.debug("Daemon: Queue<%d> is already in queues." % q.id)

    def run(self):
        start_time = timezone.now()
        try:
            while self.is_running():
                for queue in self.get_queues(QueueStatus.Processing):
                    queue.calculate_queue_status()

                for queue in self.get_queues(QueueStatus.Created):
                    if queue.timer:
                        # Check is timeout
                        if queue.timer < timezone.now() - timezone.timedelta(seconds=self.threshold):
                            self.queue_timeout(queue)
                        else:
                            self.start_queue(queue)
                    else:
                        self.start_queue(queue)

                # Log every 10 seconds
                passed = (timezone.now() - start_time).total_seconds()
                if int(passed) % 10 == 0:
                    logger.debug("Daemon: Running %d seconds." % passed)
                time.sleep(self.wait)
        except Exception:
            logger.exception("Daemon: Failed.")
            self.delrun()
            raise DaemonError()
        logger.warning("Daemon: Exiting.")
