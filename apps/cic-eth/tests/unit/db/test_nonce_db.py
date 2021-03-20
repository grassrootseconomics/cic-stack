# third-party imports
import pytest
import uuid

# local imports
from cic_eth.db.models.nonce import (
        Nonce,
        NonceReservation,
        )
from cic_eth.error import (
        InitializationError,
        IntegrityError,
        )


def test_nonce_init(
        init_database,
        eth_empty_accounts,
        ):

    nonce = Nonce.init(eth_empty_accounts[0], 42, session=init_database)
    init_database.commit()

    with pytest.raises(InitializationError):
        nonce = Nonce.init(eth_empty_accounts[0], 42, session=init_database)


def test_nonce_increment(
        init_database,
        eth_empty_accounts,
        database_engine,
        ):

    nonce = Nonce.next(eth_empty_accounts[0], 3)
    assert nonce == 3

    nonce = Nonce.next(eth_empty_accounts[0], 3)
    assert nonce == 4


def test_nonce_reserve(
        init_database,
        eth_empty_accounts,
    ):
   
    nonce = Nonce.init(eth_empty_accounts[0], 42, session=init_database)
    init_database.commit()
    uu = uuid.uuid4()
    nonce = NonceReservation.next(eth_empty_accounts[0], str(uu), session=init_database)
    init_database.commit()
    assert nonce == 42

    q = init_database.query(Nonce)
    q = q.filter(Nonce.address_hex==eth_empty_accounts[0])
    o = q.first()
    assert o.nonce == 43

    nonce = NonceReservation.release(eth_empty_accounts[0], str(uu))
    init_database.commit()
    assert nonce == 42

    q = init_database.query(NonceReservation)
    q = q.filter(NonceReservation.key==str(uu))
    o = q.first()
    assert o == None


def test_nonce_reserve_integrity(
        init_database,
        eth_empty_accounts,
        ):

    uu = uuid.uuid4()
    nonce = Nonce.init(eth_empty_accounts[0], 42, session=init_database)
    with pytest.raises(IntegrityError):
        NonceReservation.release(eth_empty_accounts[0], str(uu))
