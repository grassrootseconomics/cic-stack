# external imports
import celery
from chainlib.eth.pytest.fixtures_chain import *
from chainlib.eth.pytest.fixtures_ethtester import *
from cic_eth_registry.pytest.fixtures_contracts import *
from cic_eth_registry.pytest.fixtures_tokens import *
from erc20_demurrage_token.unittest.base import TestTokenDeploy
from erc20_demurrage_token.token import DemurrageToken
from eth_token_index.index import TokenUniqueSymbolIndex
from eth_address_declarator.declarator import AddressDeclarator

# cic-eth imports
from cic_eth.pytest.fixtures_celery import *
from cic_eth.pytest.fixtures_token import *
from cic_eth.pytest.fixtures_config import *


@pytest.fixture(scope='function')
def demurrage_token(
        default_chain_spec,
        eth_rpc,
        token_registry,
        contract_roles,
        eth_signer,
        ):
    d = TestTokenDeploy(eth_rpc, token_symbol='BAR', token_name='Bar Token')
    nonce_oracle = RPCNonceOracle(contract_roles['CONTRACT_DEPLOYER'], conn=eth_rpc)
    c = DemurrageToken(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    token_address =  d.deploy(eth_rpc, contract_roles['CONTRACT_DEPLOYER'], c, 'SingleNocap')
    logg.debug('demurrage token contract "BAR" deployed to {}'.format(token_address))

    return token_address
    

@pytest.fixture(scope='function')
def demurrage_token_symbol(
        default_chain_spec,
        eth_rpc,
        demurrage_token,
        contract_roles,
        ):

    c = DemurrageToken(default_chain_spec)
    o = c.symbol(demurrage_token, sender_address=contract_roles['CONTRACT_DEPLOYER'])
    r = eth_rpc.do(o)
    return c.parse_symbol(r)


@pytest.fixture(scope='function')
def demurrage_token_declaration(
        foo_token_declaration,
        ):
    return foo_token_declaration


@pytest.fixture(scope='function')
def register_demurrage_token(
        default_chain_spec,
        token_registry,
        eth_rpc,
        eth_signer,
        register_lookups,
        contract_roles,
        demurrage_token_declaration,
        demurrage_token,
        address_declarator,
        ):

    nonce_oracle = RPCNonceOracle(contract_roles['CONTRACT_DEPLOYER'], eth_rpc)

    c = TokenUniqueSymbolIndex(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.register(token_registry, contract_roles['CONTRACT_DEPLOYER'], demurrage_token)
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    nonce_oracle = RPCNonceOracle(contract_roles['TRUSTED_DECLARATOR'], eth_rpc)
    c = AddressDeclarator(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.add_declaration(address_declarator, contract_roles['TRUSTED_DECLARATOR'], demurrage_token, demurrage_token_declaration)

    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    return token_registry

