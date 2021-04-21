# standard imports
import json
import uuid
from random import randint

# third party imports
import pytest
from cic_types.models.person import generate_metadata_pointer
from faker import Faker

# local imports
from cic_ussd.db.models.account import AccountStatus, Account
from cic_ussd.redis import cache_data
from cic_ussd.metadata import blockchain_address_to_metadata_pointer


fake = Faker()


@pytest.fixture(scope='function')
def create_activated_user(init_database, set_fernet_key):
    user = Account(
        blockchain_address='0xFD9c5aD15C72C6F60f1a119A608931226674243f',
        phone_number='+25498765432'
    )
    user.preferred_language = 'en'
    user.create_password('0000')
    user.activate_account()
    init_database.add(user)
    init_database.commit()
    return user


@pytest.fixture(scope='function')
def create_valid_tx_recipient(init_database, set_fernet_key):
    user = Account(
        blockchain_address='0xd6204101012270Bf2558EDcFEd595938d1847bf0',
        phone_number='+25498765432'
    )
    user.preferred_language = 'en'
    user.create_password('0000')
    user.activate_account()
    init_database.add(user)
    init_database.commit()
    return user


@pytest.fixture(scope='function')
def create_valid_tx_sender(init_database, set_fernet_key):
    user = Account(
        blockchain_address='0xd6204101012270Bf2558EDcFEd595938d1847bf1',
        phone_number='+25498765433'
    )
    user.preferred_language = 'en'
    user.create_password('0000')
    user.activate_account()
    init_database.add(user)
    init_database.commit()
    return user


@pytest.fixture(scope='function')
def create_pending_user(init_database, set_fernet_key):
    user = Account(
        blockchain_address='0x0ebdea8612c1b05d952c036859266c7f2cfcd6a29842d9c6cce3b9f1ba427588',
        phone_number='+25498765432'
    )
    init_database.add(user)
    init_database.commit()
    return user


@pytest.fixture(scope='function')
def create_pin_blocked_user(init_database, set_fernet_key):
    user = Account(
        blockchain_address='0x0ebdea8612c1b05d952c036859266c7f2cfcd6a29842d9c6cce3b9f1ba427588',
        phone_number='+25498765432'
    )
    user.create_password('0000')
    user.failed_pin_attempts = 3
    user.account_status = 3
    init_database.add(user)
    init_database.commit()
    return user


@pytest.fixture(scope='function')
def create_locked_accounts(init_database, set_fernet_key):
    for i in range(20):
        blockchain_address = str(uuid.uuid4())
        phone_number = fake.phone_number()
        pin = f'{randint(1000, 9999)}'
        user = Account(phone_number=phone_number, blockchain_address=blockchain_address)
        user.create_password(password=pin)
        user.failed_pin_attempts = 3
        user.account_status = AccountStatus.LOCKED.value
        user.session.add(user)
        user.session.commit()


@pytest.fixture(scope='function')
def complete_user_metadata(create_activated_user):
    return {
        "date_registered": create_activated_user.created,
        "family_name": "Snow",
        "given_name": "Name",
        "gender": 'Male',
        "location": "Kangemi",
        "products": "Mandazi"
    }


@pytest.fixture(scope='function')
def cached_user_metadata(create_activated_user, init_redis_cache, person_metadata):
    user_metadata = json.dumps(person_metadata)
    key = generate_metadata_pointer(
        identifier=blockchain_address_to_metadata_pointer(blockchain_address=create_activated_user.blockchain_address),
        cic_type='cic.person'
    )
    cache_data(key=key, data=user_metadata)
