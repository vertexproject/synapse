'''
An RMI framework for synapse.
'''
import time
import zlib
import logging
import threading
import collections

import synapse.glob as s_glob
import synapse.link as s_link
import synapse.async as s_async
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus

import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.socket as s_socket
import synapse.lib.msgpack as s_msgpack
import synapse.lib.reflect as s_reflect

logger = logging.getLogger(__name__)

# telepath protocol version
# ( compat breaks only at major ver )
telever = (2, 0)

def openurl(url, **opts):
    '''
    Construct a Telepath Proxy from a URL.

    Args:
        url (str): A URL to parser into a link tufo.
        **opts: Additional options which are added to the link tufo.

    Examples:
        Get a proxy object from a URL, call a function then close the object::

            foo = openurl('tcp://1.2.3.4:90/foo')
            foo.dostuff(30) # call remote method
            foo.fini()

        Get a proxy object as a context manager, which will result in the object being automatically closed::

            with openurl('tcp://1.2.3.4:90/foo') as foo:
                foo.dostuff(30)

    Returns:
        Proxy: A Proxy object for calling remote tasks.
    '''
    #plex = opts.pop('plex',None)
    #return openclass(Proxy,url,**opts)
    link = s_link.chopLinkUrl(url)
    link[1].update(opts)

    return openlink(link)

def openlink(link):
    '''
    Construct a Telepath Proxy from a link tufo.

    Args:
        link ((str, dict)): A link dictionary.

    Examples:
        Get a proxy object, call a function then close the object::

            foo = openlink(link)
            foo.bar(20)
            foo.fini()

        Get a proxy object as a context manager, which will result in the object being automatically closed::

            with openlink as foo:
                foo.dostuff(30)

    Returns:
        Proxy: A Proxy object for calling remote tasks.
    '''
    # special case for dmon://fooname/ which refers to a
    # named object within whatever dmon is currently in scope
    if link[0] == 'dmon':

        dmon = s_scope.get('dmon')
        if dmon is None:
            raise s_common.NoSuchName(name='dmon', link=link, mesg='no dmon instance in current scope')

        # the "host" part is really a dmon local
        host = link[1].get('host')
        item = dmon.locs.get(host)
        if item is None:
            raise s_common.NoSuchName(name=host, link=link, mesg='dmon instance has no local with that name')

        return item

    relay = s_link.getLinkRelay(link)
    name = link[1].get('path')[1:]

    sock = relay.connect()

    synack = teleSynAck(sock, name=name)

    return Proxy(relay, sock=sock)

def evalurl(url, **opts):
    '''
    Construct either a local object or a telepath proxy.

    Args:
        url (str): URL to evaluate
        **opts: Additional options.

    Notes:
        This API enables the ctor:// protocol which uses ``eval()``.
        It should **only** be used with trusted inputs!

    Examples:
        Get a remote object over a TCP connection:

            item0 = evalurl('tcp://1.2.3.4:90/foo')

        Get a local object via ctor:

            item1 = evalurl('ctor://foo.bar.baz("woot",y=20)')

    Returns:
        object: A python object
    '''
    if url.find('://') == -1:
        raise s_common.BadUrl(url)

    scheme, therest = url.split('://', 1)
    if scheme == 'ctor':
        locs = opts.get('locs')
        return s_dyndeps.runDynEval(therest, locs=locs)

    return openurl(url, **opts)

def isProxy(item):
    '''
    Check to see if a object is a telepath proxy object or not.

    Args:
        item (object): Object to inspect.

    Returns:
        bool: True if the object is a telepath object; otherwise False.
    '''
    return isinstance(item, Proxy)

def reqIsProxy(item):
    '''
    Check if the item is a proxy and raise MustBeProxy if not.

    Args:
        item (obj): The object to test for being a telepath proxy

    Returns:
        (None)

    Example:

        reqIsProxy(foo)
        # foo is def a proxy here...

    '''
    if not isProxy(item):
        raise s_common.MustBeProxy(item=item)

def reqNotProxy(item):
    '''
    Check if the item is a proxy and raise MustBeProxy if so.

    Args:
        item (obj): The object to test for being a telepath proxy

    Returns:
        (None)

    Example:

        reqNotProxy(foo)
        # foo is def not a proxy here...

    '''
    if isProxy(item):
        raise s_common.MustBeLocal(item=item)

