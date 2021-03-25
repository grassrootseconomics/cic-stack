# standard imports
import logging

# external imports
import celery
from chainlib.eth.gas import Gas
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        transaction,
        receipt,
        )

# local imports
from cic_eth.queue.tx import register_tx
from cic_eth.eth.tx import cache_gas_data

logg = logging.getLogger()


def test_tx_send(
        init_database,
        default_chain_spec,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_worker,
        ):

    chain_id = default_chain_spec.chain_id()
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, chain_id=chain_id)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 1024, tx_format=TxFormat.RLP_SIGNED)
    #unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), chain_id)
    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

    s_send = celery.signature(
            'cic_eth.eth.tx.send',
            [
                [tx_signed_raw_hex],
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    t = s_send.apply_async()
    r = t.get()
    assert t.successful()

    o = transaction(tx_hash_hex)
    tx = eth_rpc.do(o)
    assert r == tx['hash']

    o = receipt(tx_hash_hex)
    rcpt = eth_rpc.do(o)
    assert rcpt['status'] == 1
