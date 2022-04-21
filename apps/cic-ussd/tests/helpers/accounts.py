# standard imports
import os
import random
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


def blockchain_address() -> str:
    return os.urandom(20).hex().lower()


def session_id() -> str:
    return uuid.uuid4().hex


def pin_number() -> int:
    return random.randint(1000, 9999)
