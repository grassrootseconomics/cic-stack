# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.status import Status as TxStatus
from cic_eth_registry.erc20 import ERC20Token

# local imports
from cic_eth.ext.address import translate_address


class ExtendedTx:

    _default_decimals = 6

    def __init__(self, rpc, tx_hash, chain_spec):
        self.rpc = rpc
        self.chain_spec = chain_spec
        self.hash = tx_hash
        self.sender = None
        self.sender_label = None
        self.recipient = None
        self.recipient_label = None
        self.source_token_value = 0
        self.destination_token_value = 0
        self.source_token = ZERO_ADDRESS
        self.destination_token = ZERO_ADDRESS
        self.source_token_symbol = ''
        self.destination_token_symbol = ''
        self.source_token_decimals = ExtendedTx._default_decimals
        self.destination_token_decimals = ExtendedTx._default_decimals
        self.status = TxStatus.PENDING.name
        self.status_code = TxStatus.PENDING.value


    def set_actors(self, sender, recipient, trusted_declarator_addresses=None, caller_address=ZERO_ADDRESS):
        self.sender = sender
        self.recipient = recipient
        if trusted_declarator_addresses != None:
            self.sender_label = translate_address(sender, trusted_declarator_addresses, self.chain_spec, sender_address=caller_address)
            self.recipient_label = translate_address(recipient, trusted_declarator_addresses, self.chain_spec, sender_address=caller_address)


    def set_tokens(self, source, source_value, destination=None, destination_value=None):
        if destination == None:
            destination = source
        if destination_value == None:
            destination_value = source_value
        st = ERC20Token(self.chain_spec, self.rpc, source)
        dt = ERC20Token(self.chain_spec, self.rpc, destination)
        self.source_token = source
        self.source_token_symbol = st.symbol
        self.source_token_name = st.name
        self.source_token_decimals = st.decimals
        self.source_token_value = source_value
        self.destination_token = destination
        self.destination_token_symbol = dt.symbol
        self.destination_token_name = dt.name
        self.destination_token_decimals = dt.decimals
        self.destination_token_value = destination_value


    def set_status(self, n):
        if n:
            self.status = TxStatus.ERROR.name
        else:
            self.status = TxStatus.SUCCESS.name
        self.status_code = n


    def asdict(self):
        o = {}
        for attr in dir(self):
            if attr[0] == '_' or attr in ['set_actors', 'set_tokens', 'set_status', 'asdict', 'rpc']:
                continue
            o[attr] = getattr(self, attr)
        return o 
