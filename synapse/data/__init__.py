import synapse.common as s_common
import synapse.lib.datfile as s_datfile

def get(name,defval=None):
    '''
    Return an object from the embedded synapse data folder.

    Example:

        for tld in syanpse.data.get('iana.tlds'):
            dostuff(tld)

    NOTE: Files are named synapse/data/<name>.mpk
    '''
    with s_datfile.openDatFile('synapse.data/%s.mpk' % name) as fd:
        return s_common.msgunpack( fd.read() )

