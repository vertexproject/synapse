import logging

import synapse.lib.net as s_net

from synapse.tests.common import *

logger = logging.getLogger(__name__)

class NetTest(SynTest):

    def test_lib_net_basic(self):

        names = ('conn', 'lisn', 'ping', 'pong')

        steps = self.getTestSteps(names)

        class LisnLink(s_net.Link):

            def linked(self):
                steps.done('lisn')

            def handlers(self):
                return {
                    'ping': self._onRecvPing,
                }

            def _onRecvPing(self, link, mesg):
                self.tx(('pong', {}))
                steps.done('ping')

        class ConnLink(s_net.Link):

            def linked(self):
                self.tx(('ping', {'haha': 2}))
                steps.done('conn')

            def handlers(self):
                return {
                    'pong': self._onRecvPong,
                }

            def _onRecvPong(self, link, mesg):
                steps.done('pong')

        with s_net.Plex() as plex:

            def onconn(ok, link):

                if not ok:
                    erno = link
                    estr = os.strerror(erno)
                    logger.error('test_lib_net_basic.onconn() error: %d %s' % (erno, estr))
                    return

                conn = ConnLink(link)
                link.onrx(conn.rx)
                conn.linked()

            def onlink(link):
                lisn = LisnLink(link)
                link.onrx(lisn.rx)
                lisn.linked()

            addr = plex.listen(('127.0.0.1', 0), onlink)
            plex.connect(addr, onconn)

            steps.waitall(timeout=2)

    def test_lib_net_pool(self):

        data = {}
        steps = self.getTestSteps(('accepted', 'connected'))

        def onlisn(link):
            data['lisn'] = link
            steps.done('accepted')

        with s_net.Plex() as plex:

            addr = plex.listen(('127.0.0.1', 0), onlisn)

            def onconnect(link):
                steps.done('connected')

            with s_net.LinkPool() as pool:

                pool.addLinkAddr('foo', addr, onconnect)

                steps.waitall(timeout=2)
                steps.clear('connected')

                lisn = data.get('lisn')
                lisn.fini()

                steps.wait('connected', timeout=2)
