# standard imports
import logging

# external imports
import celery
from eth_address_declarator import Declarator
from chainlib.connection import RPCConnection
from chainlib.chain import ChainSpec
from cic_eth.db.models.role import AccountRole
from cic_eth_registry import CICRegistry
from hexathon import strip_0x

# local imports
from cic_eth.task import BaseTask
from cic_eth.error import TrustError

celery_app = celery.current_app
logg = logging.getLogger()

@celery_app.task(bind=True, base=BaseTask)
def collect(self, collection):
    logg.debug('collect {}'.format(collection))

    return collection


@celery_app.task(bind=True, base=BaseTask)
def verify_proof(self, chained_input, proof, subject, chain_spec_dict):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')

    session = self.create_session()
    sender_address = AccountRole.get_address('DEFAULT', session)

    registry = CICRegistry(chain_spec, rpc)
    declarator_address = registry.by_name('AddressDeclarator', sender_address=sender_address)

    declarator = Declarator(chain_spec)

    logg.debug('foo {}'.format(proof))
    proof = strip_0x(proof)
    logg.debug('proof is {}'.format(proof))

    proof_count = 0
    for trusted_address in self.trusted_addresses:
        o = declarator.declaration(declarator_address, trusted_address, subject, sender_address=sender_address)
        r = rpc.do(o)
        declarations = declarator.parse_declaration(r)
        logg.debug('comparing proof {} with declarations for {} by {}: {}'.format(proof, subject, trusted_address, declarations))

        for declaration in declarations:
            declaration = strip_0x(declaration)
            if declaration == proof:
                logg.debug('have token proof {} match for trusted address {}'.format(declaration, trusted_address))
                proof_count += 1
  
    logg.debug('proof count {}'.format(proof_count))
    if proof_count == 0:
        logg.debug('error {}'.format(proof_count))
        raise TrustError('no trusted records found for subject {} proof {}'.format(subject, proof))

    return chained_input


@celery_app.task(bind=True, base=BaseTask)
def verify_proofs(self, chained_input, subject, proofs, chain_spec_dict):
    if isinstance(proofs, str):
        proofs = [[proofs]]
    elif not isinstance(proofs, list):
        raise ValueError('proofs argument must be string or list')

    i = 0
    for proof in proofs:
        if not isinstance(proof, list):
            proofs[i] = [proof]
            logg.debug('proof entry {} is not a list'.format(i))
        i += 1
    
    queue = self.request.delivery_info.get('routing_key')

    s_group = []
    for proof in proofs:
        logg.debug('proof before {}'.format(proof))
        if isinstance(proof, str):
            proof = [proof]
        for single_proof in proof:
            logg.debug('proof after {}'.format(single_proof))
            s = celery.signature(
                'cic_eth.eth.trust.verify_proof',
                [
                    chained_input,
                    single_proof,
                    subject,
                    chain_spec_dict,
                    ],
                queue=queue,
                    )
            #s_group.append(s)
            s.apply_async()

    #return chained_input
