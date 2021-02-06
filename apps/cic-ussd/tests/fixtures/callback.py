# standard imports
import json

# third party imports
import pytest

# local imports
from cic_ussd.redis import InMemoryStore


@pytest.fixture(scope='function')
def account_creation_action_data():
    return {
        'phone_number': '+254712345678',
        'sms_notification_sent': False,
        'status': 'PENDING',
        'task_id': '31e85315-feee-4b6d-995e-223569082cc4'
    }


@pytest.fixture(scope='function')
def set_account_creation_action_data(init_redis_cache, account_creation_action_data):
    redis_cache = init_redis_cache
    action_data = account_creation_action_data
    task_id = action_data.get('task_id')
    redis_cache.set(task_id, json.dumps(action_data))
    redis_cache.persist(task_id)


@pytest.fixture(scope='function')
def successful_incoming_token_gift_callback():
    return {
        'RESULT': {
            'hash': '0xb469fb2ebacc9574afb7b51d44e174fba7129fde71bf757fd39784363270832b',
            'sender': '0xd6204101012270Bf2558EDcFEd595938d1847bf0',
            'recipient': '0xFD9c5aD15C72C6F60f1a119A608931226674243f',
            'source_value': 1048576,
            'destination_value': 1048576,
            'source_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
            'destination_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
            'source_token_symbol': 'SRF',
            'destination_token_symbol': 'SRF',
            'source_token_decimals': 18,
            'destination_token_decimals': 18,
            'chain': 'Bloxberg:8996'
        },
        'PARAM': 'tokengift',
        'STATUS_CODE': 0,
    }


@pytest.fixture(scope='function')
def successful_incoming_transfer_callback():
    return {
        'RESULT': {
            'hash': '0x8b0ed32533164d010afc46c0011fbcb58b0198e03c05b96e2791555746bd3606',
            'sender': '0xd6204101012270Bf2558EDcFEd595938d1847bf1',
            'recipient': '0xd6204101012270Bf2558EDcFEd595938d1847bf0',
            'source_value': 10000000000000000000000,
            'destination_value': 10000000000000000000000,
            'source_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
            'destination_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
            'source_token_symbol': 'SRF',
            'destination_token_symbol': 'SRF',
            'source_token_decimals': 18,
            'destination_token_decimals': 18,
            'chain': 'Bloxberg:8996'
        },
        'PARAM': 'transfer',
        'STATUS_CODE': 0
    }


@pytest.fixture(scope='function')
def incoming_transfer_callback_invalid_tx_status_code():
    return {
        'RESULT': {
            'hash': '0x8b0ed32533164d010afc46c0011fbcb58b0198e03c05b96e2791555746bd3606',
            'sender': '0xd6204101012270Bf2558EDcFEd595938d1847bf1',
            'recipient': '0xd6204101012270Bf2558EDcFEd595938d1847bf0',
            'source_value': 10000000000000000000000,
            'destination_value': 10000000000000000000000,
            'source_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
            'destination_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
            'source_token_symbol': 'SRF',
            'destination_token_symbol': 'SRF',
            'source_token_decimals': 18,
            'destination_token_decimals': 18,
            'chain': 'Bloxberg:8996'
        },
        'PARAM': 'transfer',
        'STATUS_CODE': 1
    }


@pytest.fixture(scope='function')
def incoming_transfer_callback_invalid_tx_param():
    return {
        'RESULT': {
            'hash': '0x8b0ed32533164d010afc46c0011fbcb58b0198e03c05b96e2791555746bd3606',
            'sender': '0xd6204101012270Bf2558EDcFEd595938d1847bf1',
            'recipient': '0xd6204101012270Bf2558EDcFEd595938d1847bf0',
            'source_value': 10000000000000000000000,
            'destination_value': 10000000000000000000000,
            'source_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
            'destination_token': '0xa75B519dc9b0A50D267E03D8B6808f85A66932dd',
            'source_token_symbol': 'SRF',
            'destination_token_symbol': 'SRF',
            'source_token_decimals': 18,
            'destination_token_decimals': 18,
            'chain': 'Bloxberg:8996'
        },
        'PARAM': 'erroneousparam',
        'STATUS_CODE': 0
    }
