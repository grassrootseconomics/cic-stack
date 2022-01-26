# standard imports
import json
import random

# external accounts
import pytest
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.account.tokens import set_active_token
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
def guardian_account(init_database, set_fernet_key):
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
def cache_balances(activated_account, balances, init_cache, token_symbol):
    identifier = [bytes.fromhex(activated_account.blockchain_address), token_symbol.encode('utf-8')]
    balances = json.dumps(balances[0])
    key = cache_data_key(identifier, MetadataPointer.BALANCES)
    cache_data(key, balances)


@pytest.fixture(scope='function')
def cache_adjusted_balances(activated_account, balances, init_cache, token_symbol):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    balances_identifier = [identifier, token_symbol.encode('utf-8')]
    key = cache_data_key(balances_identifier, MetadataPointer.BALANCES_ADJUSTED)
    adjusted_balance = 45931650.64654012
    cache_data(key, adjusted_balance)


@pytest.fixture(scope='function')
def cache_default_token_data(default_token_data, init_cache, load_chain_spec):
    chain_str = Chain.spec.__str__()
    data = json.dumps(default_token_data)
    key = cache_data_key(chain_str.encode('utf-8'), MetadataPointer.TOKEN_DEFAULT)
    cache_data(key, data)


@pytest.fixture(scope='function')
def set_active_token(activated_account, init_cache, token_symbol):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier, MetadataPointer.TOKEN_ACTIVE)
    cache_data(key=key, data=token_symbol)


@pytest.fixture(scope='function')
def cache_token_data(activated_account, init_cache, token_data):
    identifier = [bytes.fromhex(activated_account.blockchain_address), token_data.get('symbol').encode('utf-8')]
    key = cache_data_key(identifier, MetadataPointer.TOKEN_DATA)
    cache_data(key=key, data=json.dumps(token_data))


@pytest.fixture(scope='function')
def cache_token_symbol_list(activated_account, init_cache, token_symbol):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_SYMBOLS_LIST)
    token_symbols_list = [token_symbol]
    cache_data(key, json.dumps(token_symbols_list))


@pytest.fixture(scope='function')
def cache_token_data_list(activated_account, init_cache, token_data):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier, MetadataPointer.TOKEN_DATA_LIST)
    token_data_list = [token_data]
    cache_data(key, json.dumps(token_data_list))


@pytest.fixture(scope='function')
def token_meta_symbol():
    return {
        "contact": {
            "phone": "+254700000000",
            "email": "info@grassrootseconomics.org"
        },
        "country_code": "KE",
        "location": "Kilifi",
        "name": "GRASSROOTS ECONOMICS"
    }


@pytest.fixture(scope='function')
def token_proof_symbol():
    return {
        "description": "Community support",
        "issuer": "Grassroots Economics",
        "namespace": "ge",
        "proofs": [
            "0x4746540000000000000000000000000000000000000000000000000000000000",
            "1f0f0e3e9db80eeaba22a9d4598e454be885855d6048545546fd488bb709dc2f"
        ],
        "version": 0
    }


@pytest.fixture(scope='function')
def token_list_entries():
    return [
        {
            'name': 'Fee',
            'symbol': 'FII',
            'issuer': 'Foo',
            'contact': {'phone': '+254712345678'},
            'location': 'Fum',
            'balance': 50.0
        },
        {
            'name': 'Giftable Token',
            'symbol': 'GFT',
            'issuer': 'Grassroots Economics',
            'contact': {
                'phone': '+254700000000',
                'email': 'info@grassrootseconomics.org'
            },
            'location': 'Fum',
            'balance': 60.0
        },
        {
            'name': 'Demurrage Token',
            'symbol': 'DET',
            'issuer': 'Grassroots Economics',
            'contact': {
                'phone': '+254700000000',
                'email': 'info@grassrootseconomics.org'
            },
            'location': 'Fum',
            'balance': 49.99
        }
    ]


@pytest.fixture(scope='function')
def cache_token_meta_symbol(token_meta_symbol, token_symbol):
    identifier = token_symbol.encode('utf-8')
    key = cache_data_key(identifier, MetadataPointer.TOKEN_META_SYMBOL)
    cache_data(key, json.dumps(token_meta_symbol))


@pytest.fixture(scope='function')
def cache_token_proof_symbol(token_proof_symbol, token_symbol):
    identifier = token_symbol.encode('utf-8')
    key = cache_data_key(identifier, MetadataPointer.TOKEN_PROOF_SYMBOL)
    cache_data(key, json.dumps(token_proof_symbol))


@pytest.fixture(scope='function')
def cache_person_metadata(activated_account, init_cache, person_metadata):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    person = json.dumps(person_metadata)
    key = cache_data_key(identifier, MetadataPointer.PERSON)
    cache_data(key, person)


@pytest.fixture(scope='function')
def cache_preferences(activated_account, init_cache, preferences):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    preferences = json.dumps(preferences)
    key = cache_data_key(identifier, MetadataPointer.PREFERENCES)
    cache_data(key, preferences)


@pytest.fixture(scope='function')
def cache_statement(activated_account, init_cache, statement):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    statement = json.dumps(statement)
    key = cache_data_key(identifier, MetadataPointer.STATEMENT)
    cache_data(key, statement)


@pytest.fixture(scope='function')
def custom_metadata():
    return {"tags": ["ussd", "individual"]}


@pytest.fixture(scope='function')
def default_token_data(token_symbol):
    return {
        'symbol': token_symbol,
        'address': '32e860c2a0645d1b7b005273696905f5d6dc5d05',
        'name': 'Giftable Token',
        'decimals': 6,
        "converters": []
    }


@pytest.fixture(scope='function')
def token_data():
    return {
        "description": "Community support",
        "issuer": "Grassroots Economics",
        "location": "Kilifi",
        "contact": {
            "phone": "+254700000000",
            "email": "info@grassrootseconomics.org"
        },
        "decimals": 6,
        "name": "Giftable Token",
        "symbol": "GFT",
        "address": "32e860c2a0645d1b7b005273696905f5d6dc5d05",
        "proofs": [
            "0x4746540000000000000000000000000000000000000000000000000000000000",
            "1f0f0e3e9db80eeaba22a9d4598e454be885855d6048545546fd488bb709dc2f"
        ],
        "converters": []
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
