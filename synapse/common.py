from __future__ import absolute_import,unicode_literals

import os
import sys
import json
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

def msgpackfd(fd):
    unpk = msgpack.Unpacker(fd, use_list=False, encoding='utf8')
    for mesg in unpk:
        yield mesg

def vertup(vstr):
    '''
    Convert a version string to a tuple.

    Example:

        ver = vertup('1.3.30')

    '''
    return tuple([ int(x) for x in vstr.split('.') ])

def genpath(*paths):
    path = os.path.join(*paths)
    path = os.path.expanduser(path)
    return os.path.abspath(path)

def genfile(*paths):
    '''
    Create or open ( for read/write ) a file path join.
    '''
    path = genpath(*paths)
    gendir( os.path.dirname(path) )
    if not os.path.isfile(path):
        return open(path,'w+b')
    return open(path,'r+b')

def gendir(*paths,**opts):
    mode = opts.get('mode',0o700)
    path = genpath(*paths)
    if not os.path.isdir(path):
        os.makedirs(path,mode=mode)
    return path

def jsload(*paths):
    with genfile(*paths) as fd:
        byts = fd.read()
        if not byts:
            return None

        return json.loads(byts.decode('utf8'))

def gentask(func,*args,**kwargs):
    return (func,args,kwargs)

def jssave(js,*paths):
    path = genpath(*paths)
    with open(path,'wb') as fd:
        fd.write( json.dumps(js).encode('utf8') )

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

def errinfo(name,mesg):
    return {
        'err':name,
        'errmsg':mesg,
        #'errfile':path,
        #'errline':line,
    }

def tufoprops(tufo,pref=None):
    if pref == None:
        pref = tufo[1].get('tufo:form')

    pref = '%s:' % (pref,)
    plen = len(pref)
    return { p[plen:]:v for (p,v) in tufo[1].items() if p.startswith(pref) }

def chunks(item,size):
    '''
    Divide an iterable into chunks.
    '''
    off = 0
    offmax = len(item)
    while off < offmax:
        yield item[off:off+size]
        off += size

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
