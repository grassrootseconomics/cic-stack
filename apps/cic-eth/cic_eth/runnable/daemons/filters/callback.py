# standard imports
import logging

# third-party imports
import web3
import celery
from cic_registry.error import UnknownContractError
from chainlib.status import Status as TxStatus
from chainlib.eth.address import to_checksum
from chainlib.eth.constant import ZERO_ADDRESS
from hexathon import strip_0x

# local imports
from .base import SyncFilter
from cic_eth.eth.token import (
        unpack_transfer,
        unpack_transferfrom,
        )
from cic_eth.eth.account import unpack_gift
from cic_eth.eth.token import ExtendedTx
from .base import SyncFilter

logg = logging.getLogger(__name__)

transfer_method_signature = 'a9059cbb' # keccak256(transfer(address,uint256))
transferfrom_method_signature = '23b872dd' # keccak256(transferFrom(address,address,uint256))
giveto_method_signature = '63e4bff4' # keccak256(giveTo(address))


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
        logg.debug('have payload {}'.format(tx.payload))
        method_signature = tx.payload[:8]

        logg.debug('tx status {}'.format(tx.status))
        if method_signature == transfer_method_signature:
            transfer_data = unpack_transfer(tx.payload)
            transfer_data['from'] = tx['from']
            transfer_data['token_address'] = tx['to']

        elif method_signature == transferfrom_method_signature:
            transfer_type = 'transferfrom'
            transfer_data = unpack_transferfrom(tx.payload)
            transfer_data['token_address'] = tx['to']

        # TODO: do not rely on logs here
        elif method_signature == giveto_method_signature:
            transfer_type = 'tokengift'
            transfer_data = unpack_gift(tx.payload)
            transfer_data['from'] = tx.inputs[0]
            transfer_data['value'] = 0
            transfer_data['token_address'] = ZERO_ADDRESS
            for l in tx.logs:
                topics = l['topics']
                logg.debug('topixx {}'.format(topics))
                if strip_0x(topics[0]) == '45c201a59ac545000ead84f30b2db67da23353aa1d58ac522c48505412143ffa':
                    transfer_data['value'] = web3.Web3.toInt(hexstr=strip_0x(l['data']))
                    #token_address_bytes = topics[2][32-20:]
                    token_address = strip_0x(topics[2])[64-40:]
                    transfer_data['token_address'] = to_checksum(token_address)

        logg.debug('resolved method {}'.format(transfer_type))

        if transfer_data != None:
            transfer_data['status'] = tx.status

        return (transfer_type, transfer_data)


    def filter(self, conn, block, tx, db_session=None):
        chain_str = str(self.chain_spec)

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
            logg.debug('wtfoo {}'.format(transfer_data))
            token_symbol = None
            result = None
            try:
                tokentx = ExtendedTx(tx.hash, self.chain_spec)
                tokentx.set_actors(transfer_data['from'], transfer_data['to'], self.trusted_addresses)
                tokentx.set_tokens(transfer_data['token_address'], transfer_data['value'])
                if transfer_data['status'] == 0:
                    tokentx.set_status(1)
                else:
                    tokentx.set_status(0)
                t = self.call_back(transfer_type, tokentx.to_dict())
                logg.info('callback success task id {} tx {}'.format(t, tx.hash))
            except UnknownContractError:
                logg.debug('callback filter {}:{} skipping "transfer" method on unknown contract {} tx {}'.format(tc.queue, tc.method, transfer_data['to'], tx.hash))


    def __str__(self):
        return 'cic-eth callbacks'
