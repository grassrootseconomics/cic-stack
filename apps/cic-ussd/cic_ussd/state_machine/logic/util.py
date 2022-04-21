import logging
from math import floor
from decimal import Decimal

logg = logging.getLogger(__file__)

def cash_rounding_precision(input: str):
    """
    utility to convert string to properly rounded precision
    rejecting high precisions above the erc20 limit

    :param string:
    :return: float
    """

    try:
        dp = input[::-1].find('.')
        input = float(input)
    except ValueError:
        logg.error("could not convert to float")
    
    assert dp <= 8, "precision too high"

    if dp <= 2:
        return input
    else:
        return floor(input * 100) / 100

