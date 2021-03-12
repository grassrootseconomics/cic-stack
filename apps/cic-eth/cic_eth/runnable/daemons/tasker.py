# standard imports
import sys
import os
import logging
import argparse
import tempfile
import re
import urllib
import websocket

# external imports
import celery
import confini
#from crypto_dev_signer.eth.web3ext import Web3 as Web3Ext
from web3 import HTTPProvider, WebsocketProvider
import web3
#from gas_proxy.web3 import GasMiddleware
from chainlib.eth.connection import RPCConnection

# local imports
from cic_registry.registry import CICRegistry
from cic_registry.registry import ChainRegistry
from cic_registry.registry import ChainSpec
from cic_registry.helper.declarator import DeclaratorOracleAdapter

from cic_bancor.bancor import BancorRegistryClient
from cic_eth.eth import bancor
from cic_eth.eth import token
from cic_eth.eth import tx
from cic_eth.eth import account
from cic_eth.admin import debug
from cic_eth.admin import ctrl
from cic_eth.eth.rpc import RpcClient
from cic_eth.eth.rpc import GasOracle
from cic_eth.queue import tx
from cic_eth.queue import balance
from cic_eth.callbacks import Callback
from cic_eth.callbacks import http
from cic_eth.callbacks import tcp
from cic_eth.callbacks import redis
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.otx import Otx
from cic_eth.db import dsn_from_config
from cic_eth.ext import tx

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', type=str, help='web3 provider')
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('-q', type=str, default='cic-eth', help='queue name for worker tasks')
argparser.add_argument('-r', type=str, help='CIC registry address')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, help='Directory containing bytecode and abi')
argparser.add_argument('--trace-queue-status', default=None, dest='trace_queue_status', action='store_true', help='set to perist all queue entry status changes to storage')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
args = argparser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
# override args
args_override = {
        'ETH_ABI_DIR': getattr(args, 'abi_dir'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        'ETH_PROVIDER': getattr(args, 'p'),
        'TASKS_TRACE_QUEUE_STATUS': getattr(args, 'trace_queue_status'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, pool_size=50, debug=config.true('DATABASE_DEBUG'))

# verify database connection with minimal sanity query
session = SessionBase.create_session()
session.execute('select version_num from alembic_version')
session.close()

# set up celery
current_app = celery.Celery(__name__)

broker = config.get('CELERY_BROKER_URL')
if broker[:4] == 'file':
    bq = tempfile.mkdtemp()
    bp = tempfile.mkdtemp()
    current_app.conf.update({
            'broker_url': broker,
            'broker_transport_options': {
                'data_folder_in': bq,
                'data_folder_out': bq,
                'data_folder_processed': bp,
            },
            },
            )
    logg.warning('celery broker dirs queue i/o {} processed {}, will NOT be deleted on shutdown'.format(bq, bp))
else:
    current_app.conf.update({
        'broker_url': broker,
        })

result = config.get('CELERY_RESULT_URL')
if result[:4] == 'file':
    rq = tempfile.mkdtemp()
    current_app.conf.update({
        'result_backend': 'file://{}'.format(rq),
        })
    logg.warning('celery backend store dir {} created, will NOT be deleted on shutdown'.format(rq))
else:
    current_app.conf.update({
        'result_backend': result,
        })

# set up signer
RPCConnection.register_location(config.get('SIGNER_SOCKET_PATH'), 'signer')

# set up web3py
re_websocket = re.compile('^wss?://')
re_http = re.compile('^https?://')
blockchain_provider = config.get('ETH_PROVIDER')
if re.match(re_websocket, blockchain_provider) != None:
    blockchain_provider = web3.Web3.WebsocketProvider(blockchain_provider)
elif re.match(re_http, blockchain_provider) != None:
    blockchain_provider = web3.Web3.HTTPProvider(blockchain_provider)
else:
    raise ValueError('unknown provider url {}'.format(blockchain_provider))

def web3_constructor():
    w3 = web3.Web3(blockchain_provider)
    return (blockchain_provider, w3)
RpcClient.set_constructor(web3_constructor)


#
## set up web3
## TODO: web3 socket wrapping is now a lot of code. factor out
#class JSONRPCHttpSocketAdapter:
#
#    def __init__(self, url):
#        self.response = None
#        self.url = url
#
#    def send(self, data):
#        logg.debug('redirecting socket send to jsonrpc http socket adapter {} {}'.format(self.url, data))
#        req = urllib.request.Request(self.url, method='POST')
#        req.add_header('Content-type', 'application/json')
#        req.add_header('Connection', 'close')
#        res = urllib.request.urlopen(req, data=data.encode('utf-8'))
#        self.response = res.read().decode('utf-8')
#        logg.debug('setting jsonrpc http socket adapter response to {}'.format(self.response))
#
#    def recv(self, n=0):
#        return self.response
#
#
#re_websocket = re.compile('^wss?://')
#re_http = re.compile('^https?://')
#blockchain_provider = config.get('ETH_PROVIDER')
#socket_constructor = None
#if re.match(re_websocket, blockchain_provider) != None:
#    def socket_constructor_ws():
#        return websocket.create_connection(config.get('ETH_PROVIDER'))
#    socket_constructor = socket_constructor_ws
#    blockchain_provider = WebsocketProvider(blockchain_provider)
#elif re.match(re_http, blockchain_provider) != None:
#    def socket_constructor_http():
#        return JSONRPCHttpSocketAdapter(config.get('ETH_PROVIDER'))
#    socket_constructor = socket_constructor_http
#    blockchain_provider = HTTPProvider(blockchain_provider)
#else:
#    raise ValueError('unknown provider url {}'.format(blockchain_provider))
#
#
#def web3ext_constructor():
#    w3 = Web3Ext(blockchain_provider, config.get('SIGNER_SOCKET_PATH'))
#    #GasMiddleware.socket_constructor = socket_constructor
#    #w3.middleware_onion.add(GasMiddleware)
#
#    def sign_transaction(tx):
#        r = w3.eth.signTransaction(tx)
#        d = r.__dict__
#        for k in d.keys():
#            if k == 'tx':
#                d[k] = d[k].__dict__ 
#            else:
#                d[k] = d[k].hex()
#        return d
#
#    setattr(w3.eth, 'sign_transaction', sign_transaction)
#    setattr(w3.eth, 'send_raw_transaction', w3.eth.sendRawTransaction)
#    return (blockchain_provider, w3)
#RpcClient.set_constructor(web3ext_constructor) 

Otx.tracing = config.true('TASKS_TRACE_QUEUE_STATUS')


def main():
    argv = ['worker']
    if args.vv:
        argv.append('--loglevel=DEBUG')
    elif args.v:
        argv.append('--loglevel=INFO')
    argv.append('-Q')
    argv.append(args.q)
    argv.append('-n')
    argv.append(args.q)

    if config.true('SSL_ENABLE_CLIENT'):
        Callback.ssl = True
        Callback.ssl_cert_file = config.get('SSL_CERT_FILE')
        Callback.ssl_key_file = config.get('SSL_KEY_FILE')
        Callback.ssl_password = config.get('SSL_PASSWORD')

    if config.get('SSL_CA_FILE') != '':
        Callback.ssl_ca_file = config.get('SSL_CA_FILE')

    chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

    c = RpcClient(chain_spec)
    CICRegistry.init(c.w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
    CICRegistry.add_path(config.get('ETH_ABI_DIR'))

    chain_registry = ChainRegistry(chain_spec)
    CICRegistry.add_chain_registry(chain_registry, True)
    try:
        CICRegistry.get_contract(chain_spec, 'CICRegistry')
    except Exception as e:
        logg.exception('Eek, registry failure is baaad juju {}'.format(e))
        sys.exit(1)

    if config.get('ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER') != None:
        CICRegistry.add_role(chain_spec, config.get('ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER'), 'AccountRegistry', True)

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


    #chain_spec = CICRegistry.default_chain_spec
    #bancor_registry_contract = CICRegistry.get_contract(chain_spec, 'BancorRegistry', interface='Registry')
    #bancor_chain_registry = CICRegistry.get_chain_registry(chain_spec)
    #bancor_registry = BancorRegistryClient(c.w3, bancor_chain_registry, config.get('ETH_ABI_DIR'))
    #bancor_registry.load(True)
    current_app.worker_main(argv)


if __name__ == '__main__':
    main()
