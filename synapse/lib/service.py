import time
import inspect
import logging

logger = logging.getLogger(__name__)

import synapse.async as s_async
import synapse.aspects as s_aspects
import synapse.eventbus as s_eventbus

import synapse.lib.sched as s_sched
import synapse.lib.threads as s_threads
import synapse.lib.thishost as s_thishost

from synapse.common import *

class SvcBus(s_eventbus.EventBus):

    def __init__(self):
        s_eventbus.EventBus.__init__(self)

        self.bytag = s_aspects.ByTag()
        self.services = {}

        self.on('syn:svc:fini', self._onSynSvcFini)

    def _onSynSvcFini(self, mesg):
        name = mesg[1].get('name')
        props = mesg[1].get('props')

        self.bytag.pop(name)

    def iAmSynSvc(self, iden, props):
        '''
        API used by synapse service to register with the bus.

        Example:

            sbus.iAmSynSvc('syn.blah', foo='bar', baz=10)

        '''
        props['iden'] = iden

        svcfo = (iden,props)

        sock = s_threads.local('sock')
        if sock != None:
            def onfini():
                oldsvc = self.services.pop(iden,None)
                self.bytag.pop(iden)
                self.fire('syn:svc:fini', svcfo=oldsvc)

            sock.onfini(onfini)
            
        self.services[iden] = svcfo

        tags = props.get('tags',())

        self.bytag.put(iden,tags)

        self.fire('syn:svc:init', svcfo=svcfo)

    def iAmAlive(self, iden):
        '''
        "heartbeat" API for services.

        Example:

            sbus.iAmAlive(iden)

        Notes:

            This API is generally called by a scheduled loop
            within the service object.
        '''
        svcfo = self.services.get(iden)
        if svcfo != None:
            svcfo[1]['checkin'] = int(time.time())

    def getSynSvcs(self):
        '''
        Retrieve a list of the services on the service bus.

        Example:

            for name,info in sbus.getSynSvcs():
                dostuff(name,info)

        '''
        return list(self.services.values())

    def getSynSvcsByTag(self, tag):
        '''
        Return a list of synapse services by hierarchical tag.

        Example:

            for name,props in sbus.getSynSvcsByTag('foo.bar'):
                dostuff(name,props)

        '''
        idens = self.bytag.get(tag)
        return [ self.services.get(iden) for iden in idens ]

class SvcProxy:
    '''
    A client-side helper for service dispatches.

    Mostly exists to wrap functionality for calling multiple
    services by tag.
    '''
    def __init__(self, sbus, timeout=None):
        self.sbus = sbus
        self.timeout = timeout

        self.sbus.on('syn:svc:init', self._onSynSvcInit )
        self.sbus.on('syn:svc:fini', self._onSynSvcFini )

        self.bytag = s_aspects.ByTag()
        self.byiden = {}

        [ self._addSvcTufo(svcfo) for svcfo in sbus.getSynSvcs() ]

    def _onSynSvcInit(self, mesg):
        svcfo = mesg[1].get('svcfo')
        if svcfo == None:
            return

        self._addSvcTufo(svcfo)

    def _addSvcTufo(self, svcfo):
        iden = svcfo[0]

        name = svcfo[1].get('name')
        tags = svcfo[1].get('tags',())

        self.byiden[iden] = svcfo

        self.bytag.put(iden,tags)
        self.bytag.put(iden,(name,))

    def _onSynSvcFini(self, mesg):
        svcfo = mesg[1].get('svcfo')

        self.bytag.pop(svcfo[0])
        self.byiden.pop(svcfo[0],None)

    def getSynSvc(self, iden):
        '''
        Return the tufo for the specified svc iden ( or None ).

        Example:

            svcfo = svcprox.getSynSvc(iden)
            if svcfo != None:
                dostuff(svcfo)

        '''
        return self.byiden.get(iden)

    def getSynSvcs(self):
        '''
        Return the current list of known service tufos.

        Example:

            for svcfo in svcprox.getSynSvcs():
                dostuff(svcfo)

        '''
        return self.byiden.values()

    def getSynSvcsByTag(self, tag):
        '''
        Return a list of service tufos by tag.

        Example:

            for svcfo in svcprox.getSynSvcsByTag(tag):
                dostuff(svcfo)

        '''
        return [ self.byiden.get(i) for i in self.bytag.get(tag) ]

    def callByTag(self, tag, name, *args, **kwargs):
        '''
        Call a method on all services with the given tag.
        Yields (svcfo,job) tuples for the results.

        Example:

            for svcfo,job in svcprox.callByTag('foo.bar'):
                dostuff(svcfo,job)

        '''
        jobs = []

        dyntask = (name,args,kwargs)

        for iden in self.bytag.get(tag):
            job = self.sbus.callx(iden, dyntask)
            jobs.append( (iden,job) )

        for iden,job in jobs:
            # a bit hackish...
            self.sbus._waitTeleJob(job, timeout=self.timeout)
            svcfo = self.byiden.get(iden)
            yield svcfo,job

    def getTagProxy(self, tag):
        '''
        Construct and return a TagProxy to simplify callByTag use.

        Example:

            foosbars = svcprox.getTagProxy('foos.bars')

            for valu in foosbars.getBlahThing():
                dostuff(valu)

        '''
        return SvcTagProxy(self,tag)

