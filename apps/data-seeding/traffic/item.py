# standard imports
import uuid


class TrafficItem:
    """Represents a single item of traffic meta that will be processed by a traffic generation method

    The traffic generation module passed in the argument must implement a method "do" with interface conforming to local.noop_traffic.do.

    :param item: Traffic generation module.
    :type item: function
    """
    def __init__(self, item):
        self.method = item.do
        self.uuid = uuid.uuid4()
        self.ext = None
        self.result = None
        self.sender = None
        self.recipient = None
        self.source_token = None
        self.destination_token = None
        self.source_value = 0
        self.mode = item.task_mode

    def __str__(self):
        return 'traffic item method {} uuid {}'.format(self.method, self.uuid)
