# standard imports
import logging

# external imports
from chainlib.connection import RPCConnection
from chainlib.chain import ChainSpec
from chainlib.eth.gas import balance

# local imports
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.base import SessionBase
from cic_eth.db.enum import LockEnum
from cic_eth.error import LockedError
from cic_eth.admin.ctrl import check_lock
from cic_eth.eth.gas import have_gas_minimum

logg = logging.getLogger(__name__)


def health(*args, **kwargs):

    session = SessionBase.create_session()

    config = kwargs['config']
    chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
    logg.debug('check gas balance of gas gifter for chain {}'.format(chain_spec))

    try:
        check_lock(None, None, LockEnum.INIT)
    except LockedError:
        logg.warning('INIT lock is set, skipping GAS GIFTER balance check.')
        return True

    gas_provider = AccountRole.get_address('GAS_GIFTER', session=session)
    min_gas = int(config.get('ETH_GAS_HOLDER_MINIMUM_UNITS')) * int(config.get('ETH_GAS_GIFTER_REFILL_BUFFER'))
    if config.get('ETH_MIN_FEE_PRICE'):
        min_gas *= int(config.get('ETH_MIN_FEE_PRICE'))

    r = have_gas_minimum(chain_spec, gas_provider, min_gas, session=session)

    session.close()
    
    if not r:
        logg.error('EEK! gas gifter has balance {}, below minimum {}'.format(r, min_gas))

    return r
