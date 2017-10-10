import ctypes
import socket
import logging

logger = logging.getLogger(__name__)

class sockaddr(ctypes.Structure):
    _fields_ = [
        ("sa_family", ctypes.c_short),
        ("_p1", ctypes.c_ushort),
        ("ipv4", ctypes.c_byte * 4),
        ("ipv6", ctypes.c_byte * 16),
        ("_p2", ctypes.c_ulong)
    ]

if getattr(socket, 'inet_pton', None) is None:

    WSAStringToAddressA = ctypes.windll.ws2_32.WSAStringToAddressA

    def inet_pton(fam, text):
        sa = sockaddr()
        sa.sa_family = fam

        size = ctypes.c_int(ctypes.sizeof(sa))

        saref = ctypes.byref(sa)
        szref = ctypes.byref(size)

        if WSAStringToAddressA(text, fam, None, saref, szref):
            raise socket.error('Invalid Address (fam:%d) %s' % (fam, text))

        if fam == socket.AF_INET:
            return sa.ipv4

        elif fam == socket.AF_INET6:
            return sa.ipv6

        else:
            raise socket.error('Unknown Address Family: %s' % (fam,))

if getattr(socket, 'inet_ntop', None) is None:

    WSAAddressToStringA = ctypes.windll.ws2_32.WSAAddressToStringA

    def inet_ntop(fam, byts):
        sa = sockaddr()
        sa.sa_family = fam

        if fam == socket.AF_INET:
            ctypes.memmove(sa.ipv4, byts, 4)

        elif fam == socket.AF_INET6:
            ctypes.memmove(sa.ipv6, byts, 16)

        else:
            raise Exception('Unknown Address Family: %s' % (fam,))

        size = ctypes.c_int(128)
        text = ctypes.create_string_buffer(128)

        saref = ctypes.byref(sa)
        szref = ctypes.byref(size)

        if WSAAddressToStringA(saref, ctypes.sizeof(sa), None, text, szref):
            raise socket.error('Invalid Address (fam:%d) %s' % (fam, text))

        return text.value

    socket.inet_ntop = inet_ntop

def getLibC():
    '''
    Override to account for python on windows not being able to find libc sometimes...
    '''
    return ctypes.windll.msvcrt

def initHostInfo():
    return {
        'format': 'pe',
        'platform': 'windows',
    }

def daemonize():
    pass
