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
def verify_proof(self, chained_input, proof, subject, chain_spec_dict, success_callback, error_callback):
    proof = strip_0x(proof)

    proofs = []
 
    logg.debug('proof count {}'.format(len(proofs)))
    if len(proofs) == 0:
        logg.debug('error {}'.format(len(proofs)))
        raise TrustError('foo')

    return (chained_input, (proof, proofs))


@celery_app.task(bind=True, base=BaseTask)
def verify_proofs(self, chained_input, subject, proofs, chain_spec_dict, success_callback, error_callback):
    queue = self.request.delivery_info.get('routing_key')

    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')

    session = self.create_session()
    sender_address = AccountRole.get_address('DEFAULT', session)

    registry = CICRegistry(chain_spec, rpc)
    declarator_address = registry.by_name('AddressDeclarator', sender_address=sender_address)

    declarator = Declarator(chain_spec)

    have_proofs = {}

    for proof in proofs:

        proof = strip_0x(proof)

        have_proofs[proof] = []

        for trusted_address in self.trusted_addresses:
            o = declarator.declaration(declarator_address, trusted_address, subject, sender_address=sender_address)
            r = rpc.do(o)
            declarations = declarator.parse_declaration(r)
            logg.debug('comparing proof {} with declarations for {} by {}: {}'.format(proof, subject, trusted_address, declarations))

            for declaration in declarations:
                declaration = strip_0x(declaration)
                if declaration == proof:
                    logg.debug('have token proof {} match for trusted address {}'.format(declaration, trusted_address))
                    have_proofs[proof].append(trusted_address)

    out_proofs = {}
    for proof in have_proofs.keys():
        if len(have_proofs[proof]) == 0:
            logg.error('missing signer for proof {} subject {}'.format(proof, subject))
            raise TrustError((subject, proof,))
        out_proofs[proof] = have_proofs[proof]
       
    return (chained_input, out_proofs)
