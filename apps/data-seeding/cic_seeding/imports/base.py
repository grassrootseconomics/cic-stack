# standard imports
import os
import logging
import json
import time
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
from giftable_erc20_token import GiftableToken

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


# Convenience class to make commonly used data fields more accessible than in the Person object:
# - address
# - original address
# - original balance
class ImportUser:

    def __init__(self, dirhandler, person, target_chain_spec, source_chain_spec, verify_address=None):
        self.person = person
        self.chain_spec = target_chain_spec
        self.source_chain_spec = source_chain_spec
        self.phone = person.tel
        self.custom = {}

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


    def add_address(self, address, original=False):
        if original:
            set_chain_address(self.person, self.source_chain_spec, address)
        else:
            set_chain_address(self.person, self.chain_spec, address)
        self.address = address


    def serialize(self):
        return self.person.serialize()


    def __str__(self):
        return str(self.person)


# Contains routines common to all import interfaces.
# Proxies an underlying dirhandler that carries all state and data for the import session.
# Importer must be extended to implement the create_account method.
# Any initialization producing side-effects are defined in prepare(). The same should be the case for any child class.
class Importer:

    max_gas = 8000000
    min_gas = 30000

    def __init__(self, config, rpc, signer=None, signer_address=None, stores={}, default_tag=[], mint_balance=False):
        if mint_balance:
            self._gift_tokens = self._gift_tokens_mint
        else:
            self._gift_tokens = self._gift_tokens_transfer
        # set up import state backend
        self.stores = {}
        self.stores['tags'] = AddressIndex(value_filter=split_filter, name='tags index')
        self.stores['balances'] = AddressIndex(value_filter=remove_zeros_filter, name='balance index')

        for k in stores.keys():
            self.stores[k] = stores[k]

        self.dh = DirHandler(config.get('_USERDIR'), stores=self.stores, exist_ok=True)
        self.dir_reset = config.get('_RESET')
        self.default_tag = default_tag

        self.index_count = {}

        # chain stuff
        self.chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
        self.source_chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC_SOURCE'))

        # signer is only needed if we are sending txs
        self.signer = signer
        self.signer_address = signer_address
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


    # Dirhandler proxy
    def add(self, k, v, dirkey):
        return self.dh.put(k, v, dirkey)


    # Dirhandler proxy
    def get(self, k, dirkey):
        return self.dh.get(k, dirkey)


    # Dirhandler proxy
    def path(self, k):
        return self.dh.dirs.get(k)


    # Look up import user or original user by address.
    def user_by_address(self, address, original=False):
        k = 'new'
        if original:
            k = 'src'
        j = self.dh.get(address, k)
        o = json.loads(j)
        person = Person.deserialize(o)
        return ImportUser(self.dh, person, self.chain_spec, self.source_chain_spec)


    # Total number of records this import is processing
    def __len__(self):
        return self.index_count['balances']


    # Chain registry caching.
    # TODO: Trigger in registry instead and wrap the function.
    def _token_index(self):
        o = self.registry.address_of(self.registry_address, 'TokenRegistry')
        r = self.rpc.do(o)
        token_index_address = self.registry.parse_address_of(r)
        self.lookup['token_index'] = to_checksum_address(token_index_address)
        logg.info('found token index address {}'.format(token_index_address))

    
    # Chain registry caching.
    # TODO: Trigger in registry instead and wrap the function.
    def _account_registry(self):
        o = self.registry.address_of(self.registry_address, 'AccountRegistry')
        r = self.rpc.do(o)
        account_registry = self.registry.parse_address_of(r)
        self.lookup['account_registry'] = to_checksum_address(account_registry)
        logg.info('using account registry {}'.format(self.lookup.get('account_registry')))


    # Chain registry caching.
    # TODO: Trigger in registry instead and wrap the function.
    def _faucet(self):
        o = self.registry.address_of(self.registry_address, 'Faucet')
        r = self.rpc.do(o)
        faucet_address = self.registry.parse_address_of(r)
        self.lookup['faucet'] = to_checksum_address(faucet_address)
        logg.info('found faucet {}'.format(faucet_address))


    # Chain registry caching.
    # TODO: Trigger in registry instead and wrap the function.
    def _registry_default_token(self):
        o = self.registry.address_of(self.registry_address, 'DefaultToken')
        r = self.rpc.do(o)
        token_address = self.registry.parse_address_of(r)
        logg.info('found default token in registry {}'.format(token_address))
        return token_address


    # Attempt to resolve the requested token symbol to an address with the given token index.
    def _default_token(self, token_index_address, token_symbol):
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


    # Trigger all chain registry caching and set default token.
    def __init_lookups(self, use_registry_fallback=True):
        for v in  [
                'account_registry',
                'token_index',
                'faucet',
                ]:
            getattr(self, '_' + v)()

        err = None
        try:
            self.lookup['token'] = self._default_token(self.lookup.get('token_index'), self.__preferred_token_symbol)
            r = True
        except ValueError as e:
            err = e

        if err:
            if not use_registry_fallback:
                raise err
            self.lookup['token'] = self._registry_default_token()

        self.token_address = self.lookup['token']


    # Chain registry caching.
    def __set_token_details(self):
        self.token = ERC20Token(self.chain_spec, self.rpc, self.token_address)
        self.token_multiplier = 10 ** self.token.decimals


    # Initializations with side-effects.
    # Initialize the dirhandler., and triggers chain caching.
    # Load data for the special balances and tags indices from file.
    def prepare(self):
        self.dh.initialize_dirs(reset=self.dir_reset)

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


    def create_account(self, i, u):
        raise NotImplementedError()


    # Default processing for source import user.
    def process_user(self, i, u):
        address = self.create_account(i, u)

        # add address to identities in person object
        #set_chain_address(u.person, self.chain_spec, address)
        u.add_address(address)

        logg.debug('[{}] register eth new address {} for {}'.format(i, address, u))

        return address


    # Default processing for queueing metadata person import
    def process_meta_person(self, i, u):
        address_clean = legacy_normalize_address(u.address)
        meta_key = generate_metadata_pointer(bytes.fromhex(address_clean), MetadataPointer.PERSON)
        self.dh.alias('new', 'meta', address_clean, alias_filename=address_clean + '.json', use_interface=False)


    def process_meta_custom_tags(self, i, u):
        tag_data = self.dh.get(u.original_address, 'tags')
        if tag_data == None or len(tag_data) == 0:
            for tag in self.default_tag:
                tag_data.append(tag)

        for tag in u.custom['tags']:
            tag_data.append(tag)

        address_clean = legacy_normalize_address(u.address)
        custom_key = generate_metadata_pointer(bytes.fromhex(address_clean), MetadataPointer.CUSTOM)
        self.dh.put(custom_key, json.dumps({'tags': tag_data}), 'custom')
        custom_path = self.dh.path(custom_key, 'custom')
        legacy_link_data(custom_path)

        u.custom['tags'] = tag_data


    # Default processing for queueing metadata custom data import
    def process_meta_custom(self, i, u):
        for v in u.custom.keys():
            m = getattr(self, 'process_meta_custom_' + v)
            m(i, u)
        
        
    # Default processing per-address.
    # Create target import user record.
    # Queue metadata items for external metadata import processing.
    def process_address(self, i, u):
        if u.address == None:
            logg.debug('no address to process for user {}'.format(u))
            return

        # add updated person record to the migration data folder
        o = u.serialize()
        self.dh.put(u.address, json.dumps(o), 'new')

        self.process_meta_person(i, u)
        self.process_meta_custom(i, u)


    # TODO: change if leveldir should implement a built-in walk/visitor 
    # Visits callback with every user from the given import store.
    # Expects valid Person object serializations, and will fail hard on any invalid ones encountered.
    # Depending on the store implmentation, records may disappear once retrieved.
    def walk(self, callback, tags=[], batch_size=100, batch_delay=0.2, dirkey='src'):
       srcdir = self.dh.dirs.get(dirkey)

       i = 0
       j = 0
       for x in os.walk(srcdir):
           for y in x[2]:
               s = None
               try:
                   s = self.dh.get(y, dirkey)
               except ValueError:
                   logg.error('walk could not find {} {} {}'.format(x, y, dirkey))
                   continue
               o = json.loads(s)
               p = Person.deserialize(o)

               u = ImportUser(self.dh, p, self.chain_spec, self.source_chain_spec)
               u.custom['tags'] = tags

               callback(i, u)

               i += 1
               sys.stdout.write('processed {} {}'.format(i, u).ljust(200) + "\r")
           
               j += 1
               if j == batch_size:
                   time.sleep(batch_delay)
                   j = 0

       return i
            

    # Default callback for processing of the source import user store.
    # Runs process_user and process_address on each user.
    def process_sync(self, i, u):
        new_address = self.process_user(i, u)
        self.process_address(i, u)

       
    # Default source import user store processor.
    def process_src(self, tags=[], batch_size=100, batch_delay=0.2):
        self.walk(self.process_sync, tags=tags, batch_size=100, batch_delay=0.2)


    # Check the tx for a valid account registration and return the registered address.
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


    # Instantiate an ImportUser object from an address.
    # The address must be a valid record for the import target.
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


    # Combine _address_by_tx and _user_by_address
    def user_by_tx(self, tx):
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

    
    # Send the token transaction for the user's original balance.
    # TODO: There is nothing preventing this from being repeated.
    def _gift_tokens_transfer(self, conn, user):
        balance_full = user.original_balance * self.token_multiplier
        gas_oracle = RPCGasOracle(self.rpc, code_callback=self.get_max_gas)
        erc20 = ERC20(self.chain_spec, signer=self.signer, gas_oracle=gas_oracle, nonce_oracle=self.nonce_oracle)
        (tx_hash_hex, o) = erc20.transfer(self.token_address, self.signer_address, user.address, balance_full)

        r = conn.do(o)

        # export tx
        self._export_tx(tx_hash_hex, o['params'][0])

        logg.info('token gift transfer value {} submitted for {} tx {}'.format(balance_full, user, tx_hash_hex))

        return tx_hash_hex
       

    def _gift_tokens_mint(self, conn, user):
        balance_full = user.original_balance * self.token_multiplier
        gas_oracle = RPCGasOracle(self.rpc, code_callback=self.get_max_gas)
        c = GiftableToken(self.chain_spec, signer=self.signer, gas_oracle=gas_oracle, nonce_oracle=self.nonce_oracle)
        (tx_hash_hex, o) = c.mint_to(self.token_address, self.signer_address, user.address, balance_full)
        
        r = conn.do(o)

        # export tx
        self._export_tx(tx_hash_hex, o['params'][0])

        logg.info('token gift mint value {} submitted for {} tx {}'.format(balance_full, user, tx_hash_hex))

        return tx_hash_hex


    # Archive raw transaction data.
    def _export_tx(self, tx_hash, data):
        tx_hash_hex = strip_0x(tx_hash)
        tx_data = strip_0x(data)
        self.dh.put(tx_hash_hex, tx_data, 'tx')
        return tx_data


    # Trigger for every account registration transaction matching an import user.
    # Only invokes _gift_tokens.
    # Visited by chainsyncer.filter.SyncFilter.
    def filter(self, conn, block, tx, db_session=None):
        # get user if matching tx
        u = self.user_by_tx(tx)
        if u == None:
            return

        # transfer old balance
        self._gift_tokens(conn, u)

    
    # Temporary replacement for better gas handling.
    def get_max_gas(self, v):
        return self.max_gas


    # Temporary replacement for better gas handling.
    def get_min_gas(self, v):
        return self.min_gas
