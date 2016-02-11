import os
import sys
import time
import msgpack
import functools
import threading
import traceback

from binascii import hexlify

from synapse.exc import *
from synapse.compat import enbase64, debase64

def now():
    return int(time.time())

def guid():
    return hexlify(os.urandom(16)).decode('utf8')

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

def excinfo(e):
    '''
    Populate err,errmsg,errtrace info from exc.
    '''
    tb = sys.exc_info()[2]
    path,line,name,sorc = traceback.extract_tb(tb)[-1]
    return {
        'err':e.__class__.__name__,
        'errmsg':str(e),
        'errfile':path,
        'errline':line,
    }

class TufoApi:
    '''
    TufoApi is a mixin class providing get/set APIs around a
    tufo being cached in memory.
    '''

    def __init__(self, core, myfo):
        self.core = core
        self.myfo = myfo

    def get(self, prop):
        '''
        Retrieve a property from the tufo.

        Example:

            foo = tapi.get('foo')

        '''
        form = self.myfo[1].get('tufo:form')
        return self.myfo[1].get('%s:%s' % (form,prop))

    def set(self, prop, valu):
        '''
        Set a property in the tufo ( and persist change to core ).

        Example:

            tapi.set('foo', 20)

        '''
        self.core.setTufoProp(self.myfo, prop, valu)

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
