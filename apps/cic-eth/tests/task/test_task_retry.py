# standard imports
import logging
import time
import datetime

# external imports
import pytest
from chainlib.eth.gas import (
        Gas,
        RPCGasOracle,
        OverrideGasOracle,
        )

from chainlib.eth.tx import (
        TxFormat,
        unpack,
        )
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.connection import RPCConnection
from hexathon import strip_0x
from chainqueue.sql.state import (
        set_ready,
        set_reserved,
        set_sent,
        )
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )

# local imports
from cic_eth.sync.retry import RetrySyncer
from cic_eth.queue.tx import queue_create
from cic_eth.eth.gas import cache_gas_data
from cic_eth.queue.query import get_account_tx_local
import cic_eth.cli
from cic_eth.runnable.daemons.filters.straggler import StragglerFilter

logg = logging.getLogger()


class TimeParrot:

    def get(self, v):
        ts = int(datetime.datetime.utcnow().timestamp())
        return str(ts).encode('utf_8')


def test_two_retries(
        load_config,
        init_database,
        default_chain_spec,
        eth_rpc,
        eth_signer,
        agent_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
    tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)
    
    tx_hash_hex_check = queue_create(default_chain_spec, tx['nonce'], tx['from'], tx_hash_hex, tx_signed_raw_hex, session=init_database)

    set_ready(default_chain_spec, tx_hash_hex_check, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex_check, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex_check, session=init_database)

    cache_gas_data(tx_hash_hex_check, tx_signed_raw_hex, default_chain_spec.asdict())
    init_database.commit()

    o = block_latest()
    r = eth_rpc.do(o)

    o = block_by_number(r)
    r = eth_rpc.do(o)
    block = Block.from_src(r)

    retry = RetrySyncer(eth_rpc, default_chain_spec, cic_eth.cli.chain_interface, 0, TimeParrot(), failed_grace_seconds=0)
    fltr = StragglerFilter(default_chain_spec, 100000000, queue=None)
    retry.add_filter(fltr)

    retry.process(eth_rpc, block)

    i = 0
    txs = {}
    while i < 1000:
        txs = get_account_tx_local(default_chain_spec, agent_roles['ALICE'], as_recipient=False)
        if len(list(txs.keys())) == 2:
            break
        time.sleep(0.1)
        i += 1

    assert len(list(txs.keys())) == 2
          
    tx_replacement = None
    tx_hash_hex_replacement = None
    for tx_signed_raw_hex in txs.values():
        tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)
        if strip_0x(tx['hash']) != strip_0x(tx_hash_hex_check):
            tx_replacement = tx
            tx_hash_hex_replacement = tx['hash']
            break

    logg.debug('tx {}'.format(tx_replacement))

    set_ready(default_chain_spec, tx_replacement['hash'], session=init_database)
    set_reserved(default_chain_spec, tx_replacement['hash'], session=init_database)
    set_sent(default_chain_spec, tx_replacement['hash'], session=init_database)
    init_database.commit()

    retry.process(eth_rpc, block)

    i = 0
    txs = {}
    while i < 100:
        txs = get_account_tx_local(default_chain_spec, agent_roles['ALICE'], as_recipient=False)
        if len(list(txs.keys())) == 3:
            break
        time.sleep(0.1)
        i += 1

    assert len(list(txs.keys())) == 3
          
    tx_last = None
    for tx_signed_raw_hex in txs.values():
        tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)
        if strip_0x(tx['hash']) not in [
                strip_0x(tx_hash_hex_check),
                strip_0x(tx_hash_hex_replacement),
                ]:
            tx_last = tx
            break

    logg.debug('tx {}'.format(tx_last))

@pytest.mark.parametrize(
        'gas_price',
        [
            (1),
            (1000000),
            ],
        )
def test_a_bunch_of_retries(
        load_config,
        init_database,
        init_eth_tester,
        default_chain_spec,
        eth_rpc,
        eth_signer,
        agent_roles,
        celery_session_worker,
        gas_price,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    gas_oracle = OverrideGasOracle(price=gas_price, limit=100000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
    tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)
    
    tx_hash_hex_check = queue_create(default_chain_spec, tx['nonce'], tx['from'], tx_hash_hex, tx_signed_raw_hex, session=init_database)

    set_ready(default_chain_spec, tx_hash_hex_check, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex_check, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex_check, session=init_database)

    cache_gas_data(tx_hash_hex_check, tx_signed_raw_hex, default_chain_spec.asdict())
    init_database.commit()


    retry = RetrySyncer(eth_rpc, default_chain_spec, cic_eth.cli.chain_interface, 0, TimeParrot(), failed_grace_seconds=0)
    fltr = StragglerFilter(default_chain_spec, 100000000, queue=None)
    retry.add_filter(fltr)

    i = 1
    for ii in range(3):
        o = block_latest()
        r = eth_rpc.do(o)
        logg.debug('block is now {}'.format(r))

        o = block_by_number(r)
        r = eth_rpc.do(o)
        block = Block.from_src(r)

        retry.process(eth_rpc, block)

        ks = []
        txs = None
        for iii in range(10):
            txs = get_account_tx_local(default_chain_spec, agent_roles['ALICE'], as_recipient=False)
            ks = list(txs.keys())
            if len(ks) > i:
                break
            time.sleep(0.2)
            iii += 1

        assert len(ks) == i + 1

        k = ks[i]
        tx_signed_raw_hex = txs[k]
        i += 1

        tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)
        set_ready(default_chain_spec, tx['hash'], session=init_database)
        set_reserved(default_chain_spec, tx['hash'], session=init_database)
        set_sent(default_chain_spec, tx['hash'], session=init_database)

        init_database.commit()
        init_eth_tester.mine_blocks(1)
