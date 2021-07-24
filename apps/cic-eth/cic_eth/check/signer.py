# standard imports
import time
import logging
from urllib.error import URLError

# external imports
from chainlib.connection import RPCConnection
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.sign import sign_message
from chainlib.error import JSONRPCException

logg = logging.getLogger().getChild(__name__)


def health(*args, **kwargs):
    blocked = True
    max_attempts = 5
    conn = RPCConnection.connect(kwargs['config'].get('CHAIN_SPEC'), tag='signer')
    for i in range(max_attempts):
        idx = i + 1
        logg.debug('attempt signer connection check {}/{}'.format(idx, max_attempts))
        try:
            conn.do(sign_message(ZERO_ADDRESS, '0x2a'))
        except FileNotFoundError:
            pass
        except ConnectionError:
            pass
        except URLError:
            pass
        except JSONRPCException:
            logg.debug('signer connection succeeded')
            return True

        if idx < max_attempts:
            time.sleep(0.5)

    return False
