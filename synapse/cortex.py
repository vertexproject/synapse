class NoSuchScheme(Exception):pass
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
import synapse.telepath as s_telepath

import synapse.cores.ram
import synapse.cores.sqlite
import synapse.cores.postgres

corclasses = {
    'tcp':s_telepath.Proxy,

    'ram':synapse.cores.ram.Cortex,
    'sqlite':synapse.cores.sqlite.Cortex,
    'postgres':synapse.cores.postgres.Cortex,
}

def open(url):
    '''
    Construct or reference a cortex by url.

    Example:

        core = getCortex('ram://')

    Notes:
        * ram://
        * sqlite3:///<db>[?table=<table>]
        * postgres://[[<passwd>:]<user>@][<host>]/[<db>][?table=<table>]

        * default table name: syncortex

    Todo:
          auditfd=<fd>
          auditfile=<filename>

    '''
    link = s_link.chopLinkUrl(url)
    return openlink(link)

def openlink(link):
    '''
    Open a cortex via a link tuple.
    '''
    cls = corclasses.get(link[0])
    if cls == None:
        raise NoSuchScheme(link[0])
    return cls(link)
