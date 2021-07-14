# external imports
import celery
import pytest
from chainlib.connection import RPCConnection
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.gas import (
        RPCGasOracle,
        )
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        )
from chainlib.eth.nonce import RPCNonceOracle
from eth_erc20 import ERC20
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainqueue.db.models.tx import TxCache
from chainqueue.db.models.otx import Otx


def test_ext_tx_collate(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        custodial_roles,
        agent_roles,
        foo_token,
        bar_token,
        register_tokens,
        cic_registry,
        register_lookups,
        init_celery_tasks,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(custodial_roles['FOO_TOKEN_GIFTER'], eth_rpc)
    gas_oracle = RPCGasOracle(eth_rpc)

    c = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    transfer_value_foo = 1000
    transfer_value_bar = 1024
    (tx_hash_hex, tx_signed_raw_hex) = c.transfer(foo_token, custodial_roles['FOO_TOKEN_GIFTER'], agent_roles['ALICE'], transfer_value_foo, tx_format=TxFormat.RLP_SIGNED)
    tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)

    otx = Otx(
        tx['nonce'],
        tx_hash_hex,
        tx_signed_raw_hex,
        )
    init_database.add(otx)
    init_database.commit()

    txc = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        foo_token,
        bar_token,
        transfer_value_foo,
        transfer_value_bar,
        666,
        13,
        session=init_database,
            )
    init_database.add(txc)
    init_database.commit()
    
    s = celery.signature(
            'cic_eth.ext.tx.tx_collate',
            [
                {tx_hash_hex: tx_signed_raw_hex},
                default_chain_spec.asdict(),
                0,
                100,
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful()

    assert len(r) == 1

    tx = r[0]
    assert tx['source_token_symbol'] == 'FOO'
    assert tx['source_token_decimals'] == 6
    assert tx['destination_token_symbol'] == 'BAR'
    assert tx['destination_token_decimals'] == 9
