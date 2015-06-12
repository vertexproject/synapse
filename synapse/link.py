import time
import importlib

import synapse.threads as s_threads

from synapse.dispatch import Dispatcher
from synapse.statemach import StateMachine, keepstate

linktypes = {
    'tcp':'synapse.links.tcp',
    'tcpd':'synapse.links.tcpd',
    'local':'synapse.links.local',
    'locald':'synapse.links.locald',
}

class DupLink(Exception):pass
class NoSuchLink(Exception):pass
class NoSuchLinkType(Exception):pass

class BadLinkInfo(Exception):pass
class NoLinkProp(BadLinkInfo):pass
class BadLinkProp(BadLinkInfo):pass

class Linker(Dispatcher,StateMachine):
    '''
    A Linker is a mixin object for managing both persistant
    and non-persistant link configuration states.

    A "link" is a tuple of (linktype,linkinfo).

    '''
    def __init__(self, statefd=None):
        Dispatcher.__init__(self)
        self.synOn('fini',self._finiLinker)

        self.links = {}
        self.linkmods = {}
        self.linksocks = {}
        self.linkrun = False

        StateMachine.__init__(self, statefd=statefd)

    def runLinkMain(self):
        '''
        Fire off the link managers to run and maintain links.

        Example:

            linker.runLinkMain()

        Notes:

            * One *must* call this API to begin link management

        '''
        self.linkrun = True
        for link in self.links.values():
            self.runLink(link)

        self.synFire('linkrun')

    def getLinkModule(self, linktype):
        '''
        Retrieve the link module to handle a given link type.

        Example:

            mod = linker.getLinkModule('tcp')
            if mod != None:
                print('the linker knows how to speak tcp!')

        '''
        mod = self.linkmods.get(linktype)
        if mod != None:
            return mod

        name = linktypes.get(linktype)
        if name == None:
            return None

        mod = importlib.import_module(name)
        self.linkmods[linktype] = mod
        return mod

    def setLinkModule(self, linktype, mod):
        '''
        Override or add a link module type.

        Example:

            class MyLinkMod:

                def reqValidLink(self, link):
                    # do validation or raise

                def initLinkSock(self, link):
                    #return Socket() or None

            mod = MyLinkMod()
            linker.setLinkModule('woot',mod)

        '''
        self.linkmods[linktype] = mod

    def getLinkInfo(self, name, prop):
        '''
        Retrieve a property about a link by name.

        Example:

            port = linker.getLinkInfo('woot1','port')

        '''
        link = self.links.get(name)
        if link == None:
            raise NoSuchLink(name)

        return link[1].get(prop)

    @keepstate
    def setLinkInfo(self, name, prop, valu):
        '''
        Set a property about a link by name.

        Example:

            linker.setLinkInfo('woot1','foo',30)

        Notes:

            * This info *will* persist via StateMachine.

        '''
        link = self.links.get(name)
        if link == None:
            raise NoSuchLink(name)

        link[1][prop] = valu
        return link

    @keepstate
    def addLink(self, name, link):
        '''
        Add a link descriptor to be managed by this linker.

        Example:

            link = ('tcp',{'host':'1.2.3.4','port':80})
            linker.addLink('wootwoot',link)

        Notes:

            * If a StateMachine statefd is in use, this change will
              persist across restarts.  Use firePoolLink() for
              non-persistent link addition.

        '''
        if self.links.get(name) != None:
            DupLink(name)

        # a touch of magic to avoid these checks during load
        if self.statefd != None:
            self.checkLinkInfo(link)

        self.links[name] = link

        # If we're already running, run this one right away...
        if self.linkrun:
            self.runLink(link)

    def checkLinkInfo(self, link):
        '''
        Validate the link configuration or raise.

        Example:

            linker.checkLinkInfo(link)

        '''
        mod = self.getLinkModule( link[0] )
        if mod == None:
            NoSuchLinkType(link[0])

        mod.reqValidLink(link)

    def runLink(self, link):
        '''
        Run and manage a new link.

        Example:

            link = ('tcp',{'host':'1.2.3.4','port':80})
            linker.runLink(link)

        Notes:

            * This method does *not* update StateMachine.

        '''
        self.checkLinkInfo(link)
        s_threads.worker( self._runLinkThread, link )

    def _runLinkThread(self, link):
        '''
        A thread routine to attempt to establish a link sock.
        Once established, the sock is dispatched with

        synFire('linksock',sock)

        and configured to fire runLink again on close unless
        the Linker is being shut down...
        '''
        mod = self.getLinkModule(link[0])

        delay = 0
        while not self.isfini:
            sock = mod.initLinkSock(link)
            if sock != None:
                sid = sock.getSockId()
                sock.setSockInfo('link',link)
                self.linksocks[sid] = sock
                def runagain():
                    self.linksocks.pop(sid,None)
                    if not self.isfini:
                        self.runLink(link)

                sock.synOn('fini',runagain)
                self.synFire('linksock',sock)
                return

            time.sleep(delay)

            delayinc = link[1].get('delayinc',0.1)
            delaymax = link[1].get('delaymax',1)
            delay = min( delay + delayinc, delaymax )

    def _finiLinker(self):
        for sock in list(self.linksocks.values()):
            sock.close()

