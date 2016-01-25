'''
An RMI framework for synapse.
'''
import copy
import getpass
import threading
import threading
import traceback

import synapse.link as s_link
import synapse.async as s_async
import synapse.crypto as s_crypto
import synapse.eventbus as s_eventbus

import synapse.lib.pki as s_pki
import synapse.lib.queue as s_queue
import synapse.lib.socket as s_socket
import synapse.lib.threads as s_threads

from synapse.common import *
from synapse.compat import queue

def openurl(url,**opts):
    '''
    Construct a telepath proxy from a url.

    Example:

        foo = openurl('tcp://1.2.3.4:90/foo')

        foo.dostuff(30) # call remote method

    '''
    plex = opts.pop('plex',None)

    link = s_link.chopLinkUrl(url)
    link[1].update(opts)

    relay = s_link.getLinkRelay(link)
    return Proxy(relay, plex=plex)

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
        ondone = kwargs.pop('ondone',None)
        task = (self.meth,args,kwargs)
        job = self.proxy._tx_call( task, ondone=ondone )
        if ondone != None:
            return job

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
    def __init__(self, relay, plex=None):

        s_eventbus.EventBus.__init__(self)
        self.onfini( self._onProxyFini )

        # NOTE: the _tele_ prefixes are designed to prevent accidental
        #       derefs with overlapping names from working correctly

        self._tele_sid = None
        self._tele_pki = None

        self._tele_q = s_queue.Queue()
        self._tele_pushed = {}

        if plex == None:
            plex = s_socket.Plex()

        self._tele_plex = plex
        self._tele_boss = s_async.Boss()

        self._raw_on('job:done', self._tele_boss.dist )
        self._raw_on('tele:call', self._onTeleCall )

        poolmax = relay.getLinkProp('poolmax', -1)
        poolsize = relay.getLinkProp('poolsize', 0)

        self._tele_cthr = self.consume( self._tele_q )
        self._tele_pool = s_threads.Pool(size=poolsize, maxsize=poolmax)

        self._tele_ons = set()
        self._tele_sock = None
        self._tele_relay = relay    # LinkRelay()

        # obj name is path minus leading "/"
        self._tele_name = relay.link[1].get('path')[1:]

        if relay.getLinkProp('pki'):

            #TODO pkiurl

            self._tele_pki = relay.getLinkProp('pkistor')
            if self._tele_pki == None:
                self._tele_pki = s_pki.getUserPki()

        self._initTeleSock()

    def _raw_on(self, name, func):
        return s_eventbus.EventBus.on(self, name, func)

    def _raw_off(self, name, func):
        return s_eventbus.EventBus.off(self, name, func)

    def on(self, name, func):
        self._tele_ons.add(name)

        job = self._txTeleJob('tele:on', events=[name], name=self._tele_name)
        self.sync(job)

        return s_eventbus.EventBus.on(self, name, func)

    def off(self, name, func):

        self._tele_ons.discard(name)

        job = self._txTeleJob('tele:off', evt=name, name=self._tele_name)
        self.sync(job)

        return s_eventbus.EventBus.off(self, name, func)

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

    def callx(self, name, task, ondone=None):
        '''
        Call a method on a specific shared object as a job.

        Example:

            # task is (<method>,<args>,<kwargs>)
            task = ('getFooByBar', (bar,), {} )

            job = proxy.callx('woot',task)
            ret = proxy.sync(job)

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
        return self.sync(job)

    def _tx_call(self, task, ondone=None):
        return self._txTeleJob('tele:call', name=self._tele_name, task=task, ondone=ondone)

    def sync(self, job, timeout=None):
        '''
        Wait on a given job and return/raise it's result.

        Example:

            job = proxy.call('woot', 10, bar=20)
            ret = proxy.sync(job)

        '''
        # dont block the consumer thread, consume events
        # until the job completes...
        if threading.currentThread() == self._tele_cthr:
            return self._fakeConsSync(job, timeout=timeout)

        # wait for job and jobret()
        if self._tele_boss.wait(job[0], timeout=timeout):
            return s_async.jobret(job)

        raise HitMaxTime()

    def _fakeConsSync(self, job, timeout=None):
        # a sync like function for the consumer thread
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

        return s_async.jobret(job)

    def _initTeleSock(self):

        if self.isfini:
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

        # let client code do stuff on reconnect
        self.fire('tele:sock:init', sock=self._tele_sock)

        return True

    def _onLinkSockMesg(self, event):
        # MULTIPLEXOR: DO NOT BLOCK
        mesg = event[1].get('mesg')
        self._tele_q.put( mesg )

    def _onSockFini(self):
        # If we still have outstanding jobs, reconnect immediately
        if self.isfini:
            return

        self._initTeleSock()

    def _onTeleCall(self, mesg):
        # dont block consumer thread... task pool
        self._tele_pool.call( self._runTeleCall, mesg )

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
        if self._tele_sock.isfini:
            self._initTeleSock()

        return self._tele_sock

    def _getUserCert(self):
        '''
        If pki is enabled, return the cert for link username as iden.
        '''
        if self._tele_pki == None:
            return None

        iden = self._tele_relay.getLinkProp('user')
        return self._tele_pki.getTokenCert(iden)

    def _teleSynAck(self):
        '''
        Send a tele:syn to get a telepath session
        '''

        chal = os.urandom(16)
        cert = self._getUserCert()

        host = self._tele_relay.getLinkProp('host')

        msginfo = dict(sid=self._tele_sid)

        job = self._txTeleJob('tele:syn', sid=self._tele_sid, chal=chal, cert=cert, host=host )

        synresp = self.sync(job, timeout=4)

        # we require the server to auth...
        if self._tele_pki:

            cert = synresp.get('cert')
            if cert == None:
                raise Exception('NoPkiCert')

            tokn = self._tele_pki.loadCertToken(cert)
            if tokn == None:
                # FIXME pki exceptions...
                raise Exception('BadPkiCert')

            sign = synresp.get('sign')
            if sign == None:
                raise Exception('NoPkiSign')

            if not self._tele_pki.isValidSign(tokn[0],sign,chal):
                raise Exception('BadPkiSign')

            ckey = os.urandom(16)
            skey = self._tele_pki.encToIden(tokn[0], ckey)

            job = self._txTeleJob('tele:skey', iden=tokn[0], algo='rc4', skey=skey)
            if not self.sync(job):
                raise Exception('BadSetSkey')

            xform = s_crypto.Rc4Skey(ckey)
            self._tele_sock.addSockXform(xform)

        self._tele_sid = synresp.get('sess')

        events = list(self._tele_ons)

        if events:
            job = self._txTeleJob('tele:on', events=events, name=self._tele_name)
            self.sync( job )

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

        self._tele_pool.fini()
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

