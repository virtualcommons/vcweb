# FIXME: make sure this is appropriate
class cacheable(object):
    orm_cache = {}
    def __init__(self, func):
        model_object = func()
        self.key = id(model_object)
        cacheable.orm_cache[self.key] = model_object

    def __call__(self, *args):
        return cacheable.orm_cache[self.key]
