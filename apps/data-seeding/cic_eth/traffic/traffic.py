# standard imports
import os
import logging
import re
import sys
import json

# external imports
import redis
import celery
from cic_eth_registry.registry import CICRegistry
from chainsyncer.backend.memory import MemBackend
from chainsyncer.driver.head import HeadSyncer
from chainlib.eth.connection import EthHTTPConnection
from chainlib.chain import ChainSpec
from chainlib.eth.gas import RPCGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.block import block_latest
from hexathon import strip_0x
import chainlib.eth.cli
import cic_eth.cli
from cic_eth.cli.chain import chain_interface
from chainlib.eth.constant import ZERO_ADDRESS
from eth_accounts_index import AccountsIndex
from erc20_faucet import Faucet
from cic_eth.api import Api

# local imports
#import common
from cmd.traffic import (
        TrafficItem,
        TrafficRouter,
        TrafficProvisioner,
        TrafficSyncHandler,
        )
from cmd.traffic import add_args as add_traffic_args
from cmd.cache import (
        AccountRegistryCache,
        TokenRegistryCache,
        )


# common basics
script_dir = os.path.dirname(os.path.realpath(__file__))
traffic_schema_dir = os.path.join(script_dir, 'data', 'config') 
logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = cic_eth.cli.argflag_std_read | cic_eth.cli.Flag.WALLET
local_arg_flags = cic_eth.cli.argflag_local_taskcallback | cic_eth.cli.argflag_local_chain
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--batch-size', default=10, type=int, help='number of events to process simultaneously')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'batch_size': None,
        }
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, base_config_dir=traffic_schema_dir, extra_args=extra_args)

wallet = chainlib.eth.cli.Wallet()
wallet.from_config(config)

rpc = chainlib.eth.cli.Rpc(wallet=wallet)
conn = rpc.connect_by_config(config)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))


class NetworkError(Exception):
    pass


def main():
    # create signer (not currently in use, but needs to be accessible for custom traffic item generators)
    signer = rpc.get_signer()
    signer_address = rpc.get_sender_address()

    # connect to celery
    celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

    # set up registry
    CICRegistry.address = config.get('CIC_REGISTRY_ADDRESS')
    registry = CICRegistry(chain_spec, conn)

    # Connect to blockchain with chainlib
    gas_oracle = RPCGasOracle(conn)
    nonce_oracle = RPCNonceOracle(signer_address, conn)

    # Set up magic traffic handler
    traffic_router = TrafficRouter()
    traffic_router.apply_import_dict(config.all(), config)
    handler = TrafficSyncHandler(config, traffic_router, conn)

    # Set up syncer
    syncer_backend = MemBackend(config.get('CHAIN_SPEC'), 0)
    o = block_latest()
    r = conn.do(o)
    block_offset = int(strip_0x(r), 16) + 1
    syncer_backend.set(block_offset, 0)

    # get relevant registry entries
    token_registry = registry.lookup('TokenRegistry')
    if token_registry == ZERO_ADDRESS:
        raise NetworkError('TokenRegistry value missing from contract registry {}'.format(config.get('CIC_REGISTRY_ADDRESS')))
    logg.info('using token registry {}'.format(token_registry))
    token_cache = TokenRegistryCache(chain_spec, token_registry)

    account_registry = registry.lookup('AccountRegistry')
    if account_registry == ZERO_ADDRESS:
        raise NetworkError('AccountRegistry value missing from contract registry {}'.format(config.get('CIC_REGISTRY_ADDRESS')))
    logg.info('using account registry {}'.format(account_registry))
    account_cache = AccountRegistryCache(chain_spec, account_registry)

    faucet = registry.lookup('Faucet')
    if faucet == ZERO_ADDRESS:
        logg.warning('Faucet entry missing from value missing from contract registry {}. New account registrations will need external mechanism for initial token balances.'.format(config.get('CIC_REGISTRY_ADDRESS')))
    else:
        logg.info('using faucet {}'.format(faucet))
   
    # Set up provisioner for common task input data
    TrafficProvisioner.oracles['token'] = token_cache
    TrafficProvisioner.oracles['account'] = account_cache
    
    TrafficProvisioner.default_aux = {
            'chain_spec': config.get('CHAIN_SPEC'),
            'registry': registry,
            'redis_host_callback': config.get('_REDIS_HOST_CALLBACK'),
            'redis_port_callback': config.get('_REDIS_PORT_CALLBACK'),
            'redis_db': config.get('REDIS_DB'),
            'api_queue': config.get('CELERY_QUEUE'),
            }

    syncer = HeadSyncer(syncer_backend, chain_interface, block_callback=handler.refresh)
    syncer.add_filter(handler)

    # bootstrap two accounts if starting from scratch
    c = AccountsIndex(chain_spec)
    o = c.entry_count(account_registry)
    r = conn.do(o)

    logg.debug('entry count {}'.format(c.parse_entry_count(r)))

    if c.parse_entry_count(r) == 0:
        if faucet == ZERO_ADDRESS:
            raise ValueError('No accounts exist in network and no faucet exists. It will be impossible for any created accounts to trade.')
        c = Faucet(chain_spec)
        o = c.token_amount(faucet)
        r = conn.do(o)
        if c.parse_token_amount(r) == 0:
            raise ValueError('No accounts exist in network and faucet amount is set to 0. It will be impossible for any created accounts to trade.')

        api = Api(str(chain_spec), queue=config.get('CELERY_QUEUE'))
        api.create_account(register=True)
        api.create_account(register=True)

    syncer.loop(1, conn)


if __name__ == '__main__':
    main()
