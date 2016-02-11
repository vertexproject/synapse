from __future__ import absolute_import,unicode_literals

import ctypes
import socket
import platform

import synapse.lib.platforms.linux as s_linux
import synapse.lib.platforms.darwin as s_darwin
import synapse.lib.platforms.freebsd as s_freebsd
import synapse.lib.platforms.windows as s_windows

hostinfo = {}
hostinfo['ptrsize'] = ctypes.sizeof( ctypes.c_void_p )
hostinfo['hostname'] = socket.gethostname()

platinit = {
    'linux':s_linux._initHostInfo,
    'darwin':s_darwin._initHostInfo,
    'freebsd':s_freebsd._initHostInfo,
}

# avoid using osname to detect windows because of variants...
if getattr(ctypes,'windll',None):
    s_windows._initHostInfo(hostinfo)

osname = platform.system().lower()
infoinit = platinit.get(osname)
if infoinit != None:
    infoinit(hostinfo)

def get(prop):
    '''
    Retrieve a property from the hostinfo dictionary.


    Example:

        import synapse.lib.thishost as s_thishost

        if s_thishost.get('platform') == 'windows':
            dostuff()


    '''
    return hostinfo.get(prop)
