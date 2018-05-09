import os
import time
import socket
import logging
import selectors
import threading
import collections

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.queue as s_queue
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads

logger = logging.getLogger(__name__)

'''
The synapse.lib.net module implements async networking helpers.
( and will slowly replace synapse.lib.socket )
'''

class Plex(s_config.Config):
    '''
    A highly-efficient selectors-based multi-plexor for sockets.
    '''
    def __init__(self, conf=None):

        s_config.Config.__init__(self, conf)

        self.epoll = selectors.DefaultSelector()

        self.socks = {}
        self.links = {}

        self.thrd = s_threads.worker(self._runPollLoop)

        self.onfini(self._onPlexFini)

        pmax = self.getConfOpt('pool:max')
        self.pool = s_threads.Pool(maxsize=pmax)

        self.onfini(self.pool.fini)

        self.polls = {}

    @staticmethod
    @s_config.confdef(name='plex')
    def _initPlexConf():
        return (
            ('pool:max', {'defval': 8, 'type': 'int',
             'doc': 'The maximum number of threads in the thread pool'}),
        )

    def _runPollLoop(self):

        fems = []
        while not self.isfini:

            try:

                fems = self.epoll.select()
                for (_, fino, events, _), mask in fems:

                    if self.isfini:
                        return

                    poll = self.polls.get(fino)

                    if poll is None:

                        sock = self.socks.get(fino)
                        if sock is not None:
                            self._finiPlexSock(sock)

                        continue

                    try:

                        poll(mask)

                    except Exception as e:
                        logger.exception('error during poll() callback')

            except Exception as e:
                if self.isfini:
                    continue
                logger.exception('plex thread error: %r' % (e,))

            if not fems:
                time.sleep(0.035)

    def _onPlexFini(self):

        [l.fini() for l in list(self.links.values())]
        [s.close() for s in list(self.socks.values())]

        self.epoll.close()

        self.thrd.join(timeout=1)

    def _finiPlexSock(self, sock):

        fino = sock.fileno()

        self.socks.pop(fino, None)

        poll = self.polls.pop(fino)
        if poll is not None:
            self.epoll.unregister(sock)

        sock.close()

    def listen(self, addr, onlink):
        '''
        Initiate a listening socket with a Link constructor.

        Args:
            addr ((str,int)): A (host,port) socket address.
            onlink (function): A callback to receive newly connected SockLink.

        Returns:
            ((str,int)): The bound (host,port) address tuple.
        '''

        sock = socket.socket()
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)
        sock.listen(120)

        fino = sock.fileno()

        def poll(flags):

            if not flags & selectors.EVENT_READ:

                self._finiPlexSock(sock)

                errn = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                logger.warning('listen error: %d' % (errn,))

            while True:

                try:

                    news, addr = sock.accept()

                    self._setSockOpts(news)
                    link = self._initPlexSock(news)

                    try:

                        onlink(link)

                    except Exception as e:
                        logger.warning('listen() onlink error: %s' % (e,))
                        link.fini()

                except BlockingIOError as e:
                    return

        self.socks[fino] = sock
        self.polls[fino] = poll

        self.epoll.register(sock, selectors.EVENT_READ)
        return sock.getsockname()

    def _initPlexSock(self, sock):

        fino = sock.fileno()
        link = SockLink(self, sock)

        self.links[fino] = link
        self.polls[fino] = link.poll

        if self.socks.get(fino) is None:
            self.socks[fino] = sock
            self.epoll.register(sock, link.flags)

        else:
            self.epoll.modify(sock, link.flags)

        return link

    def modify(self, sock, flags):
        '''
        Modify the epoll flags mask for the give file descriptor.

        Args:
            socket (socket): The socket to modify
            flags (int): The epoll flags mask.
        '''
        return self.epoll.modify(sock, flags)

    def _setSockOpts(self, sock):

        sock.setblocking(False)
        # disable nagle ( to minimize latency for small xmit )
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # enable TCP keep alives...
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, 'TCP_KEEPIDLE'):
            # start sending a keep alives after 1 sec of inactivity
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            # send keep alives every 3 seconds once started
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
            # close the socket after 5 failed keep alives (15 sec)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

    def connect(self, addr, onconn):
        '''
        Perform a non-blocking connect with the given callback function.

        Args:
            addr ((str,int)): A (host,port) socket address.
            onconn (function): A callback (ok, link)
        '''
        sock = socket.socket()
        self._setSockOpts(sock)

        fino = sock.fileno()

        def poll(flags):

            ok = True
            retn = None

            errn = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if errn != 0:
                ok = False
                retn = errn
                self._finiPlexSock(sock)
            else:
                ok = True
                retn = self._initPlexSock(sock)
            try:
                onconn(ok, retn)
            except Exception as e:
                logger.exception('connect() onconn failed: %s' % (e,))
                return

        self.socks[fino] = sock
        self.polls[fino] = poll

        try:
            sock.connect(addr)
            # This path won't be exercised on Linux
            poll(2)
        except BlockingIOError as e:
            # This is the Linux path
            self.epoll.register(sock, selectors.EVENT_WRITE)

