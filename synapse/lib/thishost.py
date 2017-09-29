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
