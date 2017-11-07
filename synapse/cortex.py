import os
import json
import logging
'''
A synapse cortex is a data storage and indexing abstraction
which is designed to be used as a prop/valu index on various
storage backings.

Most fundamentally, a cortex instance contains rows of:
<id> | <prop> | <valu> | <time>

and is expected to provide indexed access to rows, allow bulk
insertion, and provide for atomic deconfliction if needed.

'''
import synapse.link as s_link
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.telepath as s_telepath

import synapse.cores.ram
import synapse.cores.lmdb
import synapse.cores.common
import synapse.cores.sqlite
import synapse.cores.storage
import synapse.cores.postgres

import synapse.cores.common as s_cores_common

logger = logging.getLogger(__name__)

class InvalidParam(Exception):
    def __init__(self, name, msg):
        Exception.__init__(self, '%s invalid: %s' % (name, msg))
        self.param = name

storectors = {
    'lmdb': synapse.cores.lmdb.LmdbStorage,
    'sqlite': synapse.cores.sqlite.SqliteStorage,
    'ram': synapse.cores.ram.RamStorage,
    'postgres': synapse.cores.postgres.PsqlStorage,
}

def _initDirCore(link, conf, sconf):
    return fromdir(link[1].get('path'), conf=conf)

corctors = {
    'dir': _initDirCore,
    'lmdb': synapse.cores.lmdb.initLmdbCortex,
    'sqlite': synapse.cores.sqlite.initSqliteCortex,
    'ram': synapse.cores.ram.initRamCortex,
    'postgres': synapse.cores.postgres.initPsqlCortex,
}

def fromdir(path, conf=None):
    '''
    Initialize a cortex from a directory.

    Args:
        path (str): The path to the directory
        conf (dict): An optional set of config info

    Returns:
        (synapse.cores.common.Cortex)
    '''
    if conf is None:
        conf = {}

    path = s_common.genpath(path)
    os.makedirs(path, exist_ok=True)

    conf['dir'] = path

    corepath = os.path.join(path, 'core.db')

    confpath = os.path.join(path, 'config.json')
    if not os.path.isfile(confpath):
        with open(confpath, 'wb') as fd:
            fd.write(b'{\n}')

    with open(confpath, 'r', encoding='utf8') as fd:
        text = fd.read()
        conf.update(json.loads(text))

    #TODO config option for lmdb?
    return openurl('sqlite:///%s' % (corepath,), conf=conf)

def fromstore(stor, **conf):
    '''
    Create and return a Cortex for the given Storage layer object.

    Args:
        stor (Storage): A synapse.cores.storage.Storage instance.
        conf (dict):    A cortex config dictionary

    Returns:
        (synapse.cores.common.Cortex):  The Cortex hypergraph instance.

    '''
    return synapse.cores.common.Cortex(None, stor, **conf)

def openstore(url, storconf=None, **opts):
    '''
    Opens or creates a Cortex Storage object by URL.

    This does not attempt to open Storage objects over telepath.

    Args:
        url (str): URL which is parsed in order to connect to.
        storconf (dict): Configable options passed to the storage layer.
        **opts (dict): Additional options added to the link tufo from the
            parsed URL.

    Example:
        Opening a object and adding a row::

            tick = s_common.now()
            url = 'sqlite:///./derry.db'
            store = openstore(url)
            store.addRows([('1234', 'syn:test', 'what', tick)])

    Returns:
        synapse.cores.storage.Storage: A storage object implementing a specific backend.

    Raises:
        NoSuchImpl: If the requested protocol has no storage implementation.
    '''
    if not storconf:
        storconf = {}

    link = s_link.chopLinkUrl(url)
    link[1].update(opts)

    ctor = storectors.get(link[0])
    if ctor is None:
        raise s_common.NoSuchImpl(name=link[0], mesg='No storage ctor registered for {}'.format(link[0]))

    return ctor(link, **storconf)

def openurl(url, conf=None, storconf=None, **opts):
    '''
    Construct or reference a cortex by url.

    This will open a cortex if there is a registered handler for the URL
    otherwise it will attempt to connect to the URL via Telepath.

    If telepath is used, any configable options passed via openurl will
    not be automatically set.

    Args:
        url (str): URL which is parsed in order to connect to.
        conf (dict): Configable options passed to the Cortex.
        storconf (dict): Configable options passed to the storage layer.
        **opts (dict): Additional options added to the link tufo from the
            parsed URL.

    Examples:
        Open up a ram backed cortex::

            core = openurl('ram:///')

        Open up a remote cortex over telepath::

            core = openurl('tcp://1.2.3.4:10000/core)

    Notes:
        The following handlers are registerd by default:
            * ram://
            * sqlite:///<db>
            * lmdb:///<db>
            * postgres://[[<passwd>:]<user>@][<host>]/[<db>][/<table>]

        For SQL databases, the default table name is "syncortex"

    Returns:
        s_cores_common.Cortex: Cortex object or a telepath proxy for a Cortex.
    '''

    # Todo
    #   auditfd=<fd>
    #   auditfile=<filename>

    if not conf:
        conf = {}
    if not storconf:
        storconf = {}

    link = s_link.chopLinkUrl(url)

    link[1].update(opts)
    return openlink(link, conf, storconf)

def openlink(link, conf=None, storconf=None,):
    '''
    Open a cortex via a link tuple.
    '''
    ctor = corctors.get(link[0])
    if ctor is None:
        return s_telepath.openlink(link)

    return ctor(link, conf, storconf)

def choptag(tag):
    '''
    Chop a tag into hierarchal levels.
    '''
    parts = tag.split('.')
    return ['.'.join(parts[:x + 1]) for x in range(len(parts))]

def _ctor_cortex(conf):
    url = conf.pop('url', None)
    if url is None:
        raise s_common.BadInfoValu(name='url', valu=None, mesg='cortex ctor requires "url":<url> option')

    core = openurl(url, conf=conf)

    return core

s_dyndeps.addDynAlias('syn:cortex', _ctor_cortex)

if __name__ == '__main__':  # pragma: no cover
    import sys

    import synapse.lib.cmdr as s_cmdr

    core = openurl(sys.argv[1])

    cmdr = s_cmdr.getItemCmdr(core)

    cmdr.runCmdLoop()
