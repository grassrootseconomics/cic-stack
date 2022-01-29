# Used by the create_import_users script.
# This code is largely in the same form as the initial data seeding implementation.

# standard imports
import random
import hashlib
import datetime
import os
from collections import OrderedDict

# external imports
from cic_types.models.person import (
    Person,
    generate_vcard_from_contact_data,
    get_contact_data_from_vcard,
)
from chainlib.eth.address import to_checksum_address, strip_0x
import phonenumbers
from faker import Faker

# local imports
from cic_seeding.chain import set_chain_address


categories = [
    "food/water",
    "fuel/energy",
    "education",
    "health",
    "shop",
    "environment",
    "transport",
    "farming/labor",
    "savingsgroup",
]

fake = Faker(['sl', 'en_US', 'no', 'de', 'ro'])

dt_now = datetime.datetime.utcnow()
dt_then = dt_now - datetime.timedelta(weeks=150)
ts_now = int(dt_now.timestamp())
ts_then = int(dt_then.timestamp())


def genPhoneIndex(phone):
    h = hashlib.new('sha256')
    h.update(phone.encode('utf-8'))
    h.update(b':cic.phone')
    return h.digest().hex()


def genId(addr, typ):
    h = hashlib.new('sha256')
    h.update(bytes.fromhex(addr[2:]))
    h.update(typ.encode('utf-8'))
    return h.digest().hex()


def genDate():
    ts = random.randint(ts_then, ts_now)
    return int(datetime.datetime.fromtimestamp(ts).timestamp())


def genPhone():
    phone_str = '+254' + str(random.randint(100000000, 999999999))
    phone_object = phonenumbers.parse(phone_str)
    return phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)


def genPersonal(phone):
    fn = fake.first_name()
    ln = fake.last_name()
    e = fake.email()

    return generate_vcard_from_contact_data(ln, fn, phone, e)


def genCats():
    i = random.randint(0, 3)
    return random.choices(categories, k=i)


def genAmount(gift_max, gift_factor):
    return random.randint(0, gift_max) * gift_factor


def genDob():
    dob_src = fake.date_of_birth(minimum_age=15)
    dob = {}

    if random.random() < 0.5:
        dob['year'] = dob_src.year

        if random.random() > 0.5:
            dob['month'] = dob_src.month
            dob['day'] = dob_src.day

    return dob


def genEntry(chain_spec):
    old_blockchain_address = os.urandom(20).hex()
    gender = random.choice(['female', 'male', 'other'])
    phone = genPhone()
    v = genPersonal(phone)

    contact_data = get_contact_data_from_vcard(v)
    p = Person()
    p.load_vcard(contact_data)

    p.date_registered = genDate()
    p.date_of_birth = genDob()
    p.gender = gender
    set_chain_address(p, chain_spec, old_blockchain_address)
    p.products = [fake.random_element(elements=OrderedDict(
        [('fruit', 0.25),
         ('maji', 0.05),
         ('milk', 0.1),
         ('teacher', 0.1),
         ('doctor', 0.05),
         ('boutique', 0.15),
         ('recycling', 0.05),
         ('farmer', 0.05),
         ('oil', 0.05),
         ('pastor', 0.1),
         ('chama', 0.03),
         ('pastor', 0.01),
         ('bzrTsuZieaq', 0.01)
         ]))]
    p.location['area_name'] = fake.random_element(elements=OrderedDict(
        [('mnarani', 0.05),
         ('chilumani', 0.1),
         ('madewani', 0.1),
         ('kisauni', 0.05),
         ('bangla', 0.1),
         ('kabiro', 0.1),
         ('manyani', 0.05),
         ('ruben', 0.15),
         ('makupa', 0.05),
         ('kingston', 0.05),
         ('rangala', 0.05),
         ('homabay', 0.1),
         ('nakuru', 0.03),
         ('kajiado', 0.01),
         ('zurtWicKtily', 0.01)
         ]))
    if random.randint(0, 1):
        # fake.local_latitude()
        p.location['latitude'] = (random.random() * 180) - 90
        # fake.local_latitude()
        p.location['longitude'] = (random.random() * 360) - 180

    return old_blockchain_address, phone, p

