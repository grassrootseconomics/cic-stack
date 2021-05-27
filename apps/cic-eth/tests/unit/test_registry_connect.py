# local imports
from cic_eth.registry import *

def test_registry_connect(
        eth_rpc,
        default_chain_spec,
        address_declarator,
        token_registry,
        contract_roles,
        registry,
        agent_roles,
        ):

    r = connect(eth_rpc, default_chain_spec, registry, sender_address=contract_roles['CONTRACT_DEPLOYER'])

    connect_declarator(eth_rpc, default_chain_spec, [agent_roles['ALICE']], sender_address=contract_roles['CONTRACT_DEPLOYER'])
    r.by_name('AddressDeclarator', sender_address=contract_roles['CONTRACT_DEPLOYER'])

    connect_token_registry(eth_rpc, default_chain_spec, sender_address=contract_roles['CONTRACT_DEPLOYER'])
    r.by_name('TokenRegistry', sender_address=contract_roles['CONTRACT_DEPLOYER'])

