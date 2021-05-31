# external imports
import celery
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import (
        OverrideNonceOracle,
        RPCNonceOracle,
        )
from chainlib.eth.gas import (
        OverrideGasOracle,
        Gas,
        )
from chainlib.eth.tx import (
        TxFormat,
        )
from chainlib.eth.constant import (
        MINIMUM_FEE_UNITS,
        MINIMUM_FEE_PRICE,
        )
from chainqueue.tx import create as queue_create
from chainqueue.query import get_tx
from chainqueue.db.enum import StatusBits

# local imports
from cic_eth.eth.gas import cache_gas_data
from cic_eth.error import OutOfGasError


def test_task_check_gas_ok(
        default_chain_spec,
        eth_rpc,
        eth_signer,
        init_database,
        agent_roles,
        custodial_roles,
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

    init_database.commit()

    s = celery.signature(
            'cic_eth.eth.gas.check_gas',
            [
                [
                    tx_hash_hex,
                    ],
                default_chain_spec.asdict(),
                ],
            queue=None
            )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful()

    init_database.commit()

    tx = get_tx(default_chain_spec, tx_hash_hex, session=init_database)
    assert tx['status'] & StatusBits.QUEUED == StatusBits.QUEUED


def test_task_check_gas_insufficient(
        default_chain_spec,
        eth_rpc,
        eth_signer,
        init_database,
        agent_roles,
        custodial_roles,
        celery_session_worker,
        whoever,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(whoever, 42)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(whoever, agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            42,
            whoever,
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

    s = celery.signature(
            'cic_eth.eth.gas.check_gas',
            [
                [
                    tx_hash_hex,
                    ],
                default_chain_spec.asdict(),
                ],
            queue=None
            )
    t = s.apply_async()
    try:
        r = t.get_leaf()
    except OutOfGasError:
        pass

    init_database.commit()

    tx = get_tx(default_chain_spec, tx_hash_hex, session=init_database)
    assert tx['status'] & StatusBits.GAS_ISSUES == StatusBits.GAS_ISSUES


def test_task_check_gas_low(
        default_chain_spec,
        eth_rpc,
        eth_signer,
        init_database,
        agent_roles,
        custodial_roles,
        celery_session_worker,
        whoever,
        ):

    gas_oracle = OverrideGasOracle(price=MINIMUM_FEE_PRICE, limit=MINIMUM_FEE_UNITS)
    nonce_oracle = RPCNonceOracle(custodial_roles['GAS_GIFTER'], conn=eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = c.create(custodial_roles['GAS_GIFTER'], whoever, 100 * (10 ** 6))
    r = eth_rpc.do(o)

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(whoever, 42)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(whoever, agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            42,
            whoever,
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

    s = celery.signature(
            'cic_eth.eth.gas.check_gas',
            [
                [
                    tx_hash_hex,
                    ],
                default_chain_spec.asdict(),
                ],
            queue=None
            )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful()

    init_database.commit()

    tx = get_tx(default_chain_spec, tx_hash_hex, session=init_database)
    assert tx['status'] & StatusBits.QUEUED == StatusBits.QUEUED
