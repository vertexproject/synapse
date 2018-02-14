import logging

import synapse.lib.net as s_net

from synapse.tests.common import *

logger = logging.getLogger(__name__)

class NetTest(SynTest):

    def test_lib_net_chan_txfini(self):
        class FiniableLink(s_net.Link):
            def tx(self, msg, **kwargs):
                logger.error(msg)

        msg = '%r' % (('cool', {}),)
        with self.getLoggerStream('synapse.tests.test_lib_net', msg) as stream:
            chan = s_net.Chan(FiniableLink(), None)
            chan.txfini(data=('cool', {}))
            self.true(stream.wait(10))

        stream.seek(0)
        self.isin(msg, stream.read())

    def test_lib_net_chan_iden(self):
        iden = 'hehe'
        chan = s_net.Chan(None, iden)
        self.eq(chan.iden(), iden)

    def test_lib_net_chan_queue(self):
        chan = s_net.Chan(s_net.Link(), None)

        self.raises(AttributeError, chan.next)
        self.raises(AttributeError, chan.slice, 1337)
        with self.raises(AttributeError) as e:
            [logger.error(item) for item in chan.iter()]

        chan.setq()
        msgs = (
            ('woo1', {}),
            ('woo2', {}),
            ('woo3', {}),
            ('woo4', {}),
            ('woo5', {}),
        )

        [chan.rx(None, msg) for msg in msgs]
        self.eq(chan.next(timeout=1), msgs[0])
        self.eq(chan.next(timeout=1), msgs[1])
        self.eq(chan.next(timeout=1), msgs[2])
        self.eq(chan.next(timeout=1), msgs[3])
        self.eq(chan.next(timeout=1), msgs[4])
        self.none(chan.next(timeout=0.1))

        [chan.rx(None, msg) for msg in msgs]
        self.eq(chan.slice(4), [msgs[0], msgs[1], msgs[2], msgs[3]])
        self.eq(chan.next(timeout=1), msgs[4])
        self.none(chan.next(timeout=0.1))
        self.none(chan.slice(100, timeout=0.1))

        results = []
        [chan.rx(None, msg) for msg in msgs]
        [results.append(item) for item in chan.iter(timeout=1)]
        self.eq(results, list(msgs))
        [results.append(item) for item in chan.iter(timeout=1)]
        self.eq(results, list(msgs))

        self.false(chan._chan_rxq._que_done)
        chan.rxfini()
        self.true(chan._chan_rxq._que_done)
        [chan.rx(None, msg) for msg in msgs]
        self.none(chan.next(timeout=0.1))

    def test_lib_net_link_tx(self):
        class DstLink(s_net.Link):
            def __init__(self):
                s_net.Link.__init__(self)
                self.callcount = 0
            def tx(self, mesg):
                self.callcount += 1

        dstlink = DstLink()
        link = s_net.Link(link=dstlink)
        self.none(link.txtime)
        self.eq(dstlink.callcount, 0)

        link.tx(('cool', {}))
        first_txtime = link.txtime
        self.ge(first_txtime, 0)
        self.eq(dstlink.callcount, 1)

        link.rxfini()
        link.txfini(data=('cool', {}))
        second_txtime = link.txtime
        self.ge(second_txtime, first_txtime)
        self.eq(dstlink.callcount, 2)

        link.tx(('cool', {}))
        self.eq(link.txtime, second_txtime)
        self.eq(dstlink.callcount, 2)

    def test_lib_net_link_repr(self):
        link = s_net.Link()
        rep = link.__repr__()
        self.len(28, rep)
        self.true(rep.startswith('Link: None at 0x'))

    def test_lib_net_link_props(self):
        link = s_net.Link()
        self.none(link.getLinkProp('nope'))
        self.eq(link.getLinkProp('nope', defval=1337), 1337)
        self.none(link.setLinkProp('nope', 1337))
        self.eq(link.getLinkProp('nope'), 1337)

    def test_lib_net_link_onrx(self):
        msg = 'woohoo'
        def fn(self, *args, **kwargs):
            logger.error('woohoo')

        link = s_net.Link()
        link.onrx(fn)
        self.eq(link.rxfunc, fn)

        with self.getLoggerStream('synapse.tests.test_lib_net', msg) as stream:
            link.rx(None, ('haha', {}))
            self.true(stream.wait(10))

        stream.seek(0)
        self.isin(msg, stream.read())

    def test_lib_net_link_rx_unknownmsgtype(self):
        link = s_net.Link()
        msg = 'unknown message type haha'
        with self.getLoggerStream('synapse.lib.net', msg) as stream:
            link.rx(None, ('haha', {}))
            self.true(stream.wait(10))

        stream.seek(0)
        self.isin(msg, stream.read())

    def test_lib_net_link_rx_handlerexpcetion(self):
        class BadLink(s_net.Link):
            def handlers(self):
                return {'bad': self._badfn}

            def _badfn(self, link, msg):
                raise Exception('a bad happened')

        link = BadLink()
        msg = 'Exception: a bad happened'
        with self.getLoggerStream('synapse.lib.net', msg) as stream:
            link.rx(None, ('bad', {}))
            self.true(stream.wait(10))

        stream.seek(0)
        self.isin(msg, stream.read())

    def test_lib_net_link_rx_msgexpcetion(self):
        class OtherBadLink(s_net.Link):
            def __init__(self):
                s_net.Link.__init__(self)
                self._msg_funcs = 'nope'

            def handlers(self):
                return 'wat'

        link = OtherBadLink()
        msg = 'link OtherBadLink: rx mesg exception:'
        with self.getLoggerStream('synapse.lib.net', msg) as stream:
            link.rx(None, ('bad', {}))
            self.true(stream.wait(10))

        stream.seek(0)
        self.isin(msg, stream.read())

    def test_lib_net_link_rx_rxfuncexpcetion(self):
        class BaddestLink(s_net.Link):
            def __init__(self):
                s_net.Link.__init__(self)
                self.rxfunc = self._badfn

            def _badfn(self, link, msg):
                raise Exception('the baddest exception was raised')

        link = BaddestLink()
        msg = 'BaddestLink.rxfunc() failed on: (\'bad\', {})'
        with self.getLoggerStream('synapse.lib.net', msg) as stream:
            link.rx(None, ('bad', {}))
            self.true(stream.wait(10))

        stream.seek(0)
        self.isin(msg, stream.read())

    def test_lib_net_link_rx_finid(self):

        msg = 'if this was raised, the test should fail because the logger output isnt empty'
        class FinidLink(s_net.Link):
            def __init__(self):
                s_net.Link.__init__(self)
                self.rxfunc = self._fn

            def _fn(self, link, msg):
                raise Exception(msg)  # This shouldn't execute because the link will be finid.

        link = FinidLink()
        link.fini()
        link.rxfini()
        with self.getLoggerStream('synapse.lib.net', msg) as stream:
            link.rx(None, ('anything', {}))
            self.false(stream.wait(1))

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

    def test_lib_net_finis(self):

        names = ('conn', 'lisn')
        steps = self.getTestSteps(names)
        expected_msg = 'I WAS FINID'
        with self.getLoggerStream('synapse.tests.test_lib_net', expected_msg) as stream:

            class LisnLink(s_net.Link):

                def linked(self):
                    steps.done('lisn')

            class ConnLink(s_net.Link):

                def linked(self):
                    self.rxfini()
                    self.txfini(data='GOODBYE')
                    self.txfini()
                    steps.done('conn')

                def onfini(self, msg):
                    logger.error('I WAS FINID')

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

    def test_lib_net_connectfail(self):
        expected_msg = 'connect() onconn failed'
        with self.getLoggerStream('synapse.lib.net', expected_msg) as stream:
            with s_net.Plex() as plex:
                plex.connect(('127.0.0.1', 0), None)
                self.true(stream.wait(10))

        stream.seek(0)
        mesgs = stream.read()
        self.isin(expected_msg, mesgs)

    def test_lib_net_listenfail(self):
        expected_msg = 'listen() onlink error'
        with self.getLoggerStream('synapse.lib.net', expected_msg) as stream:

            with s_net.Plex() as plex:
                addr = plex.listen(('127.0.0.1', 0), None)
                plex.connect(addr, None)
                self.true(stream.wait(10))

        stream.seek(0)
        mesgs = stream.read()
        self.isin(expected_msg, mesgs)

    def test_lib_net_stoplisten(self):

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
                self.fini()
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
                self.tx(('ping', {'haha': 2}))
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
