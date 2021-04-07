# standard imports
import os
import logging
import urllib.parse
import urllib.error
import urllib.request
import json

# external imports
import celery
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainlib.eth.address import to_checksum_address
from cic_types.processor import generate_metadata_pointer
from cic_types.models.person import Person

logg = logging.getLogger().getChild(__name__)

celery_app = celery.current_app


class MetadataTask(celery.Task):

    balances = None
    chain_spec = None
    import_path = 'out'
    meta_host = None
    meta_port = None
    meta_path = ''
    meta_ssl = False
    balance_processor = None
    autoretry_for = (
            urllib.error.HTTPError,
            )
    retry_kwargs = {
        'countdown': 3,
        'max_retries': 100,
            }

    @classmethod
    def meta_url(self):
        scheme = 'http'
        if self.meta_ssl:
            scheme += s
        url = urllib.parse.urlparse('{}://{}:{}/{}'.format(scheme, self.meta_host, self.meta_port, self.meta_path))
        return urllib.parse.urlunparse(url)


def old_address_from_phone(base_path, phone):
    pidx = generate_metadata_pointer(phone.encode('utf-8'), 'cic.phone')
    phone_idx_path = os.path.join('{}/phone/{}/{}/{}'.format(
            base_path,
            pidx[:2],
            pidx[2:4],
            pidx,
            )
        )
    f = open(phone_idx_path, 'r')
    old_address = f.read()
    f.close()

    return old_address


@celery_app.task(bind=True, base=MetadataTask)
def resolve_phone(self, phone):
    identifier = generate_metadata_pointer(phone.encode('utf-8'), 'cic.phone')
    url = urllib.parse.urljoin(self.meta_url(), identifier)
    logg.debug('attempt getting phone pointer at {} for phone {}'.format(url, phone))
    r = urllib.request.urlopen(url)
    address = json.load(r)
    address = address.replace('"', '')
    logg.debug('address {} for phone {}'.format(address, phone))

    return address


@celery_app.task(bind=True, base=MetadataTask)
def generate_metadata(self, address, phone):
    old_address = old_address_from_phone(self.import_path, phone)

    logg.debug('address {}'.format(address))
    old_address_upper = strip_0x(old_address).upper()
    metadata_path = '{}/old/{}/{}/{}.json'.format(
            self.import_path,
            old_address_upper[:2],
            old_address_upper[2:4],
            old_address_upper,
            )

    f = open(metadata_path, 'r')
    o = json.load(f)
    f.close()

    u = Person.deserialize(o)

    if u.identities.get('evm') == None:
        u.identities['evm'] = {}
    sub_chain_str = '{}:{}'.format(self.chain_spec.common_name(), self.chain_spec.network_id())
    u.identities['evm'][sub_chain_str] = [add_0x(address)]

    new_address_clean = strip_0x(address)
    filepath = os.path.join(
            self.import_path,
            'new',
            new_address_clean[:2].upper(),
            new_address_clean[2:4].upper(),
            new_address_clean.upper() + '.json',
            )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    o = u.serialize()
    f = open(filepath, 'w')
    f.write(json.dumps(o))
    f.close()

    meta_key = generate_metadata_pointer(bytes.fromhex(new_address_clean), 'cic.person')
    meta_filepath = os.path.join(
            self.import_path,
            'meta',
            '{}.json'.format(new_address_clean.upper()),
            )
    os.symlink(os.path.realpath(filepath), meta_filepath)

    logg.debug('found metadata {} for phone {}'.format(o, phone))

    return address


@celery_app.task(bind=True, base=MetadataTask)
def transfer_opening_balance(self, address, phone, serial):


    old_address = old_address_from_phone(self.import_path, phone)
  
    k = to_checksum_address(strip_0x(old_address))
    balance = self.balances[k]
    logg.debug('found balance {} for address {} phone {}'.format(balance, old_address, phone))

    decimal_balance = self.balance_processor.get_decimal_amount(balance)

    tx_hash_hex = self.balance_processor.get_rpc_tx(address, decimal_balance, serial)
    logg.debug('sending {} to {} tx hash {}'.format(decimal_balance, address, tx_hash_hex))

    return tx_hash_hex

