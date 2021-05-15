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

logg = logging.getLogger().getChild(__name__)



class CallbackFilter(SyncFilter):

    trusted_addresses = []

    def __init__(self, chain_spec, method, queue, caller_address=ZERO_ADDRESS):
        self.queue = queue
        self.method = method
        self.chain_spec = chain_spec
        self.caller_address = caller_address


    def parse_transfer(self, tx, conn):
        if not tx.payload:
            return (None, None)
        r = ERC20.parse_transfer_request(tx.payload)
        transfer_data = {}
        transfer_data['to'] = r[0]
        transfer_data['value'] = r[1]
        transfer_data['from'] = tx.outputs[0]
        transfer_data['token_address'] = tx.inputs[0]
        return ('transfer', transfer_data)


    def parse_transferfrom(self, tx, conn):
        if not tx.payload:
            return (None, None)
        r = ERC20.parse_transfer_from_request(tx.payload)
        transfer_data = {}
        transfer_data['from'] = r[0]
        transfer_data['to'] = r[1]
        transfer_data['value'] = r[2]
        transfer_data['token_address'] = tx.inputs[0]
        return ('transferfrom', transfer_data)


    def parse_giftto(self, tx, conn):
        if not tx.payload:
            return (None, None)
        r = Faucet.parse_give_to_request(tx.payload)
        transfer_data = {}
        transfer_data['to'] = r[0]
        transfer_data['value'] = tx.value
        transfer_data['from'] = tx.outputs[0]
        #transfer_data['token_address'] = tx.inputs[0]
        faucet_contract = tx.inputs[0]

        o = Faucet.token(faucet_contract, sender_address=self.caller_address)
        r = conn.do(o)
        transfer_data['token_address'] = add_0x(c.parse_token(r))

        o = c.token_amount(faucet_contract, sender_address=self.caller_address)
        r = conn.do(o)
        transfer_data['value'] = c.parse_token_amount(r)

        return ('tokengift', transfer_data)


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
        return t


    def parse_data(self, tx, conn):
        transfer_type = None
        transfer_data = None
        # TODO: what's with the mix of attributes and dict keys
        logg.debug('have payload {}'.format(tx.payload))

        logg.debug('tx status {}'.format(tx.status))

        for parser in [
                self.parse_transfer,
                self.parse_transferfrom,
                self.parse_giftto,
                ]:
            try:
                if tx:
                    (transfer_type, transfer_data) = parser(tx, conn)
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
                logg.info('callback success task id {} tx {} queue {}'.format(t, tx.hash, t.queue))
            except UnknownContractError:
                logg.debug('callback filter {}:{} skipping "transfer" method on unknown contract {} tx {}'.format(self.queue, self.method, transfer_data['to'], tx.hash))
            except NotAContractError:
                logg.debug('callback filter {}:{} skipping "transfer" on non-contract address {} tx {}'.format(self.queue, self.method, transfer_data['to'], tx.hash))


    def __str__(self):
        return 'cic-eth callbacks'
