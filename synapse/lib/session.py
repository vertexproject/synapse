import time

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.config as s_config

class Sess(s_eventbus.EventBus):
    '''
    A synapse session to store prop/vals.
    '''
    def __init__(self, iden, **props):
        s_eventbus.EventBus.__init__(self)

        self.iden = iden
        self.tick = int(time.time())

        self.props = props
        self.dirty = False

    def get(self, prop):
        '''
        Retrieve a session property by name.

        Args:
            prop (str): The property name to retrieve.

        Returns:
            (obj): The property valu (or None)
        '''
        return self.props.get(prop)

    def set(self, prop, valu):
        '''
        Set a session property to the given value.

        Args:
            prop (str): The name of the session property
            valu (obj): The property valu
        '''
        self.dirty = True
        self.props[prop] = valu
        self.fire('set', prop=prop, valu=valu)

    #TODO: make save() return *only* msgpack compat props

class Curator(s_config.Config):
    '''
    The Curator class manages sessions.
    '''
    def __init__(self, conf=None):

        if conf is None:
            conf = {}

        s_config.Config.__init__(self)
        self.setConfOpts(conf)
        self.reqConfOpts()

        self.refs = s_eventbus.BusRef()
        self.onfini(self.refs.fini)

        self.task = s_glob.sched.loop(30, self._curaMainLoop)
        self.onfini(self.task.fini)

    def _curaMainLoop(self):
        # the curator maintenance loop...
        tout = self.getConfOpt('timeout')
        tick = int(time.time()) - tout
        for sess in self.refs.vals():
            if sess.tick < tick:
                sess.fini()

    def get(self, iden=None):
        '''
        Return a Session by iden.

        Args:
            iden (str): The guid (None creates a new sess).

        Returns:
            (Sess)
        '''
        if iden is None:
            iden = s_common.guid()

        sess = self.refs.get(iden)
        if sess is None:
            sess = Sess(iden)
            self.refs.put(iden, sess)

        sess.tick = int(time.time())
        return sess

    @staticmethod
    @s_config.confdef('cura')
    def _getCuraConf():
        return (
            #TODO: ('dir', {'type': 'str', 'doc': 'The directory to persist sess info'}),
            ('timeout', {'type': 'int', 'defval': 60 * 60, 'doc': 'Session timeout in seconds'}),
        )
