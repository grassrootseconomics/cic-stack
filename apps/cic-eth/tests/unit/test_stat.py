# standard imports
import datetime

# local imports
from cic_eth.stat import init_chain_stat


def test_chain_stat(
        eth_rpc,
        init_eth_tester,
        ):

    now = int(datetime.datetime.now().timestamp()) + 1
    for i in range(11):
        init_eth_tester.time_travel(now + (i * 2))
    
    s = init_chain_stat(eth_rpc, block_start=0)
    assert s.block_average() == 2
