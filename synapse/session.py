import threading

import synapse.cache as s_cache
import synapse.cortex as s_cortex

from synapse.eventbus import EventBus
from synapse.common import *

sesslocal = threading.local()

def current():
    try:
        return sesslocal.sess
    except AttributeError as e:
        return None

def get(prop):
    '''
    Helper for use with getting session props for current()

    Example:

        with boss.getSessWith(sid):
            # ... somewhere deeper ...
            foo = s_session.get('sess:foo')

    '''
    sess = current()
    if sess == None:
        return None

    return sess[1].get(prop)

def put(prop,valu):
    '''
    Helper for use with setting session props for current()

    Example:

        with boss.getSessWith(sid):
            # ... somewhere deeper ...
            s_session.put('sess:foo', 10)

    '''
    sess = current()
    if sess == None:
        return False

    sess[1][prop] = valu
    return True

class WithSess:

    def __init__(self, sess):
        self.sess = sess
        self.olds = None

    def __enter__(self):
        self.olds = current()
        sesslocal.sess = self.sess

    def __exit__(self, exc, cls, tb):
        sesslocal.sess = self.olds

class SessBoss(EventBus):
    '''
    A Cortex backed "session" manager.
    '''

    def __init__(self, core=None, maxtime=None):
        EventBus.__init__(self)

        if core == None:
            core = s_cortex.openurl('ram:///')

        self.core = core
        self.sesswith = {}

        self.cache = s_cache.Cache(maxtime=maxtime)
        self.cache.on('cache:miss', self._onCacheMiss)
        self.cache.on('cache:flush', self._onCacheFlush)

        self.onfini( self.cache.fini )

    def _onCacheMiss(self, event):
        key = event[1].get('key')
        sess = self.core.getTufoById(key)
        self.cache.put(key,sess)

    def _onCacheFlush(self, event):
        sid = event[1].get('key')
        sess0 = event[1].get('val')

        sess1 = self.core.getTufoById(sid)
        if sess1 == None:
            return

        self.core.setTufoProps(sess1, **sess0[1])
        self.sesswith.pop(sid,None)

    def getSess(self, sid):
        '''
        Return a session tufo by id.

        Example:

            sess = boss.getSess(sid)

        '''
        return self.cache.get(sid)

    def initSess(self, **props):
        '''
        Create a new session and return the tufo.

        Example:

            sess = boss.initSess()

        '''
        sid = guidstr()
        now = int(time.time())

        props['sess:init'] = now

        sess = (sid,props)
        rows = [ (sid,p,v,now) for (p,v) in props.items() ]

        self.core.addRows(rows)
        self.cache.put(sid,sess)

        self.fire('sess:init', sess=sess)

        return sess

    def getSessWith(self, sid):
        '''
        Return a "with block" object to run within a sess context.

        Example:

            with boss.getSessWith(sid):
                runStuffAsSess()

        '''
        block = self.sesswith.get(sid)
        if block == None:
            sess = self.getSess(sid)
            block = WithSess(sess)
            self.sesswith[sid] = block
        return block
