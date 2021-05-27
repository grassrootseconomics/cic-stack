# standard imports
import logging

# external imports
import celery
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import OverrideNonceOracle
from chainqueue.tx import (
        create as queue_create,
        )
from chainlib.eth.gas import (
        Gas,
        OverrideGasOracle,
        )
from chainlib.eth.tx import TxFormat
from chainqueue.query import get_nonce_tx_cache
from chainqueue.db.models.otx import Otx
from chainqueue.db.enum import StatusBits
from hexathon import add_0x

# local imports
from cic_eth.admin.nonce import shift_nonce
from cic_eth.eth.gas import cache_gas_data

logg = logging.getLogger()


def test_shift_nonce(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        celery_session_worker,
        caplog,
        ):

    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(limit=21000, conn=eth_rpc)

    tx_hashes = []
    txs = []

    for i in range(10):
        c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
        queue_create(
                default_chain_spec,
                42+i,
                agent_roles['ALICE'],
                tx_hash_hex,
                tx_signed_raw_hex,
                session=init_database,
                )
        cache_gas_data(
                tx_hash_hex,
                tx_signed_raw_hex,
                default_chain_spec.asdict(),
                )
        tx_hashes.append(tx_hash_hex)
        txs.append(tx_signed_raw_hex)

    init_database.commit()

    s = celery.signature(
            'cic_eth.admin.nonce.shift_nonce',
            [
                str(default_chain_spec),
                tx_hashes[3],
                ],
            queue=None
            )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful()
    init_database.commit()


    for i in range(42+4, 42+10):
        txs = get_nonce_tx_cache(default_chain_spec, i, agent_roles['ALICE'], session=init_database)
        for k in txs.keys():
            hsh = add_0x(k)
            otx = Otx.load(hsh, session=init_database)
            logg.debug('checking nonce {} tx {} status {}'.format(i, otx.tx_hash, otx.status))
            if add_0x(k) == tx_hashes[i-42]:
                assert otx.status & StatusBits.OBSOLETE == StatusBits.OBSOLETE
            else:
                assert otx.status == 1
