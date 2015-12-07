'''
A modular WebDAV server.
'''
import os
import io
import re
import socket
import threading

import tornado
import tornado.web
import tornado.ioloop
import tornado.httpserver

from xml.etree.ElementTree import Element, tostring, fromstring

import synapse.lib.cache as s_cache
import synapse.lib.threads as s_threads

from synapse.eventbus import EventBus

# TODO: sub-class AsyncBoss and make callback helpers
# TODO: offer digest auth so windows is happy
# TODO: support limited response and range 
# TODO: find a way to trick linux to open non-listed files

# the default OPTIONS request headers
meths = 'GET, HEAD, POST, PUT, DELETE, OPTIONS, PROPFIND, PROPPATCH, MKCOL, LOCK, UNLOCK, MOVE, COPY'
opthdrs = {
    'dav':'1, 2',
    'allow':meths,
    'content-length':'0',
    'ms-author-via':'DAV',
}

# translate PathNode stat to webdav
davprops = {
    'mime':'{DAV:}getcontenttype',
    'size':'{DAV:}getcontentlength',
}

def statfd(fd):
    '''
    Return a stat dict for the given fd.
    '''
    fd.seek(0, os.SEEK_END)
    size = fd.tell()
    return {'size':size}

class WebDavHandler(tornado.web.RequestHandler):

    SUPPORTED_METHODS = tornado.web.RequestHandler.SUPPORTED_METHODS + ('PROPFIND',)

    def initialize(self, webdav):
        self.webdav = webdav

    @tornado.web.asynchronous
    def propfind(self):

        #print('propfind: %s %r' % (self.request.path, self.request.headers))
        #tree = fromstring( self.request.body )

        #wants = set()
        #for elem in tree.findall('.//{DAV:}prop'):
            #for prop in elem:
                #wants.add(prop.tag)

        dyns,node = self.webdav.getDavPath(self.request.path)
        if node == None:
            return self._send_resp(404,'newp')

        attr = {'xmlns':'DAV:'}
        multi = Element('multistatus',attrib=attr)

        for subn in node.getSubNodes():

            name = subn.getBaseName()

            # FIXME make this better...
            if name == None:
                return self._send_resp(413,'Too Big')

            ntype = subn.getNodeType()

            info = subn.stat(dyns)
            resp = Element('response',attrib=attr)

            href = Element('href',attrib=attr)
            href.text = name

            stat = Element('propstat',attrib=attr)

            status = Element('status',attrib=attr)
            status.text = 'HTTP/1.1 200 OK'

            prop = Element('prop',attrib=attr)

            multi.append(resp)

            resp.append( href )
            resp.append( stat )

            stat.append( status )
            stat.append( prop )

            for key,val in info.items():
                davprop = davprops.get(key)
                if davprop == None:
                    continue

                pelm = Element(davprop)#,attrib=attr)
                pelm.text = str(val)

                prop.append(pelm)

            if ntype == 'dir':
                rest = Element('resourcetype',attrib=attr)
                rest.append( Element('collection',attrib=attr) )

                prop.append(rest)

        hdrs = {}
        hdrs['content-type'] = 'text/xml'

        xmlbody = tostring( multi )

        return self._send_resp(207, body=xmlbody, reason='Multi-Status', **hdrs)

    @tornado.web.asynchronous
    def options(self):
        #print('options: %s %r' % (self.request.path, self.request.headers))
        return self._send_resp(200, **opthdrs)

    @tornado.web.asynchronous
    def get(self):

        #print('get: %s %r' % (self.request.path, self.request.headers))

        dyns,node = self.webdav.getDavPath(self.request.path)
        if node == None:
            return self._send_resp(404,'newp')

        # FIXME implement sizemax and range!
        #print('range: %r' % (self.request.headers.get('range')))

        byts = node.read(dyns)
        self._send_resp(200,byts)

    def _send_resp(self, code, body=None, reason=None, **headers):

        self.set_status(code,reason=reason)

        [ self.set_header(k,v) for (k,v) in headers.items() ]

        if body != None:
            self.write(body)

        self.finish()

