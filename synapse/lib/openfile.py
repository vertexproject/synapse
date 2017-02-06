'''
A single entry point for various protocol and open behaviors
to allow all file open (for read) requests to support URLs and
encapsulation.
'''
import io
import os
import codecs
import tornado.httpclient as t_http

from synapse.common import genpath

def _open_http(*paths,**opts):
    # all URLs use /
    purl = '/'.join(paths)
    http = t_http.HTTPClient()
    resp = http.fetch(purl)
    return resp.buffer

def openfd(*paths, **opts):
    '''
    Open and return a file like object for the given path/url.

    Example:

        with openfd('http://vertex.link/foo.csv') as fd:
            dostuff(fd)

        with openfd('foo/bar.txt') as fd:
            fd.read()

    '''
    if paths[0].startswith('http://') or paths[0].startswith('https://'):
        fd = _open_http(*paths,**opts)

    else:

        # allow relative opens from a base directory
        dirn = opts.get('file:basedir')
        if dirn != None and not os.path.isabs(paths[0]):
            paths = (dirn,) + paths

        path = genpath(*paths)
        fd = io.open(path,'rb')

    ncod = opts.get('encoding')
    if ncod != None:
        fd = codecs.getreader(ncod)(fd)

    return fd

    #FIXME hand off to universal decapsulator