s_glob.plex = Plex()  # type: ignore

class Link(s_eventbus.EventBus):
    '''
    A message aware network connection abstraction.
    '''

    def __init__(self, link=None):

        s_eventbus.EventBus.__init__(self)

        self.info = {}

        # TODO: heart beat via global sched
        self.rxtime = None
        self.txtime = None

        self.rxfunc = None
        self.finfunc = None

        self.isrxfini = False
        self.istxfini = False

        self.link = link

        self._mesg_funcs = self.handlers()
        self.onfini(self._onLinkFini)

    def chain(self, link):
        link.onrx(self.rx)
        self.onfini(link.fini)
        link.onfini(self.fini)

    def onmesg(self, name, func):
        '''
        Set a named message handler for the link.
        '''
        self._mesg_funcs[name] = func

    def onrx(self, func):
        '''
        Register a callback to recieve (link, mesg) tuples.
        '''
        self.rxfunc = func

    def _onLinkFini(self):
        self.txfini()
        self.rxfini()

    def rxfini(self):
        '''
        Called when the remote link has sent fini.
        '''
        if self.isrxfini:
            return

        self.isrxfini = True
        self.fire('rx:fini')

        if self.istxfini:
            self.fini()

    def txfini(self, data=s_common.novalu):
        '''
        Annotate that the there is nothing more to send.
        '''
        if data is not s_common.novalu:
            self.tx(data)

        if self.istxfini:
            return

        self.istxfini = True
        self.fire('tx:fini')

        if self.isrxfini:
            self.fini()

    def handlers(self):
        '''
        Return a dict of <mesg>:<func> handlers for this link layer.
        '''
        return {}

    def getLinkProp(self, name, defval=None):
        '''
        Return a previously set link property.

        Args:
            name (str): The property name.
            defval (obj): The default value.

        Returns:
            (obj): The property value or defval.
        '''
        return self.info.get(name, defval)

    def setLinkProp(self, name, valu):
        '''
        Set a link property.

        Args:
            name (str): The property name.
            valu (obj): The property value.
        '''
        self.info[name] = valu

    def rx(self, link, mesg):
        '''
        Recv a message on this link and dispatch the message.

        Args:
            link (Link): The link.
            mesg ((str,dict)): A message tufo.
        '''
        if self.isfini:
            return

        self.rxtime = s_common.now()

        if self.rxfunc is not None:
            try:
                return self.rxfunc(self, mesg)
            except Exception as e:
                logger.exception('%s.rxfunc() failed on: %r' % (self.__class__.__name__, mesg))
                self.fini()
                return

        try:
            func = self._mesg_funcs.get(mesg[0])
        except Exception as e:
            logger.exception('link %s: rx mesg exception: %s' % (self.__class__.__name__, e))
            self.fini()
            return

        if func is None:
            logger.warning('link %s: unknown message type %s' % (self.__class__.__name__, mesg[0]))
            return

        try:
            func(link, mesg)
        except Exception as e:
            logger.exception('link %s: rx exception: %s' % (self.__class__.__name__, e))
            self.fini()

    def tx(self, mesg):
        '''
        Transmit a message via this link.

        Args:
            mesg ((str,dict)): A message tufo.
        '''
        if self.istxfini:
            return

        self.txtime = s_common.now()
        self._tx_real(mesg)

    def txok(self, retn, fini=False):
        self.tx((True, retn))
        if fini:
            self.txfini()

    def txerr(self, enfo, fini=False):
        self.tx((False, enfo))
        if fini:
            self.txfini()

    def _tx_real(self, mesg):
        return self.link.tx(mesg)

    def __repr__(self):
        rstr = self.getLinkProp('repr')
        return '%s: %s at %s' % (self.__class__.__name__, rstr, hex(id(self)))

