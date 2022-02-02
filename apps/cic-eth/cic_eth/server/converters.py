# Stolen from ussd

from math import trunc

def from_wei(decimals: int, value: int) -> float:
    """This function converts values in Wei to a token in the cic network.
    :param decimals: The decimals required for wei values.
    :type decimals: int
    :param value: Value in Wei
    :type value: int
    :return: SRF equivalent of value in Wei
    :rtype: float
    """
    value = float(value) / (10**decimals)
    return truncate(value=value, decimals=2)


def to_wei(decimals: int, value: int) -> int:
    """This functions converts values from a token in the cic network to Wei.
    :param decimals: The decimals required for wei values.
    :type decimals: int
    :param value: Value in SRF
    :type value: int
    :return: Wei equivalent of value in SRF
    :rtype: int
    """
    return int(value * (10**decimals))

def truncate(value: float, decimals: int) -> float:
    """This function truncates a value to a specified number of decimals places.
    :param value: The value to be truncated.
    :type value: float
    :param decimals: The number of decimals for the value to be truncated to
    :type decimals: int
    :return: The truncated value.
    :rtype: int
    """
    return round(value,decimals)
