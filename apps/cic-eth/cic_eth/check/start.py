# external imports
from chainlib.chain import ChainSpec

# local imports
from cic_eth.admin.ctrl import check_lock
from cic_eth.enum import LockEnum
from cic_eth.error import LockedError


def health(*args, **kwargs):
    config = kwargs['config']
    chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

    try:
        check_lock(None, chain_spec.asdict(), LockEnum.START)
    except LockedError as e:
        return False
    return True
