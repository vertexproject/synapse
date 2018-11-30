'''
Constructors for the various cells.
( used for dmon config automation)
'''
import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.cryotank as s_cryotank

import synapse.lib.auth as s_auth
import synapse.lib.lmdblayer as s_lmdblayer
import synapse.lib.remotelayer as s_remotelayer

ctors = {
    'auth': s_auth.Auth,
    'axon': s_axon.Axon,
    'layer-lmdb': s_lmdblayer.LmdbLayer,
    'layer-remote': s_remotelayer.RemoteLayer,
    'cortex': s_cortex.Cortex,
    'blobstor': s_axon.BlobStor,
    'cryocell': s_cryotank.CryoCell,
    'cryotank': s_cryotank.CryoTank
}

def add(name, ctor):
    '''
    Add a Cell() constructor alias.

    Args:
        name (str): Name of the cell alias.
        ctor: Function used to create the Cell().

    Notes:
        Third party modules which implement ``synapse.lib.cell.Cell`` classes
        should import ``synapse.cells`` and register an alias and class path
        for their ``Cell`` using this function.  This can be done in a module
        ``__init__.py`` file.
    '''
    ctors[name] = ctor

async def init(name, dirn, *args, **kwargs):
    '''
    Initialize and return a Cell() object by alias.
    '''
    ctor = ctors.get(name)
    if ctor is None:
        raise s_exc.NoSuchName(name=name, mesg='No cell ctor by that name')

    return await ctor.anit(dirn, *args, **kwargs)

async def initFromDirn(dirn, *args, **kwargs):
    '''
    As above, but retrieves type from boot.yaml in dirn
    '''
    conf = s_common.yamlload(dirn, 'boot.yaml') or {}
    kind = conf.get('type')
    if type is None:
        raise s_exc.BadConfValu('boot.yaml missing type key')
    return await init(kind, dirn, *args, **kwargs)

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
    s_common.yamlsave(boot, dirn, 'boot.yaml')

    # Cell has a deploy class method (possibly per cell type)
    ctor.deploy(dirn)

def getCells():
    '''
    Get a list of registered cell aliases and their fully qualified paths.
    '''
    ret = []
    for alias, ctor in ctors.items():
        ret.append((alias, '.'.join([ctor.__module__, ctor.__qualname__])))
    return ret
