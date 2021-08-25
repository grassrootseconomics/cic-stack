# local imports
from cic_ussd.encoder import check_password_hash, create_password_hash, PasswordEncoder


def test_password_encoder(load_config, set_fernet_key):
    assert PasswordEncoder.key == load_config.get('APP_PASSWORD_PEPPER')


def test_create_password_hash(load_config, set_fernet_key):
    fernet_key = PasswordEncoder.key
    assert fernet_key == load_config.get('APP_PASSWORD_PEPPER')
    password_hash = create_password_hash(password='Password')
    assert password_hash != 'Password'
    assert type(password_hash) == str


def test_check_password_hash():
    password_hash = create_password_hash(password='Password')
    assert check_password_hash(password='Password', hashed_password=password_hash) is True
