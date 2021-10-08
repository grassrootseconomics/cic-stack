# standard imports
import logging

# external imports
import celery
from eth_address_declarator import Declarator
from chainlib.connection import RPCConnection
from chainlib.chain import ChainSpec
from cic_eth.db.models.role import AccountRole
from cic_eth_registry import CICRegistry

# local imports
from cic_eth.task import BaseTask
from cic_eth.error import TrustError

celery_app = celery.current_app
logg = logging.getLogger()


@celery_app.task(bind=True, base=BaseTask)
def verify_proofs(self, chained_input, chain_spec_dict, subjects, proofs):
    if not isinstance(subjects, list):
        raise ValueError('subjects argument must be list')
    if isinstance(proofs, str):
        proofs = [[proofs]]
    elif not isinstance(proofs, list):
        raise ValueError('proofs argument must be string or list')
    if len(proofs) != 1 and len(subjects) != len(proofs):
        raise ValueError('proof argument must be single proof or one proof input per subject')

    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')
    declarator = Declarator(chain_spec)

    session = self.create_session()
    sender_address = AccountRole.get_address('DEFAULT', session)

    registry = CICRegistry(chain_spec, rpc)
    declarator_address = registry.by_name('AddressDeclarator', sender_address=sender_address)

    i = 0
    for proof in proofs:
        if not isinstance(proof, list):
            logg.debug('proof entry {} is not a list'.format(i))
        i += 1
    
    i = 0
    for subject in subjects:
        for trusted_address in self.trusted_addresses:
            proof_count = {}
            for proof in proofs[i]:
                o = declarator.declaration(declarator_address, trusted_address, subject, sender_address=sender_address)
                r = rpc.do(o)
                declarations = declarator.parse_declaration(r)
                logg.debug('comparing proof {} with declarations for {} by {}: {}'.format(proofs, subject, trusted_address, declarations))
                for declaration in declarations:
                    if declaration == proof:
                        logg.debug('have token proof {} match for trusted address {}'.format(declaration, trusted_address))
                        if proof_count.get(proof) == None:
                            proof_count[proof] = 0
                        proof_count[proof] += 1
            
        for k in proof_count.keys():
            if proof_count[k] == 0:
                raise TrustError('no proof found for token {}'.format(subject))

        i += 1

    return chained_input