class SvcTagProxy:
    '''
    Constructed by SvcProxy for simplifying callByTag use.
    '''
    def __init__(self, svcprox, tag):
        self.tag = tag
        self.svcprox = svcprox

    def _callSvcApi(self, name, *args, **kwargs):
        return self.svcprox.callByTag(self.tag, name, *args, **kwargs)

    def __getattr__(self, name):
        item = SvcTagMeth(self,name)
        setattr(self,name,item)
        return item

class SvcTagMeth:

    def __init__(self, tagprox, name):
        self.name = name
        self.tagprox = tagprox

    def __call__(self, *args, **kwargs):
        res = 0
        exc = None

        for name,job in self.tagprox._callSvcApi(self.name, *args, **kwargs):
            try:
                yield s_async.jobret(job)
                res += 1
            except Exception as e:
                exc = e
                #logger.warning('SvcTagMeth %s.%s: %s', name, self.name, e)

        # if they all failed, probably wanna raise... (user bug)
        if exc != None and res == 0:
            raise exc

clsskip = set([object])
def getClsNames(item):
    '''
    Return a list of "fully qualified" class names for an instance.

    Example:

        for name in getClsNames(foo):
            print(name)

    '''
    mro = inspect.getmro(item.__class__)
    mro = [ c for c in mro if c not in clsskip ]
    return [ '%s.%s' % (c.__module__,c.__name__) for c in mro ]

def runSynSvc(name, item, sbus, tags=()):
    '''
    Add an object as a synapse service.

    Example:

        woot = Woot()
        sbus = s_telepath.openurl('tcp://1.2.3.4:90/syn.svcbus')

        runSynSvc('syn.woot', woot, sbus)

    '''
    iden = guid()
    sbus.push(iden,item)

    sched = s_sched.getGlobSched()
    hostinfo = s_thishost.hostinfo

    tags = list(tags)

    names = getClsNames(item)
    tags.extend( [ 'class.%s' % n for n in names ] )

    tags.append(name)

    props = {}

    props['name'] = name
    props['tags'] = tags
    props['hostinfo'] = hostinfo

    def onTeleSock(mesg):
        if not sbus.isfini:
            sbus.iAmSynSvc(iden, props)

    def svcHeartBeat():
        if sbus.isfini:
            return

        sbus.iAmAlive(iden)
        sched.insec(30, svcHeartBeat)

    svcHeartBeat()

    sbus.on('tele:sock:init', onTeleSock)
    sbus.iAmSynSvc(iden, props)
