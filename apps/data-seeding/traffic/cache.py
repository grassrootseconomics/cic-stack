# external imports
from chainlib.jsonrpc import JSONRPCException
from eth_erc20 import ERC20
from eth_accounts_index import AccountsIndex
from eth_token_index import TokenUniqueSymbolIndex
import logging

logg = logging.getLogger(__name__)


class ERC20Token:

    def __init__(self, chain_spec, address, conn):
        self.__address = address

        c = ERC20(chain_spec)
        o = c.symbol(address)
        r = conn.do(o)
        self.__symbol = c.parse_symbol(r)

        o = c.decimals(address)
        r = conn.do(o)
        self.__decimals = c.parse_decimals(r)


    def symbol(self):
        return self.__symbol


    def decimals(self):
        return self.__decimals


class IndexCache:

    def __init__(self, chain_spec, address):
        self.address = address
        self.chain_spec = chain_spec
        self.idx = 0

    
    def parse(self, r):
        return r


    def get(self, conn):
        entries = []
        while True:
            o = self.o.entry(self.address, self.idx)
            try:
                r = conn.do(o)
                entries.append(self.parse(r, conn))
            except JSONRPCException as e:
                logg.debug('foo {}'.format(e))
                return entries
            self.idx += 1


class AccountRegistryCache(IndexCache):
    
    def __init__(self, chain_spec, address):
        super(AccountRegistryCache, self).__init__(chain_spec, address)
        self.o = AccountsIndex(chain_spec)
        self.get_accounts = self.get


    def parse(self, r, conn):
        return self.o.parse_account(r)

    
class TokenRegistryCache(IndexCache):

    def __init__(self, chain_spec, address):
        super(TokenRegistryCache, self).__init__(chain_spec, address)
        self.o = TokenUniqueSymbolIndex(chain_spec)
        self.get_tokens = self.get


    def parse(self, r, conn):
        token_address = self.o.parse_entry(r)
        return ERC20Token(self.chain_spec, token_address, conn)
