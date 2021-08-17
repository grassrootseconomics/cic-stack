# standard import
import random

# external import
import pytest

# local import

# tests imports


@pytest.fixture(scope='function')
def notification_data(activated_account, cache_person_metadata, cache_preferences, preferences):
    return {
        'blockchain_address': activated_account.blockchain_address,
        'token_symbol': 'GFT',
        'token_value': 25000000,
        'role': 'sender',
        'action_tag': 'Sent',
        'direction_tag': 'To',
        'metadata_id': activated_account.standard_metadata_id(),
        'phone_number': activated_account.phone_number,
        'available_balance': 50.0,
        'preferred_language': preferences.get('preferred_language')
    }


@pytest.fixture(scope='function')
def statement(activated_account):
    return [
        {
            'blockchain_address': activated_account.blockchain_address,
            'token_symbol': 'GFT',
            'token_value': 25000000,
            'role': 'sender',
            'action_tag': 'Sent',
            'direction_tag': 'To',
            'metadata_id': activated_account.standard_metadata_id(),
            'phone_number': activated_account.phone_number,
        }
    ]


@pytest.fixture(scope='function')
def transaction_result(activated_account, load_config, valid_recipient):
    return {
        'hash': '0xb469fb2ebacc9574afb7b51d44e174fba7129fde71bf757fd39784363270832b',
        'sender': activated_account.blockchain_address,
        'recipient': valid_recipient.blockchain_address,
        'source_token_value': 25000000,
        'destination_token_value': 25000000,
        'source_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
        'destination_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
        'source_token_symbol': load_config.get('TEST_TOKEN_SYMBOL'),
        'destination_token_symbol': load_config.get('TEST_TOKEN_SYMBOL'),
        'source_token_decimals': 6,
        'destination_token_decimals': 6,
        'chain': 'evm:bloxberg:8996'
    }


