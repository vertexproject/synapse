import io
import unittest

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
