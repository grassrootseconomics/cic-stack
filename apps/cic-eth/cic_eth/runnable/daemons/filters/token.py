# external imports
from eth_erc20 import ERC20
from chainlib.eth.contract import (
        ABIContractEncoder,
        ABIContractType,
        )
import celery

# local imports
from .base import SyncFilter


class TokenFilter(SyncFilter):

    def __init__(self, chain_spec, queue):
        self.queue = queue
        self.chain_spec = chain_spec


    def filter(self, conn, block, tx, db_session=None):
        if not tx.payload:
            return (None, None)

        try:
            r = ERC20.parse_transfer_request(tx.payload)
        except RequestMismatchException:
            return (None, None)
        
        enc = ABIContractEncoder()
        enc.method('transfer')
        method = enc.get()

        s = celery.signature(
                'cic_eth.eth.gas.apply_gas_value_cache',
                [
                    tx.inputs[0],
                    method,
                    tx.gas_used,
                    tx.hash,
                    ],
                queue=self.queue,
                )
        return s.apply_async()
