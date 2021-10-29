# standard imports
import logging

# external imports
from eth_erc20 import ERC20
from chainlib.eth.contract import (
        ABIContractEncoder,
        ABIContractType,
        )
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.address import is_same_address
from cic_eth_registry import CICRegistry
from cic_eth_registry.erc20 import ERC20Token
from eth_token_index import TokenUniqueSymbolIndex
import celery

# local imports
from .base import SyncFilter

logg = logging.getLogger(__name__)


class TokenFilter(SyncFilter):

    def __init__(self, chain_spec, queue, call_address=ZERO_ADDRESS):
        self.queue = queue
        self.chain_spec = chain_spec
        self.caller_address = call_address


    def filter(self, conn, block, tx, db_session=None):
        if not tx.payload:
            return (None, None)

        try:
            r = ERC20.parse_transfer_request(tx.payload)
        except RequestMismatchException:
            return (None, None)

        token_address = tx.inputs[0]
        token = ERC20Token(self.chain_spec, conn, token_address)

        registry = CICRegistry(self.chain_spec, conn)
        r = registry.by_name(token.symbol, sender_address=self.caller_address)
        if is_same_address(r, ZERO_ADDRESS):
            return None

        enc = ABIContractEncoder()
        enc.method('transfer')
        method = enc.get()

        s = celery.signature(
                'cic_eth.eth.gas.apply_gas_value_cache',
                [
                    token_address,
                    method,
                    tx.gas_used,
                    tx.hash,
                    ],
                queue=self.queue,
                )
        return s.apply_async()
