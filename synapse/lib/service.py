import time
import logging

logger = logging.getLogger(__name__)

import synapse.glob as s_glob
import synapse.async as s_async
import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.tags as s_tags
import synapse.lib.scope as s_scope
import synapse.lib.reflect as s_reflect
import synapse.lib.thishost as s_thishost

def openurl(url, **opts):
    '''
    Open a remote service bus and return a SvcProxy class.

    Example:

        svcprox = openbus('tcp://svcbus.com/mybus')

    '''
    svcbus = s_telepath.openurl(url, **opts)
    return SvcProxy(svcbus)

class SvcBus(s_eventbus.EventBus):

    def __init__(self):
        s_eventbus.EventBus.__init__(self)

        self.bytag = s_tags.ByTag()
        self.services = {}

        self.on('syn:svc:fini', self._onSynSvcFini)

    def _onSynSvcFini(self, mesg):
        svcfo = mesg[1].get('svcfo')
        iden = svcfo[0]
        self.bytag.pop(iden)

    def iAmSynSvc(self, iden, props):
        '''
        API used by synapse service to register with the bus.

        Example:

            sbus.iAmSynSvc('syn.blah', foo='bar', baz=10)

        '''
        props['iden'] = iden

        svcfo = (iden, props)

        sock = s_scope.get('sock')
        if sock is not None:
            def onfini():
                # MULTIPLEXOR - don't block
                def _onfini():
                    oldsvc = self.services.pop(iden, None)
                    self.bytag.pop(iden)
                    self.fire('syn:svc:fini', svcfo=oldsvc)
                s_glob.pool.call(_onfini)

            sock.onfini(onfini)

        self.services[iden] = svcfo

        tags = props.get('tags', ())

        self.bytag.put(iden, tags)

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
        if svcfo is not None:
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

        Args:
            tag (str): Tag to get services for.

        Examples:
            Get all the services with the foo.bar tag and dostuff() with the data::

                for name,props in sbus.getSynSvcsByTag('foo.bar'):
                    dostuff(name,props)

        Returns:
            list: A list of service tufos.
        '''
        return [self.services.get(i) for i in self.bytag.get(tag)]

class SvcProxy(s_eventbus.EventBus):
    '''
    A client-side helper for service dispatches.

    Mostly exists to wrap functionality for calling multiple
    services by tag.
    '''
    def __init__(self, sbus, timeout=None):
        s_eventbus.EventBus.__init__(self)

        self.byiden = {}
        self.byname = {}
        self.bytag = s_tags.ByTag()

        self.idenprox = {}
        self.nameprox = {}
        self.tagprox = {}

        self.sbus = sbus
        self.timeout = timeout

        self.onfini(self.sbus.fini)

        # FIXME set a reconnect handler for sbus
        self.sbus.on('syn:svc:init', self._onSynSvcInit)
        self.sbus.on('syn:svc:init', self.dist)

        self.sbus.on('syn:svc:fini', self._onSynSvcFini)
        self.sbus.on('syn:svc:fini', self.dist)

        [self._addSvcTufo(svcfo) for svcfo in sbus.getSynSvcs()]

    def _onSynSvcInit(self, mesg):
        svcfo = mesg[1].get('svcfo')
        if svcfo is None:
            return

        self._addSvcTufo(svcfo)

    def _addSvcTufo(self, svcfo):
        iden = svcfo[0]

        tags = svcfo[1].get('tags', ())
        name = svcfo[1].get('name', iden)

        self.byiden[iden] = svcfo
        self.byname[name] = svcfo

        self.idenprox[iden] = IdenProxy(self, svcfo)

        self.bytag.put(iden, tags)

    def _onSynSvcFini(self, mesg):
        svcfo = mesg[1].get('svcfo')

        iden = svcfo[0]
        name = svcfo[1].get('name', iden)

        self.bytag.pop(iden)
        self.idenprox.pop(iden, None)

        self.byname.pop(name, None)
        self.byiden.pop(iden, None)

    def setSynSvcTimeout(self, timeout):
        self.timeout = timeout

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
        return list(self.byiden.values())

    def getSynSvcsByTag(self, tag):
        '''
        Return a list of synapse services by hierarchical tag.

        Args:
            tag (str): Tag to get services for.

        Examples:
            Get all the services with the foo.bar tag and dostuff() with the data::

                for svcfo in svcprox.getSynSvcsByTag('foo.bar'):
                    dostuff(name,props)

        Returns:
            list: A list of service tufos.
        '''
        return [self.byiden.get(i) for i in self.bytag.get(tag)]

    def __getitem__(self, name):
        '''
        Syntax sugar to allow svcprox['foo'].getFooByBar().
        '''
        return self.getTagProxy(name)

    def callByIden(self, iden, func, *args, **kwargs):
        '''
        Call a specific object on the service bus by iden.

        Example:

            ret = svcprox.callByIden(iden,'getFooByBar',bar)

        '''
        svcfo = self.byiden.get(iden)
        if svcfo is None:
            raise s_common.NoSuchObj(iden)

        dyntask = (func, args, kwargs)
        job = self.sbus.callx(iden, dyntask)
        self.sbus._waitTeleJob(job, timeout=self.timeout)
        return s_async.jobret(job)

    def getSynSvcByName(self, name):
        return self.byname.get(name)

    def callByName(self, name, dyntask, timeout=None):
        '''
        Call a specific object on the service bus by name.

        Example:

            # dyntask tuple is (name,args,kwargs)

            dyntask = gentask('getFooByBar',bar)
            ret = svcprox.callByName('foo0', dyntask)

        '''
        if timeout is None:
            timeout = self.timeout

        svcfo = self.getSynSvcByName(name)
        if svcfo is None:
            raise s_common.NoSuchObj(name)

        job = self.sbus.callx(svcfo[0], dyntask)
        self.sbus._waitTeleJob(job, timeout=timeout)
        return s_async.jobret(job)

    def getNameProxy(self, name):
        '''
        Construct and return a SvcNameProxy to simplify callByName use.

        Example:

            foosbars = svcprox.getNameProxy('foos_bars')

            valu = foosbars.getBlahThing()
            dostuff(valu)

        '''
        prox = self.nameprox.get(name)
        if prox is None:
            prox = SvcNameProxy(self, name)
            self.nameprox[name] = prox
        return prox

    def callByTag(self, tag, dyntask, timeout=None):
        '''
        Call a method on all services with the given tag.

        Args:
            tag (str): Tag to call objects by.
            dyntask ((str, tuple, dict): A tuple containing the function name, *args and **kwargs for the task.
            timeout (int): Timeout to wait for the job to complete for, in seconds.

        Examples:
            Call getFooThing on all objects with the 'foo.bar' tag and dostuff() on the results::

                dyntask = gentask('getFooThing')
                for svcfo,retval in svcprox.callByTag('foo.bar',dyntask):
                    dostuff(svcfo,retval)

        Yields:
            tuple: Tuple containing svcfo and job results.
        '''
        jobs = []
        if timeout is None:
            timeout = self.timeout

        for iden in self.bytag.get(tag):
            job = self.sbus.callx(iden, dyntask)
            jobs.append((iden, job))

        for iden, job in jobs:
            self.sbus._waitTeleJob(job, timeout=timeout)
            svcfo = self.byiden.get(iden)
            try:
                yield svcfo, s_async.jobret(job)
            except Exception as e:
                logger.warning('callByTag (%s): %s() on %s %s', tag, dyntask[0], iden, e)

    def getTagProxy(self, tag):
        '''
        Construct and return a SvcTagProxy to simplify callByTag use.

        Example:

            foosbars = svcprox.getTagProxy('foos.bars')

            for valu in foosbars.getBlahThing():
                dostuff(valu)

        '''
        prox = self.tagprox.get(tag)
        if prox is None:
            prox = SvcTagProxy(self, tag)
            self.tagprox[tag] = prox
        return prox

    def runSynSvc(self, name, item, tags=(), **props):
        '''
        Publish an object to the service bus with the given tags.

        Example:

            foo = Foo()

            svcprox.runSynSvc('foo0', foo, tags=('foos.foo0',))

        '''
        return runSynSvc(name, item, self.sbus, tags=tags, **props)

class SvcNameProxy:
    '''
    Constructed by SvcProxy for simplifying callByName use.
    '''
    def __init__(self, svcprox, name):
        self.name = name
        self.svcprox = svcprox

    def _callSvcApi(self, name, *args, **kwargs):
        dyntask = (name, args, kwargs)
        return self.svcprox.callByName(self.name, dyntask)

    def __getattr__(self, name):
        item = SvcNameMeth(self, name)
        setattr(self, name, item)
        return item

class SvcNameMeth:

    def __init__(self, nameprox, name):
        self.name = name
        self.nameprox = nameprox

    def __call__(self, *args, **kwargs):
        return self.nameprox._callSvcApi(self.name, *args, **kwargs)

class SvcTagProxy:
    '''
    Constructed by SvcProxy for simplifying callByTag use.
    '''
    def __init__(self, svcprox, tag):
        self.tag = tag
        self.svcprox = svcprox

    def _callSvcApi(self, name, *args, **kwargs):
        dyntask = (name, args, kwargs)
        return self.svcprox.callByTag(self.tag, dyntask)

    def __getattr__(self, name):
        item = SvcTagMeth(self, name)
        setattr(self, name, item)
        return item

class SvcTagMeth:

    def __init__(self, tagprox, name):
        self.name = name
        self.tagprox = tagprox

    def __call__(self, *args, **kwargs):
        for name, ret in self.tagprox._callSvcApi(self.name, *args, **kwargs):
            yield ret

# FIXME UNIFY WITH ABOVE WHEN BACKWARD BREAK IS OK
class SvcBase:

    def __init__(self, svcprox):
        self.svcprox = svcprox

    def _callSvcMeth(self, name, *args, **kwargs):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_callSvcMethod')

    def __getattr__(self, name):
        item = SvcMeth(self, name)
        setattr(self, name, item)
        return item

class SvcMeth:

    def __init__(self, svcbase, name):
        self.name = name
        self.svcbase = svcbase

    def __call__(self, *args, **kwargs):
        return self.svcbase._callSvcMeth(self.name, *args, **kwargs)

class IdenProxy(SvcBase):

    def __init__(self, svcprox, svcfo):
        self.svcfo = svcfo
        SvcBase.__init__(self, svcprox)

    def _callSvcMeth(self, name, *args, **kwargs):
        return self.svcprox.callByIden(self.svcfo[0], name, *args, **kwargs)

def runSynSvc(name, item, sbus, tags=(), **props):
    '''
    Add an object as a synapse service.

    Args:
        name (str): Name of the service.
        item (object): Callable service object.
        sbus (s_telepath.Proxy): Telepath Proxy object pointing to a ServiceBus.
        tags:
        **props: Additional props to make available about the service.

    Examples:
        Share the woot object as a service named 'syn.woot'::

            woot = Woot()
            sbus = s_telepath.openurl('tcp://1.2.3.4:90/syn.svcbus')
            runSynSvc('syn.woot', woot, sbus)

    Returns:
        str: The iden of the instance of the service on the ServiceBus.
    '''
    iden = s_common.guid()

    sbus.push(iden, item)
    sbus.push(name, item)

    hostinfo = s_thishost.hostinfo

    tags = list(tags)

    names = s_reflect.getClsNames(item)
    tags.extend(['class.%s' % n for n in names])

    tags.append(name)

    props['name'] = name
    props['tags'] = tags
    props['hostinfo'] = hostinfo
    props['hostname'] = hostinfo.get('hostname')

    def onTeleSock(mesg):
        if not sbus.isfini:
            sbus.iAmSynSvc(iden, props)

    def svcHeartBeat():
        if sbus.isfini:
            return

        sbus.call('iAmAlive', iden)
        s_glob.sched.insec(30, svcHeartBeat)

    svcHeartBeat()

    sbus.on('tele:sock:init', onTeleSock)
    sbus.iAmSynSvc(iden, props)

    return iden
