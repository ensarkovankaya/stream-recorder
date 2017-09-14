from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class TaskConfig(AppConfig):
    name = 'command'
    verbose_name = _("Command Runner")

    def ready(self):
        #from command.signals import handlers
        pass
