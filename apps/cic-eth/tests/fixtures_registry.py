# standard imports
import os
import json
import logging

# third-party imports
import pytest
from eth_address_declarator import AddressDeclarator

# local imports
from cic_registry import CICRegistry
from cic_registry import to_identifier
from cic_registry.contract import Contract
from cic_registry.error import ChainExistsError

logg = logging.getLogger()

script_dir = os.path.dirname(__file__)


@pytest.fixture(scope='session')
def local_cic_registry(
        cic_registry,
        ):
    path = os.path.realpath(os.path.join(script_dir, 'testdata', 'abi'))
    CICRegistry.add_path(path)
    return cic_registry


@pytest.fixture(scope='function')
def address_declarator(
        bloxberg_config,
        default_chain_spec,
        default_chain_registry,
        local_cic_registry,
        init_rpc,
        init_w3,
        ):

    c = init_rpc.w3.eth.contract(abi=AddressDeclarator.abi(), bytecode=AddressDeclarator.bytecode())
    default_description = '0x{:<064s}'.format(b'test'.hex()) 
    logg.debug('default_ {}'.format(default_description))
    tx_hash = c.constructor(default_description).transact()
    rcpt = init_rpc.w3.eth.getTransactionReceipt(tx_hash)

    registry = init_rpc.w3.eth.contract(abi=CICRegistry.abi(), address=local_cic_registry)
    chain_identifier = to_identifier(default_chain_registry.chain())
    registry.functions.set(to_identifier('AddressDeclarator'), rcpt.contractAddress, chain_identifier, bloxberg_config['digest']).transact()

    return rcpt.contractAddress
