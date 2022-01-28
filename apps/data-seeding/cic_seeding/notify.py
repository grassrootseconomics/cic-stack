# standard imports
import sys


def sync_progress_callback(block_number, tx_index):
    sys.stdout.write(str(block_number).ljust(200) + "\n")
