import time

import synapse.eventbus as s_eventbus

import synapse.lib.sched as s_sched
import synapse.lib.thishost as s_thishost

class SvcBus(s_eventbus.EventBus):

    def __init__(self):
        s_eventbus.EventBus.__init__(self)
        self.services = {}

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

def runSynSvc(name, item, sbus):
    '''
    Add an object as a synapse service.

    Example:

        woot = Woot()
        sbus = s_telepath.openurl('tcp://1.2.3.4:90/syn.svcbus')

        runSynSvc('syn.woot', woot, sbus)

    '''
    sbus.push(name,item)

    sched = s_sched.getGlobSched()

    def onTeleSock(mesg):
        if not sbus.isfini:
            sbus.iAmSynSvc(name,**s_thishost.hostinfo)

    def svcHeartBeat():
        if sbus.isfini:
            return

        sbus.iAmAlive(name)
        sched.insec(30, svcHeartBeat)

    svcHeartBeat()

    sbus.on('tele:sock:init', onTeleSock)
    sbus.iAmSynSvc(name,**s_thishost.hostinfo)
