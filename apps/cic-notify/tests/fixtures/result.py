# standard imports

# external imports
import pytest


# local imports

# test imports

@pytest.fixture(scope="function")
def africastalking_response():
    return {
        "SMSMessageData": {
            "Message": "Sent to 1/1 Total Cost: KES 0.8000",
            "Recipients": [{
                "statusCode": 101,
                "number": "+254711XXXYYY",
                "status": "Success",
                "cost": "KES 0.8000",
                "messageId": "ATPid_SampleTxnId123"
            }]
        }
    }
