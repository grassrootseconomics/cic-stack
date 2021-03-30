# external imports
from cic_eth_registry import CICRegistry
from cic_eth_registry.lookup.declarator import AddressDeclaratorLookup


def connect_declarator(rpc, chain_spec, trusted_addresses):
    registry = CICRegistry(chain_spec, rpc)
    declarator_address = registry.by_name('AddressDeclarator')
    lookup = AddressDeclaratorLookup(declarator_address, trusted_addresses)
    CICRegistry.add_lookup(lookup)


def connect(rpc, chain_spec, registry_address):
    CICRegistry.address = registry_address
    registry = CICRegistry(chain_spec, rpc)
    registry_address = registry.by_name('ContractRegistry')
    
    return registry
