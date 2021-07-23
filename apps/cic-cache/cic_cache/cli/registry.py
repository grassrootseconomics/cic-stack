# standard imports
import logging

# external imports
from cic_eth_registry import CICRegistry
from cic_eth_registry.lookup.declarator import AddressDeclaratorLookup
from cic_eth_registry.lookup.tokenindex import TokenIndexLookup
from chainlib.eth.constant import ZERO_ADDRESS

logg = logging.getLogger()


def connect_token_registry(self, conn, chain_spec, sender_address=ZERO_ADDRESS):
    registry = CICRegistry(chain_spec, conn)
    token_registry_address = registry.by_name('TokenRegistry', sender_address=sender_address)
    logg.debug('using token registry address {}'.format(token_registry_address))
    lookup = TokenIndexLookup(chain_spec, token_registry_address)
    CICRegistry.add_lookup(lookup)


def connect_declarator(self, conn, chain_spec, trusted_addresses, sender_address=ZERO_ADDRESS):
    registry = CICRegistry(chain_spec, conn)
    declarator_address = registry.by_name('AddressDeclarator', sender_address=sender_address)
    logg.debug('using declarator address {}'.format(declarator_address))
    lookup = AddressDeclaratorLookup(chain_spec, declarator_address, trusted_addresses)
    CICRegistry.add_lookup(lookup)


def connect_registry(conn, chain_spec, registry_address, sender_address=ZERO_ADDRESS):
    CICRegistry.address = registry_address
    registry = CICRegistry(chain_spec, conn)
    registry_address = registry.by_name('ContractRegistry', sender_address=sender_address)
    return registry
