# standard imports
import logging
import uuid
import json
import random
import queue
import threading
import celery

# external imports
import redis

# local imports
from .traffic import TrafficProvisioner

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

        logg.debug('I made it here')

        self.init = True

        th = TrafficMaker(self, block_number)
        th.start()
    
        self.c += 1



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


class TrafficMaker(threading.Thread):

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
        self.redis_channel = str(uuid.uuid4())


    # connects to redis
    def __connect_redis(self, redis_channel, config):
        r = redis.Redis(config.get('REDIS_HOST'), config.get('REDIS_PORT'), config.get('REDIS_DB'))
        redis_pubsub = r.pubsub()
        redis_pubsub.subscribe(redis_channel)
        logg.debug('redis connected on channel {}'.format(redis_channel))
        return redis_pubsub


    def run(self):
        celery.Celery(broker=self.config.get('CELERY_BROKER_URL'), backend=self.config.get('CELERY_RESULT_URL'))
        self.pubsub = self.__connect_redis(self.redis_channel, self.config)

        traffic_provisioner = TrafficProvisioner(self.conn)
        traffic_provisioner.add_aux('REDIS_CHANNEL', self.redis_channel)

        refresh_accounts = None
        # Note! This call may be very expensive if there are a lot of accounts and/or tokens on the network
        if not self.init:
            refresh_accounts = traffic_provisioner.accounts
        balances = traffic_provisioner.balances(refresh_accounts=refresh_accounts)

        if len(traffic_provisioner.tokens) == 0:
            logg.error('patiently waiting for at least one registered token...')
            return

        logg.debug('executing handler refresh with accounts {}'.format(traffic_provisioner.accounts))
        logg.debug('executing handler refresh with tokens {}'.format(traffic_provisioner.tokens))

        sender_indices = [*range(0, len(traffic_provisioner.accounts))]
        # TODO: only get balances for the selection that we will be generating for

        while True:
            traffic_item = self.traffic_router.reserve()
            if traffic_item == None:
                logg.debug('no traffic_items left to reserve {}'.format(traffic_item))
                break

            # TODO: temporary selection
            token_pair = (
                    traffic_provisioner.tokens[0],
                    traffic_provisioner.tokens[0],
                    )
            sender_index_index = random.randint(0, len(sender_indices)-1)
            sender_index = sender_indices[sender_index_index]
            sender = traffic_provisioner.accounts[sender_index]
            #balance_full = balances[sender][token_pair[0].symbol()]
            if len(sender_indices) == 1:
                sender_indices[sender_index] = sender_indices[len(sender_indices)-1]
            sender_indices = sender_indices[:len(sender_indices)-1]

            balance_full = traffic_provisioner.balance(sender, token_pair[0])

            recipient_index = random.randint(0, len(traffic_provisioner.accounts)-1)
            recipient = traffic_provisioner.accounts[recipient_index]
          
            logg.debug('trigger item {} tokens {} sender {} recipient {} balance {}'.format(
                traffic_item,
                token_pair,
                sender,
                recipient,
                balance_full,
                )
                )
            (e, t, balance_result,) = traffic_item.method(
                    token_pair,
                    sender,
                    recipient,
                    balance_full,
                    traffic_provisioner.aux,
                    self.block_number,
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
                logg.debug('match item {} {} {}'.format(match_item, match_item.result, dir(match_item)))
                if message_data['status'] != 0:
                    logg.error('task item {} failed with error code {}'.format(match_item, message_data['status']))
                else:
                    match_item.result = message_data['result']
                    logg.debug('got callback result: {}'.format(match_item))


    def __del__(self):
        self.busyqueue.put(self.c)
