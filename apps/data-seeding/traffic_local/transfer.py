# standard imports
import logging
import random

# external imports
from cic_eth.api.api_task import Api

# local imports
from traffic import TaskMode

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

queue = 'cic-eth'
task_name = 'erc20_transfer'
task_mode = TaskMode.SENDER_ACTIVE | TaskMode.RECIPIENT_ACTIVE


def do(token_pair, sender, recipient, sender_balance, aux, block_number):
    """Triggers an ERC20 token transfer through the custodial cic-eth component, with a randomly chosen amount in integer resolution.

    It expects the following aux parameters to exist:
    - redis_host_callback: Redis host name exposed to cic-eth, for callback
    - redis_port_callback: Redis port exposed to cic-eth, for callback
    - redis_db: Redis db, for callback
    - redis_channel: Redis channel, for callback
    - chain_spec: Chain specification for the chain to execute the transfer on

    See local.noop.do for details on parameters and return values.
    """
    logg.debug('running {} {} {} {}'.format(__name__, token_pair, sender, recipient))

    decimals = token_pair[0].decimals()

    logg.debug('sender balacce {}'.format(sender_balance))
    sender_balance_value = sender_balance['balance_network'] - sender_balance['balance_outgoing']

    balance_units = int(sender_balance_value / decimals)

    if balance_units <= 0:
        return (AttributeError('sender {} has zero balance ({} / {})'.format(sender, sender_balance_value, decimals)), None, 0,)

    spend_units = random.randint(1, balance_units)
    spend_value = spend_units * decimals

    api = Api(
        str(aux['CHAIN_SPEC']),
        queue=queue,
        callback_param='{}:{}:{}:{}'.format(aux['_REDIS_HOST_CALLBACK'], aux['_REDIS_PORT_CALLBACK'], aux['_REDIS_DB_CALLBACK'], aux['REDIS_CHANNEL']),
        callback_task='cic_eth.callbacks.redis.redis',
        callback_queue=queue,
        )
    t = api.transfer(sender, recipient, spend_value, token_pair[0].symbol())

    sender_balance['balance_outgoing'] += spend_value
    return (None, t, spend_value, )
