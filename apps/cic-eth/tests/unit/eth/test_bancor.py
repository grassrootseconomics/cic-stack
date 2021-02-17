# standard imports
import logging

# third-party imports
import pytest
from cic_registry import CICRegistry

# local imports
from cic_eth.eth.bancor import BancorTxFactory, unpack_convert
from cic_eth.eth.bancor import resolve_converters_by_tokens
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.queue.tx import create as queue_create
from cic_eth.eth.bancor import otx_cache_convert
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache

logg = logging.getLogger()


def test_resolve_converters_by_tokens(
        cic_registry,
        init_w3,
        bancor_tokens,
        bancor_registry,
        default_chain_spec,
        ):

    r = resolve_converters_by_tokens(
        [
            {
                'address': bancor_tokens[0],
            },
            {
                'address': bancor_tokens[1],
            },
        ],
        str(default_chain_spec),
        )

    logg.warning('this test should be hardened by verifying the converters')
    for t in r:
        assert t['converters'] != None
        assert len(t['converters']) == 1

        
def test_unpack_convert(
    default_chain_spec,
    cic_registry,
    init_w3,
    init_rpc,
    bancor_tokens,
    bancor_registry,
        ):
    
    txf = BancorTxFactory(init_w3.eth.accounts[0], init_rpc)

    default_reserve = CICRegistry.get_contract(default_chain_spec, 'BNTToken')

    convert_tx = txf.convert(
            bancor_tokens[0],
            bancor_tokens[1],
            default_reserve.address(),
            42,
            13,
            default_chain_spec,
            )

    s = init_w3.eth.sign_transaction(convert_tx)
    s_bytes = bytes.fromhex(s['raw'][2:])
    tx_dict = unpack_signed_raw_tx(s_bytes, default_chain_spec.chain_id())

    convert_contract = CICRegistry.get_contract(default_chain_spec, 'BancorNetwork')
    assert tx_dict['from'] == init_w3.eth.accounts[0]
    assert tx_dict['to'] == convert_contract.address()
    assert tx_dict['value'] == 0

    convert_data = unpack_convert(tx_dict['data'])

    assert convert_data['amount'] == 42
    assert convert_data['min_return'] == 13
    assert convert_data['source_token'] == bancor_tokens[0]
    assert convert_data['destination_token'] == bancor_tokens[1]
    assert convert_data['fee_recipient'] == '0000000000000000000000000000000000000000000000000000000000000000'
    assert convert_data['fee'] == 0


def test_queue_cache_convert(
        default_chain_spec,
        init_w3,
        init_rpc,
        init_database,
        cic_registry,
        bancor_registry,
        bancor_tokens,
        ):

    txf = BancorTxFactory(init_w3.eth.accounts[0], init_rpc)
    amount = 42
    min_return = 13
    default_reserve = CICRegistry.get_contract(default_chain_spec, 'BNTToken', 'ERC20')
    transfer_tx = txf.convert(
            bancor_tokens[0],
            bancor_tokens[1],
            default_reserve.address(),
            amount,
            min_return,
            default_chain_spec,
            )
    tx_signed = init_w3.eth.sign_transaction(transfer_tx)
    tx_hash = init_w3.eth.sendRawTransaction(tx_signed['raw'])
    tx_hash_hex = tx_hash.hex()
    nonce = int(tx_signed['nonce'][2:], 16)
    tx_hash_queue = queue_create(nonce, init_w3.eth.accounts[0], tx_hash_hex, tx_signed['raw'], str(default_chain_spec))
    tx_hash_cache = otx_cache_convert(tx_hash_hex, tx_signed['raw'], str(default_chain_spec))

    assert tx_hash_hex == tx_hash_queue
    assert tx_hash_hex == tx_hash_cache

    session = Otx.create_session()
    otx = session.query(Otx).filter(Otx.tx_hash==tx_hash_hex).first()
    assert otx.tx_hash == tx_hash_hex

    txc = session.query(TxCache).filter(TxCache.otx_id==otx.id).first()
    
    assert txc.sender == init_w3.eth.accounts[0]
    assert txc.recipient == init_w3.eth.accounts[0]
    assert txc.source_token_address == bancor_tokens[0]
    assert txc.destination_token_address == bancor_tokens[1]
    assert txc.from_value == amount
    assert txc.to_value == amount
