import fnmatch
import threading

import synapse.lib.cache as s_cache
import synapse.lib.sched as s_sched

from synapse.eventbus import EventBus
from synapse.common import *

sesslocal = threading.local()

def current():
    '''
    Return the current Sess() or None.
    '''
    try:
        return sesslocal.sess
    except AttributeError as e:
        return None

reflock = threading.Lock()

class Sess(EventBus):

    def __init__(self, cura, sess):
        EventBus.__init__(self)

        self.sid = sess[0]
        self.cura = cura
        self.sess = sess

        self.local = {}      # runtime only props

    def get(self, prop):
        prop = 'sess:%s' % prop
        return self.sess[1].get(prop)

    def put(self, prop, valu):
        self.cura.core.setTufoProp(self.sess,prop,valu)

    def __enter__(self):
        sesslocal.sess = self
        return self

    def __exit__(self, exc, cls, tb):
        sesslocal.sess = None

onehour = 60 * 60
class Curator(EventBus):
    '''
    The Curator class manages session objects and storage.
    '''
    def __init__(self, core, maxtime=onehour):
        EventBus.__init__(self)

        self.core = core

        self.cache = s_cache.Cache(maxtime=maxtime)
        self.cache.setOnMiss( self._getSessBySid )
        self.cache.on('cache:pop', self._onSessCachePop )

        self.onfini( self.cache.fini )

    def _onSessCachePop(self, event):
        sess = event[1].get('val')
        if sess != None:
            sess.fini()

    def __iter__(self):
        return self.cache.values()

    def new(self):
        '''
        Create and return a new Sess.

        Example:

            sess = cura.new()

        '''
        sess = Sess(self, self._initSessTufo())
        self.cache.put(sess.sid,sess)
        return sess

    def get(self, sid):
        '''
        Return a session tufo by id.

        Example:

            sess = boss.get(sid)
            if sess != None:
                dostuff(sess)

        '''
        return self.cache.get(sid)

    def _getSessBySid(self, sid):
        # look up the tufo and construct a Sess()
        sess = self.core.getTufoByProp('sess',sid)
        if sess == None:
            return None

        return Sess(self,sess)

    def _initSessTufo(self):
        now = int(time.time())
        sess = self.core.addTufoEvent('sess',init=now,root=0)

        self.fire('sess:init', sess=sess)
        return sess

