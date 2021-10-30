# standard imports
import os
import logging
import uuid
import random
import sys

# external imports
from chainlib.chain import ChainSpec
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.gas import (
        balance,
        Gas,
        )
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainlib.eth.connection import EthHTTPSignerConnection
from funga.eth.signer import EIP155Signer
from funga.eth.keystore.sql import SQLKeystore
from chainlib.cli.wallet import Wallet
from chainlib.eth.address import AddressChecksum
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.address import (
        is_checksum_address,
        to_checksum_address,
        )
import chainlib.eth.cli

       
script_dir = os.path.dirname(os.path.realpath(__file__))
config_dir = os.path.join(script_dir, '..', 'cic_signer', 'data', 'config')

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = chainlib.eth.cli.argflag_std_write | chainlib.eth.cli.Flag.WALLET
argparser = chainlib.eth.cli.ArgumentParser(arg_flags)
args = argparser.parse_args()

config = chainlib.eth.cli.Config.from_args(args, arg_flags, base_config_dir=config_dir)

# set up rpc
chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))


# connect to database
dsn = 'postgresql://{}:{}@{}:{}/{}'.format(
        config.get('DATABASE_USER'),
        config.get('DATABASE_PASSWORD'),
        config.get('DATABASE_HOST'),
        config.get('DATABASE_PORT'),
        config.get('DATABASE_NAME'),    
    )
logg.info('using dsn {}'.format(dsn))

keystore = SQLKeystore(dsn, symmetric_key=bytes.fromhex(config.get('SIGNER_SECRET')))
wallet = Wallet(EIP155Signer, keystore=keystore, checksummer=AddressChecksum)

rpc = chainlib.eth.cli.Rpc(wallet=wallet)
conn = rpc.connect_by_config(config)

wallet.init()

def main():
    if config.get('_RECIPIENT') == None:
        sys.stderr.write('Missing sink address\n')
        sys.exit(1)

    sink_address = config.get('_RECIPIENT')
    if config.get('_UNSAFE'):
        sink_address = to_checksum_address(sink_address)
    if not is_checksum_address(sink_address):
        sys.stderr.write('Invalid sink address {}\n'.format(sink_address))
        sys.exit(1)
#    verify_string = random.randbytes(4).hex()
#    verify_string_check = input('WARNING! This will transfer all remaining gas from all accounts in custodial care to account {}. To confirm, please enter the string: {}\n'.format(config.get('_SINK_ADDRESS'), verify_string))
#    if verify_string != verify_string_check:
#        sys.stderr.write('Verify string mismatch. Aborting!\n')
#        sys.exit(1)

#    redis_host = config.get('REDIS_HOST')
#    redis_port = config.get('REDIS_PORT')
#    redis_db = config.get('REDIS_DB')
#    redis_channel = str(uuid.uuid4())
#    r = redis.Redis(redis_host, redis_port, redis_db)
#
#    ps = r.pubsub()
#    ps.subscribe(redis_channel)
#    ps.get_message()
#
#    api = Api(
#            config.get('CHAIN_SPEC'),
#            queue=config.get('CELERY_QUEUE'),
#            callback_param='{}:{}:{}:{}'.format(config.get('_REDIS_HOST_CALLBACK'), config.get('_REDIS_PORT_CALLBACK'), config.get('REDIS_DB'), redis_channel),
#            callback_task='cic_eth.callbacks.redis.redis',
#            callback_queue=config.get('CELERY_QUEUE'),
#            )

    signer = rpc.get_signer()

    gas_oracle = rpc.get_gas_oracle()
    gas_pair = gas_oracle.get_fee()
    gas_price = gas_pair[0]
    gas_limit = 21000
    gas_cost = gas_price * gas_limit
    gas_oracle = OverrideGasOracle(price=gas_price, limit=gas_limit)
    logg.info('using gas price {}'.format(gas_price))

    for r in keystore.list():
        account = r[0]

        o = balance(add_0x(account))
        r = conn.do(o)
        account_balance = 0
        try:
            r = strip_0x(r)
            account_balance = int(r, 16)
        except ValueError:
            account_balance = int(r)

        transfer_amount = account_balance - gas_cost
        if transfer_amount <= 0:
            logg.warning('address {} has balance {} which is less than gas cost {}, skipping'.format(account, account_balance, gas_cost))
            continue

        nonce_oracle = RPCNonceOracle(account, conn)
        c = Gas(chain_spec, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle, signer=signer)
        (tx_hash_hex, o) = c.create(account, config.get('_RECIPIENT'), transfer_amount)
        r = conn.do(o)

        logg.info('address {} balance {} net transfer {} tx {}'.format(account, account_balance, transfer_amount, r))

if __name__ == '__main__':
    main()
