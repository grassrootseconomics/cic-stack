# standard imports
import logging

# external imports 
import celery
from cic_eth.api.base import ApiBase

app = celery.current_app

logg = logging.getLogger(__name__)


class Api(ApiBase):
   
    def get_adjusted_balance(self, token_symbol, balance, timestamp):
        s = celery.signature(
                'cic_eth_aux.erc20_demurrage_token.get_adjusted_balance',
                [
                    token_symbol,
                    1000,
                    timestamp,
                    ],
                queue=None,
                )
        if self.callback_param != None:
            s.link(self.callback_success)
            s.link.on_error(self.callback_error)

        t = s.apply_async(queue=self.queue)
        return t
