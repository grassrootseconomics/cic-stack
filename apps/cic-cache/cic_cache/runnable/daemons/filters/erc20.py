# standard imports
import logging

# external imports
from cic_eth_registry.erc20 import ERC20Token
from cic_eth_registry.error import (
        NotAContractError,
        ContractMismatchError,
        )

# local imports
from .base import SyncFilter

logg = logging.getLogger().getChild(__name__)


class ERC20TransferFilter(SyncFilter):

    def __init__(self, chain_spec):
        self.chain_spec = chain_spec


    def filter(self, conn, block, tx, db_session=None):
        logg.debug('filter {} {}'.format(block, tx))
        token = None
        try:
            token = ERC20Token(conn, tx.inputs[0])
        except NotAContractError:
            logg.debug('not a contract {}'.format(tx.inputs[0]))
            return
        except ContractMismatchError:
            logg.debug('not an erc20 token  {}'.format(tx.inputs[0]))
            return
        logg.debug('token {}'.format(token))
        pass
