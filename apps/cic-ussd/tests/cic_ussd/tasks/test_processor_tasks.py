# standard imports
import json

# external imports
import celery
from chainlib.hash import strip_0x
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.transaction import transaction_actors
from cic_ussd.cache import cache_data_key, get_cached_data


# test imports


def test_generate_statement(activated_account,
                            celery_session_worker,
                            cache_preferences,
                            mocker,
                            transaction_result):
    mock_task = mocker.patch('celery.app.task.Task.request')
    mock_task.delivery_info = {'routing_key': 'cic-ussd'}
    mock_chain = mocker.patch('celery.chain')
    recipient_transaction, sender_transaction = transaction_actors(transaction_result)
    s_generate_statement = celery.signature(
        'cic_ussd.tasks.processor.generate_statement', [activated_account.blockchain_address, sender_transaction]
    )
    result = s_generate_statement.apply_async().get()
    mock_chain.assert_called_once()


def test_cache_statement(activated_account,
                         cache_default_token_data,
                         cache_person_metadata,
                         cache_preferences,
                         celery_session_worker,
                         init_database,
                         transaction_result):
    recipient_transaction, sender_transaction = transaction_actors(transaction_result)
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    key = cache_data_key(identifier, MetadataPointer.STATEMENT)
    cached_statement = get_cached_data(key)
    assert cached_statement is None
    s_parse_transaction = celery.signature(
        'cic_ussd.tasks.processor.parse_transaction', [sender_transaction])
    result = s_parse_transaction.apply_async().get()
    s_cache_statement = celery.signature(
        'cic_ussd.tasks.processor.cache_statement', [result, activated_account.blockchain_address]
    )
    s_cache_statement.apply_async().get()
    cached_statement = get_cached_data(key)
    cached_statement = json.loads(cached_statement)
    assert len(cached_statement) == 1

    sender_transaction['token_value'] = 60.0
    s_parse_transaction = celery.signature(
        'cic_ussd.tasks.processor.parse_transaction', [sender_transaction])
    result = s_parse_transaction.apply_async().get()
    s_cache_statement = celery.signature(
        'cic_ussd.tasks.processor.cache_statement', [result, activated_account.blockchain_address]
    )
    s_cache_statement.apply_async().get()
    cached_statement = get_cached_data(key)
    cached_statement = json.loads(cached_statement)
    assert len(cached_statement) == 2


def test_parse_transaction(activated_account,
                           cache_person_metadata,
                           cache_preferences,
                           celery_session_worker,
                           init_database,
                           transaction_result):
    recipient_transaction, sender_transaction = transaction_actors(transaction_result)
    assert sender_transaction.get('metadata_id') is None
    assert sender_transaction.get('phone_number') is None
    s_parse_transaction = celery.signature(
        'cic_ussd.tasks.processor.parse_transaction', [sender_transaction])
    result = s_parse_transaction.apply_async().get()
    assert result.get('metadata_id') == activated_account.standard_metadata_id()
    assert result.get('phone_number') == activated_account.phone_number
