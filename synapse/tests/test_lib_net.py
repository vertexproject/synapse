
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

            def _onRecvPing(self, mesg):
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

            def _onRecvPong(self, mesg):
                steps.done('pong')

        with s_net.Plex() as plex:

            addr = plex.listen(('127.0.0.1', 0), LisnLink)
            plex.connect(addr, ConnLink)

            steps.waitall(timeout=2)
