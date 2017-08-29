from .models import Record
from django.conf import settings
import os
import time
import psutil

class Deamon:

    def __init__(self):
        self._lock = os.path.join(settings.BASE_DIR, '.deamon')

    def start(self):
        if self.is_running():
            print('Already Running')
            return

        print('Starting...')
        try:
            self._run()
        except Exception as err:
            self._remove_lock()
            raise err
        return self

    def _create_lock(self):
        try:
            with open(self._lock, 'w') as lock:
                lock.write(str(os.getpid()))
                print('Lock Created.')
        except Exception as err:
            self._remove_lock()
            raise err

    def _read_pid(self):
        try:
            with open(self._lock, 'r') as lock:
                pid = int(lock.read())
                print('Read Pid: %s' % pid)
        except Exception as err:
            raise err
        return pid

    def _remove_lock(self):
        try:
            os.remove(self._lock)
            print('Lock removed.')
        except Exception as err:
            raise err

    def _kill_proc(self, pid, signal):
        print('Sending signal %s to Process %s' % (signal, pid))
        try:
            os.kill(pid, signal)
        except Exception as err:
            raise err

    def stop(self):
        if not self.is_running():
            print('Already stoped.')
            return

        try:
            # pid = self._read_pid()

            # Remove lock and wait to close itself
            self._remove_lock()
            # time.sleep(3)

            # # If still exists send signal
            # if psutil.pid_exists(pid):
            #     self._kill_proc(pid, 15)
            #     time.sleep(1)
            #
            # # If can not killed itself terminate
            # if psutil.pid_exists(pid):
            #     self._kill_proc(pid, 9)
            #     time.sleep(1)
            #
            # if psutil.pid_exists(pid):
            #     raise OSError('Process can not stoped.')

            print('Stoped')
        except Exception as err:
            raise err

    def is_running(self):
        try:
            if os.path.exists(self._lock):
                pid = self._read_pid()
                running = psutil.pid_exists(pid)
                if not running:
                    self._remove_lock()
            else:
                running = False
        except Exception as err:
            raise err
        return running

    def _run(self):
        self._create_lock()
        print('Running...')
        count = 0
        while os.path.exists(self._lock):
            count += 1
            time.sleep(1)
        print('Run time over on %s' % count)
        return
