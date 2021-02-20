# standard imports
import os
import logging
import argparse
import re
import sys
import uuid
import importlib
import copy
import random
import json

# external imports
import redis
import confini
import web3
import celery
from cic_registry import CICRegistry
from cic_registry.chain import ChainRegistry
from chainlib.chain import ChainSpec
from eth_token_index import TokenUniqueSymbolIndex
from eth_accounts_index import AccountRegistry
from cic_registry.helper.declarator import DeclaratorOracleAdapter
from chainsyncer.backend import MemBackend
from chainsyncer.driver import HeadSyncer
from chainlib.eth.connection import HTTPConnection
from chainlib.eth.gas import DefaultGasOracle
from chainlib.eth.nonce import DefaultNonceOracle
from chainlib.eth.block import block_latest
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore import DictKeystore
from hexathon import strip_0x

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('websockets.protocol').setLevel(logging.CRITICAL)
logging.getLogger('web3.RequestManager').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.WebsocketProvider').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.HTTPProvider').setLevel(logging.CRITICAL)

script_dir = os.path.realpath(os.path.dirname(__file__))
default_data_dir = '/usr/local/share/cic/solidity/abi'

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', type=str, help='Ethereum provider url')
argparser.add_argument('-r', type=str, help='cic-registry address')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-c', type=str, default='./config', help='config file')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit to')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, help='Directory containing bytecode and abi')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
argparser.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
argparser.add_argument('--batch-size', dest='batch_size', default=10, type=int, help='number of events to process simultaneously')
args = argparser.parse_args()


# handle logging input
if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

