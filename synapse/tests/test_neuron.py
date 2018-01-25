import synapse.neuron as s_neuron

from synapse.tests.common import *

class NeuronTest(SynTest):

    def test_neuron_nosuch(self):

        with self.getTestDir() as dirn:
            self.raises(s_exc.NoSuchUser, s_neuron.opennode, 'visi@vertex.link', path=dirn)

    #def test_neuron_node(self):
