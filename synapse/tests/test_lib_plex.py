import os
import logging
import functools
import threading

import synapse.glob as s_glob
import synapse.lib.plex as s_plex
import synapse.lib.certdir as s_certdir

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class PlexTest(s_t_utils.SynTest):
    def test_plex_callLater(self):
        evt = threading.Event()
        data = {}

        def func(*args, **kwargs):
            evt.set()
            data['args'] = args
            data['kwargs'] = kwargs

        partial = functools.partial(func, 1, 2, key='valu')

        t0 = s_glob.plex.time()
        delay = 0.1
        s_glob.plex.callLater(delay, partial)
        self.true(evt.wait(2))
        t1 = s_glob.plex.time()
        self.ge(t1 - t0, delay)
        self.isin('args', data)
        self.isin('kwargs', data)

    def test_plex_callAt(self):
        evt = threading.Event()
        data = {}

        @s_glob.inpool
        def func(*args, **kwargs):
            evt.set()
            data['args'] = args
            data['kwargs'] = kwargs

        partial = functools.partial(func, 1, 2, key='valu')

        t0 = s_glob.plex.time()
        delay = 0.2
        s_glob.plex.callAt(t0 + delay, partial)
        self.true(evt.wait(3))
        t1 = s_glob.plex.time()
        self.ge(t1 - t0, delay)
        self.isin('args', data)
        self.isin('kwargs', data)

    async def test_plex_basic(self):
        '''
        Have two plexes connect to each other, send messages, and then server disconnects
        '''
        steps = self.getTestSteps(['onlink', 'onrx1', 'client_rx', 'link_fini'])
        with s_plex.Plex() as plex1, s_plex.Plex() as plex2:

            servers = []

            async def server_onlink(link):
                steps.done('onlink')

                async def do_rx(msg):
                    self.eq(msg, 'foo')
                    steps.done('onrx1')
                    await link.tx('bar')
                    await link.fini()

                link.onrx(do_rx)

            async def do_listen():
                server = await plex1.listen('127.0.0.1', None, onlink=server_onlink)
                servers.append(server)
                _, port = server.sockets[0].getsockname()
                return port

            port = plex1.coroToSync(do_listen())
            link2 = plex2.connect('127.0.0.1', port)
            await steps.asyncwait('onlink', timeout=1)

            async def client_do_rx(msg):
                self.eq(msg, 'bar')
                steps.done('client_rx')
            link2.onrx(client_do_rx)

            async def onlinkfini():
                steps.done('link_fini')

            link2.onfini(onlinkfini)
            await link2.tx('foo')
            await steps.asyncwait('onrx1', timeout=1)
            await steps.asyncwait('client_rx', timeout=1)
            await steps.asyncwait('link_fini')
            # Tear down the socket server
            for server in servers:
                try:
                    server.close()
                except Exception:
                    logger.exception('Error tearing down socket server.')

    async def test_plex_tls(self):
        '''
        Have two plexes connect to each other over TLS, send messages, and then server disconnects
        '''
        certdir = s_certdir.CertDir(os.path.join(self.getTestFilePath(), 'certdir'))
        steps = self.getTestSteps(['onlink', 'onrx1', 'client_rx', 'link_fini'])
        with s_plex.Plex() as plex1, s_plex.Plex() as plex2:

            servers = []

            async def server_onlink(link):
                steps.done('onlink')

                async def do_rx(msg):
                    self.eq(msg, 'foo')
                    steps.done('onrx1')
                    await link.tx('bar')
                    await link.fini()

                link.onrx(do_rx)

            async def do_listen():
                sslctx = certdir.getServerSSLContext('localhost')

                server = await plex1.listen('127.0.0.1', None, onlink=server_onlink, ssl=sslctx)
                servers.append(server)
                _, port = server.sockets[0].getsockname()
                return port

            port = plex1.coroToSync(do_listen())
            sslctx = certdir.getClientSSLContext()
            link2 = plex2.connect('localhost', port, ssl=sslctx)
            await steps.asyncwait('onlink', timeout=1)

            async def client_do_rx(msg):
                self.eq(msg, 'bar')
                steps.done('client_rx')
            link2.onrx(client_do_rx)

            async def onlinkfini():
                steps.done('link_fini')

            link2.onfini(onlinkfini)
            await link2.tx('foo')
            await steps.asyncwait('onrx1', timeout=1)
            await steps.asyncwait('client_rx', timeout=1)
            await steps.asyncwait('link_fini')
            # Tear down the socket server
            for server in servers:
                try:
                    server.close()
                except Exception:
                    logger.exception('Error tearing down socket server.')
