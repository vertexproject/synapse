import fnmatch
import threading

import synapse.lib.tufo as s_tufo
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

    def __init__(self, cura, iden, **props):
        EventBus.__init__(self)

        self.iden = iden
        self.cura = cura
        self.props = props

        self.on('sess:log', self.cura.dist )

    def get(self, prop):
        '''
        Retrieve a session property by name.
        '''
        return self.props.get(prop)

    def put(self, prop, valu, save=True):
        '''
        Put a value into the session ( but do not persist it to storage ).
        '''
        self.props[prop] = valu
        if save:
            self.cura._saveSessProp(self.iden,prop,valu)

    def log(self, level, mesg, **info):
        info['mesg'] = mesg
        info['level'] = level

        info['iden'] = self.iden

        self.fire('sess:log', **info)

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
    def __init__(self, core=None, maxtime=onehour):
        EventBus.__init__(self)

        self.core = core

        self.cache = s_cache.Cache(maxtime=maxtime)
        self.cache.setOnMiss( self._getSessByIden )
        self.cache.on('cache:pop', self._onSessCachePop )

        self.onfini( self.cache.fini )

    def setMaxTime(self,valu):
        return self.cache.setMaxTime(valu)

    def setSessCore(self, core):
        self.core = core

    def _onSessCachePop(self, event):

        iden = event[1].get('key')
        sess = event[1].get('val')

        if sess == None:
            return

        sess.fini()

    def __iter__(self):
        return self.cache.values()

    def new(self):
        '''
        Create and return a new Sess.

        Example:

            sess = cura.new()

        '''
        iden = guid()
        sess = Sess(self, iden)
        self.cache.put(iden,sess)
        self.fire('sess:init', sess=sess)
        return sess

    def get(self, iden):
        '''
        Return a Session by iden.

        Example:

            sess = boss.get(sid)
            if sess != None:
                dostuff(sess)

        '''
        return self.cache.get(iden)

    def _getSessByIden(self, iden):

        # If we have no cortex, we have no session storage
        if self.core == None:
            return None

        # look up the tufo and construct a Sess()
        sefo = self.core.getTufoByProp('syn:sess',iden)
        if sefo == None:
            return None

        props = s_tufo.props(sefo)
        return Sess(self,iden,**props)

    def _saveSessProp(self, iden, prop, valu):

        # if we have a cortex to persist into
        if self.core == None:
            return

        sefo = self.core.formTufoByProp('syn:sess', iden)
        self.core.setTufoProp(sefo,prop,valu)
