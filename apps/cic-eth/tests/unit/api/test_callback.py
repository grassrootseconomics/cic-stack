# standard imports
import socket
import celery
import threading
import logging
import time
import json

# third-party imports
import pytest
import redis as redis_interface

# local imports
from cic_eth.callbacks import http
from cic_eth.callbacks import tcp
from cic_eth.callbacks import redis

celery_app = celery.current_app

logg = celery_app.log.get_default_logger()


class Response:

    status = 200

def test_callback_http(
    celery_session_worker,
    mocker,
    ):

    mocker.patch('cic_eth.callbacks.http.urlopen', return_value=Response())
    s = celery.signature(
            'cic_eth.callbacks.http.http',
            [
                'foo',
                'http://localhost:65000',
                1,
               ],
            )
    t = s.apply_async()
    t.get()


def test_callback_tcp(
    celery_session_worker,
    ):

    timeout=2

    data = {
        'foo': 'bar',
        'xyzzy': 42,
        }

    class Accept(threading.Thread):

        def __init__(self, socket):
            super(Accept, self).__init__()
            self.socket = socket
            self.exception = None

        def run(self):
            (c, sockaddr) = self.socket.accept()
            echo = c.recv(1024)
            c.close()
            logg.debug('recived {} '.format(data))
            o = json.loads(echo)
            try:
                assert o['result'] == data
            except Exception as e:
                self.exception = e

        def join(self):
            threading.Thread.join(self)
            if self.exception != None:
                raise self.exception


    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    s.settimeout(timeout)
    s.listen(1)
    sockaddr = s.getsockname()

    a = Accept(s)
    a.start()

    s_cb = celery.signature(
            'cic_eth.callbacks.tcp.tcp',
            [
                data,
                '{}:{}'.format(sockaddr[0], sockaddr[1]),
                '1',
                ],
            queue=None,
            )
    s_cb.apply_async()
    a.join()
    s.close()


def test_callback_redis(
    load_config,
    celery_session_worker,
    ):

    timeout=2

    channel = 'barbarbar'
    host = load_config.get('REDIS_HOST', 'localhost')
    port = load_config.get('REDIS_PORT', '6379')
    db = load_config.get('REDIS_DB', '0')

    data = {
        'foo': 'bar',
        'xyzzy': 42,
        }

    class Accept(threading.Thread):

        def __init__(self, pubsub):
            super(Accept, self).__init__()
            self.pubsub = pubsub
            self.exception = None

        def run(self):
            self.pubsub.get_message() # subscribe message
            echo = self.pubsub.get_message(timeout=timeout)
            o = json.loads(echo['data'])
            logg.debug('recived {} '.format(o))
            try:
                assert o['result'] == data
            except Exception as e:
                self.exception = e

        def join(self):
            threading.Thread.join(self)
            if self.exception != None:
                raise self.exception

    ps = None
    try:
        r = redis_interface.Redis(host=host, port=int(port), db=int(db))
        ps = r.pubsub(
                )
        ps.subscribe(channel)
    except redis_interface.exceptions.ConnectionError as e:
        pytest.skip('cannot connect to redis, skipping test: {}'.format(e))

    a = Accept(ps)
    a.start()

    s_cb = celery.signature(
            'cic_eth.callbacks.redis.redis',
            [
                data,
                '{}:{}:{}:{}'.format(host, port, db, channel),
                '1',
                ],
            queue=None,
            )
    s_cb.apply_async()
    a.join()
    r.close()
