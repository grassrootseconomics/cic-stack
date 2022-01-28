# standard imports
import os
import logging
import json
import time
import phonenumbers
import sys

# external imports
from cic_types.models.person import Person
from cic_types.processor import generate_metadata_pointer
from cic_types import MetadataPointer
from chainlib.chain import ChainSpec
from chainlib.eth.address import to_checksum_address
from chainlib.eth.constant import ZERO_ADDRESS
from eth_token_index import TokenUniqueSymbolIndex
from eth_accounts_index import AccountsIndex
from erc20_faucet import Faucet
from chainlib.eth.gas import RPCGasOracle
from eth_erc20 import ERC20
from chainlib.eth.address import is_same_address
from eth_contract_registry import Registry
from chainlib.status import Status as TxStatus
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.error import RequestMismatchException
from hexathon import strip_0x
from cic_eth_registry.erc20 import ERC20Token

# local imports
from cic_seeding import DirHandler
from cic_seeding.index import AddressIndex
from cic_seeding.filter import (
        split_filter,
        remove_zeros_filter,
        )
from cic_seeding.chain import (
        set_chain_address,
        get_chain_addresses,
        )
from cic_seeding.legacy import (
        legacy_normalize_address,
        legacy_link_data,
        )
from cic_seeding.error import UnknownTokenError

logg = logging.getLogger(__name__)


class ImportUser:

    def __init__(self, dirhandler, person, target_chain_spec, source_chain_spec, verify_address=None):
        self.person = person
        self.chain_spec = target_chain_spec
        self.source_chain_spec = source_chain_spec
        self.phone = self.person.tel

        addresses = None
        try:
            addresses = get_chain_addresses(person, target_chain_spec)
        except AttributeError:
            logg.debug('user has no address for target chain spec: {}'.format(target_chain_spec))
            pass

        self.address = None
        if addresses != None:
            if verify_address != None:
                if not is_same_address(verify_address, addresses[0]):
                    raise ValueError('extracted adddress {} does not match verify adderss {}'.format(addresses[0], verify_address))
            self.address = addresses[0]

        original_addresses = get_chain_addresses(person, source_chain_spec)
        self.original_address = original_addresses[0]

        self.original_balance = self.original_token_balance(dirhandler)
   
        
        if self.address != None:
            self.description = '{} {}@{} -> {}@{} original token balance {}'.format(
                self.person,
                self.original_address,
                self.source_chain_spec,
                self.address,
                self.chain_spec,
                self.original_balance,
                )
        else:
            self.description = '{} {}@{} original token balance {}'.format(
                self.person,
                self.original_address,
                self.source_chain_spec,
                self.original_balance,
                )



    def original_token_balance(self, dh):
        logg.debug('found original address {}@{} for {}'.format(self.original_address, self.source_chain_spec, self.person))
        balance = 0
        try:
            balance = dh.get(self.original_address, 'balances')
        except KeyError as e:
            logg.error('balance get fail for {}'.format(self))
            return
        return balance


    def __str__(self):
        return str(self.person)


