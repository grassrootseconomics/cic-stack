# standard imports
import logging

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


def do(tokens, accounts, aux, block_number, tx_index):
    logg.debug('running {} {} {}'.format(__name__, tokens, accounts))

    return (None, None,)
