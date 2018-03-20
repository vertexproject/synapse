'''
Constructors for the various cells.
( used for dmon config automation)
'''
import synapse.axon as s_axon
import synapse.neuron as s_neuron
import synapse.cryotank as s_cryotank

def cryo(dirn, conf=None):
    return s_cryotank.CryoCell(dirn, conf=conf)

def axon(dirn, conf=None):
    return s_axon.AxonCell(dirn, conf=conf)

def blob(dirn, conf=None):
    return s_axon.BlobCell(dirn, conf=conf)

def neuron(dirn, conf=None):
    return s_neuron.Neuron(dirn, conf=conf)
