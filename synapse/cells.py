'''
Constructors for the various cells.
( used for dmon config automation)
'''
#import synapse.axon as s_axon
import synapse.cortex as s_cortex
#import synapse.neuron as s_neuron
#import synapse.cryotank as s_cryotank

import synapse.lib.layer as s_layer

ctors = {
    'layer': s_layer.Layer,
    'cortex': s_cortex.Cortex,
}

def add(name, ctor):
    '''
    Add a Cell() constructor alias.
    '''
    ctors[name] = ctor

def init(name, dirn):
    '''
    Initialize and return a Cell() object by alias.
    '''
    ctor = ctors.get(name)
    if ctor is None:
        raise s_exc.NoSuchName(name=name, mesg='No cell ctor by that name')

    return ctor(dirn)

def deploy(name, dirn):

    ctor = ctors.get(name)
    if ctor is None:
        raise s_exc.NoSuchName(name=name, mesg='No cell ctor by that name')

#def cryo(dirn, conf=None):
    #return s_cryotank.CryoCell(dirn, conf=conf)

#def axon(dirn, conf=None):
    #return s_axon.AxonCell(dirn, conf=conf)

#def blob(dirn, conf=None):
    #return s_axon.BlobCell(dirn, conf=conf)

#def neuron(dirn, conf=None):
    #return s_neuron.Neuron(dirn, conf=conf)
