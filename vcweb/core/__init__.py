# XXX: only works on no-arg functions that return instances of models that will never change (data parameters,
# experiment metadata, etc.)
class cacheable(object):
    def __init__(self, func):
        self.cached_object = func()
        #self.key = id(self.model_object)
        #cacheable.orm_cache[self.key] = self.model_object

    def __call__(self):
        return self.cached_object
        #return cacheable.orm_cache[self.key]
