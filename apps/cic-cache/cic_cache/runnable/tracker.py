# standard imports
import sys
import os
import argparse
import logging
import time
import enum
import re

# third-party imports
import confini
from cic_registry import CICRegistry
from cic_registry.chain import (
        ChainRegistry,
        ChainSpec,
        )
#from cic_registry.bancor import BancorRegistryClient
from cic_registry.token import Token
from cic_registry.error import (
        UnknownContractError,
        UnknownDeclarationError,
        )
from cic_registry.declaration import to_token_declaration
from web3.exceptions import BlockNotFound, TransactionNotFound
from websockets.exceptions import ConnectionClosedError
from requests.exceptions import ConnectionError
import web3
from web3 import HTTPProvider, WebsocketProvider

# local imports
from cic_cache import db
from cic_cache.db.models.base import SessionBase

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('websockets.protocol').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('web3.RequestManager').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.WebsocketProvider').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.HTTPProvider').setLevel(logging.CRITICAL)

log_topics = {
    'transfer': '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
    'convert': '0x7154b38b5dd31bb3122436a96d4e09aba5b323ae1fd580025fab55074334c095',
    'accountregistry_add': '0a3b0a4f4c6e53dce3dbcad5614cb2ba3a0fa7326d03c5d64b4fa2d565492737',
    }

config_dir = os.path.join('/usr/local/etc/cic-cache')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('--trust-address', default=[], type=str, dest='trust_address', action='append', help='Set address as trust')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, help='Directory containing bytecode and abi')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
args = argparser.parse_args(sys.argv[1:])

config_dir = os.path.join(args.c)
os.makedirs(config_dir, 0o777, True)


