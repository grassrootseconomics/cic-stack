# standard imports
import os
import logging
import argparse
import re
import sys

# external imports
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


logg.debug('config:\n{}'.format(config))


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

        return self.tokens


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

        return self.accounts


class Refresher:

    def __init__(self, chain_spec, registry):
        self.chain_spec = chain_spec
        self.registry = registry
        self.token_oracle = TokenOracle(self.chain_spec, self.registry)
        self.accounts_oracle = AccountsOracle(self.chain_spec, self.registry)

    def refresh(self, block_number, tx_index):
        tokens = self.token_oracle.get_tokens()
        accounts = self.accounts_oracle.get_accounts()

        if len(accounts) == 0:
            logg.error('no accounts yet')

        elif len(tokens) == 0:
            logg.error('no tokens yet')

   
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

    # Set up syncer
    syncer_backend = MemBackend(str(chain_spec), 0)
    o = block_latest()
    r = conn.do(o)
    block_offset = int(strip_0x(r), 16) + 1
    syncer_backend.set(block_offset, 0)
    refresher_callback = Refresher(chain_spec, CICRegistry)
    syncer = HeadSyncer(syncer_backend, loop_callback=refresher_callback.refresh)
    syncer.loop(1, conn)

if __name__ == '__main__':
    main(config)
