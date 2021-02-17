# standard imports
import os
import logging

# third-party imports
import web3
from cic_registry import CICRegistry

# local imports
from cic_eth.eth.token import ExtendedTx

logg = logging.getLogger()


def test_extended_token(
        default_chain_spec,
        dummy_token,
        local_cic_registry,
        address_declarator,
        init_w3,
        ):

    address_foo = web3.Web3.toChecksumAddress('0x' + os.urandom(20).hex())
    label_foo = '0x{:<064s}'.format(b'foo'.hex())
    address_bar = web3.Web3.toChecksumAddress('0x' + os.urandom(20).hex())
    label_bar = '0x{:<064s}'.format(b'bar'.hex())
    label_token = '0x{:<064s}'.format(b'toktoktok'.hex())

    # TODO: still need to test results with two different tokens
    token_contract = init_w3.eth.contract(abi=CICRegistry.abi('ERC20'), address=dummy_token)
    token = CICRegistry.add_token(default_chain_spec, token_contract)

    declarator = CICRegistry.get_contract(default_chain_spec, 'AddressDeclarator', 'Declarator')
    fn = declarator.function('addDeclaration')
    fn(address_foo, label_foo).transact({'from': init_w3.eth.accounts[1]})
    fn(address_bar, label_bar).transact({'from': init_w3.eth.accounts[1]})
    fn(dummy_token, label_token).transact({'from': init_w3.eth.accounts[1]})
    tx_hash = '0x' + os.urandom(32).hex()
    xtx = ExtendedTx(tx_hash, default_chain_spec)
    xtx.set_actors(address_foo, address_bar, [init_w3.eth.accounts[1]])
    xtx.set_tokens(dummy_token, 1024)
    tx = xtx.to_dict()

    logg.debug('tx {}'.format(tx))
    assert tx['hash'] == tx_hash
    assert tx['source_token'] == dummy_token
    assert tx['destination_token'] == dummy_token
    assert tx['source_token_symbol'] == token.symbol()
    assert tx['destination_token_symbol'] == token.symbol()
    assert tx['source_token_value'] == 1024
    assert tx['destination_token_value'] == 1024
    assert tx['source_token_decimals'] == token.decimals()
    assert tx['destination_token_decimals'] == token.decimals()
    assert tx['sender'] == address_foo
    assert tx['sender_label'] == 'foo'
    assert tx['recipient'] == address_bar
    assert tx['recipient_label'] == 'bar'
    assert tx['chain'] == str(default_chain_spec)
