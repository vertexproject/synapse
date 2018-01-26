import os
import select
import socket
import logging
import threading
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.reflect as s_reflect
import synapse.lib.threads as s_threads

logger = logging.getLogger(__file__)

'''
The synapse.lib.net module implements async networking helpers.
( and will slowly replace synapse.lib.socket )
'''

class TxQ(s_eventbus.EventBus):

    def __init__(self, size=None, ackd=False):

        s_eventbus.EventBus.__init__(self)

        self.nseq = 0
        self.ackd = ackd

        self.txque = collections.deque()
        self.akque = collections.deque()

    def reset(self):
        '''
        Reset the trasmission state.
        '''
        # put all un-acknowledged msgs back
        self.txque.extendleft(self.akque)

        self.akque.clear()

    #def ack(self, seqn):

        #while self.akque and self.akque[0][0] < seqn:
            #self.akque.popleft()

    # this should only ever be called by a multi-plexor thread
    #def next(self):
        #if not self.txque:
        #qent = self.txque.

    def iter(self):

        with self.lock:

            while self.txque:
                item = self.txque.popleft()
                self.akque

            for item in self.txque.popleft():
                self.akque.append(item)
                yield item

    def _set_tx(self, istx):

        # must be called with the lock

        if self.istx == istx:
            return

        self.istx = istx
        self.fire('istx', istx=True)

    def tx(self, item, **info):

        byts = s_msgpack.en(item)

        with self.lock:

            #if self.size and len(self.txque) >= size:
                #raise s_exc.TxFull()

            seqn = self.seqn
            self.seqn += 1

            self.txque.append((seqn, byts, info))

            self._set_tx(True)

def protorecv(name):
    '''
    Decorate a protocol message handler function.
    '''
    def wrap(f):
        f._proto_recv = name
        return f
    return wrap

