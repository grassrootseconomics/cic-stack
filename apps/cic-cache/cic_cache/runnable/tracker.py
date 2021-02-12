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
from cic_registry.bancor import BancorRegistry
from cic_registry.token import Token
from cic_registry.error import UnknownContractError
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
logging.getLogger('web3.RequestManager').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.WebsocketProvider').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.HTTPProvider').setLevel(logging.CRITICAL)

log_topics = {
    'transfer': '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
    'convert': '0x7154b38b5dd31bb3122436a96d4e09aba5b323ae1fd580025fab55074334c095',
    }

config_dir = os.path.join('/usr/local/etc/cic-cache')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
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


class Tracker:

    def __init__(self):
        self.block_height = 0
        self.tx_height = 0
        self.state = RunStateEnum.INIT


    def refresh_registry(self, w3):
        cr = CICRegistry.get_contract(CICRegistry.bancor_chain_spec, 'ConverterRegistry')
        f = cr.function('getConvertibleTokens')
        anchors = f().call()
        # TODO: if there are other token sources, this number may not match anymore. The cache count method should be moved to bancorregistry object instead
        r = CICRegistry.get_chain_registry(CICRegistry.bancor_chain_spec)
        #logg.debug('anchors {} {}'.format(anchors, ContractRegistry.cache_token_count()))
        if len(anchors) != r.cache_token_count():
            logg.debug('token count mismatch, scanning')

            for a in anchors:
                if ContractRegistry.get_address(a) == None:
                    abi = CICRegistry.abi('ERC20Token')
                    #abi = ContractRegistry.contracts['ERC20Token'].contract.abi
                    c = w3.eth.contract(address=a, abi=abi)
                    t = ContractRegistry.add_token(a, c)
                    logg.info('new token {} at {}'.format(t.symbol(), t.address))



    def __process_tx(self, w3, session, t, r, l, b):
        token_value = int(l.data, 16)
        token_sender = l.topics[1][-20:].hex()
        token_recipient = l.topics[2][-20:].hex()

        ts = ContractRegistry.get_address(t.address)
        logg.info('add token transfer {} value {} from {} to {}'.format(
            ts.symbol(),
            token_value,
            token_sender,
            token_recipient,
            )
            )

        logg.debug('block', b)
        db.add_transaction(
                session,
                r.transactionHash.hex(),
                r.blockNumber,
                r.transactionIndex,
                w3.toChecksumAddress(token_sender),
                w3.toChecksumAddress(token_recipient),
                t.address,
                t.address,
                r.status == 1,
                b.timestamp,
                )
        session.flush()


    # TODO: simplify/ split up and/or comment, function is too long
    def __process_convert(self, w3, session, t, r, l, b):
        token_source = l.topics[2][-20:].hex()
        token_source = w3.toChecksumAddress(token_source)
        token_destination = l.topics[3][-20:].hex()
        token_destination = w3.toChecksumAddress(token_destination)
        data_noox = l.data[2:]
        d = data_noox[:64]
        token_from_value = int(d, 16)
        d = data_noox[64:128]
        token_to_value = int(d, 16)
        token_trader = '0x' + data_noox[192-40:]

        ts = ContractRegistry.get_address(token_source)
        if ts == None:
            ts = ContractRegistry.reserves[token_source]
        td = ContractRegistry.get_address(token_destination)
        if td == None:
            td = ContractRegistry.reserves[token_source]
        logg.info('add token convert {} -> {} value {} -> {} trader {}'.format(
            ts.symbol(),
            td.symbol(),
            token_from_value,
            token_to_value,
            token_trader,
            )
            )

        db.add_transaction(
                session,
                r.transactionHash.hex(),
                r.blockNumber,
                r.transactionIndex,
                w3.toChecksumAddress(token_trader),
                w3.toChecksumAddress(token_trader),
                token_source,
                token_destination,
                r.status == 1,
                b.timestamp,
                )
        session.flush()


    def process(self, w3, session, block):
        self.refresh_registry(w3)
        tx_count = w3.eth.getBlockTransactionCount(block.hash)
        b = w3.eth.getBlock(block.hash)
        for i in range(self.tx_height, tx_count):
            tx = w3.eth.getTransactionByBlock(block.hash, i)
            t = None
            try:
                t = CICRegistry.get_address(CICRegistry.bancor_chain_spec, tx.to)
            except UnknownContractError:
                logg.debug('block {} tx {} not our contract, skipping'.format(block, i))
                continue
            logg.debug('block tx {} {}'.format(block.number, i))
            if t != None and isinstance(t, Token):
                r = w3.eth.getTransactionReceipt(tx.hash)
                for l in r.logs:
                    logg.info('{} token log {} {}'.format(tx.hash.hex(), l.logIndex, l.topics[0].hex()))
                    if l.topics[0].hex() == log_topics['transfer']:
                        self.__process_tx(w3, session, t, r, l, b)

            elif tx.to == CICRegistry.get_contract(CICRegistry.bancor_chain_spec, 'BancorNetwork').address:
                r = w3.eth.getTransactionReceipt(tx.hash)
                for l in r.logs:
                    logg.info('{} bancornetwork log {} {}'.format(tx.hash.hex(), l.logIndex, l.topics[0].hex()))
                    if l.topics[0].hex() == log_topics['convert']:
                        self.__process_convert(w3, session, t, r, l, b)
            

            session.execute("UPDATE tx_sync SET tx = '{}'".format(tx.hash.hex()))
            session.commit()
            self.tx_height += 1


    def __get_next_retry(self, backoff=False):
        return 1


    def loop(self, bancor_registry):
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

def main():
    (provider, w3) = web3_constructor()
    CICRegistry.finalize(w3, config.get('CIC_REGISTRY_ADDRESS'))
    bancor_registry_contract = CICRegistry.get_contract(CICRegistry.bancor_chain_spec, 'BancorRegistry')
    bancor_chain_registry = CICRegistry.get_chain_registry(CICRegistry.bancor_chain_spec)
    bancor_registry = BancorRegistry(w3, bancor_chain_registry, bancor_registry_contract.address(), config.get('BANCOR_DIR'))
    bancor_registry.load() 

    #bancor.load(w3, config.get('BANCOR_REGISTRY_ADDRESS'), config.get('BANCOR_DIR'))

    t = Tracker() 
    t.load(w3)
    t.loop(bancor_registry)
                  
if __name__ == '__main__':
    main()
