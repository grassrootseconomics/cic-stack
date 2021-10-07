# standard imports
import json
import random

# external accounts
import pytest
from chainlib.hash import strip_0x

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.cache import cache_data, cache_data_key
from cic_ussd.db.enum import AccountStatus
from cic_ussd.db.models.account import Account

# test imports
from tests.helpers.accounts import blockchain_address, phone_number


@pytest.fixture(scope='function')
def account_creation_data(task_uuid):
    return {
        'phone_number': phone_number(),
        'sms_notification_sent': False,
        'status': 'PENDING',
        'task_uuid': task_uuid
    }


@pytest.fixture(scope='function')
def activated_account(init_database, set_fernet_key):
    account = Account(blockchain_address(), phone_number())
    account.create_password('0000')
    account.activate_account()
    init_database.add(account)
    init_database.commit()
    return account


@pytest.fixture(scope='function')
def balances():
    return [{
        'address': blockchain_address(),
        'converters': [],
        'balance_network': 50000000,
        'balance_outgoing': 0,
        'balance_incoming': 0
    }]


@pytest.fixture(scope='function')
def cache_account_creation_data(init_cache, account_creation_data):
    cache_data(account_creation_data.get('task_uuid'), json.dumps(account_creation_data))


@pytest.fixture(scope='function')
def cache_balances(activated_account, balances, init_cache):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    balances = json.dumps(balances[0])
    key = cache_data_key(identifier, ':cic.balances')
    cache_data(key, balances)


@pytest.fixture(scope='function')
def cache_default_token_data(default_token_data, init_cache, load_chain_spec):
    chain_str = Chain.spec.__str__()
    data = json.dumps(default_token_data)
    key = cache_data_key(chain_str.encode('utf-8'), ':cic.default_token_data')
    cache_data(key, data)


@pytest.fixture(scope='function')
def cache_person_metadata(activated_account, init_cache, person_metadata):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    person = json.dumps(person_metadata)
    key = cache_data_key(identifier, ':cic.person')
    cache_data(key, person)


@pytest.fixture(scope='function')
def cache_preferences(activated_account, init_cache, preferences):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    preferences = json.dumps(preferences)
    key = cache_data_key(identifier, ':cic.preferences')
    cache_data(key, preferences)


@pytest.fixture(scope='function')
def cache_statement(activated_account, init_cache, statement):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    statement = json.dumps(statement)
    key = cache_data_key(identifier, ':cic.statement')
    cache_data(key, statement)


@pytest.fixture(scope='function')
def custom_metadata():
    return {"tags": ["ussd", "individual"]}


@pytest.fixture(scope='function')
def default_token_data(token_symbol):
    return {
            'symbol': token_symbol,
            'address': blockchain_address(),
            'name': 'Giftable',
            'decimals': 6
    }


@pytest.fixture(scope='function')
def locked_accounts_traffic(init_database, set_fernet_key):
    for _ in range(20):
        address = blockchain_address()
        phone = phone_number()
        account = Account(address, phone)
        account.create_password(str(random.randint(1000, 9999)))
        account.failed_pin_attempts = 3
        account.status = AccountStatus.LOCKED.value
        init_database.add(account)
        init_database.commit()


@pytest.fixture(scope='function')
def pending_account(init_database, set_fernet_key):
    account = Account(blockchain_address(), phone_number())
    init_database.add(account)
    init_database.commit()
    return account


@pytest.fixture(scope='function')
def pin_blocked_account(init_database, set_fernet_key):
    account = Account(blockchain_address(), phone_number())
    account.create_password('3333')
    account.failed_pin_attempts = 3
    init_database.add(account)
    init_database.commit()
    return account


@pytest.fixture(scope='function')
def preferences():
    return {
        'preferred_language': random.sample(['en', 'sw'], 1)[0]
    }


@pytest.fixture(scope='function')
def raw_person_metadata():
    return {
        "date_of_birth": {
            'year': 1998
        },
        "family_name": "Snow",
        "given_name": "Name",
        "gender": 'Male',
        "location": "Kangemi",
        "products": "Mandazi"
    }


@pytest.fixture(scope='function')
def valid_recipient(init_database, set_fernet_key):
    account = Account(blockchain_address(), phone_number())
    account.create_password('2222')
    account.activate_account()
    init_database.add(account)
    init_database.commit()
    return account
