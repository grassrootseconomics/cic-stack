# standard imports

# third-party imports

# local imports
from cic_ussd.balance import BalanceManager
from cic_ussd.chain import Chain


def test_balance_manager(create_valid_tx_recipient, load_config, mocker, setup_chain_spec):
    chain_str = Chain.spec.__str__()
    balance_manager = BalanceManager(
        address=create_valid_tx_recipient.blockchain_address,
        chain_str=chain_str,
        token_symbol='SRF'
    )
    balance_manager.get_balances = mocker.MagicMock()
    balance_manager.get_balances()

    balance_manager.get_balances.assert_called_once()
