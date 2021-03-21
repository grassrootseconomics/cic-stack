# standard imports
import logging

# external imports
import pytest
from hexathon import add_0x
from chainlib.eth.address import to_checksum_address

# local imports
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.nonce import Nonce

#logg = logging.getLogger(__name__)
# what the actual fuck, debug is not being shown even though explicitly set
logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


@pytest.fixture(scope='function')
def init_custodial(
    contract_roles,
    token_roles,
    agent_roles,
    init_database,
    ):
    for roles in [contract_roles, token_roles, agent_roles]:
        for role in roles.values():
            Nonce.init(role, session=init_database)

    init_database.commit()


@pytest.fixture(scope='function')
def custodial_roles(
    init_custodial,
    contract_roles,
    token_roles,
    agent_roles,
    eth_accounts,
    init_database,
    ):
    r = {}
    r.update(contract_roles)
    r.update(agent_roles)
    r.update({
        'GAS_GIFTER': eth_accounts[10],
        'FOO_TOKEN_GIFTER': token_roles['FOO_TOKEN_OWNER'],
            })
    for k in r.keys():
        role = AccountRole.set(k, r[k])
        init_database.add(role)
        logg.error('adding role {} -> {}'.format(k, r[k]))
    init_database.commit()
    return r


@pytest.fixture(scope='function')
def whoever(
    init_eth_tester,
    ):
    return init_eth_tester.new_account()
