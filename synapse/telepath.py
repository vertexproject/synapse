'''
An RMI framework for synapse.
'''
import copy
import threading
import threading
import traceback

import synapse.link as s_link
import synapse.async as s_async
import synapse.lib.queue as s_queue
import synapse.lib.socket as s_socket
import synapse.eventbus as s_eventbus

from synapse.common import *
from synapse.compat import queue

def openurl(url,**opts):
    '''
    Construct a telepath proxy from a url.

    Example:

        foo = openurl('tcp://1.2.3.4:90/foo')

        foo.dostuff(30) # call remote method

    '''
    link = s_link.chopLinkUrl(url)
    link[1].update(opts)

    relay = s_link.getLinkRelay(link)
    return Proxy(relay)

def openlink(link):
    '''
    Construct a telepath proxy from a link tufo.

    Example:

        foo = openlink(link)
        foo.bar(20)

    '''
    relay = s_link.getLinkRelay(link)
    return Proxy(relay)

class Method:

    def __init__(self, proxy, meth):
        self.meth = meth
        self.proxy = proxy

    def __call__(self, *args, **kwargs):
        task = (self.meth,args,kwargs)
        job = self.proxy._tx_call( task )
        return self.proxy.sync(job)

class Proxy(s_eventbus.EventBus):
    '''
    The telepath proxy provides "pythonic" access to remote objects.

    ( you most likely want openurl() or openlink() )

    NOTE:

        *all* locals in this class *must* have _tele_ prefixes to prevent
        accidental deref of something with the same name in code using it
        under the assumption it's something else....

    '''
    def __init__(self, relay):

        s_eventbus.EventBus.__init__(self)
        self.onfini( self._onProxyFini )

        # NOTE: the _tele_ prefixes are designed to prevent accidental
        #       derefs with overlapping names from working correctly

        self._tele_sid = None

        self._tele_q = s_queue.Queue()
        self._tele_bus = s_eventbus.EventBus()

        self._tele_boss = s_async.Boss()
        self._tele_plex = s_socket.getGlobPlex()

        self._tele_bus.on('job:done', self._tele_boss.dist )
        self._tele_bus.on('imp:dist', self._onImpDist )

        self._tele_bus.consume( self._tele_q )

        self._tele_sock = None
        self._tele_relay = relay    # LinkRelay()

        # obj name is path minus leading "/"
        self._tele_name = relay.link[1].get('path')[1:]

        self._initTeleSock()

    def call(self, name, *args, **kwargs):
        '''
        Call a shared method as a job.

        Example:

            job = proxy.call('getFooByBar',bar)

            # ... do other stuff ...

            ret = proxy.sync(job)

        '''
        ondone = kwargs.pop('ondone',None)

        task = (name, args, kwargs)
        return self._tx_call(task,ondone=ondone)

    def _tx_call(self, task, ondone=None):
        return self._txTeleJob('tele:call', name=self._tele_name, task=task, ondone=ondone)

    def sync(self, job, timeout=None):
        '''
        Wait on a given job and return/raise it's result.

        Example:

            ret = proxy.sync(job)

        '''
        # wait for job and jobret()
        if self._tele_boss.wait(job[0], timeout=timeout):
            return s_async.jobret(job)

        raise HitMaxTime()

    def _onImpDist(self, event):
        mesg = event[1].get('mesg')
        self.dist(mesg)

    def _initTeleSock(self):
        if self._tele_bus.isfini:
            return False

        if self._tele_sock != None:
            self._tele_sock.fini()

        self._tele_sock = self._tele_relay.connect()
        if self._tele_sock == None:
            return False

        # generated on the socket by the multiplexor ( and queued )
        self._tele_sock.on('link:sock:mesg', self._onLinkSockMesg )

        self._tele_sock.onfini( self._onSockFini )

        self._tele_plex.addPlexSock( self._tele_sock )

        self._teleSynAck()
        return True

    def _onLinkSockMesg(self, event):
        # MULTIPLEXOR: DO NOT BLOCK
        mesg = event[1].get('mesg')
        self._tele_q.put( mesg )

    def _onSockFini(self):
        # If we still have outstanding jobs, reconnect immediately
        if self._tele_bus.isfini:
            return

        if len( self._tele_boss.jobs() ):
            self._initTeleSock()

    def _getTeleSock(self):
        if self._tele_sock.isfini:
            self._initTeleSock()

        return self._tele_sock

    def _teleSynAck(self):
        '''
        Send a tele:syn to get a telepath session
        '''
        job = self._txTeleJob('tele:syn', sid=self._tele_sid )
        self._tele_sid = self.sync( job )

    def _txTeleJob(self, msg, **msginfo):
        '''
        Transmit a message as a job ( add jid to mesg ) and return job.
        '''
        ondone = msginfo.pop('ondone',None)
        job = self._tele_boss.initJob(ondone=ondone)

        msginfo['jid'] = job[0]
        self._txTeleSock(msg,**msginfo)

        return job

    def _txTeleSock(self, msg, **msginfo):
        '''
        Send a mesg over the socket and include our session id.
        '''
        msginfo['sid'] = self._tele_sid
        sock = self._getTeleSock()
        sock.tx( (msg,msginfo) )

    def _onProxyFini(self):

        if not self._tele_sock.isfini:
            self._tele_sock.tx( tufo('tele:fin', sid=self._tele_sid) )

        self._tele_bus.fini()
        self._tele_boss.fini()
        self._tele_sock.fini()

    def __getattr__(self, name):
        meth = Method(self, name)
        setattr(self,name,meth)
        return meth

    # some methods to avoid round trips...
    def __nonzero__(self):
        return True

    def __eq__(self, obj):
        return id(self) == id(obj)

    def __ne__(self, obj):
        return not self.__eq__(obj)

