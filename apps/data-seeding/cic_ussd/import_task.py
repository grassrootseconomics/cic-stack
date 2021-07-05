# standard imports
import json
import logging
import os
import random
import urllib.error
import urllib.parse
import urllib.request

# external imports
import celery
import psycopg2
from chainlib.eth.address import to_checksum_address
from chainlib.eth.tx import (
    unpack,
    raw,
)
from cic_types.models.person import Person
from cic_types.processor import generate_metadata_pointer
from hexathon import (
    strip_0x,
    add_0x,
)

logg = logging.getLogger()

celery_app = celery.current_app


class ImportTask(celery.Task):
    balances = None
    import_dir = 'out'
    count = 0
    chain_spec = None
    balance_processor = None
    max_retries = None


class MetadataTask(ImportTask):
    meta_host = None
    meta_port = None
    meta_path = ''
    meta_ssl = False
    autoretry_for = (
        urllib.error.HTTPError,
        OSError,
    )
    retry_jitter = True
    retry_backoff = True
    retry_backoff_max = 60

    @classmethod
    def meta_url(self):
        scheme = 'http'
        if self.meta_ssl:
            scheme += 's'
        url = urllib.parse.urlparse('{}://{}:{}/{}'.format(scheme, self.meta_host, self.meta_port, self.meta_path))
        return urllib.parse.urlunparse(url)


def old_address_from_phone(base_path, phone):
    pidx = generate_metadata_pointer(phone.encode('utf-8'), ':cic.phone')
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
    identifier = generate_metadata_pointer(phone.encode('utf-8'), ':cic.phone')
    url = urllib.parse.urljoin(self.meta_url(), identifier)
    logg.debug('attempt getting phone pointer at {} for phone {}'.format(url, phone))
    r = urllib.request.urlopen(url)
    address = json.load(r)
    address = address.replace('"', '')
    logg.debug('address {} for phone {}'.format(address, phone))

    return address


