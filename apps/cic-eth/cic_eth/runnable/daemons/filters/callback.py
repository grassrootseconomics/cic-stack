# standard imports
import logging

# external imports
import celery
from cic_eth_registry.error import (
    UnknownContractError,
    NotAContractError,
    )
from chainlib.status import Status as TxStatus
from chainlib.eth.address import to_checksum_address
from chainlib.eth.error import RequestMismatchException
from chainlib.eth.constant import ZERO_ADDRESS
from hexathon import (
        strip_0x,
        add_0x,
        )
from eth_erc20 import ERC20
from erc20_faucet import Faucet

# local imports
from .base import SyncFilter
from cic_eth.eth.meta import ExtendedTx
from cic_eth.encode import tx_normalize
from cic_eth.eth.erc20 import (
        parse_transfer,
        parse_transferfrom,
        )
from cic_eth.eth.account import parse_giftto

logg = logging.getLogger(__name__)


class CallbackFilter(SyncFilter):

    trusted_addresses = []

    def __init__(self, chain_spec, method, queue, caller_address=ZERO_ADDRESS):
        super(CallbackFilter, self).__init__()
        self.queue = queue
        self.method = method
        self.chain_spec = chain_spec
        self.caller_address = caller_address


    def call_back(self, transfer_type, result):
        result['chain_spec'] = result['chain_spec'].asdict()
        s = celery.signature(
            self.method,
            [
                result,
                transfer_type,
                int(result['status_code'] != 0),
            ],
            queue=self.queue,
            )
        t = s.apply_async()
        return t


    def parse_data(self, tx, conn):
        transfer_type = None
        transfer_data = None
        # TODO: what's with the mix of attributes and dict keys
        logg.debug('have payload {}'.format(tx.payload))

        logg.debug('tx status {}'.format(tx.status))

        for parser in [
                parse_transfer,
                parse_transferfrom,
                parse_giftto,
                ]:
            try:
                if tx:
                    (transfer_type, transfer_data) = parser(tx, conn, self.chain_spec, self.caller_address)
                    if transfer_type == None:
                        continue
                break
            except RequestMismatchException:
                continue


        logg.debug('resolved method {}'.format(transfer_type))

        if transfer_data != None:
            transfer_data['status'] = tx.status

        return (transfer_type, transfer_data)


    def filter(self, conn, block, tx, db_session=None):
        super(CallbackFilter, self).filter(conn, block, tx, db_session)
        transfer_data = None
        transfer_type = None
        try:
            (transfer_type, transfer_data) = self.parse_data(tx, conn)
        except TypeError:
            logg.debug('invalid method data length for tx {}'.format(tx.hash))
            return

        if len(tx.payload) < 8:
            logg.debug('callbacks filter data length not sufficient for method signature in tx {}, skipping'.format(tx.hash))
            return

        logg.debug('checking callbacks filter input {}'.format(tx.payload[:8]))
    
        t = None
        if transfer_data != None:
            token_symbol = None
            result = None
            try:
                tokentx = ExtendedTx(conn, tx.hash, self.chain_spec)
                tokentx.set_actors(transfer_data['from'], transfer_data['to'], self.trusted_addresses, caller_address=self.caller_address)
                tokentx.set_tokens(transfer_data['token_address'], transfer_data['value'])
                if transfer_data['status'] == 0:
                    tokentx.set_status(1)
                else:
                    tokentx.set_status(0)
                result = tokentx.asdict()
                t = self.call_back(transfer_type, result)
                self.register_match()
                logline = 'callback success task id {} tx {} queue {}'.format(t, tx.hash, t.queue)
                logline = self.to_logline(block, tx, logline)
                logg.info(logline)
            except UnknownContractError:
                logg.debug('callback filter {}:{} skipping "transfer" method on unknown contract {} tx {}'.format(self.queue, self.method, transfer_data['to'], tx.hash))
            except NotAContractError:
                logg.debug('callback filter {}:{} skipping "transfer" on non-contract address {} tx {}'.format(self.queue, self.method, transfer_data['to'], tx.hash))
    
        return t

    def __str__(self):
        return 'callbackfilter'
