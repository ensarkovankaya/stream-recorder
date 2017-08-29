from recorder.models import Record
from django.core.management.base import CommandError
from datetime import datetime
import subprocess
import time
from django.utils import timezone

def record(rcd: Record): # Open this in thread
    try:
        # Change record status
        rcd.status = 1
        rcd.record_started = timezone.now()
        rcd.add_log("Record Started")
        rcd.save()

        # Start Process
        ps = subprocess.Popen(rcd.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rcd.pid = ps.pid
        rcd.status = 2
        rcd.save()

        # While process is running wait
        while ps.poll() is None:
            # check if record canceled
            if Record.objects.get(id=rcd.id).only("id", "terminate").terminate:
                # If canceled terminate process
                ps.terminate()
                time.sleep(.5) # wait a half second
                if not ps.returncode: # If not terminated force to kill
                    ps.kill()
                rcd.status = 4 # mark as terminated
                rcd.save()
                break

            time.sleep(2) # Otherwase wait 2 second

        if ps.returncode != 0: # If not 0 means error
            try:
                rcd.status = 6
                rcd.record_ended = timezone.now()
                rcd.save()
                # Save Console Output
                rcd.add_log("".join([l.decode('utf-8') for l in ps.stderr.readlines()]))
            except:
                pass
        else:
            # Mark as Completed
            rcd.add_log("Record Succesfully Completed")
            rcd.record_ended = timezone.now()
            rcd.pid = 3
            rcd.save()
    except Record.DoesNotExist as err:
        ps.kill()
        raise err
    except subprocess.SubprocessError as err:
        rcd.status = 6
        rcd.save()
        rcd.add_log(err)
    except subprocess.TimeoutExpired as err:
        rcd.status = 6
        rcd.save()
        rcd.add_log(err)
    except Exception as err:
        rcd.status = 6
        rcd.save()
        rcd.add_log(err)
        raise err
