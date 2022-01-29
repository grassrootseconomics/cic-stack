# standard imports
import logging

# external imports
from cic_eth.api.api_task import Api

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

queue = 'cic-eth'
name = 'account'


def create_user(chain_spec, redis_host_callback, redis_port_callback, redis_db, redis_channel):
    api = Api(
        str(chain_spec),
        queue=queue,
        callback_param='{}:{}:{}:{}'.format(redis_host_callback, redis_port_callback, redis_db, redis_channel),
        callback_task='cic_eth.callbacks.redis.redis',
        callback_queue=queue,
        )

    return api.create_account(register=True)


def do(token_pair, sender, recipient, sender_balance, aux, block_number):
    """Triggers creation and registration of new account through the custodial cic-eth component.

    It expects the following aux parameters to exist:
    - redis_host_callback: Redis host name exposed to cic-eth, for callback
    - redis_port_callback: Redis port exposed to cic-eth, for callback
    - redis_db: Redis db, for callback
    - redis_channel: Redis channel, for callback
    - chain_spec: Chain specification for the chain to execute the transfer on

    See local.noop.do for details on parameters and return values.
    """
    logg.debug('running {} {} {}'.format(__name__, token_pair, sender, recipient))
    t = create_user(aux['CHAIN_SPEC'], aux['_REDIS_HOST_CALLBACK'], aux['_REDIS_PORT_CALLBACK'], aux['_REDIS_DB_CALLBACK'], aux['REDIS_CHANNEL'])

    return (None, t, sender_balance, )
