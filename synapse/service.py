
from synapse.eventbus import EventBus

class ImplementMe(Exception):pass

class Service(EventBus):
    '''
    A synapse Service defines a synapse message protocol.

    Each sense may be added to one or more Daemon instances
    to provide access via the Daemon's managed LinkRelays.
    '''
    def __init__(self, daemon):
        EventBus.__init__(self)
        self.daemon = daemon
        self.mesgmeths = {}
        self.initServiceLocals()

    def initServiceLocals():
        raise ImplementMe()

    def getInfo(self, prop):
        '''
        Retreive a persistent property by name.

        Example:

            woot = sense.getInfo('woot')

        '''
        return self.sense[1].get(prop)

    def setInfo(self, prop, valu):
        '''
        Set persistent property by name.

        Example:

            sense.setInfo('woot',10)

        '''
        return self.daemon.setSenseInfo(self.sense[0], prop, valu)


    def setMesgMethod(self, name, meth):
        '''
        Add a message handler method to the Service.

        Example:

            wootmesg(sock,mesg):
                stuff()

            sensor.setMesgMethod('woot',wootmesg)

        '''
        self.mesgmeths[name] = meth

    def getMesgMethods(self):
        '''
        Return a list of (name,meth) message handlers.

            for name,meth in sense.getMesgMethods():
                stuff()

        Notes:

            * Mostly for use by the Daemon during construction.
        '''
        return self.mesgmeths.items()
