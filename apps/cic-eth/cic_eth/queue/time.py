# standard imports
import logging

# third-party imports
import web3
import celery
from cic_registry.chain import ChainSpec

# local imports
from cic_eth.eth.rpc import RpcClient
from cic_eth.db.models.otx import Otx
from cic_eth.error import NotLocalTxError

celery_app = celery.current_app

logg = logging.getLogger()


# TODO: This method does not belong in the _queue_ module, it operates across queue and network
@celery_app.task()
def tx_times(tx_hash, chain_str):
    chain_spec = ChainSpec.from_chain_str(chain_str)
    c = RpcClient(chain_spec)
    time_pair = {
            'network': None,
            'queue': None,
            }
    try:
        rcpt = c.w3.eth.getTransactionReceipt(tx_hash)
        block = c.w3.eth.getBlock(rcpt['blockHash'])
        logg.debug('rcpt {}'.format(block))
        time_pair['network'] = block['timestamp']
    except web3.exceptions.TransactionNotFound:
        pass

    otx = Otx.load(tx_hash)
    if otx != None:
        time_pair['queue'] = int(otx['date_created'].timestamp())

    return time_pair
