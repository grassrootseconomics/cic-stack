# standard imports
import os

# external imports
import pytest
from chainlib.connection import RPCConnection
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.gas import (
        Gas,
        RPCGasOracle,
        )
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        )
from chainlib.eth.nonce import RPCNonceOracle
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainqueue.db.models.tx import TxCache
from chainqueue.db.models.otx import Otx

# test imports
from tests.util.gas import StaticGasOracle


def test_set(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)

    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)
    tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)

    otx = Otx(
        tx['nonce'],
        tx_hash_hex,
        tx_signed_raw_hex,
        )
    otx.block = 666
    init_database.add(otx)
    init_database.commit()

    bogus_from_token = add_0x(os.urandom(20).hex())
    to_value = int(tx['value'] / 2)

    txc = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        bogus_from_token,
        ZERO_ADDRESS,
        tx['value'],
        to_value,
        666,
        13,
        session=init_database,
            )
    init_database.add(txc)
    init_database.commit()

    tx_stored = init_database.query(TxCache).first()
    assert (tx_stored.sender == tx['from'])
    assert (tx_stored.recipient == tx['to'])
    assert (tx_stored.source_token_address == bogus_from_token)
    assert (tx_stored.destination_token_address == ZERO_ADDRESS)
    assert (tx_stored.from_value == tx['value'])
    assert (tx_stored.to_value == to_value)
    assert (tx_stored.tx_index == 13)


def test_clone(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    gas_oracle = StaticGasOracle(2 * (10 ** 9), 21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)

    txs_rpc = [
        c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED),
        ]

    gas_oracle = StaticGasOracle(4 * (10 ** 9), 21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    txs_rpc += [
        c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED),
        ]

    txs = []
    for tx_rpc in txs_rpc:
        tx_hash_hex = tx_rpc[0]
        tx_signed_raw_hex = tx_rpc[1]
        tx_dict = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)
        otx = Otx(
            tx_dict['nonce'],
            tx_hash_hex,
            tx_signed_raw_hex,
            )
        init_database.add(otx)
        tx_dict['hash'] = tx_hash_hex
        txs.append(tx_dict)

    init_database.commit()

    txc = TxCache(
        txs[0]['hash'],
        txs[0]['from'],
        txs[0]['to'],
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        txs[0]['value'],
        txs[0]['value'],
        session=init_database,
            )
    init_database.add(txc)
    init_database.commit()

    TxCache.clone(txs[0]['hash'], txs[1]['hash'], session=init_database)

    q = init_database.query(TxCache)
    q = q.join(Otx)
    q = q.filter(Otx.tx_hash==strip_0x(txs[1]['hash']))
    txc_clone = q.first()
    
    assert txc_clone != None
    assert txc_clone.sender == txc.sender
    assert txc_clone.recipient == txc.recipient
    assert txc_clone.source_token_address == txc.source_token_address
    assert txc_clone.destination_token_address == txc.destination_token_address
    assert txc_clone.from_value == txc.from_value
    assert txc_clone.to_value == txc.to_value
