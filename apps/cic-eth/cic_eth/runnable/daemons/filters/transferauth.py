# standard imports
import logging

# external imports
import celery
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainlib.eth.address import to_checksum
from .base import SyncFilter


logg = logging.getLogger(__name__)

transfer_request_signature = 'ed71262a'

def unpack_create_request(data):

    data = strip_0x(data)
    cursor = 0
    f = data[cursor:cursor+8]
    cursor += 8

    if f != transfer_request_signature:
        raise ValueError('Invalid create request data ({})'.format(f))

    o = {}
    o['sender'] = data[cursor+24:cursor+64]
    cursor += 64
    o['recipient'] = data[cursor+24:cursor+64]
    cursor += 64
    o['token'] = data[cursor+24:cursor+64]
    cursor += 64
    o['value'] = int(data[cursor:], 16)
    return o


class TransferAuthFilter(SyncFilter):

    def __init__(self, registry, chain_spec, queue=None):
        self.queue = queue
        self.chain_spec = chain_spec
        self.transfer_request_contract = registry.get_contract(self.chain_spec, 'TransferAuthorization')


    def filter(self, conn, block, tx, session): #rcpt, chain_str, session=None):

        if tx.payload == None:
            logg.debug('no payload')
            return False

        payloadlength = len(tx.payload)
        if payloadlength != 8+256:
            logg.debug('{} below minimum length for a transfer auth call'.format(payloadlength))
            logg.debug('payload {}'.format(tx.payload))
            return False

        recipient = tx.inputs[0]
        if recipient != self.transfer_request_contract.address():
            logg.debug('not our transfer auth contract address {}'.format(recipient))
            return False

        o = unpack_create_request(tx.payload) 
           
        sender = add_0x(to_checksum(o['sender']))
        recipient = add_0x(to_checksum(recipient))
        token = add_0x(to_checksum(o['token']))
        s = celery.signature(
            'cic_eth.eth.token.approve',
            [
                [
                    {
                        'address': token,
                        },
                    ],
                sender,
                recipient,
                o['value'],
                str(self.chain_spec),
                ],
            queue=self.queue,
            )
        t = s.apply_async()
        return True


    def __str__(self):
        return 'cic-eth transfer auth filter'
