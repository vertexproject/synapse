import time
import logging

logger = logging.getLogger(__name__)

import synapse.async as s_async
import synapse.aspects as s_aspects
import synapse.eventbus as s_eventbus

import synapse.lib.sched as s_sched
import synapse.lib.thishost as s_thishost

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

    def iAmSynSvc(self, name, **props):
        '''
        API used by synapse service to register with the bus.

        Example:

            sbus.iAmSynSvc('syn.blah', foo='bar', baz=10)

        '''
        oldp = self.services.pop(name,None)
        if oldp != None:
            self.fire('syn:svc:fini', name=name, props=oldp)
            
        self.services[name] = props
        self.bytag.put(name,(name,))
        self.bytag.put(name,props.get('tags',()))

        self.fire('syn:svc:init', name=name, props=props)

    def iAmAlive(self, name):
        '''
        "heartbeat" API for services.

        Example:

            sbus.iAmAlive('syn.blah')

        Notes:

            This API is generally called by a scheduled loop
            within the service object.
        '''
        props = self.services.get(name)
        if props == None:
            return

        props['checkin'] = int(time.time())

    def getSynSvcs(self):
        '''
        Retrieve a list of the services on the service bus.

        Example:

            for name,info in sbus.getSynSvcs():
                dostuff(name,info)

        '''
        return list(self.services.items())

    def getSynSvcsByTag(self, tag):
        '''
        Return a list of synapse services by hierarchical tag.

        Example:

            for name,props in sbus.getSynSvcsByTag('foo.bar'):
                dostuff(name,props)

        '''
        names = self.bytag.get(tag)
        return [ (name,self.services.get(name)) for name in names ]

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

        [ self._addSvcName(n,p.get('tags',())) for (n,p) in sbus.getSynSvcs() ]

    def _onSynSvcInit(self, mesg):
        name = mesg[1].get('name')
        props = mesg[1].get('props')

        self._addSvcName(name,props.get('tags',()))

    def _addSvcName(self, name, tags):
        self.bytag.put(name,tags)
        self.bytag.put(name,(name,))

    def _onSynSvcFini(self, mesg):
        name = mesg[1].get('name')
        self.bytag.pop(name)

    def callByTag(self, tag, name, *args, **kwargs):
        '''
        Call a method on all services with the given tag.
        Yields (svcname,job) tuples for the results.

        Example:

            for svc,job in svc.callByTag('foo.bar'):
                dostuff(svc,job)

        '''
        jobs = []

        dyntask = (name,args,kwargs)

        for svcname in self.bytag.get(tag):
            job = self.sbus.callx(svcname, dyntask)
            jobs.append( (svcname,job) )

        for svcname,job in jobs:
            # a bit hackish...
            self.sbus._waitTeleJob(job, timeout=self.timeout)
            yield svcname,job

    def getTagProxy(self, tag):
        '''
        Construct and return a TagProxy to simplify callByTag use.

        Example:

            foosbars = svc.getTagProxy('foos.bars')

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

def runSynSvc(name, item, sbus, tags=()):
    '''
    Add an object as a synapse service.

    Example:

        woot = Woot()
        sbus = s_telepath.openurl('tcp://1.2.3.4:90/syn.svcbus')

        runSynSvc('syn.woot', woot, sbus)

    '''
    sbus.push(name,item)

    sched = s_sched.getGlobSched()
    hostinfo = s_thishost.hostinfo

    def onTeleSock(mesg):
        if not sbus.isfini:
            sbus.iAmSynSvc(name, hostinfo=hostinfo, tags=tags)

    def svcHeartBeat():
        if sbus.isfini:
            return

        sbus.iAmAlive(name)
        sched.insec(30, svcHeartBeat)

    svcHeartBeat()

    sbus.on('tele:sock:init', onTeleSock)
    sbus.iAmSynSvc(name, hostinfo=hostinfo, tags=tags)
