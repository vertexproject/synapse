import synapse.lib.net as s_net

from synapse.tests.common import *

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

    def test_lib_net_unknown(self):

        names = ('conn', 'lisn')
        steps = self.getTestSteps(names)
        expected_msg = 'unknown message type wat'

        with self.getLoggerStream('synapse.lib.net', expected_msg) as stream:

            class LisnLink(s_net.Link):

                def linked(self):
                    steps.done('lisn')

            class ConnLink(s_net.Link):

                def linked(self):
                    steps.done('conn')
                    self.tx(('wat', {}))

            with s_net.Plex() as plex:

                def onconn(ok, link):
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
                self.true(stream.wait(10))

            stream.seek(0)
            mesgs = stream.read()
            self.isin(expected_msg, mesgs)
