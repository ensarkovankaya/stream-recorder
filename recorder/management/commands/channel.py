from django.core.management.base import BaseCommand, CommandError
from recorder.models import Category, Channel


class Command(BaseCommand):
    help = """Add Channel or Category"""

    def add_arguments(self, parser):
        parser.add_argument('-add', choices=['channel', 'category'], help="Add a channel")
        parser.add_argument('--channel-name', type=str, help="Channel Name")
        parser.add_argument('--channel-url', type=str, help="Channel URL")
        parser.add_argument('--update-channel', action='store_true', help="Update channel if exists")
        parser.add_argument('--category-name', type=str, help="Category Name")
        parser.add_argument('--category-id', type=int, help="Channel Category ID")
        parser.add_argument('--create-category', action='store_true', help="Create channel category if not exists")

    def handle(self, *args, **options):
        if options.get('add') == 'category':
            self.add_category(**options)
        if options.get('add') == 'channel':
            self.add_channel(**options)

    def add_category(self, **options):
        name = options.get('category_name')

        if not name:
            raise CommandError('Category name not specified')

        category, created = self.get_or_create_category(name)
        if created:
            self.stdout.write(self.style.SUCCESS('Category created: %s' % name))
        else:
            self.stdout.write(self.style.WARNONG('Category already exists: %s' % name))

    def add_channel(self, **options):
        channel_name = options.get('channel_name')
        category_name = options.get('category_name')
        category_id = options.get('category_id')
        channel_url = options.get('channel_url')
        create_category = options.get('create_category')
        update_channel = options.get('update_channel')

        if not channel_name:
            raise CommandError('Channel name must be specified')

        if not channel_url:
            raise CommandError('Channel url must be specified')

        if category_name and category_id:
            raise CommandError('Category Name and Category ID can not specified at the same time')

        if category_id:
            category = self.get_categorty_by_id(category_id)
        elif category_name and create_category:
            category, created = self.get_or_create_category(category_name)
            if created:
                self.stdout.write(self.style.NOTICE('Category created'))
        elif category_name:
            category = self.get_categorty_by_name(category_name)
        else:
            category = None

        self.create_channel(name=channel_name, url=channel_url, category=category, update=update_channel)

    def create_channel(self, name, url, category=None, update=False):
        channel = Channel.objects.all().filter(name=name)

        if channel and update:
            channel.update(url=url)
            if category:
                channel.update(category=category)
            self.stdout.write(self.style.SUCCESS('Channel updated'))
        elif channel:
            self.stdout.write(self.style.NOTICE('Channel already exists'))
        else:
            try:
                Channel.objects.create(name=name, url=url, category=category)
                self.stdout.write(self.style.SUCCESS('Channel created'))
            except Exception as err:
                raise CommandError('Channel %s can not created\n%s' % (name, err))

    def get_categorty_by_name(self, name):
        try:
            return Category.objects.get(name=name)
        except Channel.DoesNotExist:
            raise CommandError('Category not found with name %s' % name)
        except Exception as err:
            raise CommandError('Error while getting category with name \n%s' % err)

    def get_categorty_by_id(self, id):
        try:
            return Category.objects.get(id=id)
        except Channel.DoesNotExist:
            raise CommandError('Category not found with id %s' % id)
        except Exception as err:
            raise CommandError('Error while getting category with id \n%s' % err)

    def create_category(self, name):
        try:
            return Category.objects.create(name=name)
        except Exception as err:
            raise CommandError('Category can not created by name %s\n%s' % (name, err))

    def get_or_create_category(self, name):
        try:
            return Category.objects.get_or_create(name=name)
        except Exception as err:
            raise CommandError('Category can not created by name %s\n%s' % (name, err))
