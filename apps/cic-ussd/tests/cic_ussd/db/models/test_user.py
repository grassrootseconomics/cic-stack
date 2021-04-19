"""Tests the persistence of the user record and associated functions to the user object"""

# standard imports
import pytest

# platform imports
from cic_ussd.db.models.account import Account


def test_user(init_database, set_fernet_key):
    user = Account(blockchain_address='0x417f5962fc52dc33ff0689659b25848680dec6dcedc6785b03d1df60fc6d5c51',
                   phone_number='+254700000000')
    user.create_password('0000')

    session = Account.session
    session.add(user)
    session.commit()

    queried_user = session.query(Account).get(1)
    assert queried_user.blockchain_address == '0x417f5962fc52dc33ff0689659b25848680dec6dcedc6785b03d1df60fc6d5c51'
    assert queried_user.phone_number == '+254700000000'
    assert queried_user.failed_pin_attempts == 0
    assert queried_user.verify_password('0000') is True


def test_user_state_transition(create_pending_user):
    user = create_pending_user
    session = Account.session

    assert user.get_account_status() == 'PENDING'
    user.activate_account()
    assert user.get_account_status() == 'ACTIVE'
    user.failed_pin_attempts = 3
    assert user.get_account_status() == 'LOCKED'
    user.reset_account_pin()
    assert user.get_account_status() == 'RESET'
    user.activate_account()
    assert user.get_account_status() == 'ACTIVE'
    session.add(user)
    session.commit()
