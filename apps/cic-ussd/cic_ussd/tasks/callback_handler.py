# standard imports

import json
import logging
from datetime import datetime, timedelta

# external imports
import celery
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.balance import get_balances, calculate_available_balance
from cic_ussd.account.statement import generate
from cic_ussd.cache import Cache, cache_data, cache_data_key, get_cached_data
from cic_ussd.account.chain import Chain
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.models.account import Account
from cic_ussd.processor.poller import wait_for_cache
from cic_ussd.account.statement import filter_statement_transactions
from cic_ussd.account.transaction import transaction_actors
from cic_ussd.account.tokens import (collate_token_metadata,
                                     get_cached_token_data,
                                     get_default_token_symbol,
                                     handle_token_symbol_list,
                                     process_token_data,
                                     set_active_token)
from cic_ussd.error import AccountCreationDataNotFound
from cic_ussd.tasks.base import CriticalSQLAlchemyTask

logg = logging.getLogger(__file__)
celery_app = celery.current_app


@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def account_creation_callback(self, result: str, param: str, status_code: int):
    """This function defines a task that creates a user and
    :param self: Reference providing access to the callback task instance.
    :type self: celery.Task
    :param result: The blockchain address for the created account
    :type result: str
    :param param: URL provided to callback task in cic-eth should http be used for callback.
    :type param: str
    :param status_code: The status of the task to create an account
    :type status_code: int
    """
    task_uuid = self.request.root_id
    cached_account_creation_data = get_cached_data(task_uuid)

    if not cached_account_creation_data:
        raise AccountCreationDataNotFound(f'No account creation data found for task id: {task_uuid}')

    if status_code != 0:
        raise ValueError(f'Unexpected status code: {status_code}')

    account_creation_data = json.loads(cached_account_creation_data)
    account_creation_data['status'] = 'CREATED'
    cache_data(task_uuid, json.dumps(account_creation_data))

    phone_number = account_creation_data.get('phone_number')

    session = SessionBase.create_session()
    account = Account(blockchain_address=result, phone_number=phone_number)
    session.add(account)
    session.commit()
    session.close()
    logg.debug(f'recorded account with identifier: {result}')

    token_symbol = get_default_token_symbol()
    set_active_token(blockchain_address=result, token_symbol=token_symbol)

    queue = self.request.delivery_info.get('routing_key')
    preferences_data = {"preferred_language": param}
    # temporarily caching selected language
    key = cache_data_key(bytes.fromhex(result), MetadataPointer.PREFERENCES)
    cache_data(key, json.dumps(preferences_data))
    s_preferences_metadata = celery.signature(
        'cic_ussd.tasks.metadata.add_preferences_metadata', [result, preferences_data], queue=queue
    )
    s_preferences_metadata.apply_async()

    s_phone_pointer = celery.signature(
        'cic_ussd.tasks.metadata.add_phone_pointer', [result, phone_number], queue=queue
    )
    s_phone_pointer.apply_async()

    custom_metadata = {"tags": ["ussd", "individual"]}
    s_custom_metadata = celery.signature(
        'cic_ussd.tasks.metadata.add_custom_metadata', [result, custom_metadata], queue=queue
    )
    s_custom_metadata.apply_async()
    Cache.store.expire(task_uuid, timedelta(seconds=180))


@celery_app.task
def balances_callback(result: list, param: str, status_code: int):
    """
    :param result:
    :type result:
    :param param:
    :type param:
    :param status_code:
    :type status_code:
    :return:
    :rtype:
    """
    if status_code != 0:
        raise ValueError(f'Unexpected status code: {status_code}.')

    balances = result[0]
    identifier = []
    param = param.split(',')
    for identity in param:
        try:
            i = bytes.fromhex(identity)
            identifier.append(i)
        except ValueError:
            i = identity.encode('utf-8')
            identifier.append(i)
    key = cache_data_key(identifier=identifier, salt=MetadataPointer.BALANCES)
    cache_data(key, json.dumps(balances))


@celery_app.task(bind=True)
def statement_callback(self, result, param: str, status_code: int):
    """
    :param self:
    :type self:
    :param result:
    :type result:
    :param param:
    :type param:
    :param status_code:
    :type status_code:
    :return:
    :rtype:
    """
    if status_code != 0:
        raise ValueError(f'Unexpected status code: {status_code}.')

    queue = self.request.delivery_info.get('routing_key')
    statement_transactions = filter_statement_transactions(result)
    for transaction in statement_transactions:
        recipient_transaction, sender_transaction = transaction_actors(transaction)
        if recipient_transaction.get('blockchain_address') == param:
            recipient_transaction['alt_blockchain_address'] = sender_transaction.get('blockchain_address')
            recipient_transaction['timestamp'] = datetime.utcfromtimestamp(transaction.get('timestamp')).strftime('%d/%m/%y, %H:%M')
            generate(param, queue, recipient_transaction)
        if sender_transaction.get('blockchain_address') == param:
            sender_transaction['alt_blockchain_address'] = recipient_transaction.get('blockchain_address')
            sender_transaction['timestamp'] = datetime.utcfromtimestamp(transaction.get('timestamp')).strftime('%d/%m/%y, %H:%M')
            generate(param, queue, sender_transaction)


