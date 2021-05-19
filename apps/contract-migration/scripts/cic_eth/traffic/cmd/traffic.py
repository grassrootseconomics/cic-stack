# standard imports
import logging
import json
import uuid
import importlib
import random
import copy
from argparse import RawTextHelpFormatter

# external imports
import redis
from cic_eth.api.api_task import Api

logg = logging.getLogger(__name__)


def add_args(argparser):
    """Parse script specific command line arguments

    :param argparser: Top-level argument parser
    :type argparser: argparse.ArgumentParser
    """
    argparser.formatter_class = formatter_class=RawTextHelpFormatter
    argparser.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
    argparser.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
    argparser.add_argument('--batch-size', dest='batch_size', default=10, type=int, help='number of events to process simultaneously')
    argparser.description = """Generates traffic on the cic network using dynamically loaded modules as event sources

"""
    return argparser


class TrafficItem:
    """Represents a single item of traffic meta that will be processed by a traffic generation method

    The traffic generation module passed in the argument must implement a method "do" with interface conforming to local.noop_traffic.do.

    :param item: Traffic generation module.
    :type item: function
    """
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
    """Holds and selects from the collection of traffic generator modules that will be used for the execution.

    :params batch_size: Amount of simultaneous traffic items that can simultanously be in flight.
    :type batch_size: number
    :raises ValueError: If batch size is zero of negative
    """
    def __init__(self, batch_size=1):
        if batch_size < 1:
            raise ValueError('batch size cannot be 0')
        self.items = []
        self.weights = []
        self.total_weights = 0
        self.batch_size = batch_size
        self.reserved = {}
        self.reserved_count = 0
        self.traffic = {}


    def add(self, item, weight):
        """Add a traffic generator module to the list of modules to choose between for traffic item exectuion.

        The probability that a module will be chosen for any single item is the ratio between the weight parameter and the accumulated weights for all items.

        See local.noop for which criteria the generator module must fulfill.

        :param item: Qualified class path to traffic generator module. Will be dynamically loaded.
        :type item: str
        :param weight: Selection probability weight
        :type weight: number
        :raises ModuleNotFound: Invalid item argument
        """
        self.weights.append(self.total_weights)
        self.total_weights += weight
        m = importlib.import_module(item)
        self.items.append(m)
        

    def reserve(self):
        """Selects the module to be used to execute the next traffic item, using the provided weights.

        If the current number of calls to "reserve" without corresponding calls to "release" equals the set batch size limit, None will be returned. The calling code should allow a short grace period before trying the call again.
        :raises ValueError: No items have been added
        :returns: A traffic item with the selected module method as the method property.
        :rtype: TrafficItem|None
        """
        if len(self.items) == 0:
            raise ValueError('Add at least one item first')

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
        """Releases the traffic item from the list of simultaneous traffic items in flight.

        :param traffic_item: Traffic item
        :type traffic_item: TrafficItem
        """
        del self.reserved[traffic_item.uuid]


    def apply_import_dict(self, keys, dct):
        """Convenience method to add traffic generator modules from a dictionary.

        :param keys: Keys in dictionary to add
        :type keys: list of str
        :param dct: Dictionary to choose module strings from
        :type dct: dict
        :raises ModuleNotFoundError: If one of the module strings refer to an invalid module.
        """
        # parse traffic items
        for k in keys:
            if len(k) > 8 and k[:8] == 'TRAFFIC_':
                v = int(dct.get(k))
                self.add(k[8:].lower(), v)
                logg.debug('found traffic item {} weight {}'.format(k, v))


