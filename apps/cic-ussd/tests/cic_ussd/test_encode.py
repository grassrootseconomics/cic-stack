# local imports
from cic_ussd.encoder import check_password_hash, create_password_hash


def test_create_password_hash(load_config):
    password_hash = create_password_hash(password='Password')
    assert password_hash != 'Password'
    assert type(password_hash) == str


def test_check_password_hash():
    password_hash = create_password_hash(password='Password')
    assert check_password_hash(password='Password', hashed_password=password_hash) is True
