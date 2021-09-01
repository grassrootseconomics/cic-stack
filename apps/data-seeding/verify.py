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
from cic_types.models.person import (
    Person,
    generate_metadata_pointer,
)
from erc20_faucet import Faucet
from eth_erc20 import ERC20
from hexathon.parse import strip_0x, add_0x
from eth_contract_registry import Registry
from eth_accounts_index import AccountsIndex
from eth_token_index import TokenUniqueSymbolIndex

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = '/usr/local/etc/cic-syncer'

custodial_tests = [
        'local_key',
        'gas',
        'faucet',
        'ussd',
        'ussd_pins',
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
        'ussd_pins'
        ]

admin_tests = [
        'local_key',
        ]

all_tests = eth_tests + custodial_tests + metadata_tests + phone_tests

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:oldchain:1', help='chain spec')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('--meta-provider', type=str, dest='meta_provider', default='http://localhost:63380', help='cic-meta url')
argparser.add_argument('--ussd-provider', type=str, dest='ussd_provider', default='http://localhost:63315', help='cic-ussd url')
argparser.add_argument('--skip-custodial', dest='skip_custodial', action='store_true', help='skip all custodial verifications')
argparser.add_argument('--skip-ussd', dest='skip_ussd', action='store_true', help='skip all ussd verifications')
argparser.add_argument('--skip-metadata', dest='skip_metadata', action='store_true', help='skip all metadata verifications')
argparser.add_argument('--exclude', action='append', type=str, default=[], help='skip specified verification')
argparser.add_argument('--include', action='append', type=str, help='include specified verification')
argparser.add_argument('--token-symbol', default='GFT', type=str, dest='token_symbol', help='Token symbol to use for trnsactions')
argparser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-x', '--exit-on-error', dest='x', action='store_true', help='Halt exection on error')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('user_dir', type=str, help='user export directory')
args = argparser.parse_args(sys.argv[1:])

