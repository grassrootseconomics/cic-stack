# external imports
from chainqueue.db.enum import (
        StatusEnum,
        StatusBits,
        )
from chainlib.connection import RPCConnection
from chainlib.eth.gas import (
        RPCGasOracle,
        Gas,
        )
from chainlib.chain import ChainSpec

# local imports
from cic_eth.db.enum import LockEnum
from cic_eth.db.models.lock import Lock
from cic_eth.queue.query import get_upcoming_tx
from cic_eth.queue.tx import register_tx
from cic_eth.eth.tx import cache_gas_data

# test imports
from tests.util.nonce import StaticNonceOracle


def test_upcoming_with_lock(
    default_chain_spec,
    init_database,
    eth_rpc,
    eth_signer,
    agent_roles,
    ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = StaticNonceOracle(42)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    (tx_hash_hex, tx_rpc) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6))
    tx_signed_raw_hex = tx_rpc['params'][0]

    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

    txs = get_upcoming_tx(default_chain_spec, StatusEnum.PENDING)
    assert len(txs.keys()) == 1

    Lock.set(str(default_chain_spec), LockEnum.SEND, address=agent_roles['ALICE'])

    txs = get_upcoming_tx(default_chain_spec, StatusEnum.PENDING)
    assert len(txs.keys()) == 0

    (tx_hash_hex, tx_rpc) = c.create(agent_roles['BOB'], agent_roles['ALICE'], 100 * (10 ** 6))
    tx_signed_raw_hex = tx_rpc['params'][0]

    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())
 
    txs = get_upcoming_tx(default_chain_spec, StatusEnum.PENDING)
    assert len(txs.keys()) == 1
