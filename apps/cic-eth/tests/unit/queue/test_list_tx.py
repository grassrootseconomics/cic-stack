# standard imports
import logging

# external imports
from chainlib.connection import RPCConnection
from chainlib.eth.gas import RPCGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import Gas

# local imports
from cic_eth.queue.tx import get_status_tx
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        )
from cic_eth.queue.tx import create as queue_create
from cic_eth.eth.tx import cache_gas_data
from cic_eth.queue.tx import register_tx
from cic_eth.db.models.otx import Otx

logg = logging.getLogger()


def test_status_tx_list(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')

    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    (tx_hash_hex, o) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 1024)
    r = rpc.do(o)

    tx_signed_raw_hex = o['params'][0]
    #queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

    q = init_database.query(Otx)
    otx = q.get(1)
    otx.sendfail(session=init_database)
    init_database.add(otx)
    init_database.commit()
    init_database.refresh(otx)

    txs = get_status_tx(StatusBits.LOCAL_ERROR, session=init_database)
    assert len(txs) == 1

    otx.sendfail(session=init_database)
    otx.retry(session=init_database)
    init_database.add(otx)
    init_database.commit()
    init_database.refresh(otx)

    txs = get_status_tx(StatusBits.LOCAL_ERROR, session=init_database)
    assert len(txs) == 1

    txs = get_status_tx(StatusBits.QUEUED, session=init_database)
    assert len(txs) == 1

    txs = get_status_tx(StatusBits.QUEUED, not_status=StatusBits.LOCAL_ERROR, session=init_database)
    assert len(txs) == 0

    txs = get_status_tx(StatusBits.QUEUED, not_status=StatusBits.IN_NETWORK, session=init_database)
    assert len(txs) == 1

    txs = get_status_tx(StatusBits.IN_NETWORK, session=init_database)
    assert len(txs) == 0

