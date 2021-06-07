# external imports
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import (
        receipt,
        )
from eth_address_declarator import Declarator
from hexathon import add_0x

# local imports
from cic_eth.ext.address import translate_tx_addresses


def test_translate(
        default_chain_spec,
        address_declarator,
        eth_signer,
        eth_rpc,
        contract_roles,
        agent_roles,
        cic_registry,
        init_celery_tasks,
        register_lookups,
    ):

    nonce_oracle = RPCNonceOracle(contract_roles['CONTRACT_DEPLOYER'], eth_rpc)

    c = Declarator(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)

    description = 'alice'.encode('utf-8').ljust(32, b'\x00').hex()
    (tx_hash_hex, o) = c.add_declaration(address_declarator, contract_roles['CONTRACT_DEPLOYER'], agent_roles['ALICE'], add_0x(description))
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    description = 'bob'.encode('utf-8').ljust(32, b'\x00').hex()
    (tx_hash_hex, o) = c.add_declaration(address_declarator, contract_roles['CONTRACT_DEPLOYER'], agent_roles['BOB'], add_0x(description))
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    tx = {
        'sender': agent_roles['ALICE'],
        'sender_label': None,
        'recipient': agent_roles['BOB'],
        'recipient_label': None,
            }
    tx = translate_tx_addresses(tx, [contract_roles['CONTRACT_DEPLOYER']], default_chain_spec.asdict())
    assert tx['sender_label'] == 'alice'
    assert tx['recipient_label'] == 'bob'
