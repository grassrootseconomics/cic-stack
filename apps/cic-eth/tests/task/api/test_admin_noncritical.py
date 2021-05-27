# external imports
import pytest
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import OverrideNonceOracle
from chainqueue.tx import create as queue_create
from chainlib.eth.tx import (
        TxFormat,
        )
from chainlib.eth.block import block_latest
from chainlib.eth.gas import (
        Gas,
        OverrideGasOracle,
        )
from chainqueue.state import (
        set_reserved,
        set_sent,
        set_ready,
        )
from chainqueue.db.models.otx import Otx
from chainqueue.db.enum import StatusBits
from chainqueue.query import get_nonce_tx_cache

# local imports
from cic_eth.api.api_admin import AdminApi
from cic_eth.eth.gas import cache_gas_data


def test_registry(
        eth_rpc,
        cic_registry,
        contract_roles,
        celery_session_worker,
        ):

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    t = api.registry()
    r = t.get_leaf()
    assert r == cic_registry


def test_proxy_do(
        default_chain_spec,
        eth_rpc,
        contract_roles,
        celery_session_worker,
        ):

    o = block_latest()
    r = eth_rpc.do(o)
    
    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    t = api.proxy_do(default_chain_spec, o)
    rr = t.get_leaf()

    assert r == rr


def test_resend_inplace(
        init_database,
        default_chain_spec,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            42,
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

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex, session=init_database)

    init_database.commit()

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    t = api.resend(tx_hash_hex, default_chain_spec)
    r = t.get_leaf()
    assert t.successful()


    otx = Otx.load(tx_hash_hex, session=init_database)
    assert otx.status & StatusBits.OBSOLETE == StatusBits.OBSOLETE

    txs = get_nonce_tx_cache(default_chain_spec, otx.nonce, agent_roles['ALICE'], session=init_database)
    assert len(txs) == 2



@pytest.mark.xfail()
def test_resend_clone(
        init_database,
        default_chain_spec,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            42,
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

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex, session=init_database)

    init_database.commit()

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    t = api.resend(tx_hash_hex, default_chain_spec, in_place=False)
    r = t.get_leaf()
    assert t.successful()

    otx = Otx.load(tx_hash_hex, session=init_database)
    assert otx.status & StatusBits.IN_NETWORK == StatusBits.IN_NETWORK
    assert otx.status & StatusBits.OBSOLETE == StatusBits.OBSOLETE

    txs = get_nonce_tx_cache(default_chain_spec, otx.nonce, agent_roles['ALICE'], session=init_database)
    assert len(txs) == 1

    txs = get_nonce_tx_cache(default_chain_spec, otx.nonce + 1, agent_roles['ALICE'], session=init_database)
    assert len(txs) == 1

    otx = Otx.load(txs[0], session=init_database)
    assert otx.status == 0