if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config_dir = os.path.join(args.c)
os.makedirs(config_dir, 0o777, True)
config = confini.Config(config_dir, args.env_prefix)
config.process()
# override args
args_override = {
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'ETH_PROVIDER': getattr(args, 'p'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
config.add(args.meta_provider, '_META_PROVIDER', True)
config.add(args.ussd_provider, '_USSD_PROVIDER', True)

token_symbol = args.token_symbol

logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

celery_app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
chain_str = str(chain_spec)
old_chain_spec = ChainSpec.from_chain_str(args.old_chain_spec)
old_chain_str = str(old_chain_spec)
user_dir = args.user_dir # user_out_dir from import_users.py
exit_on_error = args.x

active_tests = []
exclude = []
include = args.include
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
if args.skip_metadata:
    logg.info('will skip all metadata verifications ({})'.format(','.join(metadata_tests)))
    for t in metadata_tests:
        if t not in exclude:
            exclude.append(t)
for t in include:
    if t not in all_tests:
        raise ValueError('Cannot include unknown verification "{}"'.format(t))
    if t not in exclude:
        active_tests.append(t)
        logg.info('will perform verification "{}"'.format(t))

api = None
for t in custodial_tests:
    if t in active_tests:
        from cic_eth.api.admin import AdminApi
        api = AdminApi(None)
        logg.info('activating custodial module'.format(t))
        break

cols = os.get_terminal_size().columns


def to_terminalwidth(s):
    ss = s.ljust(int(cols)-1)
    ss += "\r"
    return ss

def default_outfunc(s):
    ss = to_terminalwidth(s)
    sys.stdout.write(ss)
outfunc = default_outfunc
if logg.isEnabledFor(logging.DEBUG):
    outfunc = logg.debug


def send_ussd_request(address, data_dir):
    upper_address = strip_0x(address).upper()
    f = open(os.path.join(
        data_dir,
        'new',
        upper_address[:2],
        upper_address[2:4],
        upper_address + '.json',
    ), 'r'
    )
    o = json.load(f)
    f.close()

    p = Person.deserialize(o)
    phone = p.tel

    session = uuid.uuid4().hex
    data = {
        'sessionId': session,
        'serviceCode': config.get('APP_SERVICE_CODE'),
        'phoneNumber': phone,
        'text': '',
    }

    req = urllib.request.Request(config.get('_USSD_PROVIDER'))
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
        for k in item_keys:
            self.items[k] = 0
        if active_tests == None:
            self.active_tests = copy.copy(item_keys)
        else:
            self.active_tests = copy.copy(active_tests)


    def poke(self, item_key):
        self.items[item_key] += 1


    def __str__(self):
        r = ''
        for k in self.items.keys():
            if k in self.active_tests:
                r += '{}: {}/{}\n'.format(k, self.items[k], self.target_count)
            else:
                r += '{}: skipped\n'.format(k)
        return r


class VerifierError(Exception):

    def __init__(self, e, c):
        super(VerifierError, self).__init__(e)
        self.c = c


    def __str__(self):
        super_error = super(VerifierError, self).__str__()
        return '[{}] {}'.format(self.c, super_error)


class Verifier:

    # TODO: what an awful function signature
    def __init__(self, conn, target_count, cic_eth_api, gas_oracle, chain_spec, index_address, token_address, faucet_address, data_dir, exit_on_error=False):
        self.conn = conn
        self.gas_oracle = gas_oracle
        self.chain_spec = chain_spec
        self.index_address = index_address
        self.token_address = token_address
        self.faucet_address = faucet_address
        self.erc20_tx_factory = ERC20(chain_spec, gas_oracle=gas_oracle)
        self.tx_factory = TxFactory(chain_spec, gas_oracle=gas_oracle)
        self.api = cic_eth_api
        self.data_dir = data_dir
        self.exit_on_error = exit_on_error
        self.faucet_tx_factory = Faucet(chain_spec, gas_oracle=gas_oracle)

        verifymethods = []
        for k in dir(self):
            if len(k) > 7 and k[:7] == 'verify_':
                logg.debug('verifier has verify method {}'.format(k))
                verifymethods.append(k[7:])
        o = self.faucet_tx_factory.token_amount(self.faucet_address, sender_address=ZERO_ADDRESS)
        r = self.conn.do(o)
        self.faucet_amount = self.faucet_tx_factory.parse_token_amount(r)
        logg.info('faucet amount set to {} at verify initialization time'.format(self.faucet_amount))

        self.state = VerifierState(verifymethods, target_count, active_tests=active_tests)


    def verify_accounts_index(self, address, balance=None):
        accounts_index = AccountsIndex(self.chain_spec)
        o = accounts_index.have(self.index_address, address)
        r = self.conn.do(o)
        n = accounts_index.parse_have(r)
        logg.debug('index check for {}: {}'.format(address, n))
        if n != 1:
            raise VerifierError(n, 'accounts index')


    def verify_balance(self, address, balance):
        o = self.erc20_tx_factory.balance(self.token_address, address)
        r = self.conn.do(o)
        try:
            actual_balance = int(strip_0x(r), 16)
        except ValueError:
            actual_balance = int(r)
        balance = int(balance / 1000000) * 1000000
        balance += self.faucet_amount
        logg.info('balance for {}: {}'.format(address, balance))
        if balance != actual_balance:
            raise VerifierError((actual_balance, balance), 'balance')


    def verify_local_key(self, address, balance=None):
        t = self.api.have_account(address, self.chain_spec)
        r = t.get()
        logg.debug('verify local key result {}'.format(r))
        if r != address:
            raise VerifierError((address, r), 'local key')


    def verify_gas(self, address, balance_token=None):
        o = balance(address)
        r = self.conn.do(o)
        logg.debug('wtf {}'.format(r))
        actual_balance = int(strip_0x(r), 16)
        if actual_balance == 0:
            raise VerifierError((address, actual_balance), 'gas')


    def verify_faucet(self, address, balance_token=None):
        o = self.faucet_tx_factory.usable_for(self.faucet_address, address)
        r = self.conn.do(o)
        if self.faucet_tx_factory.parse_usable_for(r):
            raise VerifierError((address, r), 'faucet')


    def verify_metadata(self, address, balance=None):
        k = generate_metadata_pointer(bytes.fromhex(strip_0x(address)), ':cic.person')
        url = os.path.join(config.get('_META_PROVIDER'), k)
        logg.debug('verify metadata url {}'.format(url))
        try:
            res = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            raise VerifierError(
                    '({}) {}'.format(url, e),
                    'metadata (person)',
                    )
        b = res.read()
        o_retrieved = json.loads(b.decode('utf-8'))

        upper_address = strip_0x(address).upper()
        f = open(os.path.join(
            self.data_dir,
            'new',
            upper_address[:2],
            upper_address[2:4],
            upper_address + '.json',
            ), 'r'
            )
        o_original = json.load(f)
        f.close()

        if o_original != o_retrieved:
            raise VerifierError(o_retrieved, 'metadata (person)')


    def verify_metadata_phone(self, address, balance=None):
        upper_address = strip_0x(address).upper()
        f = open(os.path.join(
            self.data_dir,
            'new',
            upper_address[:2],
            upper_address[2:4],
            upper_address + '.json',
            ), 'r'
            )
        o = json.load(f)
        f.close()

        p = Person.deserialize(o) 

        k = generate_metadata_pointer(p.tel.encode('utf-8'), ':cic.phone')
        url = os.path.join(config.get('_META_PROVIDER'), k)
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


    def verify_ussd(self, address, balance=None):
        response_data = send_ussd_request(address, self.data_dir)
        state = response_data[:3]
        out = response_data[4:]
        m = '{} {}'.format(state, out[:7])
        if m != 'CON Welcome':
            raise VerifierError(response_data, 'ussd')

    def verify_ussd_pins(self, address, balance):
        response_data = send_ussd_request(address, self.data_dir)
        if response_data[:11] != 'CON Balance' and response_data[:9] != 'CON Salio':
            raise VerifierError(response_data, 'pins')

    def verify(self, address, balance, debug_stem=None):
  
        for k in active_tests:
            s = '{} {}'.format(debug_stem, k)
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


    def __str__(self):
        return str(self.state)


def main():
    global chain_str, block_offset, user_dir
    
    conn = EthHTTPConnection(config.get('ETH_PROVIDER'))
    gas_oracle = OverrideGasOracle(conn=conn, limit=8000000)

    # Get Token registry address
    registry = Registry(chain_spec)
    o = registry.address_of(config.get('CIC_REGISTRY_ADDRESS'), 'TokenRegistry')
    r = conn.do(o)
    token_index_address = registry.parse_address_of(r)
    token_index_address = to_checksum_address(token_index_address)
    logg.info('found token index address {}'.format(token_index_address))

    # Get Account registry address
    o = registry.address_of(config.get('CIC_REGISTRY_ADDRESS'), 'AccountRegistry')
    r = conn.do(o)
    account_index_address = registry.parse_address_of(r)
    account_index_address = to_checksum_address(account_index_address)
    logg.info('found account index address {}'.format(account_index_address))

    # Get Faucet address
    o = registry.address_of(config.get('CIC_REGISTRY_ADDRESS'), 'Faucet')
    r = conn.do(o)
    faucet_address = registry.parse_address_of(r)
    faucet_index_address = to_checksum_address(token_index_address)
    logg.info('found faucet {}'.format(faucet_address))

# Get Sarafu token address
    token_index = TokenUniqueSymbolIndex(chain_spec)
    o = token_index.address_of(token_index_address, token_symbol)
    r = conn.do(o)
    token_address = token_index.parse_address_of(r)
    try:
        token_address = to_checksum_address(token_address)
    except ValueError as e:
        logg.critical('lookup failed for token {}: {}'.format(token_symbol, e))
        sys.exit(1)
    logg.info('found token address {}'.format(token_address))
 
    balances = {}
    f = open('{}/balances.csv'.format(user_dir, 'r'))
    i = 0
    while True:
        l = f.readline()
        if l == None:
            break
        r = l.split(',')
        try:
            address = to_checksum_address(r[0])
            #sys.stdout.write('loading balance {} {}'.format(i, address).ljust(200) + "\r")
            outfunc('loading balance {} {}'.format(i, address)) #.ljust(200))
        except ValueError:
            break
        balance = int(r[1].rstrip())
        balances[address] = balance
        i += 1

    f.close()

    verifier = Verifier(conn, i, api, gas_oracle, chain_spec, account_index_address, token_address, faucet_address, user_dir, exit_on_error)

    user_new_dir = os.path.join(user_dir, 'new')
    i = 0
    for x in os.walk(user_new_dir):
        for y in x[2]:
            if y[len(y)-5:] != '.json':
                continue
            filepath = os.path.join(x[0], y)
            f = open(filepath, 'r')
            try:
                o = json.load(f)
            except json.decoder.JSONDecodeError as e:
                f.close()
                logg.error('load error for {}: {}'.format(y, e))
                continue
            f.close()

            u = Person.deserialize(o)
            #logg.debug('data {}'.format(u.identities['evm']))

            subchain_str = '{}:{}'.format(chain_spec.common_name(), chain_spec.network_id())
            new_address = u.identities['evm'][subchain_str][0]
            subchain_str = '{}:{}'.format(old_chain_spec.common_name(), old_chain_spec.network_id())
            old_address = u.identities['evm'][subchain_str][0]
            balance = 0
            try:
                balance = balances[old_address]
            except KeyError:
                logg.info('no old balance found for {}, assuming 0'.format(old_address))

            s = 'checking {}: {} -> {} = {}'.format(i, old_address, new_address, balance)

            verifier.verify(new_address, balance, debug_stem=s)
            i += 1

    print()
    print(verifier)


if __name__ == '__main__':
    main()
