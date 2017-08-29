import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from prettytable import PrettyTable

from recorder.deamon import Daemon
from recorder.models import Record
from recorder.record import Recorder


class Command(BaseCommand):
    help = """List, Start and Stop Recodings"""

    def add_arguments(self, parser):
        parser.add_argument('-list', nargs='+',
                            choices=['all', 'scheluded', 'started', 'processing', 'succesful', 'canceled', 'timeout',
                                     'error'],
                            help="List all recordings. You can use multiple choice to filter results.")
        parser.add_argument('-check', choices=['timeout'], help="Check Records for timeouts")
        parser.add_argument('-start', type=int, help="Start Record with given id.")
        parser.add_argument('-stop', type=int, help="Stop Record with given id.")
        parser.add_argument('-status', type=int, nargs='+', help="Show Record Status with given id.")
        parser.add_argument('-daemon', choices=['status', 'start', 'stop'], help="Start, Stop or Check deamon status.")
        parser.add_argument('--count', type=int, default=20, help="How many items will be shown, default 20.")
        parser.add_argument('--now', action="store_true", help="Don't attention to the record start time.")
        parser.add_argument('--dry-run', action="store_true", help="Do not apply anything to the database.")

    def handle(self, *args, **options):
        if options.get('daemon'):
            self.daemon(**options)
        elif options.get('check') == 'timeout':
            self.check_timeouts(**options)
        elif options.get('list'):
            self.list(**options)
        elif options.get('start'):
            self.start_record(**options)
        elif options.get('status'):
            self.record_status(**options)
        else:
            self.print_help('recorder', None)

    def get_filter_ids(self, statuses):
        avlb_statuses = ['scheluded', 'started', 'processing', 'succesful', 'canceled', 'timeout', 'error']
        ids = []

        for i, st in enumerate(avlb_statuses):
            if st in statuses:
                ids.append(i)

        return ids

    def create_record_table(self, records):
        # Create Table
        t = PrettyTable(['id', 'Name', 'Channel', 'Status', 'Start Time', 'Lenght'])
        for r in records:
            t.add_row(self.get_record_display(r))
        return t

    def get_record_display(self, r):
        return [r.id, r.name, r.channel.name, r.get_status_display(), r.start_time, r.time]

    def list(self, **options):
        statuses = self.get_filter_ids(options.get('list')) if not 'all' in options.get('list') else None
        records = Record.objects.all().filter(status__in=statuses) if statuses else Record.objects.all()
        # TODO: Add records to order

        table = self.create_record_table(records[:options.get('count')])

        # Print Top Message
        max_item = options.get('count')
        item_count = records.count()
        msg = "Server Time: %s," % timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = msg + " Total Items: %s," % records.count() + \
              " Shown Item: %s" % (item_count if item_count <= max_item else max_item)
        self.stdout.write(self.style.WARNING(msg))
        # Print Table
        print(table)

    def check_timeouts(self, **options):
        records = Record.objects.all().filter(status=0, start_time__lt=timezone.now())
        if not options.get('dry_run'):
            try:
                records.update(status=5)
                self.stdout.write(self.style.WARNING(
                    "Timeout Records: {count} found, {count} updated.".format(count=records.count())))
            except Exception as err:
                raise err
        else:
            self.stdout.write(self.style.WARNING("Timeout Records: %s found, None updated." % records.count()))

    def get_record_by_id(self, id):
        try:
            if isinstance(id, int):
                return Record.objects.get(id=id)
            elif isinstance(id, list):
                return Record.objects.all().filter(id__in=id)
            else:
                raise ValueError("Argument id can be int or list")
        except Record.DoesNotExist:
            raise CommandError("Record not found by id %s" % id)
        except Exception as err:
            raise err

    def start_record(self, **options):
        rcd = self.get_record_by_id(options.get('start'))
        if rcd.status in [1, 2]:
            return self.stdout.write(self.style.SUCCESS("Record already started."))

        if rcd.status not in [0, 6] and not options.get('now'):
            raise CommandError("Record is not scheduled")

        msg = "Record Starting: {id} - {name} - {channel}".format(
            id=rcd.id, name=rcd.name, channel=rcd.channel.name
        )
        self.stdout.write(self.style.NOTICE(msg))

        try:
            r = Recorder(rcd.id)
            r.start()
            time.sleep(.3)
            if r.is_alive():
                self.stdout.write(self.style.SUCCESS("Record started."))
            else:
                self.stdout.write(self.style.ERROR("Record could not started."))
            return r
        except Exception as err:
            raise err

    def stop_record(self, **options):
        rcd = self.get_record_by_id(options.get('stop'))

        if rcd.status not in [1, 2]:
            self.stdout.write(self.style.WARNING("Record not running"))
        else:
            rcd.terminate = True
            rcd.status = 4
            rcd.save()
            self.stdout.write(self.style.SUCCESS("Stopped"))

    def record_status(self, **options):
        rcd = self.get_record_by_id(options.get('status'))
        print(self.create_record_table(rcd))

    def daemon(self, **options):
        action = options.get('daemon')
        d = Daemon()
        running = d.is_running()

        if action == 'status':
            if running:
                self.stdout.write(self.style.SUCCESS("Daemon: Running"))
            else:
                self.stdout.write(self.style.NOTICE("Daemon: Not Running"))

        if action == 'start':
            if running:
                self.stdout.write(self.style.NOTICE("Daemon Already Running"))
            else:
                d.start()
                time.sleep(.5)
                if d.is_running():
                    self.stdout.write(self.style.SUCCESS("Daemon: Started"))
                else:
                    self.stdout.write(self.style.ERROR("Daemon Could not Started"))

        if action == 'stop':
            if running:
                d.stop()
                time.sleep(1)
                if not d.is_running():
                    self.stdout.write(self.style.SUCCESS("Daemon: Stopped"))
                else:
                    self.stdout.write(self.style.ERROR("Daemon Could not Stopped"))
            else:
                self.stdout.write(self.style.NOTICE("Daemon Already Stopped"))
