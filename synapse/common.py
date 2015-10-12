import os
import time
import msgpack
import functools
import threading

from binascii import hexlify

from synapse.compat import enbase64, debase64

def now():
    return int(time.time())

def guid():
    return os.urandom(16)

def guidstr():
    return hexlify(guid()).decode('utf8')

def tufo(typ,**kwargs):
    return (typ,kwargs)

def msgenpack(obj):
    return msgpack.dumps(obj, use_bin_type=True, encoding='utf8')

def msgunpack(byts):
    return msgpack.loads(byts, use_list=False, encoding='utf8')

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

def firethread(f):
    '''
    A decorator for making a function fire a thread.
    '''
    @functools.wraps(f)
    def callmeth(*args,**kwargs):
        thr = worker(f,*args,**kwargs)
        return thr
    return callmeth

def worker(meth, *args, **kwargs):
    thr = threading.Thread(target=meth,args=args,kwargs=kwargs)
    thr.setDaemon(True)
    thr.start()
    return thr

