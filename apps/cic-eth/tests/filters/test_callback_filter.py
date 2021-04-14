# standard import
import logging

# external imports
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.tx import (
        receipt,
        transaction,
        Tx,
        snake_and_camel,
        )
from chainlib.eth.erc20 import ERC20

# local imports
from cic_eth.runnable.daemons.filters.callback import (
        parse_transfer,
        parse_transferfrom,
        )

logg = logging.getLogger()


def test_transfer_tx(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        foo_token,
        agent_roles,
        token_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], rpc)
    gas_oracle = OverrideGasOracle(conn=rpc, limit=200000)
   
    txf = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = txf.transfer(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], 1024)
    r = rpc.do(o)
    
    o = transaction(tx_hash_hex)
    r = rpc.do(o)
    logg.debug(r)
    tx_src = snake_and_camel(r)
    tx = Tx(tx_src)

    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    rcpt = snake_and_camel(r)
    tx.apply_receipt(rcpt)

    (transfer_type, transfer_data) = parse_transfer(tx)

    assert transfer_type == 'transfer'



def test_transfer_from_tx(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        foo_token,
        agent_roles,
        token_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], rpc)
    gas_oracle = OverrideGasOracle(conn=rpc, limit=200000)
   
    txf = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)

    (tx_hash_hex, o) = txf.approve(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], 1024)
    r = rpc.do(o)
    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], rpc)
    txf = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = txf.transfer_from(foo_token, agent_roles['ALICE'], token_roles['FOO_TOKEN_OWNER'], agent_roles['BOB'], 1024)
    r = rpc.do(o)
    
    o = transaction(tx_hash_hex)
    r = rpc.do(o)
    logg.debug(r)
    tx_src = snake_and_camel(r)
    tx = Tx(tx_src)

    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    rcpt = snake_and_camel(r)
    tx.apply_receipt(rcpt)

    (transfer_type, transfer_data) = parse_transferfrom(tx)

    assert transfer_type == 'transferfrom'
