# standard imports
import logging
import sha3
import web3

# third-party imports
from rlp import decode as rlp_decode
from rlp import encode as rlp_encode
from eth_keys import KeyAPI

logg = logging.getLogger()

field_debugs = [
        'nonce',
        'gasPrice',
        'gas',
        'to',
        'value',
        'data',
        'v',
        'r',
        's',
        ]


def unpack_signed_raw_tx(tx_raw_bytes, chain_id):
    d = rlp_decode(tx_raw_bytes)

    logg.debug('decoding using chain id {}'.format(chain_id))
    j = 0
    for i in d:
        logg.debug('decoded {}: {}'.format(field_debugs[j], i.hex()))
        j += 1
    vb = chain_id
    if chain_id != 0:
        v = int.from_bytes(d[6], 'big')
        vb = v - (chain_id * 2) - 35
    while len(d[7]) < 32:
        d[7] = b'\x00' + d[7]
    while len(d[8]) < 32:
        d[8] = b'\x00' + d[8]
    s = b''.join([d[7], d[8], bytes([vb])])
    so = KeyAPI.Signature(signature_bytes=s)

    h = sha3.keccak_256()
    h.update(rlp_encode(d))
    signed_hash = h.digest()

    d[6] = chain_id
    d[7] = b''
    d[8] = b''

    h = sha3.keccak_256()
    h.update(rlp_encode(d))
    unsigned_hash = h.digest()
    
    p = so.recover_public_key_from_msg_hash(unsigned_hash)
    a = p.to_checksum_address()
    logg.debug('decoded recovery byte {}'.format(vb))
    logg.debug('decoded address {}'.format(a))
    logg.debug('decoded signed hash {}'.format(signed_hash.hex()))
    logg.debug('decoded unsigned hash {}'.format(unsigned_hash.hex()))

    to = d[3].hex() or None
    if to != None:
        to = web3.Web3.toChecksumAddress('0x' + to)

    return {
        'from': a,
        'nonce': int.from_bytes(d[0], 'big'),
        'gasPrice': int.from_bytes(d[1], 'big'),
        'gas': int.from_bytes(d[2], 'big'),
        'to': to, 
        'value': int.from_bytes(d[4], 'big'),
        'data': '0x' + d[5].hex(),
        'v': chain_id,
        'r': '0x' + s[:32].hex(),
        's': '0x' + s[32:64].hex(),
        'chainId': chain_id,
        'hash': '0x' + signed_hash.hex(),
        'hash_unsigned': '0x' + unsigned_hash.hex(),
            }


def unpack_signed_raw_tx_hex(tx_raw_hex, chain_id):
    return unpack_signed_raw_tx(bytes.fromhex(tx_raw_hex[2:]), chain_id)


# TODO: consider moving tx string representation generation from api_admin to here
def tx_string(tx_raw_bytes, chain_id):
    tx_unpacked = unpack_signed_raw_tx(tx_raw_bytes, chain_id)
    return 'tx nonce {} from {} to {} hash {}'.format(
            tx_unpacked['nonce'],
            tx_unpacked['from'],
            tx_unpacked['to'],
            tx_unpacked['hash'],
        )

def tx_hex_string(tx_hex, chain_id):
    if len(tx_hex) < 2:
        raise ValueError('invalid data length')
    elif tx_hex[:2] == '0x':
        tx_hex = tx_hex[2:]

    tx_raw_bytes = bytes.fromhex(tx_hex)
    return tx_string(tx_raw_bytes, chain_id)


