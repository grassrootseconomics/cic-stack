# standard imports

# third-party imports

# local imports
from cic_ussd.accounts import BalanceManager


def test_balance_manager(mocker, load_config, create_valid_tx_recipient):

    balance_manager = BalanceManager(
        address=create_valid_tx_recipient.blockchain_address,
        chain_str=load_config.get('CIC_CHAIN_SPEC'),
        token_symbol='SRF'
    )
    balance_manager.get_operational_balance = mocker.MagicMock()
    balance_manager.get_operational_balance()

    balance_manager.get_operational_balance.assert_called_once()
