# standard imports
import logging
import copy

# external imports
from cic_eth.api.api_task import Api
from chainlib.eth.constant import ZERO_ADDRESS
from eth_accounts_index import AccountsIndex
from erc20_faucet import Faucet
from cic_eth_registry.registry import CICRegistry
from chainlib.chain import ChainSpec

# local imports
from cic_seeding.imports.cic_eth import CicEthRedisTransport
from traffic.cache import (
        AccountRegistryCache,
        TokenRegistryCache,
        )
from traffic.error import NetworkError

logg = logging.getLogger(__name__)


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
        self.aux = copy.copy(self.default_aux)
        self.tokens = None
        self.accounts = None
        self.__balances = {}
        self.tokens = TrafficProvisioner.oracles['token'].get_tokens(conn)
        self.accounts = TrafficProvisioner.oracles['account'].get_accounts(conn)
        for a in self.accounts:
            self.__balances[a] = {}


    @staticmethod
    def __init_chain(registry):
        # get relevant registry entries
        token_registry = registry.lookup('TokenRegistry')
        if token_registry == ZERO_ADDRESS:
            raise NetworkError('TokenRegistry value missing from contract registry {}'.format(config.get('CIC_REGISTRY_ADDRESS')))
        logg.info('using token registry {}'.format(token_registry))
        token_cache = TokenRegistryCache(registry.chain_spec, token_registry)

        account_registry = registry.lookup('AccountRegistry')
        if account_registry == ZERO_ADDRESS:
            raise NetworkError('AccountRegistry value missing from contract registry {}'.format(config.get('CIC_REGISTRY_ADDRESS')))
        logg.info('using account registry {}'.format(account_registry))
        account_cache = AccountRegistryCache(registry.chain_spec, account_registry)

        faucet = registry.lookup('Faucet')
        if faucet == ZERO_ADDRESS:
            logg.warning('Faucet entry missing from value missing from contract registry {}. New account registrations will need external mechanism for initial token balances.'.format(config.get('CIC_REGISTRY_ADDRESS')))
        else:
            logg.info('using faucet {}'.format(faucet))

        # Set up provisioner for common task input data
        TrafficProvisioner.oracles['token'] = token_cache
        TrafficProvisioner.oracles['account'] = account_cache


    @staticmethod
    def __bootstrap_accounts(registry):
        if faucet == ZERO_ADDRESS:
            raise ValueError('No accounts exist in network and no faucet exists. It will be impossible for any created accounts to trade.')
        c = Faucet(chain_spec)
        o = c.token_amount(faucet)
        r = registry.rpc.do(o)
        if c.parse_token_amount(r) == 0:
            raise ValueError('No accounts exist in network and faucet amount is set to 0. It will be impossible for any created accounts to trade.')

        api = Api(str(chain_spec), queue=config.get('CELERY_QUEUE'))
        api.create_account(register=True)
        api.create_account(register=True)


    @staticmethod
    def __check_sanity(registry):
        # bootstrap two accounts if starting from scratch
        account_registry = registry.lookup('AccountRegistry')
        c = AccountsIndex(registry.chain_spec)
        o = c.entry_count(account_registry)
        r = registry.rpc.do(o)
        count = c.parse_entry_count(r)
        logg.debug('entry count {}'.format(count))

        if c.parse_entry_count(r) == 0:
            TrafficProvisioner.__bootstrap_accounts()


    @staticmethod
    def prepare(registry):
        TrafficProvisioner.__init_chain(registry)
        TrafficProvisioner.__check_sanity(registry)


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
        redis_transport = CicEthRedisTransport(self.aux)
        redis_transport.prepare()
        api = Api(
            str(self.aux['CHAIN_SPEC']),
            queue=self.aux['CELERY_QUEUE'],
            callback_param=redis_transport.params,
            callback_task=redis_transport.task,
            callback_queue=redis_transport.queue,
            )
        t = api.balance(account, token.symbol())
        r = redis_transport.get(t)
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


def prepare_for_traffic(config, conn):
    # set up registry
    CICRegistry.address = config.get('CIC_REGISTRY_ADDRESS')

    # default aux parameters that will be sent to every invoked trafficitem
    TrafficProvisioner.default_aux = {
            'CHAIN_SPEC': config.get('CHAIN_SPEC'),
            'REDIS_HOST': config.get('REDIS_HOST'),
            'REDIS_PORT': config.get('REDIS_PORT'),
            'REDIS_DB': config.get('REDIS_DB'),
            '_REDIS_HOST_CALLBACK': config.get('_REDIS_HOST_CALLBACK'),
            '_REDIS_PORT_CALLBACK': config.get('_REDIS_PORT_CALLBACK'),
            '_REDIS_DB_CALLBACK': config.get('REDIS_DB'),
            'CELERY_QUEUE': config.get('CELERY_QUEUE'),
            '_TIMEOUT': 1.0,
            }

    chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
    registry = CICRegistry(chain_spec, conn)
    TrafficProvisioner.prepare(registry)
