# standard imports
import uuid

# external imports
from faker import Faker
from faker_e164.providers import E164Provider

# local imports

# test imports

fake = Faker()
fake.add_provider(E164Provider)


def phone_number() -> str:
    return fake.e164('KE')


def session_id() -> str:
    return uuid.uuid4().hex


def given_name() -> str:
    return fake.first_name()


def family_name() -> str:
    return fake.last_name()
