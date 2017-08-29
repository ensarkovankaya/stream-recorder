from django.core.management.base import BaseCommand, CommandError
from recorder.models import Channel, Record
from prettytable import PrettyTable
from django.utils import timezone
from django.conf import settings
from recorder.record import record
from recorder.deamon import Deamon
import os
import threading
import time

class Command(BaseCommand):
    help = """List, Start and Stop Recodings"""

    def add_arguments(self, parser):
        parser.add_argument('-list', nargs='+', choices=['all', 'scheluded', 'started', 'processing', 'succesful', 'canceled', 'timeout', 'error'], help="List all recordings. You can use multiple choice to filter results.")
        parser.add_argument('-check', choices=['timeout'], help="Check Records for timeouts")
        parser.add_argument('-start', type=int, help="Start Record with given id.")
        parser.add_argument('-stop', type=int, help="Stop Record with given id.")
        parser.add_argument('-deamon', choices=['status', 'start', 'stop'], help="Start, Stop or Check deamon status.")
        parser.add_argument('--count', type=int, default=20, help="How many items will be shown, default 20.")
        parser.add_argument('--dry-run', action="store_true", help="Do not apply anything to the database.")

    def handle(self, *args, **options):
        if options.get('deamon'):
            self.deamon(**options)
        elif options.get('check') == 'timeout':
            self.check_timeouts(**options)
        elif options.get('list'):
            self.list(**options)
        elif options.get('start'):
            self.start_record(**options)
        else:
            self.print_help('recorder', None)

    def get_filter_ids(self, statuses):
        avlb_statuses = ['scheluded', 'started', 'processing', 'succesful', 'canceled', 'timeout', 'error']
        ids = []

        for i, st in enumerate(avlb_statuses):
            if st in statuses:
                ids.append(i)

        return ids

    def list(self, **options):
        statuses = self.get_filter_ids(options.get('list')) if not 'all' in options.get('list') else None
        records = Record.objects.all().filter(status__in=statuses) if statuses else Record.objects.all()
        # TODO: Add records to order

        # Create Table
        t = PrettyTable(['id', 'Name', 'Channel', 'Status', 'Start Time', 'Lenght'])
        for r in records[:options.get('count')]:
            t.add_row([
            r.id, r.name, r.channel.name, r.get_status_display(),
            r.start_time, r.time
            ])

        # Print Top Message
        max_item = options.get('count')
        item_count = records.count()
        msg = "Server Time: %s," % timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = msg + " Total Items: %s," % records.count() + \
        " Shown Item: %s" % (item_count if item_count <= max_item else max_item)
        self.stdout.write(self.style.WARNING(msg))
        # Print Table
        print(t)

    def check_timeouts(self, **options):
        records = Record.objects.all().filter(status=0, start_time__lt=timezone.now())
        if not options.get('dry_run'):
            try:
                records.update(status=5)
                self.stdout.write(self.style.WARNING("Timeout Records: {count} found, {count} updated.".format(count=records.count())))
            except Exception as err:
                raise err
        else:
            self.stdout.write(self.style.WARNING("Timeout Records: %s found, None updated." % records.count()))

    def get_record_by_id(self, id):
        try:
            return Record.objects.get(id=id)
        except Record.DoesNotExist:
            raise CommandError("Record not found by id %s" % id)
        except Exception as err:
            raise err

    def start_record(self, **options):
        rcd = get_record_by_id(options.get('start'))

        msg = "Record Starting: {id} - {name} - {channel}".format(
            id=rcd.id, name=rcd.name, channel=rcd.channel.name
        )
        self.stdout.write(self.style.WARNING(msg))

        try:
            record(rcd)
            self.stdout.write(self.style.SUCCESS("Completed."))
        except Exception as err:
            raise err

    def stop_record(self, **options):
        rcd = get_record_by_id(options.get('stop'))

        if rcd.status not in [1, 2]:
            self.stdout.write(self.style.WARNING("Record not running"))
        else:
            rcd.terminate = True
            rcd.status = 4
            rcd.save()
            self.stdout.write(self.style.SUCCESS("Stoped"))

    def deamon(self, **options):
        action = options.get('deamon')
        d = Deamon()
        running = d.is_running()

        if action == 'status':
            if running:
                self.stdout.write(self.style.SUCCESS("Deamon: Running on pid %s" % d.pid))
            else:
                self.stdout.write(self.style.NOTICE("Deamon: Not Running"))

        if action == 'start':
            if running:
                self.stdout.write(self.style.NOTICE("Deamon: Already Running"))
            else:
                t = threading.Thread(target=Deamon().start)
                t.daemon = True
                t.start()
                time.sleep(1)
                if d.is_running():
                    self.stdout.write(self.style.SUCCESS("Deamon: Started"))
                else:
                    self.stdout.write(self.style.ERROR("Deamon: Can not Started"))

        if action == 'stop':
            if running:
                d.stop()
                time.sleep(1)
                if not d.is_running():
                    self.stdout.write(self.style.SUCCESS("Deamon: Stoped"))
                else:
                    self.stdout.write(self.style.ERROR("Deamon: Can not Stoped"))
            else:
                self.stdout.write(self.style.NOTICE("Deamon: Already Stoped"))
