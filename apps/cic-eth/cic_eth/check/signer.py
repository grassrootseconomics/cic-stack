# standard imports
import logging
from urllib.error import URLError

# external imports
from chainlib.connection import RPCConnection
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.sign import sign_message
from chainlib.error import JSONRPCException

logg = logging.getLogger().getChild(__name__)


def health(*args, **kwargs):
    conn = RPCConnection.connect(kwargs['config'].get('CIC_CHAIN_SPEC'), tag='signer')
    try:
        conn.do(sign_message(ZERO_ADDRESS, '0x2a'))
    except FileNotFoundError:
        return False
    except ConnectionError:
        return False
    except URLError:
        return False
    except JSONRPCException as e:
        pass
    return True
