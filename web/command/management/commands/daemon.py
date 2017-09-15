from django.core.management.base import BaseCommand
from command.daemon import Daemon, DaemonRunning, DaemonNotRunning


class Command(BaseCommand):
    help = """Task Daemon"""

    def __init__(self, *arg, **kwargs):
        self.daemon = Daemon()
        super(Command, self).__init__(*arg, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('-start', action='store_true', help="Start Daemon")
        parser.add_argument('-stop', action='store_true', help="Start Daemon")
        parser.add_argument('-restart', action='store_true', help="Start Daemon")
        parser.add_argument('-status', action='store_true', help="Daemon Status")

    def handle(self, *args, **options):
        if options.get('start'):
            self.start()
        elif options.get('stop'):
            self.stop()
        elif options.get('restart'):
            if self.daemon.is_running():
                self.stop()
            self.start()
        elif options.get('status'):
            msg = "Daemon: Running" if self.daemon.is_running() else "Daemon: Stopped"
            self.stdout.write(self.style.NOTICE(msg))
        else:
            self.print_help('daemon', None)

    def start(self):
        try:
            self.daemon.start()
        except DaemonRunning:
            self.stdout.write(self.style.WARNING("Daemon: Already Running"))
        except Exception as err:
            self.stdout.write(self.style.ERROR("Daemon: Can not started.\n%s" % err))

    def stop(self):
        try:
            self.daemon.stop()
            self.stdout.write(self.style.SUCCESS("Daemon: Stopped."))
        except DaemonNotRunning:
            self.stdout.write(self.style.WARNING("Daemon: Not Running"))
        except Exception:
            self.stdout.write(self.style.ERROR("Daemon: Can not stopped."))
