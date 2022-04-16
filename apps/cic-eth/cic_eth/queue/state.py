# external imports
from chainlib.chain import ChainSpec
import chainqueue.sql.state

# local imports
import celery
from cic_eth.task import CriticalSQLAlchemyTask
from cic_eth.db.models.base import SessionBase
from cic_eth.encode import tx_normalize

celery_app = celery.current_app


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_sent(chain_spec_dict, tx_hash, fail=False):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_sent(chain_spec, tx_hash, fail, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_final(chain_spec_dict, tx_hash, block=None, tx_index=None, fail=False):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_final(chain_spec, tx_hash, block=block, tx_index=tx_index, fail=fail, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_cancel(chain_spec_dict, tx_hash, manual=False):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_cancel(chain_spec, tx_hash, manual, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_rejected(chain_spec_dict, tx_hash):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_rejected(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_fubar(chain_spec_dict, tx_hash):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_fubar(chain_spec, tx_hash, session=session)
    session.close()
    return 'foo ' + r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_manual(chain_spec_dict, tx_hash):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_manual(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_ready(chain_spec_dict, tx_hash):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_ready(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_reserved(chain_spec_dict, tx_hash):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_reserved(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_waitforgas(chain_spec_dict, tx_hash):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_waitforgas(chain_spec, tx_hash, session=session)
    session.close()
    return r
    

@celery_app.task(base=CriticalSQLAlchemyTask)
def get_state_log(chain_spec_dict, tx_hash):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.get_state_log(chain_spec, tx_hash, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def obsolete(chain_spec_dict, tx_hash, final):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.obsolete_by_cache(chain_spec, tx_hash, final, session=session)
    session.close()
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def set_checked(chain_spec_dict, tx_hash):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    session = SessionBase.create_session()
    r = chainqueue.sql.state.set_updated(chain_spec, tx_hash, session=session)
    session.close()
    return r
