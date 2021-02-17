# standard imports
import os

# third-party imports
import pytest

# local imports
from cic_eth.db.models.otx import Otx
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        is_alive,
        )


@pytest.fixture(scope='function')
def otx(
        init_database,
        ):

    bogus_hash = '0x' + os.urandom(32).hex()
    bogus_address = '0x' + os.urandom(20).hex()
    bogus_tx_raw = '0x' + os.urandom(128).hex()
    return Otx(0, bogus_address, bogus_hash, bogus_tx_raw)


def test_status_chain_gas(
        init_database,
        otx,
        ):

    otx.waitforgas(init_database)
    otx.readysend(init_database)
    otx.sent(init_database)
    otx.success(1024, init_database)
    assert not is_alive(otx.status)


def test_status_chain_straight_success(
        init_database,
        otx,
        ):

    otx.readysend(init_database)
    otx.sent(init_database)
    otx.success(1024, init_database)
    assert not is_alive(otx.status)


def test_status_chain_straight_revert(
        init_database,
        otx,
        ):

    otx.readysend(init_database)
    otx.sent(init_database)
    otx.minefail(1024, init_database)
    assert not is_alive(otx.status)


def test_status_chain_nodeerror(
        init_database,
        otx,
        ):

    otx.readysend(init_database)
    otx.sendfail(init_database)
    otx.retry(init_database)
    otx.sent(init_database)
    otx.success(1024, init_database)
    assert not is_alive(otx.status)



def test_status_chain_nodeerror_multiple(
        init_database,
        otx,
        ):

    otx.readysend(init_database)
    otx.sendfail(init_database)
    otx.retry(init_database)
    otx.sendfail(init_database)
    otx.retry(init_database)
    otx.sent(init_database)
    otx.success(1024, init_database)
    assert not is_alive(otx.status)


def test_status_chain_nodeerror(
        init_database,
        otx,
        ):

    otx.readysend(init_database)
    otx.reject(init_database)
    assert not is_alive(otx.status)
