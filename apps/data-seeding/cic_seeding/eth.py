# standard imports
import logging
import json
import uuid

# external imports
import celery
from chainlib.eth.address import to_checksum_address
from hexathon import add_0x
from eth_accounts_index.registry import AccountRegistry
from funga.eth.keystore.keyfile import to_dict as to_keyfile_dict
from funga.eth.keystore.dict import DictKeystore
from chainlib.eth.gas import RPCGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from eth_contract_registry import Registry
from cic_eth.api.api_task import Api

# local imports
from cic_seeding.imports import Importer
from cic_seeding.legacy import (
        legacy_normalize_file_key,
        legacy_link_data,
        )


logg = logging.getLogger(__name__)


class CicEthRedisTransport(Importer):
   
    def __init__(self, config):
        global celery_app

        import redis
        self.redis_host = config.get('REDIS_HOST')
        self.redis_port = config.get('REDIS_PORT')
        self.redis_db = config.get('REDIS_DB')
        r = redis.Redis(
                config.get('REDIS_HOST'),
                config.get('REDIS_PORT'),
                config.get('REDIS_DB'),
                )
        self.ps = r.pubsub()
        self.timeout = config.get('_TIMEOUT', 10.0)
        self.base_params = '{}:{}:{}'.format(
                config.get('_REDIS_HOST_CALLBACK'),
                config.get('_REDIS_PORT_CALLBACK'),
                config.get('_REDIS_DB_CALLBACK'),
                )
        self.params = self.base_params

        self.task='cic_eth.callbacks.redis.redis'
        self.queue='cic-eth'

        celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))


    def prepare(self):
        redis_channel = str(uuid.uuid4())
        self.ps.subscribe(redis_channel)
        self.params = '{}:{}'.format(
                self.base_params,
                redis_channel,
                )


    def get(self, k):
        while True:
            self.ps.get_message() # this is the initial connect message
            m = self.ps.get_message(timeout=self.timeout)
            address = None
            if m == None:
                raise TimeoutError()
            if m['type'] == 'subscribe':
                logg.debug('skipping subscribe message')
                continue
            try:
                r = json.loads(m['data'])
                address = r['result']
                break
            except Exception as e:
                s = ''
                if m == None:
                    s = 'empty response from redis callback (did the service crash?) {}'.format(e)
                else:
                    s = 'unexpected response from redis callback: {} {}'.format(m, e)
                raise RuntimeError(s)

            logg.debug('[{}] register eth {} {}'.format(i, u, address))
    
        return address


class CicEthImporter(Importer):

    def __init__(self, config, result_transport=None, stores={}):
        super(CicEthImporter, self).__init__(config, stores=stores)
        self.res = result_transport
        if self.res == None:
            self.res = CicEthRedisTransport(config)
        self.queue = config.get('CELERY_QUEUE')


    def create_account(self, i, u):
        ch = self.res.prepare()

        logg.debug('foo {} {} {} {} {}'.format(
            str(self.chain_spec),
            self.queue,
            self.res.params,
            self.res.task,
            self.res.queue,
                )
                )
        api = Api(
            str(self.chain_spec),
            queue=self.queue,
            callback_param=self.res.params,
            callback_task=self.res.task,
            callback_queue=self.res.queue,
            )

        t = api.create_account(register=True)
        address = self.res.get(ch)

        logg.debug('register {} -> {}'.format(u, t))

        return address


class EthImporter(Importer):

    def __init__(self, rpc, signer, signer_address, target_chain_spec, source_chain_spec, registry_address, data_dir, stores=None, exist_ok=False, reset=False, reset_src=False, default_tag=[]):
        super(EthImporter, self).__init__(target_chain_spec, source_chain_spec, registry_address, data_dir, stores=stores, exist_ok=exist_ok, reset=reset, reset_src=reset_src, default_tag=[])
        self.keystore = DictKeystore()
        self.rpc = rpc
        self.signer = signer
        self.signer_address = signer_address
        self.nonce_oracle = RPCNonceOracle(signer_address, rpc)
        self.registry_address = registry_address
        self.registry = Registry(self.chain_spec)

        self.lookup = {
            'account_registry': None,
                }


    def prepare(self):
        # TODO: registry should be the lookup backend, should not be necessary to store the address here
        o = self.registry.address_of(self.registry_address, 'AccountRegistry')
        r = self.rpc.do(o)
        self.lookup['account_registry'] = self.registry.parse_address_of(r)
        logg.info('using account registry {}'.format(self.lookup.get('account_registry')))


    def create_account(self, i, u):
        address_hex = self.keystore.new()
        address = add_0x(to_checksum_address(address_hex))
        gas_oracle = RPCGasOracle(self.rpc, code_callback=AccountRegistry.gas)
        c = AccountRegistry(self.chain_spec, signer=self.signer, nonce_oracle=self.nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, o) = c.add(self.lookup.get('account_registry'), self.signer_address, address)
        logg.debug('o {}'.format(o))
        self.rpc.do(o)
        
        pk = self.keystore.get(address)
        keyfile_content = to_keyfile_dict(pk, 'foo')

        address_index = legacy_normalize_file_key(address)
        self.dh.add(address_index, json.dumps(keyfile_content), 'keystore')
        path = self.dh.path(address_index, 'keystore')
        legacy_link_data(path)

        logg.debug('[{}] register eth chain tx {} keyfile {}'.format(i, tx_hash_hex, path))

        return address
