import logging
import traceback
import collections

logger = logging.getLogger(__name__)

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

    def __init__(self, core=None, pool=None):
        EventBus.__init__(self)

        if core == None:
            core = s_cortex.openurl('ram:///')

        self.socks = {}
        self.shared = {}

        if pool == None:
            pool = s_threads.Pool(size=8, maxsize=-1)

        self.pool = pool
        self.core = core
        self.plex = s_socket.Plex()
        self.cura = s_session.Curator(core=core)

        self.onfini( self.plex.fini )
        self.onfini( self.cura.fini )
        self.onfini( self.pool.fini )

        self.plex.on('link:sock:mesg', self._onLinkSockMesg )

        self.mesgfuncs = {}

        self.setMesgFunc('tele:syn', self._onTeleSynMesg )
        self.setMesgFunc('tele:fin', self._onTeleFinMesg )
        self.setMesgFunc('tele:call', self._onTeleCallMesg )

    def setMesgFunc(self, name, func):
        self.mesgfuncs[name] = func

    def _onLinkSockInit(self, event):

        sock = event[1].get('sock')
        sock.on('link:sock:mesg', self._onLinkSockMesg )

        self.plex.addPlexSock(sock)

    def _onLinkSockMesg(self, event):
        # THIS MUST NOT BLOCK THE MULTIPLEXOR!
        #print('ON LINK SOCK MESG: %r' % (event,))
        self.pool.call( self._runLinkSockMesg, event )

    def _runLinkSockMesg(self, event):
        sock = event[1].get('sock')
        mesg = event[1].get('mesg')

        func = self.mesgfuncs.get(mesg[0])
        if func == None:
            return

        try:

            func(sock,mesg)

        except Exception as e:
            traceback.print_exc()
            logger.error('_runLinkSockMesg: %s', e )

    def _onTeleFinMesg(self, sock, mesg):
        # if the client is nice enough to notify us...
        sid = mesg[1].get('sid')
        sess = self.cura.getSessBySid(sid)
        if sess == None:
            return

        sess.fini()

    def _onTeleSynMesg(self, sock, mesg):

        jid = mesg[1].get('jid')
        sid = mesg[1].get('sid')
        if sid == None:
            sid = self.cura.getNewSess().sid

        with self.cura.getSessBySid(sid) as sess:
            sess.setSessSock(sock)
            sess.relay( tufo('job:done', jid=jid, ret=sess.sid) )

    def _onTeleCallMesg(self, sock, mesg):

        jid = mesg[1].get('jid')
        sid = mesg[1].get('sid')

        with self.cura.getSessBySid(sid) as sess:

            try:

                name = mesg[1].get('name')

                item = self.shared.get(name)
                if item == None:
                    raise NoSuchObj(name)

                task = mesg[1].get('task')
                meth,args,kwargs = task

                func = getattr(item,meth,None)
                if func == None:
                    raise NoSuchMeth(meth)

                ret = func(*args,**kwargs)

                sock.tx( tufo('job:done', jid=jid, ret=ret) )

            except Exception as e:
                sock.tx( tufo('job:done', jid=jid, **excinfo(e)) )

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
        sock.on('link:sock:init', self._onLinkSockInit )

        self.plex.addPlexSock(sock)

        return link

    def share(self, name, obj):
        '''
        Share an object via the telepath protocol.
        '''
        self.shared[name] = obj
