# external imports
from chainlib.chain import ChainSpec
import chainqueue.state

# local imports
from cic_eth.task import CriticalSQLAlchemyTask


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_sent_status(chain_spec_dict, tx_hash, fail=False):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_sent_status(chain_spec, tx_hash, fail)


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_final_status(chain_spec_dict, tx_hash, block=None, fail=False):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_final_status(chain_spec, tx_hash, block, fail)


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_cancel(chain_spec_dict, tx_hash, manual=False):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_cancel(chain_spec, tx_hash, manual)
    
@celery_app.task(base=CriticalSQLAlchemyTask)
def set_rejected(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_rejected(chain_spec, tx_hash)


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_fubar(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_fubar(chain_spec, tx_hash)


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_manual(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_manual(chain_spec, tx_hash)
    

@celery_app.task(base=CriticalSQLAlchemyTask)
def set_ready(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_ready(chain_spec, tx_hash)
    

@celery_app.task(base=CriticalSQLAlchemyTask)
def set_reserved(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_reserved(chain_spec, tx_hash)
    

@celery_app.task(base=CriticalSQLAlchemyTask)
def set_waitforgas(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.set_waitforgas(chain_spec, tx_hash)
    

@celery_app.task(base=CriticalSQLAlchemyTask)
def get_state_log(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return chainqueue.state.get_state_log(chain_spec, tx_hash)


