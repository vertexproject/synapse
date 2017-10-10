'''
Utilities for handling data files embedded within python packages.
'''
import os

import synapse.dyndeps as s_dyndeps

def openDatFile(datpath):
    '''
    Open a file-like object using a pkg relative path.

    Example:

        fd = openDatFile('foopkg.barpkg/wootwoot.bin')
    '''
    pkgname, filename = datpath.split('/', 1)

    pkgmod = s_dyndeps.getDynMod(pkgname)

    # are we a regular file?
    pkgfile = os.path.abspath(pkgmod.__file__)
    if os.path.isfile(pkgfile):
        dirname = os.path.dirname(pkgfile)
        datname = os.path.join(dirname, filename)
        return open(datname, 'rb')
