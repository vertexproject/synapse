import synapse.common as s_common

import synapse.lib.datfile as s_datfile
import synapse.lib.msgpack as s_msgpack

def get(name, defval=None):
    '''
    Return an object from the embedded synapse data folder.

    Example:

        for tld in syanpse.data.get('iana.tlds'):
            dostuff(tld)

    NOTE: Files are named synapse/data/<name>.mpk
    '''
    with s_datfile.openDatFile('synapse.data/%s.mpk' % name) as fd:
        return s_msgpack.un(fd.read())
