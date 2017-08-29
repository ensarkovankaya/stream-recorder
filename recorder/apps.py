from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

class RecorderConfig(AppConfig):
    name = 'recorder'
    verbose_name = _('IP TV Recorder')

    def ready(self):
        #import recorder.signals.handlers  #noqa
        pass
