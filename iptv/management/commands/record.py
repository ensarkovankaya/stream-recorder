from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from iptv.models import Record
import subprocess

class Command(BaseCommand):
    help = """Start or stop Recording"""

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, required=True)
        parser.add_argument('-status', choices=['start', 'stop'], required=True)

    def handle(self, *args, **options):
        pass