# standard imports
import argparse
import logging
import sys
import os

# external imports
import celery
import confini
import redis
from chainlib.chain import ChainSpec
from chainlib.eth.address import to_checksum_address
from chainlib.eth.connection import EthHTTPConnection
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore.dict import DictKeystore

# local imports
from import_task import ImportTask, MetadataTask
from import_util import BalanceProcessor, get_celery_worker_status

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = './config'

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:oldchain:1', help='chain spec')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
argparser.add_argument('--meta-host', dest='meta_host', type=str, help='metadata server host')
argparser.add_argument('--meta-port', dest='meta_port', type=int, help='metadata server host')
argparser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
argparser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
argparser.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use for task submission and callback')
argparser.add_argument('--token-symbol', default='GFT', type=str, dest='token_symbol',
                       help='Token symbol to use for transactions')
argparser.add_argument('--head', action='store_true', help='start at current block height (overrides --offset)')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str,
                       help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-import-ussd', help='celery queue to submit transaction tasks to')
argparser.add_argument('--offset', type=int, default=0, help='block offset to start syncer from')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('user_dir', default='out', type=str, help='user export directory')
args = argparser.parse_args(sys.argv[1:])

if args.v:
    logging.getLogger().setLevel(logging.INFO)

elif args.vv:
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
    'REDIS_HOST': getattr(args, 'redis_host'),
    'REDIS_PORT': getattr(args, 'redis_port'),
    'REDIS_DB': getattr(args, 'redis_db'),
    'META_HOST': getattr(args, 'meta_host'),
    'META_PORT': getattr(args, 'meta_port'),
    'KEYSTORE_FILE_PATH': getattr(args, 'y')
}
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

redis_host = config.get('REDIS_HOST')
redis_port = config.get('REDIS_PORT')
redis_db = config.get('REDIS_DB')
r = redis.Redis(redis_host, redis_port, redis_db)

# create celery apps
celery_app = celery.Celery(backend=config.get('CELERY_RESULT_URL'), broker=config.get('CELERY_BROKER_URL'))
status = get_celery_worker_status(celery_app=celery_app)

signer_address = None
keystore = DictKeystore()
if args.y is not None:
    logg.debug('loading keystore file {}'.format(args.y))
    signer_address = keystore.import_keystore_file(args.y)
    logg.debug('now have key for signer address {}'.format(signer_address))

# define signer
signer = EIP155Signer(keystore)

queue = args.q
chain_str = config.get('CIC_CHAIN_SPEC')
block_offset = 0
if args.head:
    block_offset = -1
else:
    block_offset = args.offset

chain_spec = ChainSpec.from_chain_str(chain_str)
old_chain_spec_str = args.old_chain_spec
old_chain_spec = ChainSpec.from_chain_str(old_chain_spec_str)

user_dir = args.user_dir  # user_out_dir from import_users.py

token_symbol = args.token_symbol

MetadataTask.meta_host = config.get('META_HOST')
MetadataTask.meta_port = config.get('META_PORT')
ImportTask.chain_spec = chain_spec


def main():
    conn = EthHTTPConnection(config.get('ETH_PROVIDER'))

    ImportTask.balance_processor = BalanceProcessor(conn, chain_spec, config.get('CIC_REGISTRY_ADDRESS'),
                                                    signer_address, signer)
    ImportTask.balance_processor.init(token_symbol)

    # TODO get decimals from token
    balances = {}
    f = open('{}/balances.csv'.format(user_dir, 'r'))
    remove_zeros = 10 ** 6
    i = 0
    while True:
        l = f.readline()
        if l is None:
            break
        r = l.split(',')
        try:
            address = to_checksum_address(r[0])
            sys.stdout.write('loading balance {} {} {}'.format(i, address, r[1]).ljust(200) + "\r")
        except ValueError:
            break
        balance = int(int(r[1].rstrip()) / remove_zeros)
        balances[address] = balance
        i += 1

    f.close()

    ImportTask.balances = balances
    ImportTask.count = i
    ImportTask.import_dir = user_dir

    s = celery.signature(
        'import_task.send_txs',
        [
            MetadataTask.balance_processor.nonce_offset,
        ],
        queue=queue,
    )
    s.apply_async()

    argv = ['worker']
    if args.vv:
        argv.append('--loglevel=DEBUG')
    elif args.v:
        argv.append('--loglevel=INFO')
    argv.append('-Q')
    argv.append(args.q)
    argv.append('-n')
    argv.append(args.q)
    celery_app.worker_main(argv)


if __name__ == '__main__':
    main()