@pytest.fixture(scope='function')
def transactions_list(activated_account, valid_recipient):
    return [
        {
            'tx_hash': '0x7cdca277861665fa56c4c32930101ff41316c61af3683be12b4879e3d9990125',
            'signed_tx': '0xf8a70201837a120094b708175e3f6cd850643aaf7b32212afad50e254980b844a9059cbb000000000000000000000000367cb0f65137b0a845c1db4b7ca47d3def32dde800000000000000000000000000000000000000000000000000000000017d784082466ba030a75acff9081e57e0a9daa6858d7473fc10348bf95a6da4dd1dc6a602883c8da005358742612001ad44fc142c30bcc23b452af48c90f9c6c80433ae2a93b2e96e',
            'nonce': 2,
            'status': 'SUCCESS',
            'status_code': 4104,
            'source_token': '0xb708175e3f6Cd850643aAF7B32212AFad50e2549',
            'destination_token': '0xb708175e3f6Cd850643aAF7B32212AFad50e2549',
            'block_number': 94,
            'tx_index': 0,
            'sender': activated_account.blockchain_address,
            'recipient': valid_recipient.blockchain_address,
            'from_value': 25000000,
            'to_value': 25000000,
            'date_created': '2021-07-14T14:14:58.117017',
            'date_updated': '2021-07-14T14:14:58.117017',
            'date_checked': '2021-07-14T14:14:58.603124',
            'timestamp': 1626272098,
            'hash': '0x7cdca277861665fa56c4c32930101ff41316c61af3683be12b4879e3d9990125',
            'source_token_symbol': 'GFT',
            'source_token_decimals': 6,
            'destination_token_symbol': 'GFT',
            'destination_token_decimals': 6
        },
        {
            'tx_hash': '0x5bd3b72f07ceb55199e759e8e82006b1c70bd5b87a3d37e3327515ea27872290',
            'signed_tx': '0xf88601018323186094103d1ed6e370dba6267045c70d4999384c18a04a80a463e4bff4000000000000000000000000367cb0f65137b0a845c1db4b7ca47d3def32dde882466ca00beb6913cdd0b9b63469fbca53e2fb48dceeedf73d31d54c23c85392f01419a8a02352fff9187ba3dd6409ef6e473369dc4c3459a8baaa9bc1d68a541ca8a8f923',
            'nonce': 1,
            'status': 'REVERTED',
            'status_code': 5128,
            'source_token': '0x0000000000000000000000000000000000000000',
            'destination_token': '0x0000000000000000000000000000000000000000',
            'block_number': 80,
            'tx_index': 0,
            'sender': '0x367cB0F65137b0A845c1DB4B7Ca47D3DEF32dDe8',
            'recipient': '0x103d1ed6e370dBa6267045c70d4999384c18a04A',
            'from_value': 0,
            'to_value': 0,
            'date_created': '2021-07-14T14:13:46.036198',
            'date_updated': '2021-07-14T14:13:46.036198',
            'date_checked': '2021-07-14T14:13:46.450050',
            'timestamp': 1626272026,
            'hash': '0x5bd3b72f07ceb55199e759e8e82006b1c70bd5b87a3d37e3327515ea27872290'},
        {
            'tx_hash': '0x9d586562e1e40ae80fd506161e59825bc316293b5c522b8f243cf6c804c7843b',
            'signed_tx': '0xf868800182520894367cb0f65137b0a845c1db4b7ca47d3def32dde887066517289880008082466ca0c75083ea13d4fa9dfd408073cd0a8234199b78e79afe441fb71d7c79aa282ca6a00a7dd29e3ec1102817236d85af365fce7593b337ee609d02efdb86d298cf11ab',
            'nonce': 0,
            'status': 'SUCCESS',
            'status_code': 4104,
            'source_token': '0x0000000000000000000000000000000000000000',
            'destination_token': '0x0000000000000000000000000000000000000000',
            'block_number': 78,
            'tx_index': 0,
            'sender': '0xb41BfEE260693A473254D62b81aE1ADCC9E51AFb',
            'recipient': '0x367cB0F65137b0A845c1DB4B7Ca47D3DEF32dDe8',
            'from_value': 1800000000000000,
            'to_value': 1800000000000000,
            'date_created': '2021-07-14T14:13:35.839638',
            'date_updated': '2021-07-14T14:13:35.839638',
            'date_checked': '2021-07-14T14:13:36.333426',
            'timestamp': 1626272015,
            'hash': '0x9d586562e1e40ae80fd506161e59825bc316293b5c522b8f243cf6c804c7843b'
        },
        {
            'tx_hash': '0x32ca3dd3bef06463b452f4d32f5f563d083cb4759219eed90f3d2a9c1791c5fc',
            'signed_tx': '0xf88680018323186094103d1ed6e370dba6267045c70d4999384c18a04a80a463e4bff4000000000000000000000000367cb0f65137b0a845c1db4b7ca47d3def32dde882466ca0ab9ec1c6affb80f54bb6c2a25e64f38b3da840404180fb189bd6e191266f3c63a03cc53e59f8528da04aeec36ab8ae099553fca366bd067feffed6362ccb28d8f0',
            'nonce': 0,
            'status': 'SUCCESS',
            'status_code': 4104,
            'source_token': '0x0000000000000000000000000000000000000000',
            'destination_token': '0x0000000000000000000000000000000000000000',
            'block_number': 79,
            'tx_index': 0,
            'sender': '0x367cB0F65137b0A845c1DB4B7Ca47D3DEF32dDe8',
            'recipient': '0x103d1ed6e370dBa6267045c70d4999384c18a04A',
            'from_value': 0,
            'to_value': 0,
            'date_created': '2021-07-14T14:13:35.638355',
            'date_updated': '2021-07-14T14:13:35.638355',
            'date_checked': '2021-07-14T14:13:40.927113',
            'timestamp': 1626272015,
            'hash': '0x32ca3dd3bef06463b452f4d32f5f563d083cb4759219eed90f3d2a9c1791c5fc'}
    ]