# TODO: This will not work well with big networks. The provisioner should use lazy loading and LRU instead.
class TrafficProvisioner:
    """Loads metadata necessary for traffic item execution.

    Instantiation will by default trigger retrieval of accounts and tokens on the network.

    It will also populate the aux property of the instance with the values from the static aux parameter template. 
    """

    oracles = {
        'account': None,
        'token': None,
            }
    """Data oracles to be used for traffic item generation"""
    default_aux = {
            }
    """Aux parameter template to be passed to the traffic generator module"""


    def __init__(self, conn):
        self.tokens = self.oracles['token'].get_tokens(conn)
        self.accounts = self.oracles['account'].get_accounts(conn)
        self.aux = copy.copy(self.default_aux)
        self.__balances = {}
        for a in self.accounts:
            self.__balances[a] = {}


    # Caches a single address' balance of a single token
    def __cache_balance(self, holder_address, token, value):
        if self.__balances.get(holder_address) == None:
            self.__balances[holder_address] = {}
        self.__balances[holder_address][token] = value
        logg.debug('setting cached balance of {} token {} to {}'.format(holder_address, token, value))


    def add_aux(self, k, v):
        """Add a key-value pair to the aux parameter list.

        Does not protect existing entries from being overwritten.

        :param k: Key
        :type k: str
        :param v: Value
        :type v: any
        """
        logg.debug('added {} = {} to traffictasker'.format(k, v))
        self.aux[k] = v


    # TODO: Balance list type should perhaps be a class (provided by cic-eth package) due to its complexity.
    def balances(self, refresh_accounts=None):
        """Retrieves all token balances for the given account list.

        If refresh_accounts is not None, the balance values for the given accounts will be retrieved from upstream. If the argument is an empty list, the balances will be updated for all tokens of all ccounts. If there are many accounts and/or tokens, this may be a VERY EXPENSIVE OPERATION. The "balance" method can be used instead to update individual account/token pair balances.

        :param accounts: List of accounts to refresh balances for.
        :type accounts: list of str, 0x-hex
        :returns: Dict of dict of dicts; v[accounts][token] = {balance_types}
        :rtype: dict
        """
        if refresh_accounts != None:
            accounts = refresh_accounts
            if len(accounts) == 0:
                accounts = self.accounts
            for account in accounts:
                for token in self.tokens:
                    value = self.balance(account, token)
                    self.__cache_balance(account, token.symbol(), value)
                    logg.debug('balance sender {} token {} = {}'.format(account, token, value))
        else:
            logg.debug('returning cached balances')

        return self.__balances


    # TODO: use proper redis callback 
    def balance(self, account, token):
        """Update balance for a single token of a single account from upstream.
        
        The balance will be the spendable balance at the time of the call. This value may be less than the balance reported by the consensus network, if a previous outgoing transaction is still pending in the network or the custodial system queue.

        :param account: Account to update
        :type account: str, 0x-hex
        :param token: Token to update balance for
        :type token: cic_registry.token.Token
        :returns: Updated balance
        :rtype: complex balance dict
        """
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
        #return r[0]['balance_network'] - r[0]['balance_outgoing']
        return r[0]


    def update_balance(self, account, token, value):
        """Manually set a token balance for an account.

        :param account: Account to update
        :type account: str, 0x-hex
        :param token: Token to update balance for
        :type token: cic_registry.token.Token
        :param value: Balance value to set
        :type value: number
        :returns: Balance value (unchanged)
        :rtype: complex balance dict
        """
        self.__cache_balance(account, token.symbol(), value)
        return value


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
        self.redis_channel = str(uuid.uuid4())
        self.pubsub = self.__connect_redis(self.redis_channel, config)
        self.traffic_items = {}
        self.config = config
        self.init = False
        self.conn = conn


    # connects to redis
    def __connect_redis(self, redis_channel, config):
        r = redis.Redis(config.get('REDIS_HOST'), config.get('REDIS_PORT'), config.get('REDIS_DB'))
        redis_pubsub = r.pubsub()
        redis_pubsub.subscribe(redis_channel)
        logg.debug('redis connected on channel {}'.format(redis_channel))
        return redis_pubsub


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
        traffic_provisioner = TrafficProvisioner(self.conn)
        traffic_provisioner.add_aux('redis_channel', self.redis_channel)

        refresh_accounts = None
        # Note! This call may be very expensive if there are a lot of accounts and/or tokens on the network
        if not self.init:
            refresh_accounts = traffic_provisioner.accounts
        balances = traffic_provisioner.balances(refresh_accounts=refresh_accounts)
        self.init = True

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
                    block_number,
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
                logg.debug('>>>>>>>>>>>>>>>>>>> match item {} {} {}'.format(match_item, match_item.result, dir(match_item)))
                if message_data['status'] != 0:
                    logg.error('task item {} failed with error code {}'.format(match_item, message_data['status']))
                else:
                    match_item.result = message_data['result']
                    logg.debug('got callback result: {}'.format(match_item))


    def name(self):
        """Returns the common name for the syncer callback implementation. Required by the chain syncer.
        """
        return 'traffic_item_handler'


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
        logg.debug('handler get {}'.format(tx))
