from django.conf import settings

def debug_mode(request):
    return {'debug_mode': settings.DEBUG}

def socket_io(request):
    return {'SOCKET_IO_PORT' : settings.SOCKET_IO_PORT}
