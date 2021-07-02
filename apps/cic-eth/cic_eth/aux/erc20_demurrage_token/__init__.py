# standard imports
import celery

# external imports
from erc20_demurrage_token.demurrage import DemurrageCalculator

celery_app = celery.current_app


class DemurrageCalculationTask(celery.Task):

    demurrage_token_rates = {}


@celery_app.task(bind=True, base=DemurrageCalculationTask)
def get_adjusted_balance(self, token_symbol, amount, timestamp):
    c = self.demurrage_token_rates[token_symbol]
    return c.amount_since(amount, timestamp)
