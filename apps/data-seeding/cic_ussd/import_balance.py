import argparse
import logging
import os
import sys

# external imports
import celery
from chainlib.chain import ChainSpec
from chainlib.eth.address import to_checksum_address
from chainlib.eth.connection import EthHTTPConnection
from confini import Config
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore.dict import DictKeystore

# local imports
from import_util import BalanceProcessor, get_celery_worker_status
from import_task import ImportTask, MetadataTask

default_config_dir = '/usr/local/etc/data-seeding/'
logg = logging.getLogger()

arg_parser = argparse.ArgumentParser(description='Daemon worker that handles data seeding tasks.')
arg_parser.add_argument('-c', type=str, default=default_config_dir, help='config root to use.')
arg_parser.add_argument('--env-prefix',
                        default=os.environ.get('CONFINI_ENV_PREFIX'),
                        dest='env_prefix',
                        type=str,
                        help='environment prefix for variables to overwrite configuration.')
arg_parser.add_argument('--head', action='store_true', help='start at current block height (overrides --offset)')
arg_parser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
arg_parser.add_argument('--include-balances', dest='include_balances', help='include opening balance transactions',
                        action='store_true')
arg_parser.add_argument('--meta-host', dest='meta_host', type=str, help='metadata server host')
arg_parser.add_argument('--meta-port', dest='meta_port', type=int, help='metadata server host')
arg_parser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
arg_parser.add_argument('-q', type=str, default='cic-import-ussd', help='celery queue to submit data seeding tasks to.')
arg_parser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
arg_parser.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use for task submission and callback')
arg_parser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
arg_parser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
arg_parser.add_argument('--token-symbol', default='GFT', type=str, dest='token_symbol',
                        help='Token symbol to use for transactions')
arg_parser.add_argument('-v', help='be verbose', action='store_true')
arg_parser.add_argument('-vv', help='be more verbose', action='store_true')
arg_parser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
arg_parser.add_argument('--offset', type=int, default=0, help='block offset to start syncer from')
arg_parser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:oldchain:1',
                        help='chain spec')
arg_parser.add_argument('import_dir', default='out', type=str, help='user export directory')
args = arg_parser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = Config(args.c, args.env_prefix)
config.process()
args_override = {
    'CHAIN_SPEC': getattr(args, 'i'),
    'RPC_PROVIDER': getattr(args, 'p'),
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
logg.debug(f'config loaded from {args.c}:\n{config}')

db_config = {
    'database': config.get('DATABASE_NAME'),
    'host': config.get('DATABASE_HOST'),
    'port': config.get('DATABASE_PORT'),
    'user': config.get('DATABASE_USER'),
    'password': config.get('DATABASE_PASSWORD')
}
ImportTask.db_config = db_config

keystore = DictKeystore()
os.path.isfile(args.y)
logg.debug(f'loading keystore file {args.y}')
signer_address = keystore.import_keystore_file(args.y)
logg.debug(f'now have key for signer address {signer_address}')
signer = EIP155Signer(keystore)

block_offset = -1 if args.head else args.offset

chain_str = config.get('CHAIN_SPEC')
chain_spec = ChainSpec.from_chain_str(chain_str)
ImportTask.chain_spec = chain_spec
old_chain_spec_str = args.old_chain_spec
old_chain_spec = ChainSpec.from_chain_str(old_chain_spec_str)

MetadataTask.meta_host = config.get('META_HOST')
MetadataTask.meta_port = config.get('META_PORT')

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))
get_celery_worker_status(celery_app)


def main():
    conn = EthHTTPConnection(config.get('RPC_PROVIDER'))
    ImportTask.balance_processor = BalanceProcessor(conn,
                                                    chain_spec,
                                                    config.get('CIC_REGISTRY_ADDRESS'),
                                                    signer_address,
                                                    signer)
    ImportTask.balance_processor.init(args.token_symbol)
    balances = {}
    accuracy = 10 ** 6
    count = 0
    with open(f'{args.import_dir}/balances.csv', 'r') as balances_file:
        while True:
            line = balances_file.readline()
            if line is None:
                break
            balance_data = line.split(',')
            try:
                blockchain_address = to_checksum_address(balance_data[0])
                logg.info(
                    'loading balance: {} {} {}'.format(count, blockchain_address, balance_data[1].ljust(200) + "\r"))
            except ValueError:
                break
            balance = int(int(balance_data[1].rstrip()) / accuracy)
            balances[blockchain_address] = balance
            count += 1
    ImportTask.balances = balances
    ImportTask.count = count
    ImportTask.include_balances = args.include_balances is True
    ImportTask.import_dir = args.import_dir
    s_send_txs = celery.signature(
        'import_task.send_txs', [ImportTask.balance_processor.nonce_offset], queue=args.q)
    s_send_txs.apply_async()

    argv = ['worker']
    if args.vv:
        argv.append('--loglevel=DEBUG')
    elif args.v:
        argv.append('--loglevel=INFO')
    argv.append('-Q')
    argv.append(args.q)
    argv.append('-n')
    argv.append(args.q)
    argv.append(f'--pidfile={args.q}.pid')
    celery_app.worker_main(argv)


if __name__ == '__main__':
    main()
