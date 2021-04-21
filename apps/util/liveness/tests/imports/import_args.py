a = ['foo']
kw = {
    'bar': 42,
        }

def health(*args, **kwargs):
    args[0] == a[0]
    kwargs['bar'] = kw['bar']
