import functools
import threading
import synapse.glob as s_glob
import synapse.lib.plex as s_plex

import synapse.tests.common as s_test

class PlexTest(s_test.SynTest):
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

    @s_glob.synchelp
    async def test_plex_basic(self):
        '''
        Have two plexes connect to each other, send messages, and then server disconnects
        '''
        steps = self.getTestSteps(['onlink', 'onrx1', 'client_rx', 'link_fini'])
        with s_plex.Plex() as plex1, s_plex.Plex() as plex2:

            async def server_onlink(link):
                steps.done('onlink')

                async def do_rx(msg):
                    self.eq(msg, 'foo')
                    steps.done('onrx1')
                    await link.tx('bar')
                    await link.fini()

                link.onrx(do_rx)

            server = plex1.listen('127.0.0.1', None, onlink=server_onlink)
            _, port = server.sockets[0].getsockname()
            link2 = plex2.connect('127.0.0.1', port)
            steps.wait('onlink', timeout=1)

            async def client_do_rx(msg):
                self.eq(msg, 'bar')
                steps.done('client_rx')
            link2.onrx(client_do_rx)

            async def onlinkfini():
                steps.done('link_fini')

            link2.onfini(onlinkfini)
            await link2.tx('foo')
            steps.wait('onrx1', timeout=1)
            steps.wait('client_rx', timeout=1)
            steps.wait('link_fini')
