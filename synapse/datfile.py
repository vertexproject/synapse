'''
Utilities for handling data files embedded within python packages.
'''
import os
import synapse.dyndeps as s_dyndeps
import synapse.mindmeld as s_mindmeld

def openDatFile(datpath):
    '''
    Open a file-like object using a pkg relative path.

    Example:

        fd = openDatFile('foopkg.barpkg/wootwoot.bin')

    Notes:

        * This API supports datfiles in the plain filesystem,
          embedded within pyz files, and datfiles included in
          mindmeld code bundles.
    '''
    pkgname,filename = datpath.split('/',1)

    pkgmod = s_dyndeps.getDynMod(pkgname)

    loader = getattr(pkgmod,'__loader__',None)
    if isinstance(loader, s_mindmeld.MindMeld):
        return loader.openDatFile(datpath)

    # are we a regular file?
    pkgfile = os.path.abspath( pkgmod.__file__ )
    if os.path.isfile(pkgfile):
        dirname = os.path.dirname(pkgfile)
        datname = os.path.join(dirname, filename)
        return open(datname,'rb')

