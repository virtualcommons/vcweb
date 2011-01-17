from django.http import HttpResponseRedirect

def anonymous_required(view_function=None, redirect_to='core:dashboard'):
    def _decorate(view_function):
        def _view(request, *args, **kwargs):
            if request.user is not None and request.user.is_authenticated():
                return HttpResponseRedirect(redirect_to)
            else:
                return view_function(request, *args, **kwargs)
        _view.__name__ = view_function.__name__
        _view.__dict__ = view_function.__dict__
        _view.__doc__ = view_function.__doc__
        return _view
    return _decorate if view_function is None else _decorate(view_function)
