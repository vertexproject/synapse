import os

from binascii import hexlify

def guid():
    return os.urandom(16)

def guidstr():
    return hexlify(guid()).decode('utf8')

def tufo(name,**kwargs):
    return (name,kwargs)

