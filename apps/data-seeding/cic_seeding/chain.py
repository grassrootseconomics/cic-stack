# standard imports
import json

# external imports
from chainlib.eth.block import Block
from chainlib.eth.tx import Tx


# Walk the given identities path and return the list object holding addresses for it.
def __process_chain(person, chain_spec, create_path=False):
    engine = person.identities.get(chain_spec.engine())
    if engine == None:
        if not create_path:
            raise AttributeError('missing chain engine {}'.format(chain_spec.engine()))
        person.identities[chain_spec.engine()] = {}
        engine = person.identities[chain_spec.engine()]

    fork = engine.get(chain_spec.fork())
    if fork == None:
        if not create_path:
            raise AttributeError('missing chain fork {}'.format(chain_spec.fork()))
        person.identities[chain_spec.engine()][chain_spec.fork()] = {}
        fork = person.identities[chain_spec.engine()][chain_spec.fork()]

    network_selector = '{}:{}'.format(chain_spec.network_id(), chain_spec.common_name())
    chain = fork.get(network_selector)
    if chain == None:
        if not create_path:
            raise AttributeError('missing chain network selector {} (network id {} common name {})'.format(network_selector, chain_spec.network_id(), chain_spec.common_name()))
        person.identities[chain_spec.engine()][chain_spec.fork()][network_selector] = []
        chain = person.identities[chain_spec.engine()][chain_spec.fork()][network_selector]

    return chain


# Get all addresses from a particular chain identity.
def get_chain_addresses(person, chain_spec):
    return __process_chain(person, chain_spec)


# Set an address for a particular chain identity on a person.
# The chain identity path will be created if it does not exist.
def set_chain_address(person, chain_spec, address):
    chain = __process_chain(person, chain_spec, create_path=True)
    chain.append(address)


# Replace the transaction list in a block with exactly one transaction of interest.
# This block record cannot be used for validation.
class TamperedBlock(Block):

    def __init__(self, src, tx):
        super(TamperedBlock, self).__init__(src)
        self.txs = [tx.src()]
