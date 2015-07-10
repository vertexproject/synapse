class NoSuchScheme(Exception):pass

import synapse.cores.ram
import synapse.cores.sqlite
import synapse.cores.postgres

corclasses = {
    'ram':synapse.cores.ram.Cortex,
    'sqlite':synapse.cores.sqlite.Cortex,
    'postgres':synapse.cores.postgres.Cortex,
}

def getCortex(scheme,**corinfo):
    '''
    Construct a Cortex instance by scheme.

    ( see: synapse.cores.common.Cortex )

    Example:

        core = getCortex('ram')

    Notes:

        * scheme <all>
          auditfd=<fd>
          auditfile=<filename>

        * scheme 'ram'

        * scheme 'sqlite3'
          dbname=<dbfile> | db=<db>

          Optional:
            tablename=<name> (default: syncortex)

        * scheme 'postgres'
          db=<dbname>
          host=<hostname>
          user=<username>
          passwd=<passwd>

          Optional:
            tablename=<name> (default: syncortex)

    '''
    cls = corclasses.get(scheme)
    if cls == None:
        raise NoSuchScheme(scheme)
    return cls(**corinfo)
