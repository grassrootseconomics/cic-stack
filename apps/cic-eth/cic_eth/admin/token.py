# standard imports
import logging

# external imports
import celery

# local imports
from cic_eth.task import BaseTask

celery_app = celery.current_app
logg = logging.getLogger()


@celery_app.task(bind=True, base=BaseTask)
def default_token(self):
    return {
            'symbol': self.default_token_symbol,
            'address': self.default_token_address,
            }