@celery_app.task
def token_data_callback(result: dict, param: str, status_code: int):
    """
    :param result:
    :type result:
    :param param:
    :type param:
    :param status_code:
    :type status_code:
    :return:
    :rtype:
    """

    if status_code != 0:
        raise ValueError(f'Unexpected status code: {status_code}.')

    token = result[0]
    token_symbol = token.get('symbol')
    identifier = token_symbol.encode('utf-8')
    token_meta_key = cache_data_key(identifier, MetadataPointer.TOKEN_META_SYMBOL)
    token_info_key = cache_data_key(identifier, MetadataPointer.TOKEN_PROOF_SYMBOL)
    token_meta = get_cached_data(token_meta_key)
    token_meta = json.loads(token_meta)
    token_info = get_cached_data(token_info_key)
    token_info = json.loads(token_info)
    token_data = collate_token_metadata(token_info=token_info, token_metadata=token_meta)
    token_data = {**token_data, **token}
    token_data_key = cache_data_key(identifier, MetadataPointer.TOKEN_DATA)
    cache_data(token_data_key, json.dumps(token_data))
    handle_token_symbol_list(blockchain_address=param, token_symbol=token_symbol)


@celery_app.task(bind=True)
def transaction_balances_callback(self, result: list, param: dict, status_code: int):
    """
    :param self:
    :type self:
    :param result:
    :type result:
    :param param:
    :type param:
    :param status_code:
    :type status_code:
    :return:
    :rtype:
    """
    if status_code != 0:
        raise ValueError(f'Unexpected status code: {status_code}.')
    balances_data = result[0]
    transaction = param
    token_symbol = transaction.get('token_symbol')
    blockchain_address = transaction.get('blockchain_address')
    identifier = token_symbol.encode('utf-8')
    wait_for_cache(identifier, f'Cached token data for: {token_symbol}', MetadataPointer.TOKEN_DATA)
    token_data = get_cached_token_data(blockchain_address, token_symbol)
    decimals = token_data.get('decimals')
    available_balance = calculate_available_balance(balances_data, decimals)
    transaction['available_balance'] = available_balance
    queue = self.request.delivery_info.get('routing_key')

    s_process_account_metadata = celery.signature(
        'cic_ussd.tasks.processor.parse_transaction', [transaction], queue=queue
    )
    s_notify_account = celery.signature('cic_ussd.tasks.notifications.transaction', queue=queue)
    celery.chain(s_process_account_metadata, s_notify_account).apply_async()


@celery_app.task
def transaction_callback(result: dict, param: str, status_code: int):
    """
    :param result:
    :type result:
    :param param:
    :type param:
    :param status_code:
    :type status_code:
    :return:
    :rtype:
    """
    if status_code != 0:
        raise ValueError(f'Unexpected status code: {status_code}.')

    chain_str = Chain.spec.__str__()
    destination_token_symbol = result.get('destination_token_symbol')
    destination_token_value = result.get('destination_token_value')
    recipient_blockchain_address = result.get('recipient')
    sender_blockchain_address = result.get('sender')
    source_token_symbol = result.get('source_token_symbol')
    source_token_value = result.get('source_token_value')

    process_token_data(blockchain_address=recipient_blockchain_address, token_symbol=destination_token_symbol)

    recipient_metadata = {
        "alt_blockchain_address": sender_blockchain_address,
        "blockchain_address": recipient_blockchain_address,
        "role": "recipient",
        "token_symbol": destination_token_symbol,
        "token_value": destination_token_value,
        "transaction_type": param
    }

    get_balances(
        address=recipient_blockchain_address,
        callback_param=recipient_metadata,
        chain_str=chain_str,
        callback_task='cic_ussd.tasks.callback_handler.transaction_balances_callback',
        token_symbol=destination_token_symbol,
        asynchronous=True)

    if param == 'transfer':
        sender_metadata = {
            "alt_blockchain_address": recipient_blockchain_address,
            "blockchain_address": sender_blockchain_address,
            "role": "sender",
            "token_symbol": source_token_symbol,
            "token_value": source_token_value,
            "transaction_type": param
        }

        get_balances(
            address=sender_blockchain_address,
            callback_param=sender_metadata,
            chain_str=chain_str,
            callback_task='cic_ussd.tasks.callback_handler.transaction_balances_callback',
            token_symbol=source_token_symbol,
            asynchronous=True)
