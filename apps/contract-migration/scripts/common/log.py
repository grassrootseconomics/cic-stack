# standard imports
import logging

logging.basicConfig(level=logging.WARNING)

default_mutelist = [
        'urllib3',
        'websockets.protocol',
        'web3.RequestManager',
        'web3.providers.WebsocketProvider',
        'web3.providers.HTTPProvider',
        ]

def create(name=None, mutelist=default_mutelist):
    logg = logging.getLogger(name)
    for m in mutelist:
        logging.getLogger(m).setLevel(logging.CRITICAL)
    return logg
