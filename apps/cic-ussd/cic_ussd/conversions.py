# standard imports
import decimal

# third-party imports

# local imports


def truncate(value: float, decimals: int):
    """This function truncates a value to a specified number of decimals places.
    :param value: The value to be truncated.
    :type value: float
    :param decimals: The number of decimals for the value to be truncated to
    :type decimals: int
    :return: The truncated value.
    :rtype: int
    """
    decimal.getcontext().rounding = decimal.ROUND_DOWN
    contextualized_value = decimal.Decimal(value)
    return round(contextualized_value, decimals)


def from_wei(value: int) -> float:
    """This function converts values in Wei to a token in the cic network.
    :param value: Value in Wei
    :type value: int
    :return: SRF equivalent of value in Wei
    :rtype: float
    """
    value = float(value) / 1e+6
    return truncate(value=value, decimals=2)


def to_wei(value: int) -> int:
    """This functions converts values from a token in the cic network to Wei.
    :param value: Value in SRF
    :type value: int
    :return: Wei equivalent of value in SRF
    :rtype: int
    """
    return int(value * 1e+6)