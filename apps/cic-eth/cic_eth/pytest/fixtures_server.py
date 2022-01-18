# coding: utf-8
import logging

import pytest
from cic_eth.pytest.fixtures_celery import *
from cic_eth.server.app import create_app
from cic_eth.server.getters import TestGetter
from fastapi.testclient import TestClient
from cic_eth.pytest.mock.callback import CallbackTask, test_getter_callback

log = logging.getLogger(__name__)

@pytest.fixture(scope='function')
def client(
    default_chain_spec,
    default_token,
    account_registry,
    cic_registry,
    celery_session_worker,
    init_database,
    init_eth_tester,
    eth_rpc,
    contract_roles,
    custodial_roles,
    foo_token,
    foo_token_symbol,
    bar_token,
    token_registry,
    register_tokens,
    register_lookups,
    init_celery_tasks,
):
    app = create_app(str(default_chain_spec), "", "", "","", TestGetter, celery_queue=None)
    client = TestClient(app)
    return client
