from django.conf import settings

def debug_mode(request):
    return {'debug_mode': settings.DEBUG}

def websocket(request):
    return {'WEBSOCKET_PORT' : settings.WEBSOCKET_PORT}
