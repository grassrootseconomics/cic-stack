from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        status_str,
        )


def test_status_str():

    # String representation for a status in StatusEnum
    s = status_str(StatusEnum.REVERTED)
    assert s == 'REVERTED'

    # String representation for a status not in StatusEnum
    s = status_str(StatusBits.LOCAL_ERROR | StatusBits.NODE_ERROR)
    assert s == 'LOCAL_ERROR,NODE_ERROR*'

    # String representation for a status in StatusEnum, but bits only representation bit set
    s = status_str(StatusEnum.REVERTED, bits_only=True)
    assert s == 'IN_NETWORK,NETWORK_ERROR,FINAL'
