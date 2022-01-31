# standard imports
import logging
import importlib
import random

# local imports
from .item import TrafficItem

logg = logging.getLogger(__name__)


class TrafficRouter:
    """Holds and selects from the collection of traffic generator modules that will be used for the execution.

    :params batch_size: Amount of simultaneous traffic items that can simultanously be in flight.
    :type batch_size: number
    :raises ValueError: If batch size is zero of negative
    """
    def __init__(self, batch_size=1):
        if batch_size < 1:
            raise ValueError('batch size cannot be 0')
        self.items = []
        self.item_weights = []
        self.weights = []
        self.total_weights = 0
        self.batch_size = batch_size
        self.reserved = {}
        self.traffic = {}


    def add(self, item, weight):
        """Add a traffic generator module to the list of modules to choose between for traffic item exectuion.

        The probability that a module will be chosen for any single item is the ratio between the weight parameter and the accumulated weights for all items.

        See local.noop for which criteria the generator module must fulfill.

        :param item: Qualified class path to traffic generator module. Will be dynamically loaded.
        :type item: str
        :param weight: Selection probability weight
        :type weight: number
        :raises ModuleNotFound: Invalid item argument
        """
        self.total_weights += weight
        self.weights.append(self.total_weights)
        m = importlib.import_module(item)
        self.items.append(m)
        self.item_weights.append(weight)
        

    def reserve(self):
        """Selects the module to be used to execute the next traffic item, using the provided weights.

        If the current number of calls to "reserve" without corresponding calls to "release" equals the set batch size limit, None will be returned. The calling code should allow a short grace period before trying the call again.
        :raises ValueError: No items have been added
        :returns: A traffic item with the selected module method as the method property.
        :rtype: TrafficItem|None
        """
        if len(self.items) == 0:
            raise ValueError('Add at least one item first')

        if len(self.reserved) == self.batch_size:
            return None

        n = random.randint(0, self.total_weights)
        item = self.items[0]
        for i in range(len(self.weights)):
            if n <= self.weights[i]:
                item = self.items[i]
                break

        ti = TrafficItem(item)
        self.reserved[ti.uuid] = ti
        return ti


    def count(self):
        return (len(self.reserved), self.batch_size,)


    def release(self, traffic_item):
        """Releases the traffic item from the list of simultaneous traffic items in flight.

        :param traffic_item: Traffic item
        :type traffic_item: TrafficItem
        """
        del self.reserved[traffic_item.uuid]


    def apply_import_dict(self, keys, dct):
        """Convenience method to add traffic generator modules from a dictionary.

        :param keys: Keys in dictionary to add
        :type keys: list of str
        :param dct: Dictionary to choose module strings from
        :type dct: dict
        :raises ModuleNotFoundError: If one of the module strings refer to an invalid module.
        """
        # parse traffic items
        for k in keys:
            if len(k) > 8 and k[:8] == 'TRAFFIC_':
                v = int(dct.get(k))
                if v == 0:
                    logg.debug('skipping traffic item {} with weight {}'.format(k, v))
                else:
                    logg.debug('found traffic item {} weight {}'.format(k, v))
                    self.add(k[8:].lower(), v)
