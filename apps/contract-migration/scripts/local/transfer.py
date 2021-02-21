# standard imports
import logging
import random

# external imports
from cic_eth.api.api_task import Api

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

queue = 'cic-eth'
name = 'erc20_transfer'


def do(token_pair, sender, recipient, sender_balance, aux, block_number, tx_index):

    logg.debug('running {} {} {} {}'.format(__name__, token_pair, sender, recipient))

    decimals = token_pair[0].decimals()
    balance_units = int(sender_balance / decimals)

    if balance_units == 0:
        return (AttributeError('sender {} has zero balance'), None, 0,)

    spend_units = random.randint(1, balance_units)
    spend_value = spend_units * decimals

    api = Api(
        str(aux['chain_spec']),
        queue=queue,
        callback_param='{}:{}:{}:{}'.format(aux['redis_host_callback'], aux['redis_port_callback'], aux['redis_db'], aux['redis_channel']),
        callback_task='cic_eth.callbacks.redis.redis',
        callback_queue=queue,
        )
    t = api.transfer(sender, recipient, spend_value, token_pair[0].symbol())

    changed_sender_balance = sender_balance - spend_value

    return (None, t, changed_sender_balance,)
