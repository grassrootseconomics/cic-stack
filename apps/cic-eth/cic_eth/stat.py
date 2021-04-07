# standard imports
import logging

# external imports
from chainlib.stat import ChainStat
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )

logg = logging.getLogger().getChild(__name__)

BLOCK_SAMPLES = 10


def init_chain_stat(rpc, block_start=0):
    stat = ChainStat()

    if block_start == 0:
        o = block_latest()
        r = rpc.do(o)
        block_start = int(r, 16)

    for i in range(BLOCK_SAMPLES):
        o = block_by_number(block_start-10+i)
        block_src = rpc.do(o)
        logg.debug('block {}'.format(block_src))
        block = Block(block_src)
        stat.block_apply(block)

    logg.debug('calculated block time {} from {} block samples'.format(stat.block_average(), BLOCK_SAMPLES))
    return stat
