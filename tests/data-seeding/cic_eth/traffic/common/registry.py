# standard imports
import logging
import copy

# external imports
from cic_registry.registry import Registry
from eth_token_index import TokenUniqueSymbolIndex
from eth_accounts_index import AccountRegistry
from chainlib.chain import ChainSpec
from cic_registry.chain import ChainRegistry
from cic_registry.helper.declarator import DeclaratorOracleAdapter

logg = logging.getLogger(__name__)


class TokenOracle:

    def __init__(self, conn, chain_spec, registry):
        self.tokens = []
        self.chain_spec = chain_spec
        self.registry = registry

        token_registry_contract = CICRegistry.get_contract(chain_spec, 'TokenRegistry', 'Registry')
        self.getter = TokenUniqueSymbolIndex(conn, token_registry_contract.address())


    def get_tokens(self):
        token_count = self.getter.count()
        if token_count == len(self.tokens):
            return self.tokens

        for i in range(len(self.tokens), token_count):
            token_address = self.getter.get_index(i)
            t = self.registry.get_address(self.chain_spec, token_address)
            token_symbol = t.symbol()
            self.tokens.append(t)

            logg.debug('adding token idx {} symbol {} address {}'.format(i, token_symbol, token_address))

        return copy.copy(self.tokens)


class AccountsOracle:

    def __init__(self, conn, chain_spec, registry):
        self.accounts = []
        self.chain_spec = chain_spec
        self.registry = registry

        accounts_registry_contract = CICRegistry.get_contract(chain_spec, 'AccountRegistry', 'Registry')
        self.getter = AccountRegistry(conn, accounts_registry_contract.address())


    def get_accounts(self):
        accounts_count = self.getter.count()
        if accounts_count == len(self.accounts):
            return self.accounts

        for i in range(len(self.accounts), accounts_count):
            account = self.getter.get_index(i)
            self.accounts.append(account)
            logg.debug('adding account {}'.format(account))

        return copy.copy(self.accounts)


def init_legacy(config, w3):
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
