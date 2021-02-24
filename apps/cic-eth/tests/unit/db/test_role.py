# local imports
from cic_eth.db.models.role import AccountRole

def test_db_role(
        init_database,
        eth_empty_accounts,
        ):

    foo = AccountRole.set('foo', eth_empty_accounts[0])
    init_database.add(foo)
    init_database.commit()
    assert AccountRole.get_address('foo', init_database) == eth_empty_accounts[0]

    bar = AccountRole.set('bar', eth_empty_accounts[1])
    init_database.add(bar)
    init_database.commit()
    assert AccountRole.get_address('bar', init_database) == eth_empty_accounts[1]

    foo = AccountRole.set('foo', eth_empty_accounts[2])
    init_database.add(foo)
    init_database.commit()
    assert AccountRole.get_address('foo', init_database) == eth_empty_accounts[2]
    assert AccountRole.get_address('bar', init_database) == eth_empty_accounts[1]

    tag = AccountRole.role_for(eth_empty_accounts[2])
    assert tag == 'foo'

    tag = AccountRole.role_for(eth_empty_accounts[3])
    assert tag == None
