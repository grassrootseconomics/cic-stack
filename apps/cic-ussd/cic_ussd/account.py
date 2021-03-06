# standard imports
import json

# third-party imports
from cic_eth.api import Api
from cic_types.models.person import Person
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.chain import Chain
from cic_ussd.db.models.user import User
from cic_ussd.metadata import blockchain_address_to_metadata_pointer
from cic_ussd.redis import get_cached_data


def define_account_tx_metadata(user: User):
    # get sender metadata
    identifier = blockchain_address_to_metadata_pointer(
        blockchain_address=user.blockchain_address
    )
    key = generate_metadata_pointer(
        identifier=identifier,
        cic_type='cic.person'
    )
    account_metadata = get_cached_data(key=key)

    if account_metadata:
        account_metadata = json.loads(account_metadata)
        person = Person()
        deserialized_person = person.deserialize(metadata=account_metadata)
        given_name = deserialized_person.given_name
        family_name = deserialized_person.family_name
        phone_number = deserialized_person.tel

        return f'{given_name} {family_name} {phone_number}'
    else:
        phone_number = user.phone_number
        return phone_number


def retrieve_account_statement(blockchain_address: str):
    chain_str = Chain.spec.__str__()
    cic_eth_api = Api(
        chain_str=chain_str,
        callback_queue='cic-ussd',
        callback_task='cic_ussd.tasks.callback_handler.process_statement_callback',
        callback_param=blockchain_address
    )
    result = cic_eth_api.list(address=blockchain_address, limit=9)
