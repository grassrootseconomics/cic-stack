# standard imports
import json
import logging
import mmap
import os
import tempfile

# external imports
import celery

logg = logging.getLogger(__name__)

celery_app = celery.current_app


class CallbackTask(celery.Task):

    mmap_path = tempfile.mkdtemp()

@celery_app.task(bind=True, base=CallbackTask)
def test_getter_callback(self, result, taskId, c):
    print("path", self.mmap_path)
    print("callback", result, taskId, c)
    s = 'ok'
    if c > 0:
        s = 'err'

    fp = os.path.join(self.mmap_path, taskId+ '_0')
    if os.path.exists(fp):
        index = int(fp.split('_')[-1]) + 1
        fp = os.path.join(self.mmap_path, f"{taskId}_{index}" )
    f = open(fp, 'wb+')
    if isinstance(result, (dict, list)):
        bResult = json.dumps(result).encode('utf-8')
    else:
        bResult = bytes(result, 'utf-8')
    f.write(b'\x00' * 4000)
    f.seek(0)
    m = mmap.mmap(f.fileno(), length=4000)
    m.write(bResult)
    m.close()
    f.close()

    logg.debug('test callback ({}): {} {} {}'.format(s, result, taskId, c))

@celery_app.task(bind=True, base=CallbackTask)
def test_callback(self, a, b, c):
    s = 'ok'
    if c > 0:
        s = 'err'

    fp = os.path.join(self.mmap_path, b)
    f = open(fp, 'wb+')
    f.write(b'\x00')
    f.seek(0)
    m = mmap.mmap(f.fileno(), length=1)
    m.write(c.to_bytes(1, 'big'))
    m.close()
    f.close()

    logg.debug('test callback ({}): {} {} {}'.format(s, a, b, c))
