import os

from binascii import hexlify

def guid():
    return os.urandom(16)

def guidstr():
    return hexlify(guid()).decode('utf8')

def tufo(name,**kwargs):
    return (name,kwargs)

def vertup(vstr):
    '''
    Convert a version string to a tuple.

    Example:

        ver = vertup('1.3.30')

    '''
    return tuple([ int(x) for x in vstr.split('.') ])

def verstr(vtup):
    '''
    Convert a version tuple to a string.
    '''
    return '.'.join([ str(v) for v in vtup ])

