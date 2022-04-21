# standard imports
import logging
import os

# external imports
from confini import Config

# local imports
from cic_notify.error import SeppukuError

logg = logging.getLogger()


class Muxer:
    channels_dict = None
    default_channel_keys = ['db', 'log']
    tasks = []

    # handle muxer
    @classmethod
    def initialize(cls, config: Config):
        logg.debug(f"Loading task configs: {config}")

        channels_dict = {}
        for config_key, config_value in config.store.items():
            if config_key[:5] == 'TASKS':
                # split by tasks key entry
                channel_key = config_key[6:].lower()
                task_status = config_value.split(':')
                config_value_status = task_status[1]
                if config_value_status == 'enabled':
                    channels_dict[channel_key] = task_status[0]
                else:
                    logg.debug(f'Disabled channels: {channel_key}')

        logg.debug(f'Loaded channels: {list(channels_dict.keys())}')
        cls.channels_dict = channels_dict

    def route(self, channel_keys: list):
        """
        :param channel_keys:
        :type channel_keys:
        :return:
        :rtype:
        """

        if not self.channels_dict:
            raise SeppukuError("No channels added to primary channels object.")

        # add default channels
        channel_keys.extend(self.default_channel_keys)

        for key in channel_keys:
            if key in list(self.channels_dict.keys()) and self.channels_dict.get(key) not in self.tasks:
                task_path = self.channels_dict.get(key)
                self.tasks.append(task_path)
