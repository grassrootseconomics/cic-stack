# standard imports
import logging

# external imports
import celery
import moolb
from chainlib.eth.tx import (
        count,
        receipt,
        )
from eth_erc20 import ERC20
from chainlib.eth.nonce import RPCNonceOracle
from hexathon import add_0x 

# local imports
from cic_eth.db.models.nonce import (
        NonceReservation,
        Nonce,
        )

logg = logging.getLogger()


def test_filter_process(
        init_database,
        default_chain_spec,
        init_eth_tester,
        eth_rpc,
        eth_signer,
        agent_roles,
        init_custodial,
        cic_registry,
        foo_token,
        celery_session_worker,
        ):

    b = moolb.Bloom(1024, 3)
    t = moolb.Bloom(1024, 3)

    tx_hashes = []

    # external tx
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)

    init_eth_tester.mine_blocks(13)
    c = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.transfer(foo_token, agent_roles['ALICE'], agent_roles['BOB'], 1024)
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    block_bytes = r['block_number'].to_bytes(4, 'big')
    b.add(block_bytes)
    tx_index_bytes = r['transaction_index'].to_bytes(4, 'big')
    t.add(block_bytes + tx_index_bytes)
    tx_hashes.append(tx_hash_hex)

    # external tx
    init_eth_tester.mine_blocks(28)
    c = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.transfer(foo_token, agent_roles['ALICE'], agent_roles['BOB'], 512)
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    block_bytes = r['block_number'].to_bytes(4, 'big')
    b.add(block_bytes)
    tx_index_bytes = r['transaction_index'].to_bytes(4, 'big')
    t.add(block_bytes + tx_index_bytes)
    tx_hashes.append(tx_hash_hex)

    init_eth_tester.mine_blocks(10)
        
    o = {
        'alg': 'sha256',
        'filter_rounds': 3,
        'low': 0,
        'high': 50,
        'block_filter': b.to_bytes().hex(),
        'blocktx_filter': t.to_bytes().hex(),
            }

    s = celery.signature(
            'cic_eth.ext.tx.list_tx_by_bloom',
        [
            o,
            agent_roles['BOB'],
            default_chain_spec.asdict(),
            ],
        queue=None
        )
    t = s.apply_async()
    r = t.get() 

    assert len(r) == 2
    for tx_hash in r.keys():
        tx_hashes.remove(add_0x(tx_hash))
    assert len(tx_hashes) == 0
