# standard imports
import logging

# external imports
import pytest
from hexathon import add_0x
from chainlib.eth.address import to_checksum_address

# local imports
from cic_eth.db.models.role import AccountRole

logg = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def custodial_roles(
    contract_roles,
    eth_accounts,
    init_database,
    ):
    r = {}
    r.update(contract_roles)
    r.update({
        'DEFAULT': eth_accounts[0],
            })
    for k in r.keys():
        role = AccountRole.set(k, r[k])
        init_database.add(role)
        logg.info('adding role {} -> {}'.format(k, r[k]))
    init_database.commit()
    return r


@pytest.fixture(scope='function')
def whoever(
    init_eth_tester,
    ):
    return init_eth_tester.new_account()
