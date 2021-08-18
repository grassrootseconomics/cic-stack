# standard imports
import logging

# external imports
import celery

logg = logging.getLogger(__name__)


class CeleryApp:
   
    @classmethod
    def from_config(cls, config):
        backend_url = config.get('CELERY_RESULT_URL')
        broker_url = config.get('CELERY_BROKER_URL')
        celery_app = None
        if backend_url != None:
            celery_app = celery.Celery(broker=broker_url, backend=backend_url)
            logg.info('creating celery app on {} with backend on {}'.format(broker_url, backend_url))
        else:
            celery_app = celery.Celery(broker=broker_url)
            logg.info('creating celery app without results backend on {}'.format(broker_url))

        return celery_app
