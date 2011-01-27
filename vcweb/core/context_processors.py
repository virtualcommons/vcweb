from django.conf import settings

def debug_mode(request):
    return {'debug_mode': settings.DEBUG}

def socket_io(request):
    return {'socket_io_host' : settings.SOCKET_IO_HOST}