class Chan(Link):

    def __init__(self, plex, iden, txinit=True):

        Link.__init__(self, plex)

        self._chan_rxq = None
        self._chan_iden = iden
        self._chan_txinit = True

    def iden(self):
        return self._chan_iden

    def _tx_real(self, mesg):

        name = 'data'
        if self._chan_txinit:
            self._chan_txinit = False
            name = 'init'

        self.link.tx((name, {'chan': self._chan_iden, 'data': mesg}))

    def txfini(self, data=s_common.novalu):

        name = 'fini'
        info = {'chan': self._chan_iden}

        if data is not s_common.novalu:
            info['data'] = data

        # check for syn/psh/fin
        if self._chan_txinit:
            self._chan_txinit = False
            name = 'init'
            info['fini'] = True

        self.link.tx((name, info))

    def setq(self):
        '''
        Set this Chan to using a Queue for rx.
        '''
        if self._chan_rxq is not None:
            return

        self._chan_rxq = s_queue.Queue()

        def rx(link, mesg):
            self._chan_rxq.put(mesg)

        def rxfini(mesg):
            self._chan_rxq.done()

        self.onrx(rx)

        self.on('rx:fini', rxfini)
        self.onfini(self._chan_rxq.done)

    def next(self, timeout=None):
        return self._chan_rxq.get(timeout=timeout)

    def slice(self, size, timeout=None):
        return self._chan_rxq.slice(size, timeout=timeout)

    def iter(self, timeout=None):
        while not self.isfini:
            yield self._chan_rxq.get(timeout=timeout)

    def rxwind(self, timeout=None):
        '''
        Yield items from an txwind caller.
        '''
        self.setq()

        while not self.isfini:

            for ok, retn in self.slice(1000, timeout=timeout):

                if not ok:

                    if retn is not None:
                        logger.warning('rxwind(): %r' % (retn,))

                    return

                self.tx((True, True))
                yield retn

    def txwind(self, items, size, timeout=None):
        '''
        Execute a windowed transmission loop from a generator.
        '''
        wind = 0

        try:

            for item in items:

                self.tx((True, item))
                wind += 1

                while wind >= size:
                    acks = self.slice(wind, timeout=timeout)
                    wind -= len(acks)

        except Exception as e:
            enfo = s_common.getexcfo(e)
            self.txerr(enfo)
            logger.exception('tx wind genr')
            return

        self.tx((False, None))

        while wind > 0:
            try:
                acks = self.slice(wind, timeout=timeout)
                wind -= len(acks)
            except Exception as e:
                print('TXWIND REMAIN WIND: %r' % (wind,))
                raise

        return True

class ChanPlex(Link):
    '''
    A Link which has multiple channels.
    '''
    def __init__(self, onchan=None):

        Link.__init__(self)

        self.onchan = onchan
        self.chans = s_eventbus.BusRef()
        # TODO: chan timeouts... (maybe add to BusRef?)

        self.onfini(self.chans.fini)

    def handlers(self):
        return {
            'init': self._onChanInit,
            'data': self._onChanData,
            'fini': self._onChanFini,
        }

    def _onChanInit(self, link, mesg):

        iden = mesg[1].get('chan')
        data = mesg[1].get('data', s_common.novalu)

        chan = self.chans.get(iden)
        if chan is not None:
            # an init for an existing chan
            # (return init message from our tx)
            if data is not s_common.novalu:
                chan.rx(self, data)

            return

        if self.onchan is None:
            logger.warning('%r: got init without onchan: %r' % (self, chan))
            return

        chan = self.initPlexChan(iden, txinit=False)
        chan.setLinkProp('plex:recv', True)

        self.chans.put(iden, chan)
        chan.setLinkProp('plex:link', link)

        try:

            self.onchan(chan)

        except Exception as e:
            logger.exception('onchan (%r) failed: %s' % (self.onchan, e))
            chan.fini()
            return

        if data is not None:
            chan.rx(self, data)

        # syn/psh/fin ;)
        if mesg[1].get('fini'):
            chan.rxfini()

    def _tx_real(self, mesg):

        iden = mesg[1].get('chan')

        chan = self.chans.get(iden)
        if chan is None:
            logger.warning('tx() for missing chan %r' % (mesg,))
            return

        link = chan.getLinkProp('plex:link', defval=self.link)
        if link is None:
            logger.warning('tx() for chan without link: %r' % (iden,))
            return

        return link.tx(mesg)

    def _onChanData(self, link, mesg):
        iden = mesg[1].get('chan')
        data = mesg[1].get('data')

        chan = self.chans.get(iden)
        if chan is None:
            # There are many chan shutdown instances where this is ok
            logger.info('chan data for missing chan: %r (link: %r)' % (iden, link))
            return

        chan.setLinkProp('plex:link', link)
        chan.rx(self, data)

    def _onChanFini(self, link, mesg):

        # this message means the remote end is done sending
        # ( and does not by itself fini() the chan )
        iden = mesg[1].get('chan')
        data = mesg[1].get('data', s_common.novalu)

        chan = self.chans.get(iden)
        if chan is None:
            return

        chan.setLinkProp('plex:link', link)

        if data is not s_common.novalu:
            chan.rx(self, data)

        chan.rxfini()

    def initPlexChan(self, iden, txinit=True):
        chan = Chan(self, iden, txinit=txinit)
        chan.info.update(self.info)
        self.chans.put(iden, chan)
        return chan

    def open(self, link):

        iden = os.urandom(16)

        chan = self.initPlexChan(iden, txinit=True)
        chan.setLinkProp('plex:link', link)
        chan.setLinkProp('plex:open', True)

        return chan

