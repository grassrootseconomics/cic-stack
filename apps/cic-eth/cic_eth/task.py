# import
import time
import logging
import uuid

# external imports
import celery
import sqlalchemy
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import RPCGasOracle
from cic_eth_registry import CICRegistry
from cic_eth_registry.error import UnknownContractError

# local imports
from cic_eth.error import SeppukuError
from cic_eth.db.models.base import SessionBase

#logg = logging.getLogger().getChild(__name__)
logg = logging.getLogger()

celery_app = celery.current_app


class BaseTask(celery.Task):

    session_func = SessionBase.create_session
    call_address = ZERO_ADDRESS
    trusted_addresses = []
    min_fee_price = 1
    create_nonce_oracle = RPCNonceOracle
    default_token_address = None
    default_token_symbol = None
    default_token_name = None
    default_token_decimals = None
    run_dir = '/run'


    def create_gas_oracle(self, conn, code_callback=None, id_generator=None):
        return RPCGasOracle(conn, code_callback=code_callback, min_price=self.min_fee_price, id_generator=id_generator)


    def create_session(self):
        return BaseTask.session_func()


    def log_banner(self):
        logg.debug('task {} root uuid {}'.format(self.__class__.__name__, self.request.root_id))
        return


    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if isinstance(exc, SeppukuError):
            import liveness.linux
            liveness.linux.reset(rundir=self.run_dir)
            logg.critical(einfo)
            msg = 'received critical exception {}, calling shutdown'.format(str(exc))
            s = celery.signature(
                'cic_eth.admin.ctrl.shutdown',
                [msg],
                queue=self.request.delivery_info.get('routing_key'),
                    )
            s.apply_async()

    
class CriticalTask(BaseTask):
    retry_jitter = True
    retry_backoff = True
    retry_backoff_max = 8


class CriticalSQLAlchemyTask(CriticalTask):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        sqlalchemy.exc.ResourceClosedError,
        ) 


class CriticalWeb3Task(CriticalTask):
    autoretry_for = (
        ConnectionError,
        )
    safe_gas_threshold_amount = 60000 * 3
    safe_gas_refill_amount = safe_gas_threshold_amount * 5 
    safe_gas_gifter_balance = safe_gas_threshold_amount * 5 * 100


class CriticalSQLAlchemyAndWeb3Task(CriticalWeb3Task):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        ConnectionError,
        sqlalchemy.exc.ResourceClosedError,
        )


class CriticalSQLAlchemyAndSignerTask(CriticalTask):
     autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        sqlalchemy.exc.ResourceClosedError,
        ) 

class CriticalWeb3AndSignerTask(CriticalWeb3Task):
    autoretry_for = (
        ConnectionError,
        )
    
@celery_app.task()
def check_health(self):
    pass


# TODO: registry / rpc methods should perhaps be moved to better named module
@celery_app.task()
def registry():
    return CICRegistry.address


@celery_app.task(bind=True, base=BaseTask)
def registry_address_lookup(self, chain_spec_dict, address, connection_tag='default'):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    conn = RPCConnection.connect(chain_spec, tag=connection_tag)
    registry = CICRegistry(chain_spec, conn)
    r = registry.by_address(address, sender_address=self.call_address)
    return r


@celery_app.task(throws=(UnknownContractError,))
def registry_name_lookup(chain_spec_dict, name, connection_tag='default'):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    conn = RPCConnection.connect(chain_spec, tag=connection_tag)
    registry = CICRegistry(chain_spec, conn)
    return registry.by_name(name, sender_address=self.call_address)


@celery_app.task()
def rpc_proxy(chain_spec_dict, o, connection_tag='default'):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    conn = RPCConnection.connect(chain_spec, tag=connection_tag)
    return conn.do(o)