class Method:

    def __init__(self, proxy, meth):
        self.meth = meth
        self.cside = None
        self.proxy = proxy

        # act as much like a bound method as possible...
        self.__name__ = meth
        self.__self__ = proxy

    def __call__(self, *args, **kwargs):

        # check if we have a cached client-side function
        if self.cside is not None:
            return self.cside(self.proxy, *args, **kwargs)

        ondone = kwargs.pop('ondone', None)
        task = (self.meth, args, kwargs)

        job = self.proxy._tx_call(task, ondone=ondone)
        if ondone is not None:
            return job

        return self.proxy.syncjob(job)

telelocal = set(['tele:sock:init',
                 'tele:sock:runsockfini',
                 'ebus:init',
                 'fifo:xmit'])

class Proxy(s_eventbus.EventBus):
    '''
    The telepath proxy provides "pythonic" access to remote objects.

    ( you most likely want openurl() or openlink() )

    NOTE:

        *all* locals in this class *must* have _tele_ prefixes to prevent
        accidental deref of something with the same name in code using it
        under the assumption it's something else....

    '''
    def __init__(self, relay, plex=None, sock=None):

        s_eventbus.EventBus.__init__(self)
        self.onfini(self._onProxyFini)

        # NOTE: the _tele_ prefixes are designed to prevent accidental
        #       derefs with overlapping names from working correctly

        self._tele_sid = None

        self._tele_q = s_queue.Queue()
        self._tele_pushed = {}

        # allow the server to give us events to fire back on
        # reconnect so we can help re-init our server-side state
        self._tele_reminders = []

        if plex is None:
            plex = s_socket.Plex()
            self.onfini(plex.fini)

        self._tele_plex = plex
        self._tele_boss = s_async.Boss()

        self._tele_plex.on('link:sock:mesg', self._onLinkSockMesg)

        self._raw_on('tele:yield:init', self._onTeleYieldInit)
        self._raw_on('tele:yield:item', self._onTeleYieldItem)
        self._raw_on('tele:yield:fini', self._onTeleYieldFini)

        self._raw_on('tele:reminder', self._onTeleReminder)

        self._raw_on('fifo:xmit', self._onFifoXmit)
        self._raw_on('job:done', self._tele_boss.dist)
        self._raw_on('sock:gzip', self._onSockGzip)
        self._raw_on('tele:call', self._onTeleCall)
        self._raw_on('tele:sock:init', self._onTeleSockInit)

        self._tele_cthr = self.consume(self._tele_q)

        self._tele_ons = {}

        self._tele_sock = None
        self._tele_relay = relay    # LinkRelay()
        self._tele_link = relay.link
        self._tele_yields = {}
        self._tele_csides = {}
        self._tele_reflect = None

        # obj name is path minus leading "/"
        self._tele_name = relay.link[1].get('path')[1:]

        if sock is None:
            sock = self._tele_relay.connect()

        self._initTeleSock(sock=sock)

    def _onTeleReminder(self, mesg):
        self._tele_reminders.append(mesg[1].get('mesg'))

    def _onFifoXmit(self, mesg):

        # a bit of magic specific to cortex proxy...
        # ( this will be made cleaner in neuron use case )

        name = mesg[1].get('name')
        seqn, nseq, item = mesg[1].get('qent')
        self.call('fire', 'fifo:ack', name, seqn)

    def _onTeleYieldInit(self, mesg):
        jid = mesg[1].get('jid')
        iden = mesg[1].get('iden')

        que = s_queue.Queue()
        self._tele_yields[iden] = que

        def onfini():
            self._tele_yields.pop(iden, None)
            self._txTeleSock('tele:yield:fini', iden=iden)

        que.onfini(onfini)
        self._tele_boss.done(jid, que)

    def _onTeleYieldItem(self, mesg):
        iden = mesg[1].get('iden')
        que = self._tele_yields.get(iden)
        if que is None:
            self._txTeleSock('tele:yield:fini', iden=iden)
            return

        que.put(mesg[1].get('item'))

    def _onTeleYieldFini(self, mesg):
        iden = mesg[1].get('iden')
        que = self._tele_yields.get(iden)
        if que is not None:
            que.done()

    def _raw_on(self, name, func):
        return s_eventbus.EventBus.on(self, name, func)

    def _raw_off(self, name, func):
        return s_eventbus.EventBus.off(self, name, func)

    def on(self, evnt, func, **filts):

        # create a separate record for each so the dmon
        # can potentially create an "any" filter for us
        if evnt not in telelocal:
            iden = s_common.guid()
            filt = tuple(filts.items())

            onit = (iden, filt)

            okey = (evnt, func)
            self._tele_ons[okey] = (iden, filt)

            job = self._txTeleJob('tele:on', ons=[(evnt, [onit])], name=self._tele_name)
            self.syncjob(job)

        return s_eventbus.EventBus.on(self, evnt, func, **filts)

    def off(self, name, func):

        ret = s_eventbus.EventBus.off(self, name, func)
        if name in telelocal:
            return ret

        okey = (name, func)
        onit = self._tele_ons.pop(okey, None)
        if onit is None:
            return ret

        iden, filt = onit
        job = self._txTeleJob('tele:off', evnt=name, iden=iden, name=self._tele_name)
        self.syncjob(job)

        return ret

    def fire(self, evntname, **info):
        if evntname in telelocal:
            return s_eventbus.EventBus.fire(self, evntname, **info)

        job = self.call('fire', evntname, **info)
        return self.syncjob(job)

    def call(self, methname, *args, **kwargs):
        '''
        Call a shared method as a job.

        Example:

            job = proxy.call('getFooByBar',bar)

            # ... do other stuff ...

            ret = proxy.syncjob(job)

        '''
        ondone = kwargs.pop('ondone', None)

        task = (methname, args, kwargs)
        return self._tx_call(task, ondone=ondone)

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
        csides = getClientSides(item)
        reflect = s_reflect.getItemInfo(item)
        job = self._txTeleJob('tele:push', name=name, reflect=reflect, csides=csides)
        self._tele_pushed[name] = item
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
        self._waitTeleJob(job, timeout=timeout)
        return s_async.jobret(job)

    def _waitTeleJob(self, job, timeout=None):
        # dont block the consumer thread, consume events
        # until the job completes...
        if threading.currentThread() == self._tele_cthr:
            return self._fakeConsWait(job, timeout=timeout)

        if not self._tele_boss.wait(job[0], timeout=timeout):
            raise s_common.HitMaxTime()

    def _fakeConsWait(self, job, timeout=None):
        # a wait like function for the consumer thread
        # which continues to consume events until a job
        # has been completed.
        maxtime = None
        if timeout is not None:
            maxtime = time.time() + timeout

        while not job[1].get('done'):

            if maxtime is not None and time.time() >= maxtime:
                raise s_common.HitMaxTime()

            mesg = self._tele_q.get()
            self.dist(mesg)

    def _initTeleSock(self, sock=None):

        if sock is None:
            sock = self._tele_relay.connect()

        def sockfini():
            # called by multiplexor... must not block
            if not self.isfini:
                s_glob.pool.call(self._runSockFini)

        logger.debug('[%s] has sock [%s]', self, sock)

        sock.onfini(sockfini)

        self._teleSynAck(sock)

        # add the sock to the multiplexor
        self._tele_plex.addPlexSock(sock)

        self._tele_sock = sock

        # fire the remiders that the server wanted
        for evntname, evntinfo in self._tele_reminders:
            self.call('fire', evntname, **evntinfo)

        # let client code do stuff on reconnect
        self.fire('tele:sock:init', sock=sock)

    def _onLinkSockMesg(self, event):
        # MULTIPLEXOR: DO NOT BLOCK
        mesg = event[1].get('mesg')
        self._tele_q.put(mesg)

    def _runSockFini(self):
        if self.isfini:
            return

        self.fire('tele:sock:runsockfini')

        try:
            self._initTeleSock()
        except s_common.LinkErr as e:
            s_glob.sched.insec(1, self._runSockFini)

    def _onTeleCall(self, mesg):
        # dont block consumer thread... task pool
        s_glob.pool.call(self._runTeleCall, mesg)

    def _onSockGzip(self, mesg):
        data = zlib.decompress(mesg[1].get('data'))
        self.dist(s_msgpack.un(data))

    def _runTeleCall(self, mesg):

        jid = mesg[1].get('jid')
        name = mesg[1].get('name')
        task = mesg[1].get('task')
        suid = mesg[1].get('suid')

        retinfo = dict(suid=suid, jid=jid)

        try:

            item = self._tele_pushed.get(name)
            if item is None:
                return self._txTeleSock('tele:retn', err='NoSuchObj', errmsg=name, **retinfo)

            meth, args, kwargs = task
            func = getattr(item, meth, None)
            if func is None:
                return self._txTeleSock('tele:retn', err='NoSuchMeth', errmsg=meth, **retinfo)

            self._txTeleSock('tele:retn', ret=func(*args, **kwargs), **retinfo)

        except Exception as e:
            retinfo.update(s_common.excinfo(e))
            return self._txTeleSock('tele:retn', **retinfo)

    def _getTeleSock(self):
        if self.isfini:
            raise s_common.IsFini()

        return self._tele_sock

    def _syn_reflect(self):
        return self._tele_reflect

    def _onTeleSockInit(self, mesg):
        '''
        Callback to allow the client to do anything neccesary after a Telepath
        connection has been made with the remote.

        This is in response to a tele:sock:init event. This occurs during
        startup of the Proxy object or during reconnection.
        '''
        sock = mesg[1].get('sock')

        # Reset any on handlers which the Proxy has registered with the remote
        eper = collections.defaultdict(list)
        for (evnt, func), (iden, filt) in self._tele_ons.items():
            eper[evnt].append((iden, filt))

        if eper:
            job = self._txTeleJob('tele:on', ons=list(eper.items()), name=self._tele_name)
            self.syncjob(job)

    def _teleSynAck(self, sock):
        '''
        Send a tele:syn to get a telepath session
        '''
        sid = self._tele_sid
        name = self._tele_name

        synack = teleSynAck(sock, name=name, sid=sid)

        self._tele_sid = synack.get('sess')
        self._tele_reflect = synack.get('reflect')

        csides = synack.get('csides')
        if csides is not None:
            self._tele_csides.update(csides)

        hisopts = synack.get('opts', {})

        if hisopts.get('sock:can:gzip'):
            sock.set('sock:can:gzip', True)

    def _txTeleJob(self, msg, **msginfo):
        '''
        Transmit a message as a job ( add jid to mesg ) and return job.
        '''
        ondone = msginfo.pop('ondone', None)
        job = self._tele_boss.initJob(ondone=ondone)

        msginfo['jid'] = job[0]
        self._txTeleSock(msg, **msginfo)

        return job

    def _txTeleSock(self, msg, **msginfo):
        '''
        Send a mesg over the socket and include our session id.
        '''
        msginfo['sid'] = self._tele_sid
        sock = self._getTeleSock()
        if sock is not None:
            sock.tx((msg, msginfo))

    def _onProxyFini(self):

        [que.fini() for que in self._tele_yields.values()]

        if self._tele_sock is not None:
            self._tele_sock.fini()

        self._tele_boss.fini()

    def __getattr__(self, name):
        path = self._tele_csides.get(name)
        if path is not None:
            func = s_dyndeps.getDynMeth(path)
            if func is None:
                return None

            meth = func.__get__(self)

        else:
            meth = Method(self, name)

        setattr(self, name, meth)
        return meth

    # some methods to avoid round trips...
    def __bool__(self):
        return True

    def __eq__(self, obj):
        return id(self) == id(obj)

    def __ne__(self, obj):
        return not self.__eq__(obj)

