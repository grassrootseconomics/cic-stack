# standard imports
import logging

# external imports
from chainlib.eth.erc20 import ERC20
from chainlib.eth.address import (
        to_checksum_address,
        )
from chainlib.eth.error import RequestMismatchException
from chainlib.status import Status
from cic_eth_registry.erc20 import ERC20Token
from cic_eth_registry.error import (
        NotAContractError,
        ContractMismatchError,
        )

# local imports
from .base import SyncFilter
from cic_cache import db as cic_cache_db

logg = logging.getLogger().getChild(__name__)


class ERC20TransferFilter(SyncFilter):

    def __init__(self, chain_spec):
        self.chain_spec = chain_spec


    # TODO: Verify token in declarator / token index
    def filter(self, conn, block, tx, db_session=None):
        logg.debug('filter {} {}'.format(block, tx))
        token = None
        try:
            token = ERC20Token(self.chain_spec, conn, tx.inputs[0])
        except NotAContractError:
            logg.debug('not a contract {}'.format(tx.inputs[0]))
            return False
        except ContractMismatchError:
            logg.debug('not an erc20 token  {}'.format(tx.inputs[0]))
            return False

        transfer_data = None
        try:
            transfer_data = ERC20.parse_transfer_request(tx.payload)
        except RequestMismatchException:
            logg.debug('erc20 match but not a transfer, skipping')
            return False

        token_sender = tx.outputs[0]
        token_recipient = transfer_data[0]
        token_value = transfer_data[1]

        logg.debug('matched erc20 token transfer {} ({}) to {} value {}'.format(token.name, token.address, transfer_data[0], transfer_data[1]))

        cic_cache_db.add_transaction(
                db_session,
                tx.hash,
                block.number,
                tx.index,
                to_checksum_address(token_sender),
                to_checksum_address(token_recipient),
                token.address,
                token.address,
                token_value,
                token_value,
                tx.status == Status.SUCCESS,
                block.timestamp,
                )
        db_session.flush()

        return True
