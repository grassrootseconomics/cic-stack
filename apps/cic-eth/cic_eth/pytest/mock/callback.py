# standard imports
import logging
import mmap

# standard imports
import tempfile

# external imports
import celery

#logg = logging.getLogger(__name__)
logg = logging.getLogger()

celery_app = celery.current_app

class CallbackTask(celery.Task):

    mmap_path = tempfile.mkdtemp()

@celery_app.task(bind=True, base=CallbackTask)
def test_error_callback(self, a, b, c):
    s = 'ok'
    if c > 0:
        s = 'err'

    fp = os.path.join(self.mmap_path, b)
    f = open(fp, 'wb')
    m = mmap.mmap(f.fileno(), access=mmap.ACCESS_WRITE, length=1)
    m.write(c.to_bytes(1, 'big'))
    m.close()
    f.close()

    logg.debug('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> test callback ({}): {} {} {} -> {}'.format(s, a, b, c, fp))