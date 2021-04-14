# standard imports
import re

# external imports
import web3

def create(url):
    # web3 input
    # TODO: Replace with chainlib
    re_websocket = r'^wss?:'
    re_http = r'^https?:'
    blockchain_provider = None
    if re.match(re_websocket, url):
        blockchain_provider = web3.Web3.WebsocketProvider(url)
    elif re.match(re_http, url):
        blockchain_provider = web3.Web3.HTTPProvider(url)
    w3 = web3.Web3(blockchain_provider)
    return w3
