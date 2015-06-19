import io
import unittest

import synapse.daemon as s_daemon
import synapse.neuron as s_neuron
import synapse.common as s_common

class TestNeuron(unittest.TestCase):

    def test_neuron_keepstate(self):
        return
        fd = io.BytesIO()
        neu = s_neuron.Neuron(statefd=fd)

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

        #neu,peers = self.getNeuronMesh(3)

        daemon = s_daemon.Daemon()

        neuron = daemon.loadSynService('neuron')

        ident = neuron.ident
        peers = [ s_common.guid() for i in range(3) ]

        neuron._addPeerLink( ident, peers[0] )
        neuron._addPeerLink( peers[0], ident )

        neuron._addPeerLink( peers[0], peers[1] )
        neuron._addPeerLink( peers[1], peers[0] )

        neuron._addPeerLink( peers[1], peers[2] )
        neuron._addPeerLink( peers[2], peers[1] )

        route = neuron._getPeerRoute( peers[2] )

        self.assertListEqual( route, [ ident, peers[0], peers[1], peers[2] ] )
        daemon.synFini()

    #def test_neuron_route_asymetric(self):
    #def test_neuron_route_teardown(self):
