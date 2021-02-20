# standard imports
import logging

# external imports
from cic_eth.api.api_task import Api

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

queue = 'cic-eth'
name = 'account'


def do(tokens, accounts, aux, block_number, tx_index):

    logg.debug('running {} {} {}'.format(__name__, tokens, accounts))
    api = Api(
        str(aux['chain_spec']),
        queue=queue,
        callback_param='{}:{}:{}:{}'.format(aux['redis_host_callback'], aux['redis_port_callback'], aux['redis_db'], aux['redis_channel']),
        callback_task='cic_eth.callbacks.redis.redis',
        callback_queue=queue,
        )
    t = api.create_account(register=True)
    return (None, t,)