class SockLink(Link):
    '''
    A Link implements Plex aware non-blocking operations for a socket.
    '''
    def __init__(self, plex, sock):

        Link.__init__(self, None)

        self.plex = plex
        self.sock = sock

        self.txbuf = b''
        self.txque = collections.deque() # (byts, info)
        self.txlock = threading.Lock()

        self.unpk = s_msgpack.Unpk()
        self.flags = selectors.EVENT_READ

        def fini():
            self.plex._finiPlexSock(self.sock)

        self.onfini(fini)

    def poll(self, flags):
        '''
        Handle an epoll event for this Link's socket.

        Args:
            flags (int): The epoll return flags.
        '''
        try:

            txdone = False

            if flags & selectors.EVENT_READ:

                self._rxloop()

                # chances are, after an rxloop(), a txloop() is needed...
                self._txloop()

                txdone = True

            if flags & selectors.EVENT_WRITE and not txdone:
                self._txloop()

        except Exception as e:
            logger.exception('error during epoll event: %s for %r' % (e, self.sock))
            self.fini()

    def tx(self, mesg, fini=False):
        '''
        Transmit the message on the socket.

        Args:
            mesg ((str,dict)): A message tufo.
        '''
        byts = s_msgpack.en(mesg)
        return self._add_tx(byts)

    def _add_tx(self, byts):

        with self.txlock:

            self.txque.append(byts)

            if self.flags & selectors.EVENT_WRITE:
                return

            self.flags |= selectors.EVENT_WRITE
            self.plex.modify(self.sock, self.flags)

    def _rxbytes(self, size):
        '''
        Try to recv size bytes.

        Args:
            size (int): The number of bytes to recv.

        Returns:
            (bytes): The bytes (or None) if would block.
        '''
        try:
            rv = self.sock.recv(size)
            if rv == b'':
                raise ConnectionError
            return rv

        except ConnectionError as e:
            return ''

        except BlockingIOError as e:
            return None

    def _rxloop(self):

        while not self.isfini:

            byts = self._rxbytes(1024000)
            if byts is None:
                return

            if not byts:
                self.fini()
                return

            for size, mesg in self.unpk.feed(byts):

                try:

                    self.rx(self, mesg)

                except Exception as e:
                    logger.exception('rxloop() error processing mesg: %r' % (mesg,))

    def _txloop(self):

        with self.txlock:

            while not self.isfini:

                if self.txbuf:

                    try:

                        sent = self.sock.send(self.txbuf)

                        # if we didn't send anything, gtfo
                        if sent == 0:
                            return

                    except BlockingIOError as e:
                        # we cant send any more without blocking
                        return

                    except BrokenPipeError as e:
                        logger.debug('tx broken pipe: ignore...')
                        return

                    self.txbuf = self.txbuf[sent:]

                    # if we still have a txbuf, we've done all we can
                    if self.txbuf:
                        return

                # no more txbuf... are we done?
                if not self.txque:
                    if self.istxfini:
                        self.fini()
                        return
                    self.flags &= ~selectors.EVENT_WRITE
                    self.plex.modify(self.sock, self.flags)
                    return

                self.txbuf = self.txque.popleft()

class LinkDisp:
    '''
    The Link Dispatcher ensures sequential/bulk processing
    which executes from the global thread pool as needed.

    This can be used to create transaction boundaries across
    multiple links or prevent the need to permenantly eat threads.

    Example:

        def func(items):

            with getFooXact() as xact:

                for link, mesg in items:

                    xact.dostuff(mesg)
                    link.tx(True)

        disp = LinkDisp(func):
        chan.onrx(disp.rx)

    '''

    def __init__(self, func):

        self.func = func
        self.lock = threading.Lock()
        self.items = collections.deque()
        self.working = False

    def rx(self, link, item):

        with self.lock:

            self.items.append((link, item))

            if not self.working:
                self.working = True
                self._runItemsFunc()

    @s_glob.inpool
    def _runItemsFunc(self):

        while True:

            with self.lock:

                items = self.items
                if not items:
                    self.working = False
                    return

                self.items = []

            try:
                self.func(items)
            except Exception as e:
                logger.exception('LinkDisp callback error')
