from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from recorder.models import Category, Channel

import os
import re


class Command(BaseCommand):
    help = """Imports Channels from EXTM3U formated file
    
    # IMPORTANT!
    Data must formatted as follow: 
    '#EXTINF:-1 tvg-id="(?P<tvg_id>.*)" tvg-name="(?P<tvg_name>.*)" tvg-logo="(?P<tvg_logo>http.+)?" group-title="(?P<group_title>.*)",(?P<name>.+)\n(?P<url>http.+)'
    """

    channel_count = 0
    group_count = 0
    processed = 0

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True)

    def handle(self, *args, **options):
        pattern = '#EXTINF:-1 tvg-id="(?P<tvg_id>.*)" tvg-name="(?P<tvg_name>.*)" tvg-logo="(?P<tvg_logo>http.+)?" group-title="(?P<group_title>.*)",(?P<name>.+)\n(?P<url>http.+)'

        file = os.path.abspath(options['file'])
        if not os.path.exists(file):
            raise CommandError(_('File not found in %s' % str(file)))

        with open(file, 'r') as data:
            matches = re.findall(pattern, data.read())

            self.stdout.write(self.style.NOTICE('Data Founded: %s' % len(matches)))

            for match in matches:
                tvg_id, tvg_name, tvg_logo, group_title, name, url = match

                channel_name = name or tvg_name

                try:

                    kwargs = {
                        'name': channel_name,
                        'url': url,
                        'category': self.create_group(group_title) if group_title else None
                    }
                    channel, created = Channel.objects.get_or_create(**kwargs)
                    if created:
                        self.stdout.write(self.style.NOTICE('Channel Created: %s' % channel_name))
                        self.channel_count += 1
                except Exception as err:
                    self.stdout.write(self.style.ERROR('Error enquire while creating channel %s' % channel_name))
                    raise err
                self.processed += 1

            self.stdout.write(self.style.SUCCESS('Processed: %s\nGroup Added: %s\nChannel Added: %s' % (
                self.processed, self.group_count, self.channel_count)))

        self.stdout.write(self.style.SUCCESS('Completed'))

    def create_group(self, name):
        try:
            group, created = Category.objects.get_or_create(name=str(name))
            if created:
                self.stdout.write(self.style.NOTICE('Group Created: %s' % (name)))
                self.group_count += 1
            return group
        except Exception as err:
            self.stdout.write(self.style.ERROR('Error enquire while creating group %s' % name))
            raise err
