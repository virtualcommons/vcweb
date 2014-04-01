from django.conf import settings

def site_url(request):
    return { 'SITE_URL': settings.SITE_URL }

def debug_mode(request):
    return {'DEBUG': settings.DEBUG}

def websocket(request):
    return {'WEBSOCKET_PORT' : settings.WEBSOCKET_PORT}
