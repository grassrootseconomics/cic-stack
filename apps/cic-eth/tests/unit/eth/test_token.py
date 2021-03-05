# standard imports
import logging

# third-party imports
import pytest
from cic_registry import CICRegistry

# local imports
from cic_eth.eth.token import TokenTxFactory, unpack_transfer, otx_cache_transfer
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.queue.tx import create as queue_create
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.nonce import NonceReservation

logg = logging.getLogger()


def test_unpack_transfer(
    default_chain_spec,
    init_database,
    init_w3,
    init_rpc,
    cic_registry,
    bancor_tokens,
    bancor_registry,
        ):
 
    NonceReservation.next(init_w3.eth.accounts[0], 'foo', init_database)
    init_database.commit()

    source_token = CICRegistry.get_address(default_chain_spec, bancor_tokens[0])
    logg.debug('bancor tokens {} {}'.format(bancor_tokens, source_token))
    txf = TokenTxFactory(init_w3.eth.accounts[0], init_rpc)
    transfer_tx = txf.transfer(
            source_token.address(),
            init_w3.eth.accounts[1],
            42,
            default_chain_spec,
            'foo',
            )
    s = init_w3.eth.sign_transaction(transfer_tx)
    s_bytes = bytes.fromhex(s['raw'][2:])
    tx_dict = unpack_signed_raw_tx(s_bytes, default_chain_spec.chain_id())
    assert tx_dict['from'] == init_w3.eth.accounts[0]
    assert tx_dict['to'] == bancor_tokens[0]
    assert tx_dict['value'] == 0

    transfer_data = unpack_transfer(tx_dict['data'])

    assert transfer_data['to'] == init_w3.eth.accounts[1]
    assert transfer_data['amount'] == 42


def test_queue_cache_transfer(
        default_chain_spec,
        init_w3,
        init_rpc,
        init_database,
        cic_registry,
        bancor_tokens,
        bancor_registry,
        ):

    NonceReservation.next(init_w3.eth.accounts[0], 'foo', init_database)
    init_database.commit()

    source_token = CICRegistry.get_address(default_chain_spec, bancor_tokens[0])
    txf = TokenTxFactory(init_w3.eth.accounts[0], init_rpc)
    value = 42
    transfer_tx = txf.transfer(
            source_token.address(),
            init_w3.eth.accounts[1],
            value,
            default_chain_spec,
            'foo',
            )
    tx_signed = init_w3.eth.sign_transaction(transfer_tx)
    tx_hash = init_w3.eth.sendRawTransaction(tx_signed['raw'])
    tx_hash_hex = tx_hash.hex()
    nonce = int(tx_signed['nonce'][2:], 16)
    tx_hash_queue = queue_create(nonce, init_w3.eth.accounts[0], tx_hash_hex, tx_signed['raw'], str(default_chain_spec))
    tx_hash_cache = otx_cache_transfer(tx_hash_hex, tx_signed['raw'], str(default_chain_spec))

    assert tx_hash_hex == tx_hash_queue
    assert tx_hash_hex == tx_hash_cache

    session = Otx.create_session()
    otx = session.query(Otx).filter(Otx.tx_hash==tx_hash_hex).first()
    assert otx.tx_hash == tx_hash_hex

    txc = session.query(TxCache).filter(TxCache.otx_id==otx.id).first()
    
    assert txc.sender == init_w3.eth.accounts[0]
    assert txc.recipient == init_w3.eth.accounts[1]
    assert txc.source_token_address == bancor_tokens[0]
    assert txc.destination_token_address == bancor_tokens[0]
    assert txc.from_value == value
    assert txc.to_value == value
