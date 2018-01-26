
'''
Constructors for the various cells.
( used for dmon config automation)
'''
import synapse.neuron as s_neuron

def neuron(dirn, conf=None):
    return s_neuron.Neuron(dirn, conf=conf)

#def axon(dirn, conf=None):
#def cortex(dirn, conf=None):
