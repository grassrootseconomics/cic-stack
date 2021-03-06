# standard imports

# third-party imports
import pytest

# local imports
from cic_ussd.chain import Chain
from cic_ussd.transactions import OutgoingTransactionProcessor, truncate


def test_outgoing_transaction_processor(load_config,
                                        create_valid_tx_recipient,
                                        create_valid_tx_sender,
                                        mock_outgoing_transactions):
    chain_str = Chain.spec.__str__()
    outgoing_tx_processor = OutgoingTransactionProcessor(
        chain_str=chain_str,
        from_address=create_valid_tx_sender.blockchain_address,
        to_address=create_valid_tx_recipient.blockchain_address
    )

    outgoing_tx_processor.process_outgoing_transfer_transaction(
        amount=120,
        token_symbol='SRF'
    )
    assert mock_outgoing_transactions[0].get('amount') == 120.0
    assert mock_outgoing_transactions[0].get('token_symbol') == 'SRF'


@pytest.mark.parametrize("decimals, value, expected_result",[
    (3, 1234.32875, 1234.328),
    (2, 98.998, 98.99)
])
def test_truncate(decimals, value, expected_result):
    assert truncate(value=value, decimals=decimals).__float__() == expected_result