if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config = confini.Config(config_dir, args.env_prefix)
config.process()
args_override = {
        'ETH_ABI_DIR': getattr(args, 'abi_dir'),
        'CIC_TRUST_ADDRESS': ",".join(getattr(args, 'trust_address', [])),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

# connect to database
dsn = db.dsn_from_config(config)
SessionBase.connect(dsn)


re_websocket = re.compile('^wss?://')
re_http = re.compile('^https?://')
blockchain_provider = config.get('ETH_PROVIDER')
if re.match(re_websocket, blockchain_provider) != None:
    blockchain_provider = WebsocketProvider(blockchain_provider)
elif re.match(re_http, blockchain_provider) != None:
    blockchain_provider = HTTPProvider(blockchain_provider)
else:
    raise ValueError('unknown provider url {}'.format(blockchain_provider))

def web3_constructor():
    w3 = web3.Web3(blockchain_provider)
    return (blockchain_provider, w3)


class RunStateEnum(enum.IntEnum):
    INIT = 0
    RUN = 1
    TERMINATE = 9


def rubberstamp(src):
    return True


class Tracker:

    def __init__(self, chain_spec, trusts=[]):
        self.block_height = 0
        self.tx_height = 0
        self.state = RunStateEnum.INIT
        self.declarator_cache = {}
        self.convert_enabled = False
        self.trusts = trusts
        self.chain_spec = chain_spec
        self.declarator = CICRegistry.get_contract(chain_spec, 'AddressDeclarator', 'Declarator')


    def __process_tx(self, w3, session, t, r, l, b):
        token_value = int(l.data, 16)
        token_sender = l.topics[1][-20:].hex()
        token_recipient = l.topics[2][-20:].hex()

        #ts = ContractRegistry.get_address(t.address)
        ts = CICRegistry.get_address(self.chain_spec, t.address())
        logg.info('add token transfer {} value {} from {} to {}'.format(
            ts.symbol(),
            token_value,
            token_sender,
            token_recipient,
            )
            )

        db.add_transaction(
                session,
                r.transactionHash.hex(),
                r.blockNumber,
                r.transactionIndex,
                w3.toChecksumAddress(token_sender),
                w3.toChecksumAddress(token_recipient),
                t.address(),
                t.address(),
                token_value,
                token_value,
                r.status == 1,
                b.timestamp,
                )
        session.flush()


    # TODO: simplify/ split up and/or comment, function is too long
    def __process_convert(self, w3, session, t, r, l, b):
        logg.warning('conversions are deactivated')
        return
#        token_source = l.topics[2][-20:].hex()
#        token_source = w3.toChecksumAddress(token_source)
#        token_destination = l.topics[3][-20:].hex()
#        token_destination = w3.toChecksumAddress(token_destination)
#        data_noox = l.data[2:]
#        d = data_noox[:64]
#        token_from_value = int(d, 16)
#        d = data_noox[64:128]
#        token_to_value = int(d, 16)
#        token_trader = '0x' + data_noox[192-40:]
#
#        #ts = ContractRegistry.get_address(token_source)
#        ts = CICRegistry.get_address(CICRegistry.bancor_chain_spec, t.address())
#        #if ts == None:
#        #    ts = ContractRegistry.reserves[token_source]
#        td = ContractRegistry.get_address(token_destination)
#        #if td == None:
#        #    td = ContractRegistry.reserves[token_source]
#        logg.info('add token convert {} -> {} value {} -> {} trader {}'.format(
#            ts.symbol(),
#            td.symbol(),
#            token_from_value,
#            token_to_value,
#            token_trader,
#            )
#            )
#
#        db.add_transaction(
#                session,
#                r.transactionHash.hex(),
#                r.blockNumber,
#                r.transactionIndex,
#                w3.toChecksumAddress(token_trader),
#                w3.toChecksumAddress(token_trader),
#                token_source,
#                token_destination,
#                r.status == 1,
#                b.timestamp,
#                )
#        session.flush()


    def check_token(self, address):
            t = None
            try:
                t = CICRegistry.get_address(CICRegistry.default_chain_spec, address)
                return t
            except UnknownContractError:
                logg.debug('contract {} not in registry'.format(address))

            # If nothing was returned, we look up the token in the declarator
            for trust in self.trusts:
                logg.debug('look up declaration for contract {} with trust {}'.format(address, trust))
                fn = self.declarator.function('declaration')
                # TODO: cache trust in LRUcache
                declaration_array = fn(trust, address).call()
                try:
                    declaration = to_token_declaration(trust, address, declaration_array, [rubberstamp])
                    logg.debug('found declaration for token {} from trust address {}'.format(address, trust))
                except UnknownDeclarationError:
                    continue
               
                try:
                    c = w3.eth.contract(abi=CICRegistry.abi('ERC20'), address=address)
                    t = CICRegistry.add_token(self.chain_spec, c)
                    break
                except ValueError:
                    logg.error('declaration for {} validates as token, but location is not ERC20 compatible'.format(address))

            return t


    # TODO use input data instead of logs
    def process(self, w3, session, block):
        #self.refresh_registry(w3)
        tx_count = w3.eth.getBlockTransactionCount(block.hash)
        b = w3.eth.getBlock(block.hash)
        for i in range(self.tx_height, tx_count):
            tx = w3.eth.getTransactionByBlock(block.hash, i)
            if tx.to == None:
                logg.debug('block {} tx {} is contract creation tx, skipping'.format(block.number, i))
                continue
            if len(w3.eth.getCode(tx.to)) == 0:
                logg.debug('block {} tx {} not a contract tx, skipping'.format(block.number, i))
                continue

            t = self.check_token(tx.to)
            if t != None and isinstance(t, Token):
                r = w3.eth.getTransactionReceipt(tx.hash)
                for l in r.logs:
                    logg.debug('block {} tx {} {} token log {} {}'.format(block.number, i, tx.hash.hex(), l.logIndex, l.topics[0].hex()))
                    if l.topics[0].hex() == log_topics['transfer']:
                        self.__process_tx(w3, session, t, r, l, b)

            # TODO: cache contracts in LRUcache
            elif self.convert_enabled and tx.to == CICRegistry.get_contract(CICRegistry.default_chain_spec, 'Converter').address:
                r = w3.eth.getTransactionReceipt(tx.hash)
                for l in r.logs:
                    logg.info('block {} tx {} {} bancornetwork log {} {}'.format(block.number, i, tx.hash.hex(), l.logIndex, l.topics[0].hex()))
                    if l.topics[0].hex() == log_topics['convert']:
                        self.__process_convert(w3, session, t, r, l, b)
            
            session.execute("UPDATE tx_sync SET tx = '{}'".format(tx.hash.hex()))
            session.commit()
            self.tx_height += 1


    def __get_next_retry(self, backoff=False):
        return 1


    def loop(self):
        logg.info('starting at block {} tx index {}'.format(self.block_height, self.tx_height))
        self.state = RunStateEnum.RUN
        while self.state == RunStateEnum.RUN:
            (provider, w3) = web3_constructor()
            session = SessionBase.create_session()
            try:
                block = w3.eth.getBlock(self.block_height)
                self.process(w3, session, block)
                self.block_height += 1
                self.tx_height = 0
            except BlockNotFound as e:
                logg.debug('no block {} yet, zZzZ...'.format(self.block_height))
                time.sleep(self.__get_next_retry())
            except ConnectionClosedError as e:
                logg.info('connection gone, retrying')
                time.sleep(self.__get_next_retry(True))
            except OSError as e:
                logg.error('cannot connect {}'.format(e))
                time.sleep(self.__get_next_retry(True))
            except Exception as e:
                session.close()
                raise(e)
            session.close()


    def load(self, w3):
        session = SessionBase.create_session()
        r = session.execute('SELECT tx FROM tx_sync').first()
        if r != None:
            if r[0] == '0x{0:0{1}X}'.format(0, 64):
                logg.debug('last tx was zero-address, starting from scratch')
                return
            t = w3.eth.getTransaction(r[0])
            
            self.block_height = t.blockNumber
            self.tx_height = t.transactionIndex+1
            c = w3.eth.getBlockTransactionCount(t.blockHash.hex())
            logg.debug('last tx processed {} index {} (max index {})'.format(t.blockNumber, t.transactionIndex, c-1))
            if c == self.tx_height:
                self.block_height += 1
                self.tx_height = 0
        session.close()

(provider, w3) = web3_constructor()
trust = config.get('CIC_TRUST_ADDRESS', []).split(",")
chain_spec = args.i

try:
    w3.eth.chainId
except Exception as e:
    logg.exception(e)
    sys.stderr.write('cannot connect to evm node\n')
    sys.exit(1)

def main():
    chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

    CICRegistry.init(w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
    CICRegistry.add_path(config.get('ETH_ABI_DIR'))
    chain_registry = ChainRegistry(chain_spec)
    CICRegistry.add_chain_registry(chain_registry)

    t = Tracker(chain_spec, trust) 
    t.load(w3)
    t.loop()
    

if __name__ == '__main__':
    main()
