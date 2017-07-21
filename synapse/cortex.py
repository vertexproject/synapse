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
import synapse.cores.sqlite
import synapse.cores.postgres

logger = logging.getLogger(__name__)

class InvalidParam(Exception):
    def __init__(self, name, msg):
        Exception.__init__(self, '%s invalid: %s' % (name, msg))
        self.param = name

corctors = {
    'lmdb': synapse.cores.lmdb.initLmdbCortex,
    'sqlite': synapse.cores.sqlite.initSqliteCortex,
    'ram': synapse.cores.ram.initRamCortex,
    'postgres': synapse.cores.postgres.initPsqlCortex,
}

def openurl(url, **opts):
    '''
    Construct or reference a cortex by url.

    Example:

        core = openurl('ram://')

    Notes:
        * ram://
        * sqlite:///<db>
        * postgres://[[<passwd>:]<user>@][<host>]/[<db>][/<table>]

        * default table name: syncortex

    Todo:
          auditfd=<fd>
          auditfile=<filename>

    '''
    link = s_link.chopLinkUrl(url)

    link[1].update(opts)
    return openlink(link)

def openlink(link):
    '''
    Open a cortex via a link tuple.
    '''
    ctor = corctors.get(link[0])
    if ctor is None:
        return s_telepath.openlink(link)

    return ctor(link)

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

    core = openurl(url)
    core.setConfOpts(conf)

    return core

s_dyndeps.addDynAlias('syn:cortex', _ctor_cortex)

if __name__ == '__main__':  # pragma: no cover
    import sys

    import synapse.lib.cmdr as s_cmdr

    core = openurl(sys.argv[1])

    cmdr = s_cmdr.getItemCmdr(core)

    cmdr.runCmdLoop()
