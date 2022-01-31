# standard imports
import logging
import uuid
import json
import random
import queue
import threading
import celery
import time

# external imports
import redis
from chainlib.eth.constant import ZERO_ADDRESS

# local imports
from .traffic import TrafficProvisioner
from .mode import TaskMode
from .error import NoActionTaken

logg = logging.getLogger(__name__)


# TODO: Abstract redis with a generic pubsub adapter
class TrafficSyncHandler:
    """Encapsulates callback methods required by the chain syncer.
    
    This implementation uses a redis subscription as backend to retrieve results from asynchronously executed tasks.

    :param config: Configuration of current top-level execution
    :type config: object with dict get interface
    :param traffic_router: Traffic router instance to use for the syncer session.
    :type traffic_router: TrafficRouter
    :raises Exception: Any Exception redis may raise on connection attempt.
    """
    def __init__(self, config, traffic_router, conn):
        self.traffic_router = traffic_router
        self.traffic_items = {}
        self.config = config
        self.init = False
        self.conn = conn
        self.busyqueue = queue.Queue(1)
        self.c = 0
        self.busyqueue.put(self.c)
        self.th = None
        self.redis_channel = str(uuid.uuid4())
        self.pubsub = self.__connect_redis(self.redis_channel, self.config)

        
    # TODO: This method is too long, split up
    # TODO: This method will not yet cache balances for newly created accounts
    def refresh(self, block_number, tx_index):
        """Traffic method and item execution driver to be called on every loop execution of the chain syncer. 

        Implements the signature required by callbacks called from chainsyncer.driver.loop.

        :param block_number: Syncer block height at time of call.
        :type block_number: number
        :param tx_index: Syncer block transaction index at time of call.
        :type tx_index: number
        """
        try:
            v = self.busyqueue.get_nowait()
        except queue.Empty:
            return

        self.init = True

        self.th = TrafficMaker(self, block_number)
        self.th.start()
    
        self.c += 1


    def quit(self):
        self.th.join()


    def name(self):
        """Returns the common name for the syncer callback implementation. Required by the chain syncer.
        """
        return 'traffic_item_handler'


    # Visited by chainsyncer.driver.Syncer implementation
    def filter(self, conn, block, tx, db_session):
        """Callback for every transaction found in a block. Required by the chain syncer.

        Currently performs no operation.

        :param conn: A HTTPConnection object to the chain rpc provider.
        :type conn: chainlib.eth.rpc.HTTPConnection
        :param block: The block object of current transaction
        :type block: chainlib.eth.block.Block
        :param tx: The block transaction object
        :type tx: chainlib.eth.tx.Tx
        :param db_session: Syncer backend database session
        :type db_session: SQLAlchemy.Session
        """
        pass


    # connects to redis
    def __connect_redis(self, redis_channel, config):
        r = redis.Redis(config.get('REDIS_HOST'), config.get('REDIS_PORT'), config.get('REDIS_DB'))
        redis_pubsub = r.pubsub()
        redis_pubsub.subscribe(redis_channel)
        logg.debug('redis connected on channel {}'.format(redis_channel))
        return redis_pubsub


