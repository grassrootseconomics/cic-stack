# external imports
from chainlib.chain import ChainSpec
import chainqueue.state

# local imports
import celery
from cic_eth.task import CriticalSQLAlchemyTask
from cic_eth.db.models.base import SessionBase

celery_app = celery.current_app


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_sent(chain_spec_dict, tx_hash, fail=False):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_sent(chain_spec, tx_hash, fail, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_final(chain_spec_dict, tx_hash, block=None, fail=False):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_final(chain_spec, tx_hash, block, fail, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_cancel(chain_spec_dict, tx_hash, manual=False):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_cancel(chain_spec, tx_hash, manual, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_rejected(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_rejected(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_fubar(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_fubar(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_manual(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_manual(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_ready(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_ready(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_reserved(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_reserved(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_waitforgas(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.set_waitforgas(chain_spec, tx_hash, session=session)
    session.close()
    return r
    

@celery_app.task(base=CriticalSQLAlchemyTask)
def get_state_log(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.state.get_state_log(chain_spec, tx_hash, session=session)
    session.close()
    return r
