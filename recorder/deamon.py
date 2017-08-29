import os
import threading
import time
from logging import getLogger

from django.conf import settings
from django.utils import timezone

from recorder.record import Recorder
from .models import Record

logger = getLogger('recorder.daemon')


class Daemon(threading.Thread):
    def __init__(self, wait=2, threshold=5):
        """Recorder Daemon: Gets records and when times come run them.

        :arg wait : How many seconds should wait before check new records again. This should be lower than threshold
        :arg threshold : Gets records that given threshold between now and now + threshold second
        """
        threading.Thread.__init__(self, daemon=True)
        self._lock = os.path.join(settings.BASE_DIR, '.daemon.lock')
        self.wait = wait
        self.threshold = threshold
        logger.debug("Lock File: %s" % self._lock)

    def _remove_lock(self):
        """Remove daemon lock file"""
        try:
            os.remove(self._lock)
            logger.debug("Lock removed")
        except Exception as err:
            raise err

    def _create_lock(self):
        """Create a lock file"""
        try:
            with open(self._lock, 'w') as lock:
                pid = str(os.getpid())
                lock.write(pid)
                logger.debug("Lock Created pid: %s" % pid)
        except Exception as err:
            self._remove_lock()
            raise err

    def is_running(self):
        """Checks daemon is running"""
        return os.path.exists(self._lock)

    def stop(self):
        """Stop daemon"""
        if not self.is_running():
            logger.warning("Already stopped.")
            return

        try:
            self._remove_lock()
            logger.debug("Daemon stopped.")
        except Exception as err:
            raise err

    def get_records(self):
        """Get timely records"""
        now = timezone.now()
        records = Record.objects.all().filter(status=0, start_time__range=[
            now, now + timezone.timedelta(seconds=self.threshold)])
        count = records.count()
        if count > 0:
            logger.debug("%s New Record(s) found." % count)
        return records

    def run(self):
        """Main method that will run on thread.
        !IMPORTANT: This method should not call directly, call 'start' method instead"""
        self._create_lock()

        processes = []  # Recorder[]
        while os.path.exists(self._lock):

            # Start Process timely records
            for rcd in self.get_records():
                try:
                    t = Recorder(rcd.id)
                    t.start()
                    processes.append(t)
                except Exception as err:
                    logger.exception("Record could not started with id %s" % rcd.id)
                    raise err

            # Remove completed processes
            for p in processes:
                try:
                    if not p.is_alive() or not p.is_process_running() or p.completed:
                        processes.remove(p)
                except Exception:
                    logger.exception("Process could not removed from list")
                    pass
            time.sleep(self.wait)

        # When stopped check any running processes if exists stop them
        for p in processes:  # Recorder[]
            try:
                if p.is_alive():
                    p.stop()
            except:
                pass
