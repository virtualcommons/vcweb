from django.http import HttpResponse


class JsonResponse(HttpResponse):

    def __init__(self, *args, **kwargs):
        kwargs['content_type'] = 'application/json'
        super(JsonResponse, self).__init__(*args, **kwargs)
