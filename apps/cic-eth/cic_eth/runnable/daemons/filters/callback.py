# standard imports
import logging

# third-party imports
import celery
from cic_eth_registry.error import UnknownContractError
from chainlib.status import Status as TxStatus
from chainlib.eth.address import to_checksum_address
from chainlib.eth.error import RequestMismatchException
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.erc20 import ERC20
from hexathon import strip_0x
from sarafu_faucet import MinterFaucet as Faucet

# local imports
from .base import SyncFilter
from cic_eth.eth.meta import ExtendedTx

logg = logging.getLogger().getChild(__name__)


def parse_transfer(tx):
    if tx.payload:
        r = ERC20.parse_transfer_request(tx.payload)
        transfer_data = {}
        transfer_data['to'] = r[0]
        transfer_data['value'] = r[1]
        transfer_data['from'] = tx['from']
        transfer_data['token_address'] = tx['to']
        return ('transfer', transfer_data)
    else:
        pass


def parse_transferfrom(tx):
    if tx.payload:
        r = ERC20.parse_transfer_request(tx.payload)
        transfer_data = {}
        transfer_data['from'] = r[0]
        transfer_data['to'] = r[1]
        transfer_data['value'] = r[2]
        transfer_data['token_address'] = tx['to']
        return ('transferfrom', transfer_data)
    else:
        pass


def parse_giftto(tx):
    if tx.payload:
        r = Faucet.parse_give_to_request(tx.payload)
        transfer_data = {}
        transfer_data['to'] = r[0]
        transfer_data['value'] = tx['value']
        transfer_data['from'] = tx['from']
        transfer_data['token_address'] = tx['to']
        return ('tokengift', transfer_data)
    else:
        pass


class CallbackFilter(SyncFilter):

    trusted_addresses = []

    def __init__(self, chain_spec, method, queue):
        self.queue = queue
        self.method = method
        self.chain_spec = chain_spec


    def call_back(self, transfer_type, result):
        logg.debug('result {}'.format(result))
        s = celery.signature(
            self.method,
            [
                result,
                transfer_type,
                int(result['status_code'] == 0),
            ],
            queue=self.queue,
            )
#        s_translate = celery.signature(
#            'cic_eth.ext.address.translate',
#            [
#                result,
#                self.trusted_addresses,
#                chain_str,
#                ],
#            queue=self.queue,
#            )
#        s_translate.link(s)
#        s_translate.apply_async()
        t = s.apply_async()
        return s


    def parse_data(self, tx):
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
                    (transfer_type, transfer_data) = parser(tx)
                    break
                else:
                    pass
            except RequestMismatchException:
                continue


        logg.debug('resolved method {}'.format(transfer_type))

        if transfer_data != None:
            transfer_data['status'] = tx.status

        return (transfer_type, transfer_data)


    def filter(self, conn, block, tx, db_session=None):
        transfer_data = None
        transfer_type = None
        try:
            (transfer_type, transfer_data) = self.parse_data(tx)
        except TypeError:
            logg.debug('invalid method data length for tx {}'.format(tx.hash))
            return

        if len(tx.payload) < 8:
            logg.debug('callbacks filter data length not sufficient for method signature in tx {}, skipping'.format(tx.hash))
            return

        logg.debug('checking callbacks filter input {}'.format(tx.payload[:8]))

        if transfer_data != None:
            token_symbol = None
            result = None
            try:
                tokentx = ExtendedTx(conn, tx.hash, self.chain_spec)
                tokentx.set_actors(transfer_data['from'], transfer_data['to'], self.trusted_addresses)
                tokentx.set_tokens(transfer_data['token_address'], transfer_data['value'])
                if transfer_data['status'] == 0:
                    tokentx.set_status(1)
                else:
                    tokentx.set_status(0)
                t = self.call_back(transfer_type, tokentx.to_dict())
                logg.info('callback success task id {} tx {}'.format(t, tx.hash))
            except UnknownContractError:
                logg.debug('callback filter {}:{} skipping "transfer" method on unknown contract {} tx {}'.format(tx.queue, tx.method, transfer_data['to'], tx.hash))


    def __str__(self):
        return 'cic-eth callbacks'