class TrafficMaker(threading.Thread):

    max_strikes = 3

    def __init__(self, h, block_number):
        super(TrafficMaker, self).__init__()
        self.conn = h.conn
        self.traffic_router = h.traffic_router
        self.busyqueue = h.busyqueue
        self.c = h.c
        self.traffic_items = h.traffic_items
        self.config = h.config
        self.init = h.init
        self.block_number = block_number
        self.redis_channel = h.redis_channel
        self.pubsub = h.pubsub
        self.sender_indices = None


    # update provision indices and return asset counts
    def create_provisioner(self):
        provisioner = TrafficProvisioner()
        # account balances need to be updated by the syncer (provisioner filter method)
        index_stats = provisioner.load(self.conn)

        refresh_accounts = None
        if not self.init:
            refresh_accounts = provisioner.new_accounts

        provisioner.add_aux('_REDIS_CHANNEL', self.redis_channel)

        self.sender_indices = [*range(0, len(provisioner.accounts))]

        return provisioner


    def run(self):
        celery.Celery(broker=self.config.get('CELERY_BROKER_URL'), backend=self.config.get('CELERY_RESULT_URL'))

        provisioner = self.create_provisioner()

        if provisioner.token_count == 0:
            logg.error('patiently waiting for at least one registered token...')
            self.busyqueue.put(self.c)
            return

        if len(self.sender_indices) == 0:
            logg.warning('no accounts yet. unless of the tasks configured add accounts, nothing will ever happen!')

        #account_count = len(provisioner.accounts)
        (batch_reserved, batch_capacity,) = self.traffic_router.count()
        logg.info('trafficmaker reserved {}/{} tokens {} accounts {}'.format(
            batch_reserved,
            batch_capacity,
            provisioner.token_count,
            provisioner.account_count,
            )
            )
        logg.debug('trafficmaker accounts {}'.format(provisioner.accounts))
        logg.debug('trafficmaker tokens {}'.format(provisioner.tokens))

        strikes = 0

        while True:
            traffic_item = self.traffic_router.reserve()
            if traffic_item == None:
                logg.debug('no traffic_items left to reserve {}'.format(traffic_item))
                break

            # TODO: temporary selection
            token_pair = (
                    provisioner.tokens[0],
                    provisioner.tokens[0],
                    )

            sender = ZERO_ADDRESS
            recipient = ZERO_ADDRESS
            balance_full = {
                    'balance_outgoing': 0,
                    'balance_incoming': 0,
                    'balance_network': 0,
                    }
            if len(self.sender_indices) == 0:
                sender_address = ZERO_ADDRESS
            else:
                sender_index_index = random.randint(0, len(self.sender_indices)-1)
                sender_index = self.sender_indices[sender_index_index]
                sender = provisioner.accounts[sender_index]
                #balance_full = balances[sender][token_pair[0].symbol()]
                if len(self.sender_indices) == 1:
                    self.sender_indices[sender_index] = self.sender_indices[len(self.sender_indices)-1]
                self.sender_indices = self.sender_indices[:len(self.sender_indices)-1]
        
                try:
                    balance_full = provisioner.balance(sender, token_pair[0])
                except TimeoutError:
                    logg.error('could not retreive balance for sender {} tokens {}'.format(sender, token_pair))
                    self.traffic_router.release(traffic_item)
                    self.busyqueue.put(self.c)
                    return

                recipient_index = random.randint(0, len(provisioner.accounts)-1)
                recipient = provisioner.accounts[recipient_index]
          
            try:
                (e, t, spend_value,) = traffic_item.method(
                        token_pair,
                        sender,
                        recipient,
                        balance_full,
                        provisioner.aux,
                        self.block_number,
                        )
            except NoActionTaken as e:
                self.traffic_router.release(traffic_item)
                logg.error('task {} has taken no action ({}/{}): {}'.format(traffic_item.__name__, strikes, self.max_strikes, e))
                strikes += 1
                if strikes == self.max_strikes:
                    logg.error('too many strikes, bailing!')
                    self.busyqueue.put(self.c)
                    return
                continue
            
            logg.info('trigger item {} tokens {} sender {} recipient {} balance {} >>\n\te {} t {} v {}'.format(
                traffic_item.name,
                token_pair,
                sender,
                recipient,
                balance_full,
                e, 
                t,
                spend_value,
                )
                )
            strikes = 0

            provisioner.update_balance(sender, token_pair[0], balance_full['balance_outgoing'] + spend_value)
            if traffic_item.mode & TaskMode.RECIPIENT_ACTIVE:
                self.sender_indices.append(recipient_index)

            if e != None:
                logg.info('API FAIL {}: {}'.format(str(traffic_item), e))
                self.traffic_router.release(traffic_item)
                continue

            if t == None:
                logg.info('API item {} completed immediately'.format(traffic_item.__name__))
                self.traffic_router.release(traffic_item.__name__)
            traffic_item.ext = t
            self.traffic_items[traffic_item.ext] = traffic_item


        while True:
            m = self.pubsub.get_message(timeout=0.2)
            if m == None:
                break
            if m['type'] == 'message':
                message_data = json.loads(m['data'])
                uu = message_data['root_id']
                match_item = self.traffic_items[uu]
                self.traffic_router.release(match_item)
                if message_data['status'] != 0:
                    logg.error('API ERROR (error code {}): {}'.format(message_data['status'], match_item))
                else:
                    match_item.result = message_data['result']
                    logg.info('APT SUCCESS: {}'.format(match_item))

        self.busyqueue.put(self.c)
