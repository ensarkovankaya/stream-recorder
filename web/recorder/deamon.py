import os
import time
import sys
import signal
from logging import getLogger

from django.conf import settings
from django.utils import timezone
from django.core.management.base import OutputWrapper
from django.core.management.color import color_style, no_style

from recorder.record import Recorder
from .models import Record

from .utils.emrah import Daemon as BaseDaemon

logger = getLogger('recorder.daemon')
_runfile = os.path.join(settings.BASE_DIR, '.daemon.lock')
_pidfile = os.path.join(settings.BASE_DIR, '.daemon.pid')


class Daemon(BaseDaemon):
    def __init__(self, wait=5, threshold=10, stdout=None, stderr=None, no_color=False):
        """Recorder Daemon: Gets records and when times come run them.

        :arg wait : How many seconds should wait before check new records again. This should be lower than threshold
        :arg threshold : Gets records that given threshold between now and now + threshold second
        """
        self.wait = wait
        self.threshold = threshold
        self.subprocesses = []
        self.errored_records = []

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
            sys.exit(1)

        # Start Daemon
        self.stdout.write(self.style.SUCCESS("Daemon: Started"))
        self.daemonize()
        self.run()

    def stop(self):
        # Check alive daemon if not exists already
        pid = self.__getpid()
        if not pid:
            self.stdout.write(self.style.WARNING("Daemon already not running"))
            sys.exit(1)

        # Daemon'i durdurma islemlerine basla.
        self.stdout.write(self.style.WARNING("Trying to stop..."))

        # Oncelikle daemon'a kendisini kapatma sansi ver.
        # Kendi kendini kapatamazsa kill edilecek.
        self.__cleanstop(pid)

        # Daeman kill olana kadar belli araliklarla SIGTERM gonder.
        # Daemon kill olduktan sonraki kill denemesinde OSError olusacak.
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
                sys.stderr.write(self.style.ERROR('%s\n' % (err)))
                sys.exit(1)

    def is_running(self):
        """Checks daemon is running"""
        return os.path.exists(self.runfile)

    def get_records(self):
        logger.debug("Checking new records.")
        """Get timely records"""
        records = Record.objects.all().filter(status=0, start_time__range=[
            timezone.now(), timezone.now() + timezone.timedelta(seconds=self.threshold)])
        count = records.count()
        if count > 0:
            logger.debug("%s New Record(s) found." % count)
        else:
            logger.debug("0 found.")
        return records

    def check_timeouts(self):
        try:
            logger.debug("Checking timeouts.")
            Record.objects.all().filter(status=0, start_time__lt=timezone.now()).update(status=5)
        except Exception as err:
            logger.exception("While checking timeouts error")
            raise err

    def _clear_subprocesses(self):
        # When stopped check any running subprocesses if exists stop them
        logger.debug("Checking alive processes, fount %d" % len(self.subprocesses))
        for p in self.subprocesses:  # Recorder[]
            try:
                if p.is_alive():
                    p.stop()
            except:
                pass

    def _remove_complete_subprocesses(self):
        logger.debug("Removing complete subprocesses, found %d" % len(self.subprocesses))
        # Remove completed subprocesses
        for p in self.subprocesses:
            try:
                if not p.is_alive() or not p.is_process_running() or p.completed:
                    self.subprocesses.remove(p)
                    logger.debug("Subprocess removed: %s" % p.id)
            except Exception:
                logger.exception("Process could not removed from list")
                pass

    def run(self):
        """Main method that will run on thread.
        !IMPORTANT: This method should not call directly, call 'start' method instead"""
        count = 0
        try:
            while os.path.exists(self.runfile):
                self.check_timeouts()

                # Start Process timely records
                for rcd in self.get_records():
                    if rcd.id not in self.errored_records:
                        try:
                            logger.debug("Starting record: %d" % rcd.id)
                            t = Recorder(rcd.id, wait=True)
                            t.start()
                            self.subprocesses.append(t)
                        except Exception:
                            self.errored_records.append(rcd.id)
                            logger.exception("Record could not started with id %s" % rcd.id)
                            pass

                self._remove_complete_subprocesses()

                count += 1
                time.sleep(self.wait)

            self._clear_subprocesses()

        except Exception as err:
            logger.exception("Daemon error")
            raise err

        logger.debug("Daemon stopped at loop: %s" % count)