@celery_app.task(bind=True, base=MetadataTask)
def generate_metadata(self, address, phone):
    old_address = old_address_from_phone(self.import_dir, phone)

    logg.debug('address {}'.format(address))
    old_address_upper = strip_0x(old_address).upper()
    metadata_path = '{}/old/{}/{}/{}.json'.format(
        self.import_dir,
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
        self.import_dir,
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

    meta_key = generate_metadata_pointer(bytes.fromhex(new_address_clean), ':cic.person')
    meta_filepath = os.path.join(
        self.import_dir,
        'meta',
        '{}.json'.format(new_address_clean.upper()),
    )
    os.symlink(os.path.realpath(filepath), meta_filepath)

    # write ussd data
    ussd_data = {
        'phone': phone,
        'is_activated': 1,
        'preferred_language': random.sample(['en', 'sw'], 1)[0],
        'is_disabled': False
    }
    ussd_data_dir = os.path.join(self.import_dir, 'ussd')
    ussd_data_file_path = os.path.join(ussd_data_dir, f'{old_address}.json')
    f = open(ussd_data_file_path, 'w')
    f.write(json.dumps(ussd_data))
    f.close()

    # write preferences data
    preferences_dir = os.path.join(self.import_dir, 'preferences')
    preferences_data = {
        'preferred_language': ussd_data['preferred_language']
    }

    preferences_key = generate_metadata_pointer(bytes.fromhex(new_address_clean[2:]), ':cic.preferences')
    preferences_filepath = os.path.join(preferences_dir, 'meta', preferences_key)

    filepath = os.path.join(
        preferences_dir,
        'new',
        preferences_key[:2].upper(),
        preferences_key[2:4].upper(),
        preferences_key.upper() + '.json'
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    f = open(filepath, 'w')
    f.write(json.dumps(preferences_data))
    f.close()
    os.symlink(os.path.realpath(filepath), preferences_filepath)

    logg.debug('found metadata {} for phone {}'.format(o, phone))

    return address


@celery_app.task(bind=True, base=MetadataTask)
def opening_balance_tx(self, address, phone, serial):
    old_address = old_address_from_phone(self.import_dir, phone)

    k = to_checksum_address(strip_0x(old_address))
    balance = self.balances[k]
    logg.debug('found balance {} for address {} phone {}'.format(balance, old_address, phone))

    decimal_balance = self.balance_processor.get_decimal_amount(int(balance))

    (tx_hash_hex, o) = self.balance_processor.get_rpc_tx(address, decimal_balance, serial)

    tx = unpack(bytes.fromhex(strip_0x(o)), self.chain_spec)
    logg.debug('generated tx token value {} to {} tx hash {}'.format(decimal_balance, address, tx_hash_hex))

    tx_path = os.path.join(
        self.import_dir,
        'txs',
        strip_0x(tx_hash_hex),
    )

    f = open(tx_path, 'w')
    f.write(strip_0x(o))
    f.close()

    tx_nonce_path = os.path.join(
        self.import_dir,
        'txs',
        '.' + str(tx['nonce']),
    )
    os.symlink(os.path.realpath(tx_path), tx_nonce_path)

    return tx['hash']


@celery_app.task(bind=True, base=ImportTask, autoretry_for=(FileNotFoundError,), max_retries=None,
                 default_retry_delay=0.1)
def send_txs(self, nonce):
    if nonce == self.count + self.balance_processor.nonce_offset:
        logg.info('reached nonce {} (offset {} + count {}) exiting'.format(nonce, self.balance_processor.nonce_offset,
                                                                           self.count))
        return

    logg.debug('attempt to open symlink for nonce {}'.format(nonce))
    tx_nonce_path = os.path.join(
        self.import_dir,
        'txs',
        '.' + str(nonce),
    )
    f = open(tx_nonce_path, 'r')
    tx_signed_raw_hex = f.read()
    f.close()

    os.unlink(tx_nonce_path)

    o = raw(add_0x(tx_signed_raw_hex))
    tx_hash_hex = self.balance_processor.conn.do(o)

    logg.info('sent nonce {} tx hash {}'.format(nonce, tx_hash_hex))  # tx_signed_raw_hex))

    nonce += 1

    queue = self.request.delivery_info.get('routing_key')
    s = celery.signature(
        'import_task.send_txs',
        [
            nonce,
        ],
        queue=queue,
    )
    s.apply_async()

    return nonce


@celery_app.task
def set_pins(config: dict, phone_to_pins: list):
    # define db connection
    db_conn = psycopg2.connect(
        database=config.get('database'),
        host=config.get('host'),
        port=config.get('port'),
        user=config.get('user'),
        password=config.get('password')
    )
    db_cursor = db_conn.cursor()

    # update db
    for element in phone_to_pins:
        sql = 'UPDATE account SET password_hash = %s WHERE phone_number = %s'
        db_cursor.execute(sql, (element[1], element[0]))
        logg.debug(f'Updating: {element[0]} with: {element[1]}')

    # commit changes
    db_conn.commit()

    # close connections
    db_cursor.close()
    db_conn.close()


@celery_app.task
def set_ussd_data(config: dict, ussd_data: dict):
    # define db connection
    db_conn = psycopg2.connect(
        database=config.get('database'),
        host=config.get('host'),
        port=config.get('port'),
        user=config.get('user'),
        password=config.get('password')
    )
    db_cursor = db_conn.cursor()

    # process ussd_data
    account_status = 1
    if ussd_data['is_activated'] == 1:
        account_status = 2
    preferred_language = ussd_data['preferred_language']
    phone_number = ussd_data['phone']

    sql = 'UPDATE account SET account_status = %s, preferred_language = %s WHERE phone_number = %s'
    db_cursor.execute(sql, (account_status, preferred_language, phone_number))

    # commit changes
    db_conn.commit()

    # close connections
    db_cursor.close()
    db_conn.close()
