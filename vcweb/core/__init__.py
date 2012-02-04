class simplecache(object):
    """
    only works on no-arg functions that return instances of models that will never change (data parameters,
    experiment metadata, etc.)
    """
    def __init__(self, func):
        # invoking the func at init time causes syncdb to croak
        self.cached_object = None
        self.func = func

    def __call__(self, refresh=False):
        if self.cached_object is None or refresh:
            self.cached_object = self.func()
        return self.cached_object

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)
