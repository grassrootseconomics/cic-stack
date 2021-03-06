# external imports
from chainlib.eth.gas import (
        Gas,
        RPCGasOracle,
        )
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        )
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.connection import RPCConnection
from hexathon import strip_0x

def test_unpack(
        default_chain_spec,
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

    assert tx_hash_hex == tx['hash']
