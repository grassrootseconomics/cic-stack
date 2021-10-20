# standard imports
import csv
import json
import logging
import os
import random
import uuid
from urllib import error, parse, request

# external imports
import celery
import psycopg2
from celery import Task
from chainlib.chain import ChainSpec
from chainlib.eth.address import to_checksum_address
from chainlib.eth.tx import raw, unpack
from cic_types.models.person import Person, identity_tag
from cic_types.processor import generate_metadata_pointer
from cic_types.condiments import MetadataPointer
from hexathon import add_0x, strip_0x

# local imports


celery_app = celery.current_app
logg = logging.getLogger()


class ImportTask(Task):
    balances = None
    balance_processor = None
    chain_spec: ChainSpec = None
    count = 0
    db_config: dict = None
    import_dir = ''
    include_balances = False
    max_retries = None


class MetadataTask(ImportTask):
    meta_host = None
    meta_port = None
    meta_path = ''
    meta_ssl = False
    autoretry_for = (error.HTTPError, OSError,)
    retry_jitter = True
    retry_backoff = True
    retry_backoff_max = 60

    @classmethod
    def meta_url(cls):
        scheme = 'http'
        if cls.meta_ssl:
            scheme += 's'
        url = parse.urlparse(f'{scheme}://{cls.meta_host}:{cls.meta_port}/{cls.meta_path}')
        return parse.urlunparse(url)


def old_address_from_phone(base_path: str, phone_number: str):
    pid_x = generate_metadata_pointer(phone_number.encode('utf-8'), MetadataPointer.PHONE)
    phone_idx_path = os.path.join(f'{base_path}/phone/{pid_x[:2]}/{pid_x[2:4]}/{pid_x}')
    with open(phone_idx_path, 'r') as f:
        old_address = f.read()
    return old_address


@celery_app.task(bind=True, base=MetadataTask)
def generate_person_metadata(self, blockchain_address: str, phone_number: str):
    logg.debug(f'blockchain address: {blockchain_address}')
    old_blockchain_address = old_address_from_phone(self.import_dir, phone_number)
    old_address_upper = strip_0x(old_blockchain_address).upper()
    metadata_path = f'{self.import_dir}/old/{old_address_upper[:2]}/{old_address_upper[2:4]}/{old_address_upper}.json'
    with open(metadata_path, 'r') as metadata_file:
        person_metadata = json.load(metadata_file)
    person = Person.deserialize(person_metadata)
    if not person.identities.get('evm'):
        person.identities['evm'] = {}
    chain_spec = self.chain_spec.asdict()
    arch = chain_spec.get('arch')
    fork = chain_spec.get('fork')
    tag = identity_tag(chain_spec)
    person.identities[arch][fork] = {
        tag: [blockchain_address]
    }
    file_path = os.path.join(
        self.import_dir,
        'new',
        blockchain_address[:2].upper(),
        blockchain_address[2:4].upper(),
        blockchain_address.upper() + '.json'
    )
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    serialized_person_metadata = person.serialize()
    with open(file_path, 'w') as metadata_file:
        metadata_file.write(json.dumps(serialized_person_metadata))
        logg.debug(f'written person metadata for address: {blockchain_address}')
    meta_filepath = os.path.join(
        self.import_dir,
        'meta',
        '{}.json'.format(blockchain_address.upper()),
    )
    os.symlink(os.path.realpath(file_path), meta_filepath)
    return blockchain_address


