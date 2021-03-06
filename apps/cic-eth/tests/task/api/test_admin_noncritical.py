# standard imports
import logging
import io
import json

# external imports
import pytest
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import (
        nonce,
        OverrideNonceOracle,
        RPCNonceOracle,
        )
from chainqueue.sql.tx import create as queue_create
from chainlib.eth.tx import (
        raw,
        receipt,
        TxFormat,
        Tx,
        )
from chainlib.eth.block import block_latest
from chainlib.eth.gas import (
        Gas,
        OverrideGasOracle,
        )
from chainqueue.sql.state import (
        set_reserved,
        set_sent,
        set_ready,
        )
from chainqueue.db.models.otx import Otx
from chainqueue.db.enum import StatusBits
from eth_erc20 import ERC20
from cic_eth_registry import CICRegistry

# local imports
from cic_eth.api.admin import AdminApi
from cic_eth.eth.gas import cache_gas_data
from cic_eth.eth.erc20 import cache_transfer_data
from cic_eth.queue.query import get_nonce_tx_local

logg = logging.getLogger()


def test_admin_api_tx(
        default_chain_spec,
        init_database,
        init_celery_tasks,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        custodial_roles,
        celery_session_worker,
        foo_token,
        address_declarator,
        cic_registry,
        register_tokens,
        register_lookups,
        caplog,
        ):

    nonce_oracle = RPCNonceOracle(custodial_roles['FOO_TOKEN_GIFTER'], conn=eth_rpc)
    gas_oracle = OverrideGasOracle(limit=100000, conn=eth_rpc)

    o = nonce(custodial_roles['FOO_TOKEN_GIFTER'])
    r = eth_rpc.do(o)
    gifter_nonce = int(r, 16)

    #c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    c = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.transfer(foo_token, custodial_roles['FOO_TOKEN_GIFTER'], agent_roles['ALICE'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
    queue_create(
            default_chain_spec,
            gifter_nonce, # will only work if agent starts at 0
            agent_roles['ALICE'],
            tx_hash_hex,
            tx_signed_raw_hex,
            session=init_database,
            )
    cache_transfer_data(
            tx_hash_hex,
            tx_signed_raw_hex,
            default_chain_spec.asdict(),
            )

    init_database.commit()

    o = raw(tx_signed_raw_hex)
    eth_rpc.do(o)

    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex, session=init_database)

    # lookup by transaction hash, without registry
    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    tx = api.tx(default_chain_spec, tx_hash=tx_hash_hex)
    logg.debug('deployed {}'.format(contract_roles['CONTRACT_DEPLOYER']))
    assert tx['tx_hash'] == tx_hash_hex 

    # lookup by RLP transaction, without registry
    tx = api.tx(default_chain_spec, tx_raw=tx_signed_raw_hex)
    assert tx['tx_hash'] == tx_hash_hex 

    # lookup by transaction hash, with registry
    registry = CICRegistry(default_chain_spec, eth_rpc)
    tx = api.tx(default_chain_spec, tx_hash=tx_hash_hex, registry=registry)
    assert tx['tx_hash'] == tx_hash_hex 

    # lookup by transaction hash, using writer
    buf = io.StringIO()
    api.tx(default_chain_spec, tx_hash=tx_hash_hex, renderer=json.dumps, w=buf)
    tx = json.loads(buf.getvalue())
    assert tx['tx_hash'] == tx_hash_hex 


def test_admin_api_account(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        caplog,
        ):

    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(limit=21000, conn=eth_rpc)

    tx_hashes_alice = []
    txs_alice = []

    for i in range(3):
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
        tx_hashes_alice.append(tx_hash_hex)
        txs_alice.append(tx_signed_raw_hex)

    init_database.commit()

    nonce_oracle = OverrideNonceOracle(agent_roles['BOB'], 13)
    tx_hashes_bob = []
    txs_bob = []

    for i in range(2):
        c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['BOB'], agent_roles['ALICE'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
        queue_create(
                default_chain_spec,
                13+i,
                agent_roles['BOB'],
                tx_hash_hex,
                tx_signed_raw_hex,
                session=init_database,
                )
        cache_gas_data(
                tx_hash_hex,
                tx_signed_raw_hex,
                default_chain_spec.asdict(),
                )
        tx_hashes_bob.append(tx_hash_hex)
        txs_bob.append(tx_signed_raw_hex)

    init_database.commit()


    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    r = api.account(default_chain_spec, agent_roles['ALICE'], include_sender=True, include_recipient=True)
    assert len(r) == 5

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    r = api.account(default_chain_spec, agent_roles['ALICE'], include_sender=False)
    assert len(r) == 2

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    r = api.account(default_chain_spec, agent_roles['ALICE'], include_recipient=False)
    assert len(r) == 3


def test_admin_api_txs_latest(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        caplog,
        ):

    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(limit=21000, conn=eth_rpc)

    tx_hashes_alice = []
    txs_alice = []

    for i in range(6):
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
        tx_hashes_alice.append(tx_hash_hex)
        txs_alice.append(tx_signed_raw_hex)

    init_database.commit()

    nonce_oracle = OverrideNonceOracle(agent_roles['BOB'], 13)
    tx_hashes_bob = []
    txs_bob = []

    for i in range(4):
        c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['BOB'], agent_roles['ALICE'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
        queue_create(
                default_chain_spec,
                13+i,
                agent_roles['BOB'],
                tx_hash_hex,
                tx_signed_raw_hex,
                session=init_database,
                )
        cache_gas_data(
                tx_hash_hex,
                tx_signed_raw_hex,
                default_chain_spec.asdict(),
                )
        tx_hashes_bob.append(tx_hash_hex)
        txs_bob.append(tx_signed_raw_hex)

    init_database.commit()


    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    r = api.txs_latest(default_chain_spec)

    assert len(r) == 10
    assert r[0]["tx_hash"] == "0x85526a782ea231cdc4ffedffb3d1140974d6a0f37acdd33ffe6183e152203100"
    assert r[0]["nonce"] == 16
    assert r[1]["nonce"] == 15

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    r = api.txs_latest(default_chain_spec, count=1)
    assert len(r) == 1
    assert r[0]["tx_hash"] == "0x85526a782ea231cdc4ffedffb3d1140974d6a0f37acdd33ffe6183e152203100"


def test_admin_api_account_writer(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        caplog,
        ):

    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(limit=21000, conn=eth_rpc)

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

    init_database.commit()

    buf = io.StringIO()
    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['CONTRACT_DEPLOYER'])
    api.account(default_chain_spec, agent_roles['ALICE'], renderer=json.dumps, w=buf)

    # TODO: improve eval
    tx = json.loads(buf.getvalue())
    assert tx['tx_hash'] == tx_hash_hex


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
    t = api.resend(tx_hash_hex, default_chain_spec, unlock=True)
    r = t.get_leaf()
    assert t.successful()


    otx = Otx.load(tx_hash_hex, session=init_database)
    assert otx.status & StatusBits.OBSOLETE == StatusBits.OBSOLETE

    txs = get_nonce_tx_local(default_chain_spec, otx.nonce, agent_roles['ALICE'], session=init_database)
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

    txs = get_nonce_tx_local(default_chain_spec, otx.nonce, agent_roles['ALICE'], session=init_database)
    assert len(txs) == 1

    txs = get_nonce_tx_local(default_chain_spec, otx.nonce + 1, agent_roles['ALICE'], session=init_database)
    assert len(txs) == 1

    otx = Otx.load(txs[0], session=init_database)
    assert otx.status == 0
