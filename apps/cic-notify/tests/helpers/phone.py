# standard imports

# external imports
from faker import Faker
from faker_e164.providers import E164Provider

# local imports

# test imports

fake = Faker()
fake.add_provider(E164Provider)


def phone_number() -> str:
    return fake.e164('KE')