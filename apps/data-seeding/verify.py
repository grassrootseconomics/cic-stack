# standard imports
import argparse
import copy
import hashlib
import json
import logging
import os
import sys
import urllib
import urllib.request
import uuid
import urllib.parse
import re

# external imports
import celery
import confini
from chainlib.chain import ChainSpec
from chainlib.eth.address import to_checksum_address
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.gas import (
    OverrideGasOracle,
    balance,
)
from chainlib.eth.tx import TxFactory
from chainlib.hash import keccak256_string_to_hex
from chainlib.jsonrpc import JSONRPCRequest
from cic_types.models.person import Person, identity_tag
from cic_types.condiments import MetadataPointer
from cic_types.processor import generate_metadata_pointer
from erc20_faucet import Faucet
from eth_erc20 import ERC20
from hexathon.parse import strip_0x, add_0x
from eth_contract_registry import Registry
from eth_accounts_index import AccountsIndex
from eth_token_index import TokenUniqueSymbolIndex

# local imports
from cic_seeding.chain import get_chain_addresses
from cic_seeding import DirHandler
from cic_seeding.index import AddressIndex
from cic_seeding.filter import remove_zeros_filter
from cic_seeding.imports import (
        ImportUser,
        Importer,
        )


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
base_config_dir = os.path.join(script_dir, 'config')

custodial_tests = [
        'custodial_key',
        'gas',
        'faucet',
        'ussd'
        # 'ussd_pins',
        ]

metadata_tests = [
        'metadata',
        'metadata_phone',
        ]

eth_tests = [
        'accounts_index',
        'balance',
        ]

phone_tests = [
        'ussd',
        'metadata_phone',
        ]

admin_tests = [
        'custodial_key',
        ]

cache_tests = [
        'cache_tx_user',
        ]

test_descriptions = {
    'custodial_key': 'Private key is in cic-eth keystore',
    'accounts_index': 'Address is in accounts index |',
    'gas': 'Address has gas balance',
    'faucet': 'Address has triggered the token faucet',
    'balance': 'Address has token balance matching the gift threshold',
    'metadata': 'Personal metadata can be retrieved and has exact match',
    'metadata_custom': 'Custom metadata can be retrieved and has exact match',
    'metadata_phone': 'Phone pointer metadata can be retrieved and matches address',
        }

all_tests = eth_tests + custodial_tests + metadata_tests + phone_tests + cache_tests

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
argparser.add_argument('-c', type=str, help='config override dir')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:foo:1:oldchain', help='chain spec')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('--meta-provider', type=str, dest='meta_provider', help='cic-meta url')
argparser.add_argument('--ussd-provider', type=str, dest='ussd_provider', help='cic-ussd url')
argparser.add_argument('--cache-provider', type=str, dest='cache_provider', help='cic-cache url')
argparser.add_argument('--skip-custodial', dest='skip_custodial', action='store_true', help='skip all custodial verifications')
argparser.add_argument('--skip-ussd', dest='skip_ussd', action='store_true', help='skip all ussd verifications')
argparser.add_argument('--skip-metadata', dest='skip_metadata', action='store_true', help='skip all metadata verifications')
argparser.add_argument('--skip-cache', dest='skip_cache', action='store_true', help='skip all cache verifications')
argparser.add_argument('--skip-all', dest='skip_all', action='store_true', help='skip all verifications (only verifies outdir validity)')
argparser.add_argument('--exclude', action='append', type=str, default=[], help='skip specified verification')
argparser.add_argument('--include', action='append', type=str, help='include specified verification')
argparser.add_argument('--list-verifications', dest='list_verifications', action='store_true', help='print a list of verification check identifiers')
argparser.add_argument('--balance-adjust', dest='balance_adjust', type=str, help='Adjust original balance and apply bounded value check')
argparser.add_argument('--token-symbol', default='GFT', type=str, dest='token_symbol', help='Token symbol to use for trnsactions')
argparser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-x', '--exit-on-error', dest='x', action='store_true', help='Halt exection on error')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('user_dir', type=str, nargs='?', help='user export directory')
args = argparser.parse_args(sys.argv[1:])

if args.list_verifications:
    unique_tests = sorted(set(all_tests))
    for t in unique_tests:
        print(t)
    sys.exit(0)

if not args.user_dir:
    argparser.error('user_dir is required')
    sys.exit(1)

if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config = None
logg.debug('config dir {}'.format(base_config_dir))
if args.c != None:
    config = confini.Config(base_config_dir, env_prefix=os.environ.get('CONFINI_ENV_PREFIX'), override_dirs=args.c)
