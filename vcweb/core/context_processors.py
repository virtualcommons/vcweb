from django.conf import settings

def debug_mode(request):
    return {'DEBUG': settings.DEBUG}

def websocket(request):
    return {'WEBSOCKET_PORT' : settings.WEBSOCKET_PORT}
