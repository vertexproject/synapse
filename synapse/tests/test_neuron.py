import io
import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.neuron as s_neuron
import synapse.common as s_common

class TestNeuron(unittest.TestCase):

    def test_neuron_peering(self):
        neu1 = s_neuron.Daemon()
        neu2 = s_neuron.Daemon()
        neu3 = s_neuron.Daemon()

        cert1 = neu1.getNeuInfo('peercert')
        cert2 = neu2.getNeuInfo('peercert')
        cert3 = neu3.getNeuInfo('peercert')

        neu1.addPeerCert(cert2)
        neu1.addPeerCert(cert3)

        neu2.addPeerCert(cert1)
        neu2.addPeerCert(cert3)

        neu3.addPeerCert(cert1)
        neu3.addPeerCert(cert2)

        link1 = s_link.chopLinkUrl('tcp://127.0.0.1:0')

        #link1 = s_common.tufo('tcp',listen=('0.0.0.0',0))
        neu1.runLinkServer(link1)

        evt1 = threading.Event()
        def peer1init(event):
            evt1.set()

        evt2 = threading.Event()
        def peer2init(event):
            evt2.set()

        evt3 = threading.Event()
        def peer3init(event):
            evt3.set()

        neu1.on('neu:peer:init',peer1init)
        neu2.on('neu:peer:init',peer2init)
        neu3.on('neu:peer:init',peer3init)

        neu2.runLinkPeer(link1)

        self.assertTrue( evt1.wait(3) )
        self.assertTrue( evt2.wait(3) )

        neu3.runLinkPeer(link1)
        self.assertTrue( evt3.wait(3) )

        rtt1 = neu1.syncPingPeer(neu2.ident)
        rtt2 = neu2.syncPingPeer(neu1.ident)

        # check that 3 can reach 2 via 1
        rtt3 = neu3.syncPingPeer(neu2.ident)

        self.assertIsNotNone(rtt1)
        self.assertIsNotNone(rtt2)
        self.assertIsNotNone(rtt3)

        neu1.fini()
        neu2.fini()
        neu3.fini()

    def test_neuron_keepstate(self):
        return
        fd = io.BytesIO()
        neu = s_neuron.Daemon(statefd=fd)

        peer1 = s_common.guid()
        peer2 = s_common.guid()

        apikey1 = neu.initApiKey('haha')
        apikey2 = neu.initApiKey('hehe')

        neu.setNeuInfo('woot',100)
        neu.setPeerInfo(peer1,'bar',80)
        neu.setPeerInfo(peer2,'bar',90)

        neu.setApiKeyInfo(apikey1,'foo',30)
        neu.setApiKeyInfo(apikey2,'foo',40)

        self.assertEqual( neu.getNeuInfo('woot'), 100 )
        self.assertEqual( neu.getPeerInfo(peer1,'bar'), 80 )
        self.assertEqual( neu.getPeerInfo(peer2,'bar'), 90 )
        self.assertEqual( neu.getApiKeyInfo(apikey1,'foo'), 30 )
        self.assertEqual( neu.getApiKeyInfo(apikey2,'foo'), 40 )

        fd.flush()
        fd.seek(0)

        neu = s_neuron.Neuron(statefd=fd)

        self.assertEqual( neu.getPeerInfo(peer1,'bar'), 80 )
        self.assertEqual( neu.getPeerInfo(peer2,'bar'), 90 )
        self.assertEqual( neu.getApiKeyInfo(apikey1,'foo'), 30 )
        self.assertEqual( neu.getApiKeyInfo(apikey2,'foo'), 40 )

    def test_neuron_route_basics(self):

        neuron = s_neuron.Daemon()

        ident = neuron.ident
        peers = [ s_common.guid() for i in range(3) ]

        neuron.addPeerGraphEdge( ident, peers[0] )
        neuron.addPeerGraphEdge( peers[0], ident )

        neuron.addPeerGraphEdge( peers[0], peers[1] )
        neuron.addPeerGraphEdge( peers[1], peers[0] )

        neuron.addPeerGraphEdge( peers[1], peers[2] )
        neuron.addPeerGraphEdge( peers[2], peers[1] )

        route = neuron._getPeerRoute( peers[2] )

        self.assertListEqual( route, [ ident, peers[0], peers[1], peers[2] ] )
        neuron.fini()

    #def test_neuron_route_asymetric(self):
    #def test_neuron_route_teardown(self):
