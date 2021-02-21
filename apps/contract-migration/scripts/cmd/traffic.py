# standard imports
import logging
import json
import uuid
import importlib
import random
import copy

# external imports
import redis
from cic_eth.api.api_task import Api

logg = logging.getLogger(__name__)


class TrafficItem:

    def __init__(self, item):
        self.method = item.do
        self.uuid = uuid.uuid4()
        self.ext = None
        self.result = None
        self.sender = None
        self.recipient = None
        self.source_token = None
        self.destination_token = None
        self.source_value = 0


    def __str__(self):
        return 'traffic item method {} uuid {}'.format(self.method, self.uuid)


class TrafficRouter:

    def __init__(self, batch_size=1):
        self.items = []
        self.weights = []
        self.total_weights = 0
        self.batch_size = batch_size
        self.reserved = {}
        self.reserved_count = 0
        self.traffic = {}


    def add(self, item, weight):
        self.weights.append(self.total_weights)
        self.total_weights += weight
        m = importlib.import_module(item)
        self.items.append(m)
        

    def reserve(self):
        if len(self.reserved) == self.batch_size:
            return None

        n = random.randint(0, self.total_weights)
        item = self.items[0]
        for i in range(len(self.weights)):
            if n <= self.weights[i]:
                item = self.items[i]
                break

        ti = TrafficItem(item)
        self.reserved[ti.uuid] = ti
        return ti


    def release(self, traffic_item):
        del self.reserved[traffic_item.uuid]


    def apply_import_dict(self, keys, dct):
        # parse traffic items
        for k in keys:
            if len(k) > 8 and k[:8] == 'TRAFFIC_':
                v = int(dct.get(k))
                try:
                    self.add(k[8:].lower(), v)
                except ModuleNotFoundError as e:
                    raise AttributeError('requested traffic item module not found: {}'.format(e))
                logg.debug('found traffic item {} weight {}'.format(k, v))


class TrafficProvisioner:

    oracles = {
        'account': None,
        'token': None,
            }
    default_aux = {
            }


    def __init__(self):

        self.tokens = self.oracles['token'].get_tokens()
        self.accounts = self.oracles['account'].get_accounts()
        self.aux = copy.copy(self.default_aux)
        self.__balances = {}


    def load_balances(self):
        pass


    def __cache_balance(self, holder_address, token, value):
        if self.__balances.get(holder_address) == None:
            self.__balances[holder_address] = {}
        self.__balances[holder_address][token] = value
        logg.debug('setting cached balance of {} token {} to {}'.format(holder_address, token, value))


    def add_aux(self, k, v):
        logg.debug('added {} = {} to traffictasker'.format(k, v))
        self.aux[k] = v


    def balances(self, accounts=None, refresh=False):
        if refresh:
            if accounts == None:
                accounts = self.accounts
            for account in accounts:
                for token in self.tokens:
                    value = self.balance(account, token)
                    self.__cache_balance(account, token.symbol(), value)
                    logg.debug('balance sender {} token {} = {}'.format(account, token, value))
        else:
            logg.debug('returning cached balances')
        return self.__balances


    def balance(self, account, token):
        # TODO: use proper redis callback 
        api = Api(
            str(self.aux['chain_spec']),
            queue=self.aux['api_queue'],
            #callback_param='{}:{}:{}:{}'.format(aux['redis_host_callback'], aux['redis_port_callback'], aux['redis_db'], aux['redis_channel']),
            #callback_task='cic_eth.callbacks.redis.redis',
            #callback_queue=queue,
            )
        t = api.balance(account, token.symbol())
        r = t.get()
        for c in t.collect():
            r = c[1]
        assert t.successful()
        return r[0]


    def update_balance(self, account, token, value):
        self.__cache_balance(account, token.symbol(), value)


class TrafficSyncHandler:

    def __init__(self, config, traffic_router):
        self.traffic_router = traffic_router
        self.redis_channel = str(uuid.uuid4())
        self.pubsub = self.__connect_redis(self.redis_channel, config)
        self.traffic_items = {}
        self.config = config
        self.init = False


    def __connect_redis(self, redis_channel, config):
        r = redis.Redis(config.get('REDIS_HOST'), config.get('REDIS_PORT'), config.get('REDIS_DB'))
        redis_pubsub = r.pubsub()
        redis_pubsub.subscribe(redis_channel)
        logg.debug('redis connected on channel {}'.format(redis_channel))
        return redis_pubsub


    def refresh(self, block_number, tx_index):

        traffic_provisioner = TrafficProvisioner()
        traffic_provisioner.add_aux('redis_channel', self.redis_channel)

        refresh_balance = not self.init
        balances = traffic_provisioner.balances(refresh=refresh_balance)
        self.init = True

        if len(traffic_provisioner.tokens) == 0:
            logg.error('patiently waiting for at least one registered token...')
            return

        logg.debug('executing handler refresh with accouts {}'.format(traffic_provisioner.accounts))
        logg.debug('executing handler refresh with tokens {}'.format(traffic_provisioner.tokens))

        sender_indices = [*range(0, len(traffic_provisioner.accounts))]
        # TODO: only get balances for the selection that we will be generating for

        while True:
            traffic_item = self.traffic_router.reserve()
            if traffic_item == None:
                logg.debug('no traffic_items left to reserve {}'.format(traffic_item))
                break

            # TODO: temporary selection
            token_pair = [
                    traffic_provisioner.tokens[0],
                    traffic_provisioner.tokens[0],
                    ]
            sender_index_index = random.randint(0, len(sender_indices)-1)
            sender_index = sender_indices[sender_index_index]
            sender = traffic_provisioner.accounts[sender_index]
            #balance_full = balances[sender][token_pair[0].symbol()]
            if len(sender_indices) == 1:
                sender_indices[m] = sender_sender_indices[len(senders)-1]
            sender_indices = sender_indices[:len(sender_indices)-1]

            balance_full = traffic_provisioner.balance(sender, token_pair[0])
            balance = balance_full['balance_network'] - balance_full['balance_outgoing']

            recipient_index = random.randint(0, len(traffic_provisioner.accounts)-1)
            recipient = traffic_provisioner.accounts[recipient_index]
            
            (e, t, balance_result,) = traffic_item.method(
                    token_pair,
                    sender,
                    recipient,
                    balance,
                    traffic_provisioner.aux,
                    block_number,
                    tx_index,
                    )
            traffic_provisioner.update_balance(sender, token_pair[0], balance_result)
            sender_indices.append(recipient_index)

            if e != None:
                logg.info('failed {}: {}'.format(str(traffic_item), e))
                self.traffic_router.release(traffic_item)
                continue

            if t == None:
                logg.info('traffic method {} completed immediately')
                self.traffic_router.release(traffic_item)
            traffic_item.ext = t
            self.traffic_items[traffic_item.ext] = traffic_item


        while True:
            m = self.pubsub.get_message(timeout=0.1)
            if m == None:
                break
            logg.debug('redis message {}'.format(m))
            if m['type'] == 'message':
                message_data = json.loads(m['data'])
                uu = message_data['root_id']
                match_item = self.traffic_items[uu]
                self.traffic_router.release(match_item)
                if message_data['status'] == 0:
                    logg.error('task item {} failed with error code {}'.format(match_item, message_data['status']))
                else:
                    match_item['result'] = message_data['result']
                    logg.debug('got callback result: {}'.format(match_item))


    def name(self):
        return 'traffic_item_handler'


    def filter(self, conn, block, tx, session):
        logg.debug('handler get {}'.format(tx))



