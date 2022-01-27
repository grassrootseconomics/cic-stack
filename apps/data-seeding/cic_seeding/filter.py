__remove_zeros = 10**6
def remove_zeros_filter(v):
        return int(int(v) / __remove_zeros)


def split_filter(v):
    if v == None:
        return []
    return v.split(',')

