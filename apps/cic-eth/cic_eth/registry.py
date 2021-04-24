# standard imports
import logging

# external imports
from cic_eth_registry import CICRegistry
from cic_eth_registry.lookup.declarator import AddressDeclaratorLookup
from cic_eth_registry.lookup.tokenindex import TokenIndexLookup

logg = logging.getLogger()


def connect_token_registry(rpc, chain_spec):
    registry = CICRegistry(chain_spec, rpc)
    token_registry_address = registry.by_name('TokenRegistry')
    logg.debug('using token registry address {}'.format(token_registry_address))
    lookup = TokenIndexLookup(chain_spec, token_registry_address)
    CICRegistry.add_lookup(lookup)


def connect_declarator(rpc, chain_spec, trusted_addresses):
    registry = CICRegistry(chain_spec, rpc)
    declarator_address = registry.by_name('AddressDeclarator')
    logg.debug('using declarator address {}'.format(declarator_address))
    lookup = AddressDeclaratorLookup(chain_spec, declarator_address, trusted_addresses)
    CICRegistry.add_lookup(lookup)


def connect(rpc, chain_spec, registry_address):
    CICRegistry.address = registry_address
    registry = CICRegistry(chain_spec, rpc)
    registry_address = registry.by_name('ContractRegistry')
    return registry

