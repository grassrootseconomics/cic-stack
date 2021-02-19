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

# external imports
import redis
import confini
import web3
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
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-c', type=str, default='./config', help='config file')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, help='Directory containing bytecode and abi')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')

argparser.add_argument('-r', type=str, help='cic-registry address')
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


class TrafficItem:

    def __init__(self, item):
        self.method = item.do
        self.uuid = uuid.uuid4()
        self.complete = False


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


    def release(self, k):
        del self.reserved[k]


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


class Handler:

    def __init__(self, config, chain_spec, registry, traffic_router):
        self.chain_spec = chain_spec
        self.registry = registry
        self.token_oracle = TokenOracle(self.chain_spec, self.registry)
        self.accounts_oracle = AccountsOracle(self.chain_spec, self.registry)
        self.traffic_router = traffic_router
        self.redis_channel = str(uuid.uuid4())
        self.pubsub = self.__connect_redis(self.redis_channel, config)


    def __connect_redis(self, redis_channel, config):
        r = redis.Redis(config.get('REDIS_HOST'), config.get('REDIS_PORT'), config.get('REDIS_DB'))
        redis_pubsub = r.pubsub()
        redis_pubsub.subscribe(redis_channel)
        logg.debug('redis connected on channel {}'.format(redis_channel))
        return redis_pubsub


    def refresh(self, block_number, tx_index):
        tokens = self.token_oracle.get_tokens()
        accounts = self.accounts_oracle.get_accounts()

        if len(accounts) == 0:
            logg.error('no accounts yet')
            #return

        elif len(tokens) == 0:
            logg.error('no tokens yet')
            #return

        item = traffic_router.reserve()
        if item != None:
            item.method(config, tokens, accounts, block_number, tx_index)

        # TODO: add drain
        m = self.pubsub.get_message(timeout=0.01)
        if m != None
            pass


    def name(self):
        return 'traffic_item_handler'


    def filter(self, conn, block, tx, session):
        logg.debug('handler get {}'.format(tx))
  

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
    handler = Handler(config, chain_spec, CICRegistry, traffic_router)


    # Set up syncer
    syncer_backend = MemBackend(str(chain_spec), 0)
    o = block_latest()
    r = conn.do(o)
    block_offset = int(strip_0x(r), 16) + 1
    syncer_backend.set(block_offset, 0)


    syncer = HeadSyncer(syncer_backend, loop_callback=handler.refresh)
    syncer.add_filter(handler)
    syncer.loop(1, conn)

if __name__ == '__main__':
    main(config)
