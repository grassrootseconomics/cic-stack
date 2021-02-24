from cic_eth.eth.task import sign_tx
from cic_eth.eth.util import tx_hex_string
from cic_eth.eth.util import unpack_signed_raw_tx_hex

def test_unpack(
    init_w3_conn,
        ):

    tx = {
        'nonce': 13,
        'from': init_w3_conn.eth.accounts[0],
        'to': init_w3_conn.eth.accounts[1],
        'data': '0xdeadbeef',
        'value': 1024,
        'gas': 23000,
        'gasPrice': 1422521,
        'chainId': 42,
            }

    (tx_hash, tx_signed) = sign_tx(tx, 'foo:bar:42')

    tx_unpacked = unpack_signed_raw_tx_hex(tx_signed, 42)

    for k in tx.keys():
        assert tx[k] == tx_unpacked[k]

    tx_str = tx_hex_string(tx_signed, 42)
    assert tx_str == 'tx nonce 13 from 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf to 0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF hash 0x23ba3c2b400fbddcacc77d99644bfb17ac4653a69bfa46e544801fbd841b8f1e'
