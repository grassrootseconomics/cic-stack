# standard imports
import logging

# external imports
import celery
from chainlib.connection import RPCConnection
from chainlib.chain import ChainSpec
from cic_eth_registry.erc20 import ERC20Token
from hexathon import add_0x
from eth_address_declarator import Declarator
from cic_eth_registry import CICRegistry
from okota.token_index import to_identifier

# local imports
from cic_eth.task import (
        BaseTask,
        )
from cic_eth.db.models.role import AccountRole
from cic_eth.error import TrustError

celery_app = celery.current_app
logg = logging.getLogger()


@celery_app.task(bind=True, base=BaseTask)
def default_token(self):
    return {
        'symbol': self.default_token_symbol,
        'address': self.default_token_address,
        'name': self.default_token_name,
        'decimals': self.default_token_decimals,
        }


@celery_app.task(bind=True, base=BaseTask)
def token(self, tokens, chain_spec_dict):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')
    declarator = Declarator(chain_spec)

    session = self.create_session()
    sender_address = AccountRole.get_address('DEFAULT', session)
    sender_address = AccountRole.get_address('DEFAULT', session)

    registry = CICRegistry(chain_spec, rpc)
    declarator_address = registry.by_name('AddressDeclarator', sender_address=sender_address)

    have_proof = False

    result_data = []
    for token in tokens:
        token_chain_object = ERC20Token(chain_spec, rpc, add_0x(token['address']))
        token_chain_object.load(rpc)
        token_data = {
            'decimals': token_chain_object.decimals,
            'name': token_chain_object.name,
            'symbol': token_chain_object.symbol,
            'address': token_chain_object.address,
            'declaration': {},
                }

        token_proof_hex = to_identifier(token_chain_object.symbol)
        logg.debug('token proof to match is {}'.format(token_proof_hex))

        for trusted_address in self.trusted_addresses:
            o = declarator.declaration(declarator_address, trusted_address, token_chain_object.address, sender_address=sender_address)
            r = rpc.do(o)
            declarations = declarator.parse_declaration(r)
            token_data['declaration'][trusted_address] = declarations
            logg.debug('declarations for {} by {}: {}'.format(token_chain_object.address, trusted_address, declarations))
            for declaration in declarations:
                if declaration == token_proof_hex:
                    logg.debug('have token proof {} match for trusted address {}'.format(declaration, trusted_address))
                    have_proof = True

        if not have_proof:
            raise TrustError('no proof found for token {}'.format(token_chain_object.symbol))

        result_data.append(token_data)

    return result_data
