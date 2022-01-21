import logging
from typing import List, Optional, Union

from cic_eth.api.api_task import Api
from cic_eth.server import converters
from cic_eth.server.models import (DefaultToken, Token, TokenBalance, Transaction)
from fastapi import FastAPI, Query
from cic_eth.version import __version_string__

log = logging.getLogger(__name__)

def create_app(chain_spec, redis_host, redis_port, redis_db,redis_timeout, Getter, celery_queue='cic-eth'):
    app = FastAPI(
        debug=True,
        title="Grassroots Economics",
        description="CIC ETH API",
        version="0.0.1",
        terms_of_service="https://www.grassrootseconomics.org/pages/terms-and-conditions.html",
        contact={
            "name": "Grassroots Economics",
            "url": "https://www.grassrootseconomics.org",
            "email": "info@grassecon.org"
        },
        license_info={
            "name": "GPLv3",
        }
    )
    @app.get("/version", response_model=str)
    def version():
        return __version_string__

    @app.get("/transactions", response_model=List[Transaction])
    def transactions(address: str, limit: Optional[str] = 10):
        getter = Getter(chain_spec, redis_host, redis_port, redis_db, redis_timeout)
        api = Api(
            chain_spec,
            queue=celery_queue,
            callback_param=getter.get_callback_param(),
            callback_task=getter.callback_task,
            callback_queue=celery_queue
        )
        task = api.list(address, limit=limit)
        data = getter.get()
        return data

    @app.get("/balance", response_model=List[TokenBalance])
    def balance(token_symbol: str, address: str = Query(..., title="Address", min_length=40, max_length=42), include_pending: bool = True):
        getter = Getter(chain_spec, redis_host, redis_port, redis_db, redis_timeout)
        api = Api(
            chain_spec,
            queue=celery_queue,
            callback_param=getter.get_callback_param(),
            callback_task=getter.callback_task,
            callback_queue=celery_queue
        )
        task = api.balance(address, token_symbol, include_pending=include_pending)
        data = getter.get()
        for b in data:
            token = get_token(token_symbol)
            b['balance_network'] = converters.from_wei(
                token.decimals, int(b['balance_network']))
            b['balance_incoming'] = converters.from_wei(
                token.decimals, int(b['balance_incoming']))
            b['balance_outgoing'] = converters.from_wei(
                token.decimals, int(b['balance_outgoing']))

            b.update({
                "balance_available": int(b['balance_network']) + int(b['balance_incoming']) - int(b['balance_outgoing'])
            })
        return data
    

    

    @app.post("/create_account")
    def create_account(password: Optional[str] = None, register: bool = True):
        """ Creates a redis channel and calls `cic_eth.api` with the provided `method` and `*args`. Returns the result of the api call. Catch allows you to specify how many messages to catch before returning.
        """

        getter = Getter(chain_spec, redis_host, redis_port, redis_db, redis_timeout)
        api = Api(
            chain_spec,
            queue=celery_queue,
            callback_param=getter.get_callback_param(),
            callback_task=getter.callback_task,
            callback_queue=celery_queue
        )
        task = api.create_account(password=password, register=register)
        return getter.get()

    @app.post("/transfer")
    def transfer(from_address: str, to_address: str, value: int, token_symbol: str):
        token = get_token(
            token_symbol)
        wei_value = converters.to_wei(token.decimals, int(value))
        getter = Getter(chain_spec, redis_host, redis_port, redis_db, redis_timeout)
        api = Api(
            chain_spec,
            queue=celery_queue,
            callback_param=getter.get_callback_param(),
            callback_task=getter.callback_task,
            callback_queue=celery_queue
        )
        task = api.transfer(from_address, to_address, wei_value, token_symbol)
        data = getter.get()
        return data

    @app.get("/token", response_model=Token)
    def token(token_symbol: str, proof: Optional[str] = None):
        token = get_token(token_symbol, proof=proof)
        return token

    @app.get("/tokens", response_model=List[Token])
    def tokens(token_symbols: Optional[List[str]] = Query(...), proof: Optional[List[str]] = None):
        getter = Getter(chain_spec, redis_host, redis_port, redis_db, redis_timeout)
        api = Api(
            chain_spec,
            queue=celery_queue,
            callback_param=getter.get_callback_param(),
            callback_task=getter.callback_task,
            callback_queue=celery_queue
        )
        task = api.tokens(token_symbols, proof=proof)
        data = getter.get(catch=len(token_symbols))
        if data:
            tokens = []
            if len(token_symbols) == 1:
                tokens.append(Token.new(data))
            else:
                for token in data:
                    tokens.append(Token.new(token))
            return tokens
        return None

    @app.get("/default_token", response_model=DefaultToken)
    def default_token():
        getter = Getter(chain_spec, redis_host, redis_port, redis_db, redis_timeout)
        api = Api(
            chain_spec,
            queue=celery_queue,
            callback_param=getter.get_callback_param(),
            callback_task=getter.callback_task,
            callback_queue=celery_queue
        )
        task = api.default_token()
        data = getter.get()
        return data

    def get_token(token_symbol: str, proof=None):
        getter = Getter(chain_spec, redis_host, redis_port, redis_db, redis_timeout)
        api = Api(
            chain_spec,
            queue=celery_queue,
            callback_param=getter.get_callback_param(),
            callback_task=getter.callback_task,
            callback_queue=celery_queue
        )
        task = api.token(token_symbol, proof=None)
        data = getter.get()
        return Token.new(data)
    return app

