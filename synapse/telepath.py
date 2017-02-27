'''
An RMI framework for synapse.
'''
import copy
import time
import zlib
import getpass
import threading
import threading
import traceback
import collections

import synapse.link as s_link
import synapse.async as s_async

from synapse.utils import importOptionalModule
s_crypto = importOptionalModule('synapse.crypto')

import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus

import synapse.lib.queue as s_queue
import synapse.lib.sched as s_sched
import synapse.lib.socket as s_socket
import synapse.lib.threads as s_threads

from synapse.common import *
from synapse.compat import queue

# telepath protocol version
# ( compat breaks only at major ver )
telever = (1,0)

def openurl(url,**opts):
    '''
    Construct a telepath proxy from a url.

    Example:

        foo = openurl('tcp://1.2.3.4:90/foo')

        foo.dostuff(30) # call remote method

    '''
    plex = opts.pop('plex',None)
    return openclass(Proxy,url,**opts)

def openclass(cls, url, **opts):
    plex = opts.pop('plex',None)

    link = s_link.chopLinkUrl(url)
    link[1].update(opts)

    relay = s_link.getLinkRelay(link)
    return cls(relay, plex=plex)

def openlink(link):
    '''
    Construct a telepath proxy from a link tufo.

    Example:

        foo = openlink(link)
        foo.bar(20)

    '''
    relay = s_link.getLinkRelay(link)
    return Proxy(relay)

def evalurl(url,**opts):
    '''
    Construct either a local object or a telepath proxy.

    WARNING: this API enables ctor:// proto which uses eval!
             ( trusted inputs only )

    Example:

        item0 = evalurl('tcp://1.2.3.4:90/foo')
        item1 = evalurl('ctor://foo.bar.baz("woot",y=20)')

    '''
    if url.find('://') == -1:
        raise BadUrl(url)

    scheme,therest = url.split('://',1)
    if scheme == 'ctor':
        locs = opts.get('locs')
        return s_dyndeps.runDynEval(therest, locs=locs)

    return openurl(url,**opts)

class Method:

    def __init__(self, proxy, meth):
        self.meth = meth
        self.proxy = proxy

    def __call__(self, *args, **kwargs):
        ondone = kwargs.pop('ondone',None)
        task = (self.meth,args,kwargs)
        job = self.proxy._tx_call( task, ondone=ondone )
        if ondone != None:
            return job

        return self.proxy.syncjob(job)

telelocal = set(['tele:sock:init'])

