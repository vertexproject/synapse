import ctypes
import socket

import synapse.lib.thisplat as s_thisplat

hostinfo = s_thisplat.initHostInfo()
hostinfo['ptrsize'] = ctypes.sizeof(ctypes.c_void_p)
hostinfo['hostname'] = socket.gethostname()

def get(prop):
    '''
    Retrieve a property from the hostinfo dictionary.


    Example:

        import synapse.lib.thishost as s_thishost

        if s_thishost.get('platform') == 'windows':
            dostuff()


    '''
    return hostinfo.get(prop)

def hostaddr(dest='8.8.8.8'):
    '''
    Retrieve the ipv4 address for this host ( optionally as seen from dest ).
    Example:
        addr = s_socket.hostaddr()
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # doesn't actually send any packets!
    sock.connect((dest, 80))
    addr, port = sock.getsockname()

    sock.close()

    return addr
