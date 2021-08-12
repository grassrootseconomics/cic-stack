# standard imports
import os
import random
import uuid

# external imports
from chainlib.eth.address import to_checksum_address
from faker import Faker
from faker_e164.providers import E164Provider

# local imports

# test imports

fake = Faker()
fake.add_provider(E164Provider)


def phone_number() -> str:
    return fake.e164('KE')


def blockchain_address() -> str:
    return to_checksum_address('0x' + os.urandom(20).hex())


def session_id() -> str:
    return uuid.uuid4().hex


def pin_number() -> int:
    return random.randint(1000, 9999)