else:
    config = confini.Config(base_config_dir, env_prefix=os.environ.get('CONFINI_ENV_PREFIX'))
config.process()

# override args
args_override = {
        'CHAIN_SPEC': getattr(args, 'i'),
        'CHAIN_SPEC_SOURCE': getattr(args, 'old_chain_spec'),
        'RPC_PROVIDER': getattr(args, 'p'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        'META_PROVIDER': getattr(args, 'meta_provider'),
        'CACHE_PROVIDER': getattr(args, 'cache_provider'),
        'USSD_PROVIDER': getattr(args, 'ussd_provider'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
config.add(args.user_dir, '_USERDIR', True)
config.add(False, '_RESET', True)
config.add(True, '_APPEND', True)
logg.debug('config loaded:\n{}'.format(config))

token_symbol = args.token_symbol

celery_app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
chain_str = str(chain_spec)
old_chain_spec = ChainSpec.from_chain_str(args.old_chain_spec)
old_chain_str = str(old_chain_spec)
user_dir = args.user_dir # user_out_dir from import_users.py
exit_on_error = args.x
balance_modifier = 0
if args.balance_adjust != None:
    re_adjust = '^([+-])?(\d+(\.\d+)?)(%)?$'
    r = re.search(re_adjust, args.balance_adjust)
    if r.group(4) == '%':
        balance_modifier = float(r.group(2))
        if r.group(1) == '-':
            balance_modifier *= -1.0
        logg.info('using balance modifier percentage of {}%'.format(balance_modifier))
        balance_modifier = float(balance_modifier * 0.01)
    else:
        balance_modifier = int(r.group(2))
        if r.group(1) == '-':
            balance_modifier *= -1
        logg.info('using balance modifier literal of {} token units'.format(balance_modifier))

active_tests = []
exclude = []
include = args.include
api = None

if args.skip_all:
    include = []
else:
    if args.include == None:
        include = all_tests

    for t in args.exclude:
        if t not in all_tests:
            raise ValueError('Cannot exclude unknown verification "{}"'.format(t))
        exclude.append(t)

    if args.skip_custodial:
        logg.info('will skip all custodial verifications ({})'.format(','.join(custodial_tests)))
        for t in custodial_tests:
            if t not in exclude:
                exclude.append(t)

    if args.skip_ussd:
        logg.info('will skip all ussd verifications ({})'.format(','.join(phone_tests)))
        for t in phone_tests:
            if t not in exclude:
                exclude.append(t)
            logg.debug( 'skip test {} {}'.format(t, exclude))

    if args.skip_metadata:
        logg.info('will skip all metadata verifications ({})'.format(','.join(metadata_tests)))
        for t in metadata_tests:
            if t not in exclude:
                exclude.append(t)

    if args.skip_cache:
        logg.info('will skip all cache verifications ({})'.format(','.join(cache_tests)))
        for t in cache_tests:
            if t not in exclude:
                exclude.append(t)

logg.debug('excluuuuude {}'.format(exclude))

for t in include:
    if t not in all_tests:
        raise ValueError('Cannot include unknown verification "{}"'.format(t))
    if t not in exclude:
        active_tests.append(t)
        logg.info('will perform verification "{}"'.format(t))

for t in custodial_tests:
    if t in active_tests:
        from cic_eth.api.admin import AdminApi
        api = AdminApi(None)
        logg.info('activating custodial module'.format(t))
        break


outfunc = logg.debug


def send_ussd_request(address, data_dir):
    upper_address = strip_0x(address).upper()
    f = open(os.path.join(
        data_dir,
        'new',
        upper_address[:2],
        upper_address[2:4],
        upper_address,
    ), 'r'
    )
    o = json.load(f)
    f.close()

    p = Person.deserialize(o)
    phone = p.tel

    session = uuid.uuid4().hex
    valid_service_codes = config.get('USSD_SERVICE_CODE').split(",")
    data = {
        'sessionId': session,
        'serviceCode': valid_service_codes[0],
        'phoneNumber': phone,
        'text': '',
    }

    req = urllib.request.Request(config.get('USSD_PROVIDER'))
    urlencoded_data = urllib.parse.urlencode(data)
    data_bytes = urlencoded_data.encode('utf-8')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.data = data_bytes
    response = urllib.request.urlopen(req)
    return response.read().decode('utf-8')


class VerifierState:

    def __init__(self, item_keys, target_count, active_tests=None):
        self.items = {}
        self.target_count = target_count
        self.count = 0
        for k in item_keys:
            self.items[k] = 0
        if active_tests == None:
            self.active_tests = copy.copy(item_keys)
        else:
            self.active_tests = copy.copy(active_tests)


    def poke(self, item_key):
        self.items[item_key] += 1
        logg.error('poked {}'.format(self.items[item_key]))


    def __str__(self):
        r = ''
        if self.target_count != self.count:
            r += '\x1b[0;33mverification count {} does not match target count {}\x1b[0;39m\n'.format(self.target_count, self.count)
        for k in self.items.keys():
            if k in self.active_tests:
                if self.items[k] == 0:
                    r += '{}: \x1b[0;92m{}/{}\x1b[0;39m\n'.format(k, self.count - self.items[k], self.count)
                else
                    r += '{}: \x1b[0;91m{}/{}\x1b[0;39m\n'.format(k, self.count - self.items[k], self.count)
            else:
                r += '{}: \x1b[0;33mskipped\x1b[0;39m\n'.format(k)
        return r


class VerifierError(Exception):

    def __init__(self, e, c):
        super(VerifierError, self).__init__(e)
        self.c = c


    def __str__(self):
        super_error = super(VerifierError, self).__str__()
        return '[{}] {}'.format(self.c, super_error)


class Verifier:

    def __init__(self, importer, conn, cic_eth_api, gas_oracle, chain_spec, exit_on_error=False, balance_adjust=0):
        self.conn = conn
        self.gas_oracle = gas_oracle
        self.chain_spec = chain_spec
        self.erc20_tx_factory = ERC20(chain_spec, gas_oracle=gas_oracle)
        self.tx_factory = TxFactory(chain_spec, gas_oracle=gas_oracle)
        self.faucet_tx_factory = Faucet(chain_spec, gas_oracle=gas_oracle)
        self.api = cic_eth_api
        self.exit_on_error = exit_on_error
        self.imp = importer
        self.lookup = self.imp.lookup
        self.faucet_amount = 0
        self.balance_adjust = balance_adjust
        self.balance_adjust_percentage = isinstance(balance_adjust, float)
        self.count = 0

        verifymethods = []
        for k in dir(self):
            if len(k) > 7 and k[:7] == 'verify_':
                logg.debug('verifier has verify method {}'.format(k))
                method = k[7:]
                verifymethods.append(method)
                if method == 'faucet':
                    o = self.faucet_tx_factory.token_amount(self.lookup.get('faucet'), sender_address=ZERO_ADDRESS)
                    r = self.conn.do(o)
                    self.faucet_amount = self.faucet_tx_factory.parse_token_amount(r)
                    logg.info('faucet amount set to {} at verify initialization time'.format(self.faucet_amount))

        self.state = VerifierState(verifymethods, len(self.imp), active_tests=active_tests)

        logg.info('verification entry count is {}'.format(len(self.imp)))


    def verify_accounts_index(self, address, balance=None):
        accounts_index = AccountsIndex(self.chain_spec)
        o = accounts_index.have(self.lookup.get('account_registry'), address)
        r = self.conn.do(o)
        n = accounts_index.parse_have(r)
        if n != 1:
            raise VerifierError(n, 'accounts index')


    def __adjust_balance(self, balance):
        if self.balance_adjust == 0:
            return balance
        old_balance = balance
        if self.balance_adjust_percentage:
            mod = int(balance * self.balance_adjust)
            balance += mod
        else:
            balance = balance + self.balance_adjust
        logg.debug('balance adjusted {} -> {}'.format(old_balance, balance))
        return balance

    def verify_balance(self, address, balance):
        o = self.erc20_tx_factory.balance(self.imp.token_address, address)
        r = self.conn.do(o)
        old_balance = balance
        balance = self.__adjust_balance(balance)
        try:
            actual_balance = int(strip_0x(r), 16)
        except ValueError:
            actual_balance = int(r)
        balance = int(balance) * 1000000
        balance += self.faucet_amount
        r = True
        if old_balance == balance:
            r = balance == actual_balance
        elif old_balance < balance:
            r = old_balance < actual_balance
        else:
            r = old_balance > actual_balance
        if not r:
            raise VerifierError((actual_balance, balance), 'balance')


    def verify_custodial_key(self, address, balance=None):
        t = self.api.have_account(address, self.chain_spec)
        r = t.get()
        if r != address:
            raise VerifierError((address, r), 'local key')


    def verify_gas(self, address, balance_token=None):
        o = balance(add_0x(address))
        r = self.conn.do(o)
        actual_balance = int(strip_0x(r), 16)
        if actual_balance == 0:
            raise VerifierError((address, actual_balance), 'gas')


    def verify_faucet(self, address, balance_token=None):
        o = self.faucet_tx_factory.usable_for(self.lookup.get('faucet'), address)
        r = self.conn.do(o)
        if self.faucet_tx_factory.parse_usable_for(r):
            raise VerifierError((address, r), 'faucet')


    def verify_metadata(self, address, balance=None):
        k = generate_metadata_pointer(bytes.fromhex(strip_0x(address)), MetadataPointer.PERSON)
        url = os.path.join(config.get('META_PROVIDER'), k)
        try:
            res = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            raise VerifierError(
                    '({}) {}'.format(url, e),
                    'metadata (person)',
                    )
        b = res.read()
        o_retrieved = json.loads(b.decode('utf-8'))

        j = self.imp.dh.get(address, 'new')

        o_original = json.loads(j)

        if o_original != o_retrieved:
            raise VerifierError(o_retrieved, 'metadata (person)')


    def verify_cache_tx_user(self, address, balance=None):
        address = to_checksum_address(address)
        url = os.path.join(config.get('CACHE_PROVIDER'), 'txa', 'user', address, '100', '0')
        req = urllib.request.Request(url)
        req.add_header('X_CIC_CACHE_MODE', 'all')
        try:
            res = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            raise VerifierError(
                    '({}) {}'.format(url, e),
                    'cache (tx user)',
                    )
        r = json.load(res)
        if len(r['data']) == 0:
            raise VerifierError('empty tx list for address {}'.format(address), 'cache (tx user)')
        for tx in r['data']:
            logg.warning('found tx {} for {} but not checking validity'.format(tx['tx_hash'], address))


    def verify_metadata_phone(self, address, balance=None):
        upper_address = strip_0x(address).upper()
        f = open(os.path.join(
            self.imp.dh.user_dir,
            'new',
            upper_address[:2],
            upper_address[2:4],
            upper_address,
            ), 'r'
            )
        o = json.load(f)
        f.close()

        p = Person.deserialize(o) 

        k = generate_metadata_pointer(p.tel.encode('utf-8'), MetadataPointer.PHONE)
        url = os.path.join(config.get('META_PROVIDER'), k)
        logg.debug('verify metadata phone url {}'.format(url))
        try:
            res = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            raise VerifierError(
                    '({}) {}'.format(url, e),
                    'metadata (phone)',
                    )
        b = res.read()
        address_recovered = json.loads(b.decode('utf-8'))
        address_recovered = address_recovered.replace('"', '')

        try:
            upper_address_recovered = strip_0x(address_recovered).upper()
        except ValueError:
            raise VerifierError(address_recovered, 'metadata (phone) address {} address recovered {}'.format(address, address_recovered))

        if upper_address != upper_address_recovered:
            raise VerifierError(address_recovered, 'metadata (phone)')


    # TODO: should we check language preference when implemented.
    def verify_ussd(self, address, balance=None):
        response_data = send_ussd_request(address, self.imp.dh.user_dir)
        state = response_data[:3]
        out = response_data[4:]
        m = '{} {}'.format(state, out[:7])
        if m != 'CON Welcome':
            raise VerifierError(response_data, 'ussd')


    def verify(self, address, balance, debug_stem=None):
  
        for k in active_tests:
            s = '{}: {}'.format(debug_stem, k)
            outfunc(s)
            try:
                m = getattr(self, 'verify_{}'.format(k))
                m(address, balance)
            except VerifierError as e:
                logline = 'verification {} failed for {}: {}'.format(k, address, str(e))
                if self.exit_on_error:
                    logg.critical(logline)
                    sys.exit(1)
                logg.error(logline)
                self.state.poke(k)

            self.state.count += 1


    def __str__(self):
        return str(self.state)


def main():
    global chain_str, block_offset, user_dir
    
    conn = EthHTTPConnection(config.get('RPC_PROVIDER'))
    gas_oracle = OverrideGasOracle(conn=conn, limit=8000000)
 
    imp = Importer(config, conn, None, None)
    imp.prepare()

    verifier = Verifier(imp, conn, api, gas_oracle, chain_spec, exit_on_error=exit_on_error, balance_adjust=balance_modifier)

    user_new_dir = os.path.join(user_dir, 'new')
    i = 0
    for x in os.walk(user_new_dir):
        for y in x[2]:
            u = None
            try:
                u = imp.user_by_address(y)
            except ValueError:
                continue

            s = 'processing {}'.format(u.description)
            outfunc(s)

            s = 'check {}'.format(u)
            verifier.verify(u.address, u.original_balance, debug_stem=s)
            i += 1

    print()
    print(verifier)


if __name__ == '__main__':
    main()
