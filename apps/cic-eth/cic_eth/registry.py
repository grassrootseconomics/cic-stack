# standard imports
import logging

# external imports
from cic_registry import CICRegistry
from chainlib.chain import ChainSpec
from cic_registry.chain import ChainRegistry
from cic_registry.helper.declarator import DeclaratorOracleAdapter

logg = logging.getLogger(__name__)


def safe_registry(w3):
    """Temporary workaround for enabling thread-safe usage of the CICRegistry.
    """
    CICRegistry.w3 = w3
    return CICRegistry


def init_registry(config, w3):
    chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
    CICRegistry.init(w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
    CICRegistry.add_path(config.get('ETH_ABI_DIR'))

    chain_registry = ChainRegistry(chain_spec)
    CICRegistry.add_chain_registry(chain_registry, True)

    declarator = CICRegistry.get_contract(chain_spec, 'AddressDeclarator', interface='Declarator')
    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        raise ValueError('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
    trusted_addresses = trusted_addresses_src.split(',')
    for address in trusted_addresses:
        logg.info('using trusted address {}'.format(address))

    oracle = DeclaratorOracleAdapter(declarator.contract, trusted_addresses)
    chain_registry.add_oracle(oracle, 'naive_erc20_oracle')

    return CICRegistry
