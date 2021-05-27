# standard imports
import os

# external imports
import pytest
from chainlib.eth.contract import (
        ABIContractEncoder,
        ABIContractType,
        )
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainlib.eth.tx import (
        receipt,
        TxFactory,
        TxFormat,
        unpack,
        Tx,
        )
from hexathon import strip_0x

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)


@pytest.fixture(scope='function')
def bogus_tx_block(
    default_chain_spec,
    eth_rpc,
    eth_signer,
    contract_roles,
        ):

    nonce_oracle = RPCNonceOracle(contract_roles['CONTRACT_DEPLOYER'], conn=eth_rpc)
    gas_oracle = OverrideGasOracle(limit=2000000, conn=eth_rpc)

    f = open(os.path.join(script_dir, 'testdata', 'Bogus.bin'), 'r')
    bytecode = f.read()
    f.close()

    c = TxFactory(default_chain_spec, signer=eth_signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle)
    tx = c.template(contract_roles['CONTRACT_DEPLOYER'], None, use_nonce=True)
    tx = c.set_code(tx, bytecode)
    (tx_hash_hex, o) = c.build(tx)

    r = eth_rpc.do(o)

    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)

    contract_address = r['contract_address']

    enc = ABIContractEncoder()
    enc.method('poke')
    data = enc.get()
    tx = c.template(contract_roles['CONTRACT_DEPLOYER'], contract_address, use_nonce=True)
    tx = c.set_code(tx, data)
    (tx_hash_hex, o) = c.finalize(tx, TxFormat.JSONRPC)
    r = eth_rpc.do(o)
    tx_signed_raw_hex = strip_0x(o['params'][0])

    o = block_latest()
    r = eth_rpc.do(o)
    o = block_by_number(r, include_tx=False)
    r = eth_rpc.do(o)
    block = Block(r)
    block.txs = [tx_hash_hex]

    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx_src = unpack(tx_signed_raw_bytes, default_chain_spec)
    tx = Tx(tx_src, block=block)

    return (block, tx)
