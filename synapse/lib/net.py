import os
import select
import socket
import logging
import threading
import collections

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
    A highly-efficient epoll based multi-plexor for sockets.
    '''
    def __init__(self, conf=None):

        s_config.Config.__init__(self, conf)

        self.epoll = select.epoll()

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

        while not self.isfini:

            try:

                for fino, flags in self.epoll.poll(timeout=0.1):

                    if self.isfini:
                        return

                    poll = self.polls.get(fino)
                    if poll is None:
                        logger.warning('unknown epoll fd: %d' % (fino,))
                        self.epoll.unregister(fino)
                        continue

                    try:

                        poll(flags)

                    except Exception as e:
                        logger.exception('error during poll() callback')

            except Exception as e:
                logger.exception('plex thread error: %r' % (e,))

    def _onPlexFini(self):

        [l.fini() for l in self.links.values()]
        [s.close() for s in self.socks.values()]

        self.epoll.close()

        self.thrd.join(timeout=1)

    def _finiPlexSock(self, sock):

        fino = sock.fileno()

        if self.socks.pop(fino, None) is None:
            return

        self.socks.pop(fino, None)
        self.polls.pop(fino, None)

        self.epoll.unregister(fino)

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

            if not flags & select.EPOLLIN:

                self._finiPlexSock(sock)

                errn = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                logger.warning('listen error: %d' % (errn,))

            while True:

                try:

                    news, addr = sock.accept()
                    news.setblocking(False)

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

        self.epoll.register(fino, select.EPOLLIN | select.EPOLLERR | select.EPOLLET)
        return sock.getsockname()

    def _initPlexSock(self, sock):

        fino = sock.fileno()
        link = SockLink(self, sock)

        self.links[fino] = link
        self.polls[fino] = link.poll

        if self.socks.get(fino) is None:
            self.socks[fino] = sock
            self.epoll.register(fino, link.flags)

        else:
            self.epoll.modify(fino, link.flags)

        return link

    def modify(self, fino, flags):
        '''
        Modify the epoll flags mask for the give file descriptor.

        Args:
            fino (int): The file descriptor number.
            flags (int): The epoll flags mask.
        '''
        return self.epoll.modify(fino, flags)

    def connect(self, addr, onconn):
        '''
        Perform a non-blocking connect with the given callback function.

        Args:
            addr ((str,int)): A (host,port) socket address.
            onconn (function): A callback (ok, link)
        '''
        sock = socket.socket()
        sock.setblocking(False)

        fino = sock.fileno()

        def poll(flags):

            self.polls.pop(fino, None)

            if not flags & select.EPOLLOUT:
                self._finiPlexSock(sock)
                ok, link = False, sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                logger.warning('connect failed: %d' % (link,))
                sock.close()
            else:
                ok, link = True, self._initPlexSock(sock)

            try:
                onconn(ok, link)
            except Exception as e:
                logger.warning('connect() onconn failed: %s' % (e,))
                return

        self.socks[fino] = sock
        self.polls[fino] = poll

        self.epoll.register(fino, select.EPOLLOUT | select.EPOLLERR)

        try:
            sock.connect(addr)
        except BlockingIOError as e:
            pass

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

    def txfini(self, data=None):
        '''
        Annotate that the there is nothing more to send.
        '''
        if data is not None:
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
                return

        try:
            func = self._mesg_funcs.get(mesg[0])
        except Exception as e:
            logger.exception('link %s: rx mesg exception: %s' % (self.__class__.__name__, e))
            return

        if func is None:
            logger.warning('link %s: unknown message type %s' % (self.__class__.__name__, mesg[0]))
            return

        try:
            func(link, mesg)
        except Exception as e:
            logger.exception('link %s: rx exception: %s' % (self.__class__.__name__, e))

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
        self._chan_plex = plex
        self._chan_txinit = True

    def iden(self):
        return self._chan_iden

    def _tx_real(self, mesg):

        if self._chan_txinit:
            self._chan_txinit = True
            self.link.tx(('init', {'chan': self._chan_iden, 'data': mesg}))
            return

        self.link.tx(('data', {'chan': self._chan_iden, 'data': mesg}))

    def txfini(self, data=None):
        self.link.tx(('fini', {'chan': self._chan_iden, 'data': data}))

    def setq(self):
        '''
        Set this Chan to using a Queue for rx.
        '''

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
        retn = self._chan_rxq.get(timeout=timeout)
        while retn is not None:
            yield retn
            retn = self._chan_rxq.get(timeout=timeout)

    def rxwind(self, timeout=None):

        self.tx(('rx:wind', {}))

        mesg = self.next(timeout=timeout)
        if mesg is None:
            return

        if mesg[0] != 'tx:wind':
            logger.warning('rxwind expected tx:wind but got %s' % (mesg[0],))
            return

        item = self.next(timeout=timeout)
        while item is not None:
            self.tx(True)
            yield item
            item = self.next(timeout=timeout)

    def txwind(self, items, size, timeout=None):
        '''
        Execute a windowed transmission loop of each item in items.
        '''
        self.tx(('tx:wind', {}))

        mesg = self.next(timeout=timeout)
        if mesg is None:
            return

        if mesg[0] != 'rx:wind':
            logger.warning('txwind expected rx:wind but got %s' % (mesg[0],))
            return

        wind = 0
        for item in items:

            self.tx(item)
            wind += 1

            while wind >= size:

                acks = self.slice(size, timeout=timeout)
                if acks is None:
                    return False

                wind -= len(acks)

        while wind > 0:
            acks = self.slice(size, timeout=timeout)
            if acks is None:
                return False

            wind -= len(acks)

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
        data = mesg[1].get('data')

        chan = self.chans.get(iden)
        if chan is not None:
            # an init for an existing chan
            # (return init message from our tx)
            if data is not None:
                chan.rx(self, data)

            return

        if self.onchan is None:
            logger.warning('%r: got init without onchan' % (self,))
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

    def _tx_real(self, mesg):

        iden = mesg[1].get('chan')

        chan = self.chans.get(iden)
        if chan is None:
            logger.warning('tx() for missing chan')
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
        data = mesg[1].get('data')

        chan = self.chans.get(iden)
        if chan is None:
            return

        chan.setLinkProp('plex:link', link)

        if data is not None:
            chan.rx(self, data)

        chan.rxfini()

    def initPlexChan(self, iden, txinit=True):
        chan = Chan(self, iden, txinit=txinit)
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
        self.fino = sock.fileno()

        self.txbuf = b''
        self.txque = collections.deque() #(byts, info)
        self.txlock = threading.Lock()

        self.unpk = s_msgpack.Unpk()
        self.flags = select.EPOLLIN | select.EPOLLERR | select.EPOLLET

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

            if flags & select.EPOLLIN:

                self._rxloop()

                # chances are, after an rxloop(), a txloop() is needed...
                self._txloop()

                txdone = True

            if flags & select.EPOLLOUT and not txdone:
                self._txloop()

            if flags & select.EPOLLERR:
                self.fini()

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

            if self.flags & select.EPOLLOUT:
                return

            self.flags |= select.EPOLLOUT
            self.plex.modify(self.fino, self.flags)

    def _rxbytes(self, size):
        '''
        Try to recv size bytes.

        Args:
            size (int): The number of bytes to recv.

        Returns:
            (bytes): The bytes (or None) if would block.
        '''
        try:

            return self.sock.recv(size)

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
                        # we cant write any more without blocking
                        return

                    except BrokenPipeError as e:
                        logger.info('tx broken pipe: ignore...')
                        return

                    self.txbuf = self.txbuf[sent:]

                    # if we still have a txbuf, we've done all we can
                    if self.txbuf:
                        return

                # no more txbuf... are we done?
                if not self.txque:
                    self.flags &= ~select.EPOLLOUT
                    self.plex.modify(self.fino, self.flags)
                    return

                self.txbuf = self.txque.popleft()
