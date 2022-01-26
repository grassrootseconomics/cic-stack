# standard imports
import os

# external imports

# local imports
from cic_ussd.account.guardianship import Guardianship

# test imports
from tests.fixtures.config import root_directory


def test_guardianship(load_config, setup_guardianship):
    guardians_file = os.path.join(root_directory, load_config.get('SYSTEM_GUARDIANS_FILE'))
    with open(guardians_file, 'r') as system_guardians:
        guardians = [line.strip() for line in system_guardians]
    assert Guardianship.guardians == guardians

    guardianship = Guardianship()
    assert guardianship.is_system_guardian(Guardianship.guardians[0]) is True
    assert guardianship.is_system_guardian('+254712345678') is False
