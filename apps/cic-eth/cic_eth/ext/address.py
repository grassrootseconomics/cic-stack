# standard imports
import logging

# third-party imports
import celery
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainlib.eth.constant import ZERO_ADDRESS
from cic_eth_registry import CICRegistry
from eth_address_declarator import AddressDeclarator

# local imports
from cic_eth.eth import RpcClient
from cic_eth.registry import safe_registry
from cic_eth.task import BaseTask

celery_app = celery.current_app

logg = logging.getLogger()


def translate_address(address, trusted_addresses, chain_spec, sender_address=ZERO_ADDRESS):

    rpc = RPCConnection.connect(chain_spec, 'default')
    registry = CICRegistry(chain_spec, rpc)
    
    declarator_address = registry.by_name('AddressDeclarator', sender_address=sender_address)
    c = AddressDeclarator()

    for trusted_address in trusted_addresses:
        o = c.declaration(declarator_address, trusted_address, address, sender_address=sender_address)
        r = rpc.do(o)
        declaration_hex = AddressDeclarator.parse_declaration(r)
        declaration_hex = declaration_hex[0].rstrip('0')
        declaration_bytes = bytes.fromhex(declaration_hex)
        declaration = None
        try:
            declaration = declaration_bytes.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            continue
        return declaration


@celery_app.task(bind=True, base=BaseTask)
def translate_tx_addresses(self, tx, trusted_addresses, chain_spec_dict):

    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    declaration = None
    if tx['sender_label'] == None:
        declaration = translate_address(tx['sender'], trusted_addresses, chain_spec, self.call_address)
    tx['sender_label'] = declaration

    declaration = None
    if tx['recipient_label'] == None:
        declaration = translate_address(tx['recipient'], trusted_addresses, chain_spec, self.call_address)
    tx['recipient_label'] = declaration

    return tx