class Plex(s_config.Config):
    '''
    A highly-efficient epoll based multi-plexor for sockets.
    '''
    def __init__(self, conf=None):

        s_config.Config.__init__(self, conf)

        self.epoll = select.epoll()

        self.socks = {}
        self.funcs = {}
        self.links = {}

        self.thrd = s_threads.worker(self._runPollLoop)

        self.onfini(self._onPlexFini)

        pmax = self.getConfOpt('pool:max')
        self.pool = s_threads.Pool(maxsize=pmax)

        self.onfini(self.pool.fini)

        self.funcs = {}
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

    def listen(self, addr, ctor):
        '''
        Initiate a listening socket with a Link constructor.

        Args:
            addr ((str,int)): A (host,port) socket address.
            ctor (function): A Link class constructor to handle connections.

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

                    link = self._initPlexLink(news, ctor)

                except BlockingIOError as e:
                    return

        self.socks[fino] = sock
        self.polls[fino] = poll

        self.epoll.register(fino, select.EPOLLIN | select.EPOLLERR | select.EPOLLET)
        return sock.getsockname()

    def _initPlexLink(self, sock, ctor):

        fino = sock.fileno()
        link = SockLink(self, sock)

        self.links[fino] = link
        self.polls[fino] = link.poll

        if self.socks.get(fino) is None:
            self.socks[fino] = sock
            self.epoll.register(fino, link.flags)

        else:
            self.epoll.modify(fino, link.flags)

        try:

            retn = ctor(link)
            link.onrx(retn.rx)

            retn.linked()

        except Exception as e:
            logger.warning('SockLink: %r ctor/linked error: %s' % (ctor, e))
            raise

        return retn

    def modify(self, fino, flags):
        '''
        Modify the epoll flags mask for the give file descriptor.

        Args:
            fino (int): The file descriptor number.
            flags (int): The epoll flags mask.
        '''
        return self.epoll.modify(fino, flags)

    def connect(self, addr, ctor, func=None):
        '''
        Perform a non-blocking connect with the given callback function.

        Args:
            addr ((str,int)): A (host,port) socket address.
            ctor (function): A link constructor.
            func (function): A func(ok, link) callback.
        '''
        sock = socket.socket()
        sock.setblocking(False)

        fino = sock.fileno()

        def poll(flags):

            self.polls.pop(fino, None)

            if not flags & select.EPOLLOUT:

                self._finiPlexSock(sock)

                errn = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                return func(False, errn)

            link = self._initPlexLink(sock, ctor)
            if func is not None:
                return func(True, link)

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

    def __init__(self, link):

        s_eventbus.EventBus.__init__(self)

        self.info = {}
        self.funcs = {}

        # TODO: heart beat via global sched
        self.rxtime = None
        self.txtime = None

        self.rxfunc = None
        self.isrxfini = False
        self.istxfini = False

        self.link = link

        self.funcs = self.handlers()
        self.onfini(self._onLinkFini)

    def onrx(self, func):
        '''
        Register a callback to recieve decapsulated messages.
        '''
        self.rxfunc = func

    def _onLinkFini(self):
        self.txfini()
        self.rxfini()

    def rxfini(self):
        '''
        Anotate that the link will no longer receive.
        '''
        if self.isrxfini:
            return

        self.isrxfini = True
        self._rx_fini()

        if self.istxfini:
            self.fini()

    def txfini(self, data=None):
        '''
        Annotate that the there is nothing more to send.
        '''
        if self.istxfini:
            return

        self.istxfini = True
        self._tx_fini()

        if self.isrxfini:
            self.fini()

    def linked(self):
        '''
        A sub-class implementable callback for link established.
        '''
        pass

    def handlers(self):
        '''
        Return a dict of <mesg>:<func> handlers for this link layer.
        '''
        return {}

    def get(self, name, defval=None):
        '''
        Return a previously set link property.

        Args:
            name (str): The property name.
            defval (obj): The default value.

        Returns:
            (obj): The property value or defval.
        '''
        return self.info.get(name, defval)

    def set(self, name, valu):
        '''
        Set a link property.

        Args:
            name (str): The property name.
            valu (obj): The property value.
        '''
        self.info[name] = valu

    def rx(self, mesg):
        '''
        Recv a message on this link and dispatch the message.
        '''
        self.rxtime = s_common.now()
        func = self.funcs.get(mesg[0])

        if func is None:
            logger.warning('link %s: unknown message type %s' % (self.__class__.__name__, mesg[0]))
            return

        try:
            func(mesg)

        except Exception as e:
            logger.exception('link %s: rx exception: %s' % (self.__class__.__name__, e))

    def tx(self, mesg):
        '''
        Transmit a message via this link.

        Args:
            mesg ((str,dict)): A message tufo.
        '''
        self.txtime = s_common.now()
        wrap = self._tx_wrap(mesg)
        return self.link.tx(wrap)

    def _tx_wrap(self, mesg):
        return mesg

    def _tx_fini(self):
        return

    def _rx_fini(self):
        return

class Chan(Link):

    def __init__(self, link, iden):
        Link.__init__(self, link)
        # we wrap but not chain...
        self.iden = iden

    def rx(self, mesg):
        self.rxfunc(mesg)

    def _tx_wrap(self, mesg):
        return ('data', {'chan': self.iden, 'data': mesg})

    def _tx_fini(self):
        mesg = ('fini', {'chan': self.iden})
        self.link.tx(mesg)

class ChanPlex(Link):
    '''
    A Link which has multiple channels.
    '''
    def __init__(self, link, func):
        Link.__init__(self, link)

        #self.ctor = ctor
        self.func = func
        self.chans = s_eventbus.BusRef()

        # TODO: chan timeouts... (maybe add to BusRef?)

        self.onfini(self.chans.fini)

    def handlers(self):
        return {
            'init': self._onChanInit,
            'data': self._onChanData,
            'fini': self._onChanFini,
        }

    def _onChanInit(self, mesg):

        iden = mesg[1].get('chan')
        data = mesg[1].get('data')

        chan = Chan(self, iden)
        self.chans.put(iden, chan)

        try:

            self.func(chan)

            if data is not None:
                chan.rx(data)

        except Exception as e:
            logger.warning('chan init error: %s' % (e,))
            chan.fini()

    def _onChanData(self, mesg):
        iden = mesg[1].get('chan')
        data = mesg[1].get('data')

        chan = self.chans.get(iden)
        chan.rx(data)

    def _onChanFini(self, mesg):

        iden = mesg[1].get('chan')
        data = mesg[1].get('data')

        chan = self.chans.get(iden)
        if chan is None:
            return

        if data is not None:
            chan.rx(data)

        chan.rxfini()

    def open(self, data=None):
        iden = os.urandom(16)

        chan = Chan(self, iden)
        self.chans.put(iden, chan)

        self.tx(('init', {'chan': iden, 'data': data}))

        self.func(chan)

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

            if flags & select.EPOLLIN:
                self.rxloop()

            if flags & select.EPOLLOUT:
                self.txloop()

            if flags & select.EPOLLERR:
                self.fini()

        except Exception as e:
            logger.exception('error during epoll event: %s for %r' % (e,self.sock))
            self.fini()

    def tx(self, mesg):
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


    def rx(self, mesg):
        self.rxfunc(mesg)

    def rxbytes(self, size):
        '''
        Try to recv size bytes.

        Args:
            size (int): The number of bytes to recv.

        Returns:
            (bytes): The bytes (or None) if would block.
        '''
        try:

            return self.sock.recv(size)

        except BlockingIOError as e:
            return None

    def rxloop(self):
        '''
        Run the recv loop for the Link.
        '''

        while not self.isfini:

            byts = self.rxbytes(1024000)
            if byts is None:
                return

            if not byts:
                self.fini()
                return

            for size, mesg in self.unpk.feed(byts):

                try:

                    self.rx(mesg)

                except Exception as e:
                    logger.exception('rxloop() error processing mesg: %r' % (mesg,))

    def txloop(self):
        '''
        Run the transmission loop for the Link.
        '''
        with self.txlock:

            # TODO: implement self.isfin half close
            while not self.isfini:

                if self.txbuf:

                    try:

                        sent = self.sock.send(self.txbuf)

                        # if we didn't send anything, gtfo
                        if sent == 0:
                            return

                    except BrokenPipeError as e:
                        logger.warning('tx broken pipe: ignore...')
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