@celery_app.task(bind=True, base=MetadataTask)
def generate_preferences_data(self, data: tuple):
    blockchain_address: str = data[0]
    preferences = data[1]
    preferences_dir = os.path.join(self.import_dir, 'preferences')
    preferences_key = generate_metadata_pointer(bytes.fromhex(strip_0x(blockchain_address)), MetadataPointer.PREFERENCES)
    preferences_filepath = os.path.join(preferences_dir, 'meta', preferences_key)
    filepath = os.path.join(
        preferences_dir,
        'new',
        preferences_key[:2].upper(),
        preferences_key[2:4].upper(),
        preferences_key.upper() + '.json'
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as preferences_file:
        preferences_file.write(json.dumps(preferences))
        logg.debug(f'written preferences metadata: {preferences} for address: {blockchain_address}')
    os.symlink(os.path.realpath(filepath), preferences_filepath)
    return blockchain_address


@celery_app.task(bind=True, base=MetadataTask)
def generate_pins_data(self, blockchain_address: str, phone_number: str):
    pins_file = f'{self.import_dir}/pins.csv'
    file_op = 'a' if os.path.exists(pins_file) else 'w'
    with open(pins_file, file_op) as pins_file:
        password_hash = uuid.uuid4().hex
        pins_file.write(f'{phone_number},{password_hash}\n')
        logg.debug(f'written pin data for address: {blockchain_address}')
    return blockchain_address


@celery_app.task(bind=True, base=MetadataTask)
def generate_ussd_data(self, blockchain_address: str, phone_number: str):
    ussd_data_file = f'{self.import_dir}/ussd_data.csv'
    file_op = 'a' if os.path.exists(ussd_data_file) else 'w'
    preferred_language = random.sample(["en", "sw"], 1)[0]
    preferences = {'preferred_language': preferred_language}
    with open(ussd_data_file, file_op) as ussd_data_file:
        ussd_data_file.write(f'{phone_number}, 1, {preferred_language}, False\n')
        logg.debug(f'written ussd data for address: {blockchain_address}')
    return blockchain_address, preferences


@celery_app.task(bind=True, base=MetadataTask)
def opening_balance_tx(self, blockchain_address: str, phone_number: str, serial: str):
    old_blockchain_address = old_address_from_phone(self.import_dir, phone_number)
    address = to_checksum_address(strip_0x(old_blockchain_address))
    balance = self.balances[address]
    logg.debug(f'found balance: {balance} for address: {address} phone: {phone_number}')
    decimal_balance = self.balance_processor.get_decimal_amount(int(balance))
    tx_hash_hex, o = self.balance_processor.get_rpc_tx(blockchain_address, decimal_balance, serial)
    tx = unpack(bytes.fromhex(strip_0x(o)), self.chain_spec)
    logg.debug(f'generated tx token value: {decimal_balance}: {blockchain_address} tx hash {tx_hash_hex}')
    tx_path = os.path.join(self.import_dir, 'txs', strip_0x(tx_hash_hex))
    with open(tx_path, 'w') as tx_file:
        tx_file.write(strip_0x(o))
        logg.debug(f'written tx with tx hash: {tx["hash"]} for address: {blockchain_address}')
    tx_nonce_path = os.path.join(self.import_dir, 'txs', '.' + str(tx['nonce']))
    os.symlink(os.path.realpath(tx_path), tx_nonce_path)
    return tx['hash']


@celery_app.task(bind=True, base=MetadataTask)
def resolve_phone(self, phone_number: str):
    identifier = generate_metadata_pointer(phone_number.encode('utf-8'), MetadataPointer.PHONE)
    url = parse.urljoin(self.meta_url(), identifier)
    logg.debug(f'attempt getting phone pointer at: {url} for phone: {phone_number}')
    r = request.urlopen(url)
    address = json.load(r)
    address = address.replace('"', '')
    logg.debug(f'address: {address} for phone: {phone_number}')
    return address


@celery_app.task(autoretry_for=(FileNotFoundError,),
                 bind=True,
                 base=ImportTask,
                 max_retries=None,
                 default_retry_delay=0.1)
def send_txs(self, nonce):
    queue = self.request.delivery_info.get('routing_key')
    if nonce == self.count + self.balance_processor.nonce_offset:
        logg.info(f'reached nonce {nonce} (offset {self.balance_processor.nonce_offset} + count {self.count}).')
        celery_app.control.broadcast('shutdown', destination=[f'celery@{queue}'])

    logg.debug(f'attempt to open symlink for nonce {nonce}')
    tx_nonce_path = os.path.join(self.import_dir, 'txs', '.' + str(nonce))
    with open(tx_nonce_path, 'r') as tx_nonce_file:
        tx_signed_raw_hex = tx_nonce_file.read()
    os.unlink(tx_nonce_path)
    o = raw(add_0x(tx_signed_raw_hex))
    if self.include_balances:
        tx_hash_hex = self.balance_processor.conn.do(o)
        logg.info(f'sent nonce {nonce} tx hash {tx_hash_hex}')
    nonce += 1
    s = celery.signature('import_task.send_txs', [nonce], queue=queue)
    s.apply_async()
    return nonce


@celery_app.task()
def set_pin_data(config: dict, phone_to_pins: list):
    db_conn = psycopg2.connect(
        database=config.get('database'),
        host=config.get('host'),
        port=config.get('port'),
        user=config.get('user'),
        password=config.get('password')
    )
    db_cursor = db_conn.cursor()
    sql = 'UPDATE account SET password_hash = %s WHERE phone_number = %s'
    for element in phone_to_pins:
        db_cursor.execute(sql, (element[1], element[0]))
        logg.debug(f'Updating: {element[0]} with: {element[1]}')
    db_conn.commit()
    db_cursor.close()
    db_conn.close()


@celery_app.task
def set_ussd_data(config: dict, ussd_data: list):
    db_conn = psycopg2.connect(
        database=config.get('database'),
        host=config.get('host'),
        port=config.get('port'),
        user=config.get('user'),
        password=config.get('password')
    )
    db_cursor = db_conn.cursor()
    sql = 'UPDATE account SET status = %s, preferred_language = %s WHERE phone_number = %s'
    for element in ussd_data:
        status = 2 if int(element[1]) == 1 else 1
        preferred_language = element[2]
        phone_number = element[0]
        db_cursor.execute(sql, (status, preferred_language, phone_number))
    db_conn.commit()
    db_cursor.close()
    db_conn.close()
