from django.conf import settings

def common(request):
    return {'WEBSOCKET_PORT' : settings.WEBSOCKET_PORT, 'SITE_URL': settings.SITE_URL, 'DEBUG': settings.DEBUG}
