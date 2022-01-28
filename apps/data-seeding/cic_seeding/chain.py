# standard imports
import json

# external imports
from chainlib.eth.block import Block
from chainlib.eth.tx import Tx


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


def get_chain_addresses(person, chain_spec):
    return __process_chain(person, chain_spec)


def set_chain_address(person, chain_spec, address):
    chain = __process_chain(person, chain_spec, create_path=True)
    chain.append(address)


def serialize_block_tx(block, tx):
    o = {
            'block': block.src(),
            'tx': tx.src(),
            }
    return json.dumps(o)


def deserialize_block_tx(v):
    o = json.loads(v)
    block = Block(o['block'])
    tx = Tx(o['tx'])
    return (block, tx,)
