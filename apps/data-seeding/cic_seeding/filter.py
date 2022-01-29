# This file contains value filters used by the dirhandler.

# TODO: Instantiate for token decimal count.
remove_zeros = 10**6
def remove_zeros_filter(v):
        return int(int(v) / remove_zeros)


# csv to list
def split_filter(v):
    if v == None:
        return []
    return v.split(',')