def teleSynAck(sock, name=None, sid=None):

    synack = sock.get('tele:synack')

    if synack is None:

        opts = {'sock:can:gzip': 1}
        info = {
            'sid': sid,
            'opts': opts,
            'vers': telever,
            'name': name,
        }

        sock.tx(('tele:syn', info))

        done = next(sock.rx())
        synack = done[1].get('ret')

        sock.set('tele:synack', synack)

        vers = synack.get('vers', (0, 0))
        if vers[0] != telever[0]:
            raise s_common.BadMesgVers(myver=telever, hisver=vers)

    return synack

def reminder(evnt, **info):
    '''
    May be used on server side to set a telepath reconnect reminder.

    Args:
        name (str): The event name to fire on reconnect
        **info: The event metadata

    Returns:
        (bool): True if the telepath caller was notified.

    NOTE:
        This requests that the current telepath caller fire the given
        event back to us in the event of a socket reconnect.
    '''
    sock = s_scope.get('sock')
    if sock is None:
        return False

    mesg = (evnt, info)
    sock.tx(('tele:reminder', {'mesg': mesg}))
    return True

def clientside(f):
    '''
    A function decorator which causes the given function to be run on
    the telepath client side.

    Args:
        f: The function being decorated.

    Notes:
        A decorated function **must** use APIs within the function to access
        object locals, variables, etc. In other words, the method must be able
        to have **self** be a Telepath Proxy object.

    Example:
        A class with a decorated clientside function::

            class Foob:
                def __init__(self, data):
                    self.locals = data

                def getLocals():
                    return self.locals

                @s_telepath.clientside
                def foo(self, bar):

                    # We use an API to get data from self.locals instead
                    # accessing it directly, since that would cause failures.
                    object_locals = self.getLocals()

                    # Now do stuff on the client side.
                    dostuff(object_locals)

    Returns:
        The decorated function.
    '''
    f._tele_clientside = True
    return f

def getClientSides(item):
    '''
    Return a dict of name:path pairs for any clientside functions in item.
    '''
    retn = {}

    for name, valu in s_reflect.getItemLocals(item):

        if not getattr(valu, '_tele_clientside', False):
            continue

        path = s_reflect.getMethName(valu)
        if path is None:
            continue

        retn[name] = path

    return retn
