# standard imports
import logging

# external imports
from cic_eth_registry import CICRegistry
from cic_eth_registry.lookup.declarator import AddressDeclaratorLookup
from cic_eth_registry.lookup.tokenindex import TokenIndexLookup
from chainlib.eth.constant import ZERO_ADDRESS

logg = logging.getLogger(__name__)


def connect_token_registry(rpc, chain_spec, sender_address=ZERO_ADDRESS):
    registry = CICRegistry(chain_spec, rpc)
    token_registry_address = registry.by_name('TokenRegistry', sender_address=sender_address)
    logg.info('using token registry address {}'.format(token_registry_address))
    lookup = TokenIndexLookup(chain_spec, token_registry_address)
    CICRegistry.add_lookup(lookup)


def connect_declarator(rpc, chain_spec, trusted_addresses, sender_address=ZERO_ADDRESS):
    registry = CICRegistry(chain_spec, rpc)
    declarator_address = registry.by_name('AddressDeclarator', sender_address=sender_address)
    logg.info('using declarator address {}'.format(declarator_address))
    lookup = AddressDeclaratorLookup(chain_spec, declarator_address, trusted_addresses)
    CICRegistry.add_lookup(lookup)


def connect(rpc, chain_spec, registry_address, sender_address=ZERO_ADDRESS):
    CICRegistry.address = registry_address
    registry = CICRegistry(chain_spec, rpc)
    registry_address = registry.by_name('ContractRegistry', sender_address=sender_address)
    logg.info('using registry address {}'.format(registry_address))
    return registry
