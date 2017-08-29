from .models import Record
from django.conf import settings
import os
import time
import psutil
import threading

class Deamon(threading.Thread, threading.Lock):

    def __init__(self):
        pass


    def run(self):
        while True:
            time.sleep(1)
