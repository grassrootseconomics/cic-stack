# external imports
from erc20_transfer_authorization import TransferAuthorization
from eth_erc20 import ERC20
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.tx import (
        receipt,
        unpack,
        Tx,
        )
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from hexathon import strip_0x
from chainqueue.sql.query import get_account_tx

# local imports
from cic_eth.runnable.daemons.filters.transferauth import TransferAuthFilter
from cic_eth.encode import tx_normalize


def test_filter_transferauth(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        transfer_auth,
        foo_token,
        celery_session_worker,
        register_lookups,
        init_custodial,
        cic_registry,
    ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(contract_roles['CONTRACT_DEPLOYER'], eth_rpc)
    gas_oracle = OverrideGasOracle(limit=200000, conn=eth_rpc)
    c = TransferAuthorization(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = c.create_request(transfer_auth, contract_roles['CONTRACT_DEPLOYER'], agent_roles['ALICE'], agent_roles['BOB'], foo_token, 1024)
    
    r = rpc.do(o)
    tx_signed_raw_bytes = bytes.fromhex(strip_0x(o['params'][0]))

    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    o = block_latest()
    r = eth_rpc.do(o)
    o = block_by_number(r, include_tx=False)
    r = eth_rpc.do(o)
    block = Block(r)
    block.txs = [tx_hash_hex]

    #tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx_src = unpack(tx_signed_raw_bytes, default_chain_spec)
    tx = Tx(tx_src, block=block)

    fltr = TransferAuthFilter(cic_registry, default_chain_spec, eth_rpc, call_address=contract_roles['CONTRACT_DEPLOYER'])
    t = fltr.filter(eth_rpc, block, tx, db_session=init_database)

    t.get_leaf()
    assert t.successful()

    #approve_txs = get_account_tx(default_chain_spec.asdict(), agent_roles['ALICE'], as_sender=True, session=init_database)
    approve_txs = get_account_tx(default_chain_spec.asdict(), tx_normalize.wallet_address(agent_roles['ALICE']), as_sender=True, session=init_database)
    ks = list(approve_txs.keys())
    assert len(ks) == 1

    tx_raw_signed_hex = strip_0x(approve_txs[ks[0]])
    tx_raw_signed_bytes = bytes.fromhex(tx_raw_signed_hex)
    approve_tx = unpack(tx_raw_signed_bytes, default_chain_spec)

    c = ERC20(default_chain_spec)
    approve = c.parse_approve_request(approve_tx['data']) 
    assert approve[0] == agent_roles['BOB']
