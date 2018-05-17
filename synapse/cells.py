'''
Constructors for the various cells.
( used for dmon config automation)
'''
import yaml
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.cryotank as s_cryotank

import synapse.lib.auth as s_auth
import synapse.lib.layer as s_layer

ctors = {
    'auth': s_auth.Auth,
    'layer': s_layer.Layer,
    'cortex': s_cortex.Cortex,
    'cryocell': s_cryotank.CryoCell,
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

def deploy(name, dirn, boot=None):
    '''
    Deploy a cell of the named type to the specified directory.
    '''
    ctor = ctors.get(name)
    if ctor is None:
        raise s_exc.NoSuchName(name=name, mesg='No cell ctor by that name')

    if boot is None:
        boot = {}

    boot['type'] = name

    # create the boot.yaml
    with s_common.genfile(dirn, 'boot.yaml') as fd:
        fd.write(yaml.safe_dump(boot).encode('utf8'))

    # Cell has a deploy static method (possibly per cell type)
    ctor.deploy(dirn)
