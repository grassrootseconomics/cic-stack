# standard imports
import logging

# external imports
import celery

#logg = logging.getLogger(__name__)
logg = logging.getLogger()

celery_app = celery.current_app

class CallbackTask(celery.Task):
    errs = {}
    oks = {}

@celery_app.task(bind=True, base=CallbackTask)
def test_error_callback(self, a, b, c):
    o = CallbackTask.oks
    s = 'ok'
    if c > 0:
        o = CallbackTask.errs
        s = 'err'

    if o.get(b) == None:
        o[b] = []
    o[b].append(a)

    logg.debug('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> test callback ({}): {} {} {}'.format(s, a, b, c))
