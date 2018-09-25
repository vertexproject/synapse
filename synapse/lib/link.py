import socket
import asyncio
import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.queue as s_queue
import synapse.lib.msgpack as s_msgpack

class Link(s_base.Base):
    '''
    A Link() is created for each Plex sock.
    '''
    async def __anit__(self, plex, reader, writer):

        await s_base.Base.__anit__(self)

        self.plex = plex
        self.iden = s_common.guid()

        self.reader = reader
        self.writer = writer

        self.sock = self.writer.get_extra_info('socket')

        self._drain_lock = asyncio.Lock(loop=plex.loop)

        # disable nagle ( to minimize latency for small xmit )
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # enable TCP keep alives...
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, 'TCP_KEEPIDLE'):
            # start sending a keep alives after 3 sec of inactivity
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 3)
            # send keep alives every 3 seconds once started
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
            # close the socket after 5 failed keep alives (15 sec)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

        self.info = {}
        self.chans = {}

        self.unpk = s_msgpack.Unpk()
        self.txque = asyncio.Queue(maxsize=1000, loop=plex.loop)
        self.rxfunc = None

        async def fini():

            [await c.fini() for c in self.chans.values()]
            self.writer.close()

        self.onfini(fini)

    def chan(self, iden=None):

        if iden is None:
            iden = s_common.guid()

        chan = Chan(self, iden)

        async def fini():
            self.chans.pop(iden, None)

        chan.onfini(fini)
        self.chans[iden] = chan

        return chan

    async def tx(self, mesg):
        '''
        Async transmit routine which will wait for writer drain().
        '''
        if self.isfini:
            logger.debug('Attempt to transmit on disconnected link')
            return False

        if self.rxfunc is None:
            raise s_exc.NoLinkRx()

        byts = s_msgpack.en(mesg)
        try:
            self.writer.write(byts)
            # Avoid Python bug.  See https://bugs.python.org/issue29930
            async with self._drain_lock:
                await self.writer.drain()
        except ConnectionError as e:
            await self.fini()
            einfo = s_common.retnexc(e)
            logger.debug('link.tx connection trouble %s', einfo)
            return False

        return True

    async def rx(self, mesg):
        '''
        Routine called by Plex to rx a mesg for this Link.
        '''
        coro = self.rxfunc(mesg)
        if s_coro.iscoro(coro):
            await coro

    def onrx(self, func):
        '''
        Register the rx function for the link.

        NOTE: recv loop only begins once this is set!
        NOTE: func *must* be a coroutine function.
        '''
        if self.rxfunc:
            raise Exception('already set...')

        self.rxfunc = func
        self.plex.initLinkLoop(self)

    def get(self, name, defval=None):
        '''
        Get a property from the Link info.
        '''
        return self.info.get(name, defval)

    def set(self, name, valu):
        '''
        Set a property in the Link info.
        '''
        self.info[name] = valu

    def feed(self, byts):
        '''
        Used by Plex() to unpack bytes.
        '''
        return self.unpk.feed(byts)

class Chan(s_base.Base):
    '''
    An on-going data channel in a Link.
    '''
    async def __anit__(self, link, iden):
        await s_base.Base.__anit__(self)

        self.link = link
        self.iden = iden

        self.info = dict(link.info)
        self.rxque = s_queue.Queue()

    async def txfini(self):
        '''
        We are done sending on this channel.
        '''
        wrap = ('chan:data', {
            'chan': self.iden,
            'retn': None,
        })

        return await self.link.tx(wrap)

    async def init(self, task):
        '''
        Send a chan init message.
        '''
        mesg = ('chan:init', {
            'task': task,
            'chan': self.iden,
        })
        return await self.link.tx(mesg)

    async def tx(self, data):

        if self.isfini:
            return False

        wrap = ('chan:data', {
            'chan': self.iden,
            'retn': (True, data),
        })

        return await self.link.tx(wrap)

    async def txexc(self, exc):
        retn = s_common.retnexc(exc)
        wrap = ('chan:data', {
            'chan': self.iden,
            'retn': retn,
        })
        return await self.link.tx(wrap)

    def rx(self, item):
        '''
        Add an item to the rx queue. Used by Plex.
        '''
        if self.isfini:
            return

        self.rxque.put(item)

    def rxfini(self):
        self.rxque.put(s_common.novalu)

    def __iter__(self):
        try:

            for retn in self.rxque:

                if retn is None:
                    break

                yield s_common.result(retn)

        finally:
            s_glob.sync(self.fini())