class Proxy(s_eventbus.EventBus):
    '''
    The telepath proxy provides "pythonic" access to remote objects.

    ( you most likely want openurl() or openlink() )

    NOTE:

        *all* locals in this class *must* have _tele_ prefixes to prevent
        accidental deref of something with the same name in code using it
        under the assumption it's something else....

    '''
    def __init__(self, relay, plex=None):

        s_eventbus.EventBus.__init__(self)
        self.onfini( self._onProxyFini )

        # NOTE: the _tele_ prefixes are designed to prevent accidental
        #       derefs with overlapping names from working correctly

        self._tele_sid = None

        self._tele_q = s_queue.Queue()
        self._tele_pushed = {}

        if plex == None:
            plex = s_socket.Plex()

        self._tele_plex = plex
        self._tele_boss = s_async.Boss()

        self._raw_on('tele:yield:init', self._onTeleYieldInit )
        self._raw_on('tele:yield:item', self._onTeleYieldItem )
        self._raw_on('tele:yield:fini', self._onTeleYieldFini )

        self._raw_on('job:done', self._tele_boss.dist )
        self._raw_on('sock:gzip', self._onSockGzip )
        self._raw_on('tele:call', self._onTeleCall )

        poolmax = relay.getLinkProp('poolmax', -1)
        poolsize = relay.getLinkProp('poolsize', 0)

        self._tele_cthr = self.consume( self._tele_q )
        self._tele_pool = s_threads.Pool(size=poolsize, maxsize=poolmax)

        self._tele_ons = {}

        self._tele_sock = None
        self._tele_relay = relay    # LinkRelay()
        self._tele_link = relay.link
        self._tele_yields = {}

        # obj name is path minus leading "/"
        self._tele_name = relay.link[1].get('path')[1:]

        self._initTeleSock()

    def _onTeleYieldInit(self, mesg):
        jid = mesg[1].get('jid')
        iden = mesg[1].get('iden')

        que = s_queue.Queue()
        self._tele_yields[iden] = que

        def onfini():
            self._tele_yields.pop(iden,None)
            self._txTeleSock('tele:yield:fini', iden=iden)

        que.onfini(onfini)
        self._tele_boss.done(jid,que)

    def _onTeleYieldItem(self, mesg):
        iden = mesg[1].get('iden')
        que = self._tele_yields.get(iden)
        if que == None:
            self._txTeleSock('tele:yield:fini', iden=iden)
            return

        que.put( mesg[1].get('item') )

    def _onTeleYieldFini(self, mesg):
        iden = mesg[1].get('iden')
        que = self._tele_yields.get(iden)
        if que != None:
            que.done()

    def _raw_on(self, name, func):
        return s_eventbus.EventBus.on(self, name, func)

    def _raw_off(self, name, func):
        return s_eventbus.EventBus.off(self, name, func)

    def on(self, name, func):

        if name not in telelocal:

            refc = self._tele_ons.get(name)
            if refc == None:
                job = self._txTeleJob('tele:on', events=[name], name=self._tele_name)
                self.syncjob(job)

                refc = 0

            self._tele_ons[name] = refc + 1

        return s_eventbus.EventBus.on(self, name, func)

    def off(self, name, func):

        ret = s_eventbus.EventBus.off(self, name, func)

        if name not in telelocal:
            refc = self._tele_ons.get(name)
            if refc != None:
                refc -= 1
                if refc == 0:
                    self._tele_ons.pop(name,None)
                    job = self._txTeleJob('tele:off', evt=name, name=self._tele_name)
                    self.syncjob(job)

                else:
                    self._tele_ons[name] = refc

        return ret

        job = self._txTeleJob('tele:off', evt=name, name=self._tele_name)
        self.syncjob(job)

    def fire(self, name, **info):
        if name in telelocal:
            return s_eventbus.EventBus.fire(self, name, **info)

        # events fired on a proxy go through the remove first...
        job = self.call('fire', name, **info)
        return self.syncjob(job)

    def call(self, name, *args, **kwargs):
        '''
        Call a shared method as a job.

        Example:

            job = proxy.call('getFooByBar',bar)

            # ... do other stuff ...

            ret = proxy.syncjob(job)

        '''
        ondone = kwargs.pop('ondone',None)

        task = (name, args, kwargs)
        return self._tx_call(task,ondone=ondone)

    def callx(self, name, task, ondone=None):
        '''
        Call a method on a specific shared object as a job.

        Example:

            # task is (<method>,<args>,<kwargs>)
            task = ('getFooByBar', (bar,), {} )

            job = proxy.callx('woot',task)
            ret = proxy.syncjob(job)

        '''
        return self._txTeleJob('tele:call', name=name, task=task, ondone=ondone)

    def push(self, name, item):
        '''
        Push access to an object to the daemon, allowing other clients access.

        Example:

            prox = s_telepath.openurl('tcp://127.0.0.1/')
            prox.push( 'bar', Bar() )

        '''
        job = self._txTeleJob('tele:push', name=name)
        self._tele_pushed[ name ] = item
        return self.syncjob(job)

    def _tx_call(self, task, ondone=None):
        return self._txTeleJob('tele:call', name=self._tele_name, task=task, ondone=ondone)

    def syncjob(self, job, timeout=None):
        '''
        Wait on a given job and return/raise it's result.

        Example:

            job = proxy.call('woot', 10, bar=20)
            ret = proxy.syncjob(job)

        '''
        self._waitTeleJob(job,timeout=timeout)
        return s_async.jobret(job)

    def _waitTeleJob(self, job, timeout=None):
        # dont block the consumer thread, consume events
        # until the job completes...
        if threading.currentThread() == self._tele_cthr:
            return self._fakeConsWait(job, timeout=timeout)

        if not self._tele_boss.wait(job[0], timeout=timeout):
            raise HitMaxTime()

    def _fakeConsWait(self, job, timeout=None):
        # a wait like function for the consumer thread
        # which continues to consume events until a job
        # has been completed.
        maxtime = None
        if timeout != None:
            maxtime = time.time() + timeout

        while not job[1].get('done'):

            if maxtime != None and time.time() >= maxtime:
                raise HitMaxTime()

            mesg = self._tele_q.get()
            self.dist(mesg)

    def _initTeleSock(self, loop=False):

        self._tele_sock = None
        while self._tele_sock == None:

            try:
                self._tele_sock = self._tele_relay.connect()

            except LinkErr as e:
                if not e.retry or not loop:
                    raise

                time.sleep(1)

        # generated on the socket by the multiplexor ( and queued )
        self._tele_sock.on('link:sock:mesg', self._onLinkSockMesg )

        def sockfini():
            # called by multiplexor... must not block
            if not self.isfini:
                self._tele_pool.call( self._runSockFini )

        self._tele_sock.onfini( sockfini )

        self._tele_plex.addPlexSock(self._tele_sock)

        self._teleSynAck()

        # let client code do stuff on reconnect
        self.fire('tele:sock:init', sock=self._tele_sock)

    def _onLinkSockMesg(self, event):
        # MULTIPLEXOR: DO NOT BLOCK
        mesg = event[1].get('mesg')
        self._tele_q.put( mesg )

    #def _onSockFini(self):
        ## This is called by the SynPlexMain thread and may *not* block.
        #if self.isfini:
            #return

        #self._tele_pool.call( self._runSockFini )

    def _runSockFini(self):
        if self.isfini:
            return

        try:
            self._initTeleSock()
        except LinkErr as e:
            sched = s_sched.getGlobSched()
            sched.insec(1, self._runSockFini )

    def _onTeleCall(self, mesg):
        # dont block consumer thread... task pool
        self._tele_pool.call( self._runTeleCall, mesg )

    def _onSockGzip(self, mesg):
        data = zlib.decompress( mesg[1].get('data') )
        self.dist( msgunpack(data) )

    def _runTeleCall(self, mesg):

        jid = mesg[1].get('jid')
        name = mesg[1].get('name')
        task = mesg[1].get('task')
        suid = mesg[1].get('suid')

        retinfo = dict(suid=suid,jid=jid)

        try:

            item = self._tele_pushed.get(name)
            if item == None:
                return self._txTeleSock('tele:retn', err='NoSuchObj', errmsg=name, **retinfo)

            meth,args,kwargs = task
            func = getattr(item,meth,None)
            if func == None:
                return self._txTeleSock('tele:retn', err='NoSuchMeth', errmsg=meth, **retinfo)

            self._txTeleSock('tele:retn', ret=func(*args,**kwargs), **retinfo )

        except Exception as e:
            retinfo.update( excinfo(e) )
            return self._txTeleSock('tele:retn', **retinfo)

    def _getTeleSock(self):
        if self.isfini:
            raise IsFini()

        return self._tele_sock

    def _teleSynAck(self):
        '''
        Send a tele:syn to get a telepath session
        '''
        opts = {'sock:can:gzip':1}

        job = self._txTeleJob('tele:syn', sid=self._tele_sid, vers=telever, opts=opts)

        synresp = self.syncjob(job, timeout=6)

        vers = synresp.get('vers',(0,0))
        if vers[0] != telever[0]:
            raise BadMesgVers(myver=telever,hisver=vers)

        self._tele_sid = synresp.get('sess')

        hisopts = synresp.get('opts',{})

        sock = self._getTeleSock()

        if hisopts.get('sock:can:gzip'):
            sock.set('sock:can:gzip',True)

        events = list(self._tele_ons.keys())

        if events:
            job = self._txTeleJob('tele:on', events=events, name=self._tele_name)
            self.syncjob( job )

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
        if sock != None:
            sock.tx( (msg,msginfo) )

    def _onProxyFini(self):

        [ que.fini() for que in self._tele_yields.values() ]

        if self._tele_sock != None:
            self._tele_sock.fini()

        self._tele_boss.fini()
        self._tele_pool.fini()

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

