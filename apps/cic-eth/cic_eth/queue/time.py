# standard imports
import logging

# third-party imports
import celery
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainlib.eth.block import block_by_hash
from chainlib.eth.tx import receipt

# local imports
from cic_eth.db.models.otx import Otx
from cic_eth.error import NotLocalTxError
from cic_eth.task import CriticalSQLAlchemyAndWeb3Task

celery_app = celery.current_app

logg = logging.getLogger()


def tx_times(tx_hash, chain_spec):
    rpc = RPCConnection.connect(chain_spec, 'default')
    time_pair = {
            'network': None,
            'queue': None,
            }
    try:
        o = receipt(tx_hash)
        r = rpc.do(o)
        o = block_by_hash(r['block_hash'])
        block = rpc.do(o)
        logg.debug('rcpt {}'.format(block))
        time_pair['network'] = block['timestamp']
    except Exception as e:
        logg.debug('error with getting timestamp details for {}: {}'.format(tx_hash, e))
        pass

    otx = Otx.load(tx_hash)
    if otx != None:
        time_pair['queue'] = int(otx['date_created'].timestamp())

    return time_pair
