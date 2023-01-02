import os

import synapse.common as s_common
import synapse.lib.datfile as s_datfile
import synapse.lib.msgpack as s_msgpack

dirname = os.path.dirname(__file__)

def get(name, defval=None):
    '''
    Return an object from the embedded synapse data folder.

    Example:

        for tld in synapse.data.get('iana.tlds'):
            dostuff(tld)

    NOTE: Files are named synapse/data/<name>.mpk
    '''
    with s_datfile.openDatFile('synapse.data/%s.mpk' % name) as fd:
        return s_msgpack.un(fd.read())

def path(*names):
    return s_common.genpath(dirname, *names)
