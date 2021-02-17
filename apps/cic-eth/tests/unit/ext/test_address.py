# third-party imports
from eth_address_declarator import AddressDeclarator
from cic_registry import CICRegistry

# local imports
from cic_eth.ext.address import translate_tx_addresses

def test_translate(
        default_chain_spec,
        address_declarator,
        init_rpc,
        init_w3,
    ):

    chain_str = str(default_chain_spec)

    c = init_rpc.w3.eth.contract(abi=AddressDeclarator.abi(), address=address_declarator)

    description = '0x{:<064s}'.format(b'foo'.hex()) 
    c.functions.addDeclaration(init_w3.eth.accounts[2], description).transact({'from': init_w3.eth.accounts[1]})
    description = '0x{:<064s}'.format(b'bar'.hex()) 
    c.functions.addDeclaration(init_w3.eth.accounts[3], description).transact({'from': init_w3.eth.accounts[1]})

    tx = {
        'sender': init_w3.eth.accounts[2],
        'sender_label': None,
        'recipient': init_w3.eth.accounts[3],
        'recipient_label': None,

            }
    tx = translate_tx_addresses(tx, [init_w3.eth.accounts[1]], chain_str)
    assert tx['sender_label'] == 'foo'
    assert tx['recipient_label'] == 'bar'