class Importer:

    max_gas = 8000000
    min_gas = 30000

    def __init__(self, config, rpc, signer=None, signer_address=None, stores={}, default_tag=[]):
        # set up import state backend
        self.stores = {}
        self.stores['tags'] = AddressIndex(value_filter=split_filter, name='tags index')
        self.stores['balances'] = AddressIndex(value_filter=remove_zeros_filter, name='balance index')

        for k in stores.keys():
            #logg.info('adding auxiliary dirhandler store {}'.format(k))
            self.stores[k] = stores[k]

        self.dh = DirHandler(config.get('_USERDIR'), stores=self.stores, exist_ok=True)
        try:
            reset = config.get('_RESET')
            self.dh.initialize_dirs(reset=config.true('_RESET'))
        except KeyError as e:
            logg.error('whoa {}'.format(e))
            pass
        self.default_tag = default_tag

        self.index_count = {}

        # chain stuff
        self.chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
        self.source_chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC_SOURCE'))

        # signer is only needed if we are sending txs
        self.signer = signer
        self.aigner_address = signer_address
        self.nonce_oracle = None
        if self.signer != None:
            self.signer_address = signer_address
            self.nonce_oracle = RPCNonceOracle(signer_address, rpc)

        self.__preferred_token_symbol = config.get('TOKEN_SYMBOL')
        self.token_address = None
        self.token = None
        self.token_multiplier = 1
        self.registry = Registry(self.chain_spec)
        self.registry_address = config.get('CIC_REGISTRY_ADDRESS')

        self.lookup = {
            'account_registry': None,
            'token_index': None,
            'faucet': None,
                }

        self.rpc = rpc


    def add(self, k, v, dirkey):
        return self.dh.add(k, v, dirkey)


    def get(self, k, dirkey):
        return self.dh.get(k, dirkey)


    def path(self, k):
        return self.dh.dirs.get(k)


    def user_by_address(self, address, original=False):
        k = 'new'
        if original:
            k = 'src'
        j = self.dh.get(address, k)
        o = json.loads(j)
        person = Person.deserialize(o)
        return ImportUser(self.dh, person, self.chain_spec, self.source_chain_spec)


    def __len__(self):
        return self.index_count['balances']


    def _token_index(self):
        o = self.registry.address_of(self.registry_address, 'TokenRegistry')
        r = self.rpc.do(o)
        token_index_address = self.registry.parse_address_of(r)
        self.lookup['token_index'] = to_checksum_address(token_index_address)
        logg.info('found token index address {}'.format(token_index_address))

    
    def _account_registry(self):
        o = self.registry.address_of(self.registry_address, 'AccountRegistry')
        r = self.rpc.do(o)
        account_registry = self.registry.parse_address_of(r)
        self.lookup['account_registry'] = to_checksum_address(account_registry)
        logg.info('using account registry {}'.format(self.lookup.get('account_registry')))


    def _faucet(self):
        o = self.registry.address_of(self.registry_address, 'Faucet')
        r = self.rpc.do(o)
        faucet_address = self.registry.parse_address_of(r)
        self.lookup['faucet'] = to_checksum_address(faucet_address)
        logg.info('found faucet {}'.format(faucet_address))


    def _registry_default_token(self):
        o = self.registry.address_of(self.registry_address, 'DefaultToken')
        r = self.rpc.do(o)
        token_address = self.registry.parse_address_of(r)
        logg.info('found default token in registry {}'.format(token_address))
        return token_address


    def _default_token(self, token_index_address, token_symbol):
        # TODO: in place of default value in arg, should get registry default token as fallback
        if token_symbol == None:
            raise ValueError('no token symbol given')
        token_index = TokenUniqueSymbolIndex(self.chain_spec)
        o = token_index.address_of(token_index_address, token_symbol)
        r = self.rpc.do(o)
        token_address = token_index.parse_address_of(r)
        if is_same_address(token_address, ZERO_ADDRESS):
            raise FileNotFoundError('token index {} doesn\'t know token "{}"'.format(token_index_address, token_symbol))
        try:
            token_address = to_checksum_address(token_address)
        except ValueError as e:
            logg.critical('lookup failed for token {}: {}'.format(token_symbol, e))
            raise UnknownTokenError('token index {} token symbol {}'.format(token_index_address, token_symbol))
        logg.info('token index {} resolved address {} for token {}'.format(token_index_address, token_address, token_symbol))
        
        return token_address


    def __init_lookups(self):
        for v in  [
                'account_registry',
                'token_index',
                'faucet',
                ]:
            getattr(self, '_' + v)()
        try:
            self.lookup['token'] = self._default_token(self.lookup.get('token_index'), self.__preferred_token_symbol)
        except ValueError:
            self.lookup['token'] = self._registry_default_token()

        self.token_address = self.lookup['token']


    def __set_token_details(self):
        self.token = ERC20Token(self.chain_spec, self.rpc, self.token_address)
        self.token_multiplier = 10 ** self.token.decimals


    def prepare(self):
        for k in [
                'tags',
                'balances',
                ]:
            path = self.dh.path(None, k)
            logg.info('store {} {}'.format(k, path))
            c = self.stores[k].add_from_file(path)
            self.index_count[k] = c

        if self.rpc != None:
            self.__init_lookups()
            self.__set_token_details()
        else:
            logg.warning('no blockchain rpc defined, so will not look up anything from there')


    def process_user(self, i, u):
        raise NotImplementedError()


    def create_account(self, i, u):
        raise NotImplementedError()


    def process_user(self, i, u):
        address = self.create_account(i, u)
        logg.debug('[{}] register eth new address {} for {}'.format(i, address, u))
        return address


    def process_address(self, i, u, address, tags=[]):
        # add address to identities in person object
        set_chain_address(u, self.chain_spec, new_address)


        # add updated person record to the migration data folder
        o = u.serialize()
        self.dh.add(new_address, json.dumps(o), 'new')


        new_address_clean = legacy_normalize_address(new_address)
        meta_key = generate_metadata_pointer(bytes.fromhex(new_address_clean), MetadataPointer.PERSON)
        self.dh.alias('new', 'meta', new_address_clean, alias_filename=new_address_clean + '.json', use_interface=False)

        phone_object = phonenumbers.parse(u.tel)
        phone = phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)
        meta_phone_key = generate_metadata_pointer(phone.encode('utf-8'), MetadataPointer.PHONE)


        self.dh.add(meta_phone_key, new_address_clean, 'phone')
        entry_path = self.dh.path(meta_phone_key, 'phone')
        legacy_link_data(entry_path)

        # custom data
        custom_key = generate_metadata_pointer(phone.encode('utf-8'), MetadataPointer.CUSTOM)
        
        old_addresses = get_chain_addresses(u, self.source_chain_spec)
        old_address = legacy_normalize_address(old_addresses[0])

        tag_data = self.dh.get(old_address, 'tags')

        for tag in self.default_tag:
            tag_data.append(tag)

        for tag in tags:
            tag_data.append(tag)

        self.dh.add(custom_key, json.dumps({'tags': tag_data}), 'custom')
        custom_path = self.dh.path(custom_key, 'custom')
        legacy_link_data(custom_path)


    def walk(self, callback, tags=[], batch_size=100, batch_delay=0.2):
       srcdir = self.dh.dirs.get('src')

       i = 0
       j = 0
       for x in os.walk(srcdir):
           for y in x[2]:
               s = None
               try:
                   s = self.dh.get(y, 'src')
               except ValueError:
                   continue
               o = json.loads(s)
               u = Person.deserialize(o)

               logg.debug('person {}'.format(u))

               callback(i, u, tags=tags)

               i += 1
               sys.stdout.write('processed {} {}'.format(i, u).ljust(200) + "\r")
           
               j += 1
               if j == batch_size:
                   time.sleep(batch_delay)


    def process_sync(self, i, u, tags=[]):
        # create new ethereum address (in custodial backend)
        new_address = self.process_user(i, u)
        self.process_address(i, u, new_address, tags=tags)

        
    def process_src(self, tags=[], batch_size=100, batch_delay=0.2):
        self.walk(self.process_sync, tags=tags, batch_size=100, batch_delay=0.2)


    def _address_by_tx(self, tx):
        if tx.payload == None or len(tx.payload) == 0:
            return None

        r = None
        try:
            r = AccountsIndex.parse_add_request(tx.payload)
        except RequestMismatchException:
            return None
        address = r[0]

        if tx.status != TxStatus.SUCCESS:
            logg.warning('failed accounts index transaction for {}: {}'.format(address, tx.hash))
            return None

        logg.debug('account registry add match for {} in {}'.format(address, tx.hash))
        return address


    def _user_by_address(self, address):
        try:
            j = self.dh.get(address, 'new')
        except FileNotFoundError:
            logg.debug('skip tx with unknown recipient address {}'.format(address))
            return None

        o = json.loads(j)

        person = Person.deserialize(o)

        u = ImportUser(self.dh, person, self.chain_spec, self.source_chain_spec, verify_address=address)

        return u


    def _user_by_tx(self, tx):
        if tx.payload == None or len(tx.payload) == 0:
            logg.debug('no payload, skipping {}'.format(tx))
            return None

        address = self._address_by_tx(tx) 
        if address == None:
            return None
        u = self._user_by_address(address)

        if u == None:
            logg.debug('no match in import data for address {}'.format(address))
            return None

        logg.info('tx user match for ' + u.description)

        return u


    def _gift_tokens(self, conn, user):
        logg.debug('foo')
        balance_full = user.original_balance * self.token_multiplier

        gas_oracle = RPCGasOracle(self.rpc, code_callback=self.get_max_gas)
        erc20 = ERC20(self.chain_spec, signer=self.signer, gas_oracle=gas_oracle, nonce_oracle=self.nonce_oracle)
        (tx_hash_hex, o) = erc20.transfer(self.token_address, self.signer_address, user.address, balance_full)
        r = conn.do(o)

        # export tx
        self._export_tx(tx_hash_hex, o['params'][0])

        logg.info('token gift value {} submitted for {} tx {}'.format(balance_full, user, tx_hash_hex))

        return tx_hash_hex


    def _export_tx(self, tx_hash, data):
        tx_hash_hex = strip_0x(tx_hash)
        tx_data = strip_0x(data)
        self.dh.add(tx_hash_hex, tx_data, 'txs')


    def filter(self, conn, block, tx, db_session):
        raise NotImplementedError()


    def get_max_gas(self, v):
        return self.max_gas


    def get_min_gas(self, v):
        return self.min_gas
