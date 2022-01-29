# standard imports
from argparse import RawTextHelpFormatter


def add_args(argparser):
    """Parse script specific command line arguments

    :param argparser: Top-level argument parser
    :type argparser: argparse.ArgumentParser
    """
    argparser.formatter_class = formatter_class=RawTextHelpFormatter
    argparser.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
    argparser.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
    argparser.add_argument('--batch-size', dest='batch_size', default=10, type=int, help='number of events to process simultaneously')
    argparser.description = """Generates traffic on the cic network using dynamically loaded modules as event sources

"""
    return argparser


