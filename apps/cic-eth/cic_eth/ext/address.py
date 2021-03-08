# standard imports
import logging

# third-party imports
import celery
from cic_registry.chain import ChainSpec

# local imports
from cic_eth.eth import RpcClient
from cic_eth.registry import safe_registry

celery_app = celery.current_app

logg = logging.getLogger()


def translate_address(address, trusted_addresses, chain_spec):
    c = RpcClient(chain_spec)
    registry = safe_registry(c.w3)
    for trusted_address in trusted_addresses:
        o = registry.get_contract(chain_spec, 'AddressDeclarator', 'Declarator')
        fn = o.function('declaration')
        declaration_hex = fn(trusted_address, address).call()
        declaration_bytes = declaration_hex[0].rstrip(b'\x00')
        declaration = None
        try:
            declaration = declaration_bytes.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            continue
        return declaration


@celery_app.task()
def translate_tx_addresses(tx, trusted_addresses, chain_str):

    chain_spec = ChainSpec.from_chain_str(chain_str)

    declaration = None
    if tx['sender_label'] == None:
        declaration = translate_address(tx['sender'], trusted_addresses, chain_spec)
    tx['sender_label'] = declaration

    declaration = None
    if tx['recipient_label'] == None:
        declaration = translate_address(tx['recipient'], trusted_addresses, chain_spec)
    tx['recipient_label'] = declaration

    return tx