# handle config input
config = confini.Config(args.c, args.env_prefix)
config.process()
args_override = {
        'ETH_ABI_DIR': getattr(args, 'abi_dir'),
        'ETH_PROVIDER': getattr(args, 'p'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        }
config.dict_override(args_override, 'cli flag')
config.validate()

# handle batch size input
batchsize = args.batch_size
if batchsize < 1:
    batchsize = 1
logg.info('batch size {}'.format(batchsize))
config.add(batchsize, '_BATCH_SIZE', True)

# redis task result callback
config.add(args.redis_host_callback, '_REDIS_HOST_CALLBACK', True)
config.add(args.redis_port_callback, '_REDIS_PORT_CALLBACK', True)

# signer
keystore = DictKeystore()
if args.y == None:
    logg.critical('please specify signer keystore file')
    sys.exit(1)

logg.debug('loading keystore file {}'.format(args.y))
__signer_address = keystore.import_keystore_file(args.y)
config.add(__signer_address, '_SIGNER_ADDRESS')
logg.debug('now have key for signer address {}'.format(config.get('_SIGNER_ADDRESS')))
signer = EIP155Signer(keystore)

logg.debug('config:\n{}'.format(config))


# web3 input
# TODO: Replace with chainlib
re_websocket = r'^wss?:'
re_http = r'^https?:'
blockchain_provider = None
if re.match(re_websocket, config.get('ETH_PROVIDER')):
    blockchain_provider = web3.Web3.WebsocketProvider(config.get('ETH_PROVIDER'))
elif re.match(re_http, config.get('ETH_PROVIDER')):
    blockchain_provider = web3.Web3.HTTPProvider(config.get('ETH_PROVIDER'))
w3 = web3.Web3(blockchain_provider)

# connect celery
celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

class TrafficItem:

    def __init__(self, item):
        self.method = item.do
        self.uuid = uuid.uuid4()
        self.ext = None
        self.result = None


    def __str__(self):
        return 'traffic item method {} uuid {}'.format(self.method, self.uuid)


class TrafficRouter:

    def __init__(self, batch_size=1):
        self.items = []
        self.weights = []
        self.total_weights = 0
        self.batch_size = batch_size
        self.reserved = {}
        self.reserved_count = 0
        self.traffic = {}


    def add(self, item, weight):
        self.weights.append(self.total_weights)
        self.total_weights += weight
        m = importlib.import_module(item)
        self.items.append(m)
        logg.debug('found traffic item {} weight {}'.format(k, v))
        

    def reserve(self):
        if len(self.reserved) == self.batch_size:
            return None

        n = random.randint(0, self.total_weights)
        item = self.items[0]
        for i in range(len(self.weights)):
            if n <= self.weights[i]:
                item = self.items[i]
                break

        ti = TrafficItem(item)
        self.reserved[ti.uuid] = ti
        return ti


    def release(self, traffic_item):
        del self.reserved[traffic_item.uuid]


# parse traffic items
traffic_router = TrafficRouter()
for k in config.all():
    if len(k) > 8 and k[:8] == 'TRAFFIC_':
        v = int(config.get(k))
        try:
            traffic_router.add(k[8:].lower(), v)
        except ModuleNotFoundError as e:
            logg.critical('requested traffic item module not found: {}'.format(e))
            sys.exit(1)


class TrafficTasker:

    oracles = {
        'account': None,
        'token': None,
            }
    default_aux = {
            }


    def __init__(self):

        self.tokens = self.oracles['token'].get_tokens()
        self.accounts = self.oracles['account'].get_accounts()
        self.balances = {}

        self.aux = copy.copy(self.default_aux)


    def load_balances(self):
        pass


    def cache_balance(self, holder_address, token, value):
        if self.balances.get(holder_address) == None:
            self.balances[holder_address] = {}
        self.balances[holder_address][token] = value
        logg.debug('setting cached balance of {} token {} to {}'.format(holder_address, token, value))


    def add_aux(self, k, v):
        logg.debug('added {} = {} to traffictasker'.format(k, v))
        self.aux[k] = v



class Handler:

    def __init__(self, config, traffic_router):
        self.traffic_router = traffic_router
        self.redis_channel = str(uuid.uuid4())
        self.pubsub = self.__connect_redis(self.redis_channel, config)
        self.traffic_items = {}
        self.config = config


    def __connect_redis(self, redis_channel, config):
        r = redis.Redis(config.get('REDIS_HOST'), config.get('REDIS_PORT'), config.get('REDIS_DB'))
        redis_pubsub = r.pubsub()
        redis_pubsub.subscribe(redis_channel)
        logg.debug('redis connected on channel {}'.format(redis_channel))
        return redis_pubsub


    def refresh(self, block_number, tx_index):

        traffic_tasker = TrafficTasker()
        traffic_tasker.add_aux('redis_channel', self.redis_channel)

        if len(traffic_tasker.tokens) == 0:
            logg.error('patiently waiting for at least one registered token...')
            return

        logg.debug('executing handler refresh with accouts {}'.format(traffic_tasker.accounts))
        logg.debug('executing handler refresh with tokens {}'.format(traffic_tasker.tokens))

        while True:
            traffic_item = traffic_router.reserve()
            if traffic_item == None:
                logg.debug('no traffic_items left to reserve {}'.format(traffic_item))
                break
            (e, t,) = traffic_item.method(traffic_tasker.tokens, traffic_tasker.accounts, traffic_tasker.aux, block_number, tx_index)
            if e != None:
                logg.info('traffic method {} failed: {}'.format(traffic_item.name(), e))
                continue
            if t == None:
                logg.info('traffic method {} completed immediately')
                self.traffic_router.release(traffic_item)
            traffic_item.ext = t
            self.traffic_items[traffic_item.ext] = traffic_item


        # TODO: add drain
        while True:
            m = self.pubsub.get_message(timeout=0.1)
            if m == None:
                break
            logg.debug('redis message {}'.format(m))
            if m['type'] == 'message':
                message_data = json.loads(m['data'])
                uu = message_data['root_id']
                match_item = self.traffic_items[uu]
                self.traffic_router.release(match_item)
                if message_data['status'] == 0:
                    logg.error('task item {} failed with error code {}'.format(match_item, message_data['status']))
                else:
                    match_item['result'] = message_data['result']
                    logg.debug('got callback result: {}'.format(match_item))


    def name(self):
        return 'traffic_item_handler'


    def filter(self, conn, block, tx, session):
        logg.debug('handler get {}'.format(tx))
  


class TokenOracle:

    def __init__(self, chain_spec, registry):
        self.tokens = []
        self.chain_spec = chain_spec
        self.registry = registry

        token_registry_contract = CICRegistry.get_contract(chain_spec, 'TokenRegistry', 'Registry')
        self.getter = TokenUniqueSymbolIndex(w3, token_registry_contract.address())


    def get_tokens(self):
        token_count = self.getter.count()
        if token_count == len(self.tokens):
            return self.tokens

        for i in range(len(self.tokens), token_count):
            token_address = self.getter.get_index(i)
            t = self.registry.get_address(self.chain_spec, token_address)
            token_symbol = t.symbol()
            self.tokens.append(token_address)

            logg.debug('adding token idx {} symbol {} address {}'.format(i, token_symbol, token_address))

        return copy.copy(self.tokens)


class AccountsOracle:

    def __init__(self, chain_spec, registry):
        self.accounts = []
        self.chain_spec = chain_spec
        self.registry = registry

        accounts_registry_contract = CICRegistry.get_contract(chain_spec, 'AccountRegistry', 'Registry')
        self.getter = AccountRegistry(w3, accounts_registry_contract.address())


    def get_accounts(self):
        accounts_count = self.getter.count()
        if accounts_count == len(self.accounts):
            return self.accounts

        for i in range(len(self.accounts), accounts_count):
            account = self.getter.get_index(i)
            self.accounts.append(account)
            logg.debug('adding account {}'.format(account))

        return copy.copy(self.accounts)


def main(local_config=None):

    if local_config != None:
        config = local_config

    chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
    CICRegistry.init(w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
    CICRegistry.add_path(config.get('ETH_ABI_DIR'))

    chain_registry = ChainRegistry(chain_spec)
    CICRegistry.add_chain_registry(chain_registry, True)

    declarator = CICRegistry.get_contract(chain_spec, 'AddressDeclarator', interface='Declarator')
    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
        sys.exit(1)
    trusted_addresses = trusted_addresses_src.split(',')
    for address in trusted_addresses:
        logg.info('using trusted address {}'.format(address))

    oracle = DeclaratorOracleAdapter(declarator.contract, trusted_addresses)
    chain_registry.add_oracle(oracle, 'naive_erc20_oracle')

    # Connect to blockchain
    conn = HTTPConnection(config.get('ETH_PROVIDER'))
    gas_oracle = DefaultGasOracle(conn)
    nonce_oracle = DefaultNonceOracle(config.get('_SIGNER_ADDRESS'), conn)

    # Set up magic traffic handler
    handler = Handler(config, traffic_router)


    # Set up syncer
    syncer_backend = MemBackend(str(chain_spec), 0)
    o = block_latest()
    r = conn.do(o)
    block_offset = int(strip_0x(r), 16) + 1
    syncer_backend.set(block_offset, 0)

    TrafficTasker.oracles['token']= TokenOracle(chain_spec, CICRegistry)
    TrafficTasker.oracles['account'] = AccountsOracle(chain_spec, CICRegistry)
    TrafficTasker.default_aux = {
            'chain_spec': chain_spec,
            'registry': CICRegistry,
            'redis_host_callback': config.get('_REDIS_HOST_CALLBACK'),
            'redis_port_callback': config.get('_REDIS_PORT_CALLBACK'),
            'redis_db': config.get('REDIS_DB'),
            }

    syncer = HeadSyncer(syncer_backend, loop_callback=handler.refresh)
    syncer.add_filter(handler)
    syncer.loop(1, conn)

if __name__ == '__main__':
    main(config)