class WebDav(EventBus):
    '''
    The "settings" kwargs go directly to tornado HTTPServer.
    '''
    def __init__(self, **settings):
        EventBus.__init__(self)
        self.onfini( self._onDavFini )

        self.root = PathNode()

        self.paths = s_cache.Cache(maxtime=60)
        self.paths.setOnMiss( self._getDavNode )

        self.app = tornado.web.Application( (
            ('.*', WebDavHandler, {'webdav': self}),
        ))

        self.ioloop = tornado.ioloop.IOLoop()

        settings['io_loop'] = self.ioloop
        self.serv = tornado.httpserver.HTTPServer(self.app, **settings)

    def addDavListen(self, port, host='0.0.0.0'):
        '''
        Add a listening host:port for the WebDav server.
        '''
        self.serv.listen(port,address=host)

    def getDavBinds(self):
        '''
        Return getsockname() for bound sockets.

        Example:

            for sockaddr in dav.getDavBinds():
                dostuff(sockaddr)

        '''
        ret = []
        for sock in self.serv._sockets.values():
            ret.append( sock.getsockname() )
        return ret

    def runDavServer(self):
        '''
        Begin servicing clients ( blocks ).
        '''
        self.ioloop.start()

    @s_threads.firethread
    def fireDavServer(self):
        self.ioloop.start()

    def getDavRoot(self):
        '''
        Return the root PathNode for the virtual filesystem.
        '''
        return self.root

    def addDavPath(self, path, node=None):
        '''
        Add a path to the WebDave filesystem.
        ( Optionally specify node to append )


        Example:

            fd = io.BytesIO(b'oh hai!\n')
            dav.addDavPath('/foo/bar/baz', node=FileNode('faz.txt', fd) )

        '''
        pnode = self.root.addNamedPath(path)
        if node == None:
            return pnode

        pnode.addSubNode(node)
        return node

    def getDavPath(self, path):
        '''
        Parse a path and return dyns,node.
        '''
        return self.paths.get(path)

    def _getDavNode(self, path):
        return self.root.getPathNode(path)

    def _onDavFini(self):
        self.serv.stop()
        self.ioloop.stop()

class PathNode:
    '''
    PathNode ( and sub-classes ) implement a virtual filesystem.
    '''
    nodetype = 'dir'
    def __init__(self):

        self.kids = []
        self.dynkids = []

        self.parent = None
        self.kidsbyname = {}    # named kids

    def getNodeType(self):
        return self.nodetype

    def stat(self, dyns, **info):
        '''
        Returns filesystem stat info for this node.

        Example:

            info = node.stat(dyns)

        '''
        return {}

    def read(self, dyns, **info):
        '''
        Read and return bytes from a file like node.

        Example:

            byts = node.read(dyns)

        Notes:

            * dyns will come from path traversal
            * info is provided by protocol server

        '''
        return None

    def getSubNodes(self):
        return list(self.kids)

    def addNamedPath(self, path):
        '''
        Build a named path and return the child node.

        Example:

            baznode = root.addNamedPath('/foo/bar/baz')

        '''
        names = path.split('/')
        if path.startswith('/'):
            names = names[1:]

        node = self
        for name in names:
            newn = node.getSubNode(name)
            if newn == None:
                newn = BaseNode(name)
                node.addSubNode(newn)

            node = newn
        return node

    def getPathNode(self, path):
        '''
        Returns a tuple of tags,node for the path.
        '''
        dyns = []
        node = self

        if path == '/':
            return dyns,node

        names = path.strip('/').split('/')
        for name in names:
            newn = node.getSubNode(name)
            if newn == None:
                return dyns,None

            if newn.getBaseName() == None:
                dyns.append(name)

            node = newn

        return dyns,node

    def addSubNode(self, node):
        '''
        Add the given node as a child.

        Example:

            root.addSubNode( BaseNode('foo') )

        '''
        self.kids.append(node)

        base = node.getBaseName()
        if base != None:
            self.kidsbyname[base] = node
            return

        self.dynkids.append(node)
        return node

    def getSubNode(self, name):
        '''
        Return the matching child node.

        Example:

            foo = root.getSubNode('foo')

        '''
        node = self.kidsbyname.get(name)
        if node != None:
            return node

        for node in self.dynkids:
            if node.isDynMatch(name):
                return node

    def getBaseName(self):
        '''
        Returns the "static" base name if it exists.
        '''
        return None

    def isDynMatch(self, name):
        '''
        Returns True if name is a match.
        '''
        return False

class BaseNode(PathNode):
    '''
    A PathNode which implements a static dir name.
    '''
    def __init__(self, base):
        PathNode.__init__(self)
        self.base = base

    def getBaseName(self):
        return self.base

class RegexNode(PathNode):
    '''
    A PathNode which implements regex matching.
    '''
    def __init__(self, regex):
        PathNode.__init__(self)
        self.regex = re.compile(regex)

    def isDynMatch(self, name):
        '''
        Return True if the name matches our regex.
        '''
        return self.regex.search(name) != None

class FileNode(BaseNode):
    nodetype = 'file'

    def __init__(self, base, fd):
        BaseNode.__init__(self, base)
        self.fd = fd
        self.lock = threading.Lock()

    def read(self, dyns, **info):
        rang = info.get('range')
        with self.lock:
            # FIXME MAX SIZE
            if rang == None:
                self.fd.seek(0)
                return self.fd.read()
                
            print('RANGE OMG')
            return b'hehe'
            #return self.fd

    def stat(self, dyns, **info):
        with self.lock:
            return statfd(fd)

# FIXME: for temporary platform testing
if __name__ == '__main__':

    from tornado.log import enable_pretty_logging
    enable_pretty_logging()

    dav = WebDav()
    dav.addDavPath('/foo/bar/baz')
    dav.addDavPath('/', FileNode('haha.txt', io.BytesIO(b'gronk!\n')))

    dav.addDavPath('/', FileNode('lol.txt',io.BytesIO(b'hahaha')) )

    dav.addDavListen(8080)

    try:
        dav.runDavServer()
    except KeyboardInterrupt as e:
        dav.fini()
