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

logg = logging.getLogger().getChild(__name__)


def health(*args, **kwargs):

    session = SessionBase.create_session()

    config = kwargs['config']
    chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
    logg.debug('check gas balance of gas gifter for chain {}'.format(chain_spec))

    try:
        check_lock(None, None, LockEnum.INIT)
    except LockedError:
        logg.warning('INIT lock is set, skipping GAS GIFTER balance check.')
        return True

    gas_provider = AccountRole.get_address('GAS_GIFTER', session=session)
    session.close()

    rpc = RPCConnection.connect(chain_spec, 'default')
    o = balance(gas_provider)
    r = rpc.do(o)
    try: 
        r = int(r, 16)
    except TypeError:
        r = int(r)
    gas_min = int(config.get('ETH_GAS_GIFTER_MINIMUM_BALANCE'))
    if r < gas_min:
        logg.error('EEK! gas gifter has balance {}, below minimum {}'.format(r, gas_min))
        return False

    return True
