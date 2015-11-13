import traceback
import collections

import synapse.link as s_link
import synapse.socket as s_socket
import synapse.threads as s_threads

import synapse.cortex as s_cortex
import synapse.impulse as s_impulse
import synapse.reactor as s_reactor
import synapse.session as s_session

from synapse.eventbus import EventBus

from synapse.common import *

class Daemon(EventBus):

    def __init__(self, core=None, boss=None):
        EventBus.__init__(self)

        if core == None:
            core = s_cortex.openurl('ram:///')

        self.shared = {}

        self.rtor = s_reactor.Reactor()
        self.pool = s_threads.Pool(maxsize=-1)
        self.cura = s_session.Curator(core=core)

        self.onfini( self.cura.fini )
        self.onfini( self.pool.fini )

        self.rtor.act('tele:syn', self._actTeleSyn )
        self.rtor.act('tele:call', self._actTeleCall )

    def _runSockMesg(self, sock, mesg):

        try:
            ret = self.rtor.react(mesg)
            sock.fireobj(mesg[0] + ':ret', ret=ret)

        except Exception as e:
            sock.fireobj(mesg[0] + ':ret', **excinfo(e))

    def _reqSessFromMesg(self, mesg):
        sid = mesg[1].get('sid')
        if sid == None:
            return self.cura.getNewSess()

        return self.cura.getSessBySid(sid)

    def _actTeleSyn(self, mesg):
        # are they giving us an existing sid?
        with self._reqSessFromMesg(mesg) as sess:
            return sess.sid

    ###################################################

    def _actTeleCall(self, mesg):

        name,api,args,kwargs = mesg[1].get('call')

        # FIXME sess allows?

        obj = self.shared.get(name)
        if obj == None:
            raise NoSuchObj(name)

        meth = getattr(obj,api,None)
        if meth == None:
            raise NoSuchMeth(api)

        # FIXME rate limit?
        # FIXME audit trail?

        with self._reqSessFromMesg(mesg):
            return meth(*args,**kwargs)

    def listen(self, linkurl):
        '''
        Create and run a link server by url.

        Example:

            link = dmon.listen('tcp://127.0.0.1:8888')

        Notes:

            * Returns the parsed link tufo

        '''
        link = s_link.chopLinkUrl(linkurl)
        relay = s_link.getLinkRelay(link)

        sock = relay.listen()
        self.pool.call(self._runServSock,sock)
        return link

    def share(self, name, obj):
        '''
        Share an object via the telepath protocol.
        '''
        self.shared[name] = obj

    def _runServSock(self, sock):
        relay = sock.get('relay')

        sockblock = s_threads.cancelable(sock.fini)
        while not self.isfini:
            with sockblock:
                news,addr = sock.accept()
                if news == None:
                    break

                if relay != None:
                    relay._prepLinkSock(news)

                self.pool.call( self._runServConn, news )

    def _runServConn(self, sock):
        self.fire('link:sock:init', sock=sock)

        with s_threads.cancelable(sock.fini):
            for mesg in sock:
                self._runSockMesg(sock,mesg)

        self.fire('link:sock:fini', sock=sock)

