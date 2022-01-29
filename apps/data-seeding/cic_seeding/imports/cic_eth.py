# standard imports
import uuid
import logging
import json

# external imports
import celery
from cic_eth.api.api_task import Api

# local imports
from cic_seeding.imports import Importer

logg = logging.getLogger(__name__)


# Define the result transport interface.
class ResultTransport:

    # Return a channel to get result from.
    def prepare(self):
        raise NotImplementedError()


    # Get result from channel.
    def get(self, channel):
        raise NotImplementedError()


# Redis implementation of ResultTransport.
class CicEthRedisTransport(ResultTransport):
   
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


# Implement the cic-eth account creation process.
# The caller must provide the transport for the retrieval of the account creation result.
# Does not implement own sync filter.
class CicEthImporter(Importer):

    def __init__(self, config, rpc, signer, signer_address, result_transport=None, stores={}, default_tag=[]):
        super(CicEthImporter, self).__init__(config, rpc, signer, signer_address, stores=stores, default_tag=default_tag)
        self.res = result_transport
        self.queue = config.get('CELERY_QUEUE')
        self.celery_broker_url = config.get('CELERY_BROKER_URL')
        self.celery_result_url = config.get('CELERY_RESULT_URL')


    def prepare(self):
        super(CicEthImporter, self).prepare()
        celery.Celery(broker=self.celery_broker_url, backend=self.celery_result_url)


    # Execute the cic-eth account creation.
    # Visited by default by Importer.process_user
    def create_account(self, i, u):
        ch = self.res.prepare()

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
