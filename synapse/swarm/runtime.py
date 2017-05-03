import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.tufo as s_tufo
import synapse.lib.storm as s_storm
import synapse.lib.service as s_service

from synapse.eventbus import EventBus
from synapse.lib.config import Configable

deftag = 'class.synapse.cores.common.Cortex'

class Runtime(s_storm.Runtime,EventBus):
    '''
    A STORM runtime capable of using a swarm cluster
    '''
    def __init__(self, svcbus, **opts):
        EventBus.__init__(self)

        # a core we use for data model stuff..
        self.core = s_cortex.openurl('ram:///')
        self.onfini( self.core.fini )

        s_storm.Runtime.__init__(self)


        self.addConfDef('svcbus:deftag', asloc='deftag', type='syn:tag', defval=deftag, doc='Default tag for cores')
        self.addConfDef('svcbus:timeout', asloc='svctime', type='int', doc='SvcBus Telepath Link Tufo')

        self.setConfOpts(opts)

        self.svcbus = svcbus
        self.svcprox = s_service.SvcProxy(svcbus, self.svctime)

    def _getStormCore(self, name=None):
        return self.core

    def _getTufosByFrom(self, by, prop, valu=None, limit=None, fromtag=None):

        if fromtag == None:
            fromtag = self.deftag

        ret = []

        limit = self.getLiftLimit(limit)

        dyntask = s_common.gentask('stormTufosBy', by, prop, valu=valu, limit=limit)

        for svcfo,retval in self.svcprox.callByTag(fromtag, dyntask, timeout=self.svctime):
            [ tufo[1].__setitem__('.from',svcfo[0]) for tufo in retval ]
            ret.extend(retval)

        return ret

    ####################################################################
    # We override the these methods from the base runtime
    # ( they are registered as operators in the base constructor )

    def _stormOperLift(self, query, oper):

        by = oper[1].get('cmp')
        prop = oper[1].get('prop')
        valu = oper[1].get('valu')
        limit = oper[1].get('limit')
        fromtag = oper[1].get('from')

        for tufo in self._getTufosByFrom(by, prop, valu, limit=limit, fromtag=fromtag):
            query.add(tufo)

    def _stormOperPivot(self, query, oper):
        args = oper[1].get('args')
        opts = dict( oper[1].get('kwlist') )

        dstp = args[0]
        srcp = args[0]

        if len(args) > 1:
            srcp = args[1]

        limit = opts.get('limit')
        fromtag = opts.get('from')

        # use the more optimal "in" mechanism once we have the pivot vals
        vals = list({ t[1].get(srcp) for t in query.take() if t != None })
        for tufo in self._getTufosByFrom('in', dstp, vals, limit=limit, fromtag=fromtag):
            query.add(tufo)

    def _stormOperJoin(self, query, oper):

        args = oper[1].get('args')
        opts = dict( oper[1].get('kwlist') )

        dstp = args[0]
        srcp = args[0]

        if len(args) > 1:
            srcp = args[1]

        limit = opts.get('limit')
        fromtag = opts.get('from')

        # use the more optimal "in" mechanism once we have the pivot vals
        vals = list({ t[1].get(srcp) for t in query.data() if t != None })
        for tufo in self._getTufosByFrom('in', dstp, vals, limit=limit, fromtag=fromtag):
            query.add(tufo)

    ####################################################################
