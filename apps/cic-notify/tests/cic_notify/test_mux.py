# standard imports
import logging

# external imports
import pytest

# local imports
from cic_notify.error import SeppukuError
from cic_notify.mux import Muxer

# test imports


def test_muxer(celery_session_worker):
    with pytest.raises(SeppukuError) as error:
        muxer = Muxer()
        muxer.route([])
    assert str(error.value) == "No channels added to primary channels object."


def test_muxer_initialization(caplog, task_config):
    assert len(Muxer.tasks) == 0
    caplog.set_level(logging.DEBUG)
    Muxer.initialize(task_config)
    assert f"Loading task configs: {task_config}" in caplog.text
    muxer = Muxer()
    muxer.route(channel_keys=[])
    assert len(muxer.tasks) == 2




