# standard imports
import logging

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


def do(config, tokens, accounts, block_number, tx_index):
    logg.debug('running {} {} {}'.format(__name__, tokens, accounts))
