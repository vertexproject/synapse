
import os
import fnmatch
import tarfile
import zipfile
import tempfile
import traceback

import synapse.exc as s_exc
from synapse.common import *

# 10 MB
read_chunk_sz = 1048576*10
# 100 MB
max_temp_sz = 1048576*100

'''
Provide a generic opener API for paths that cross into supported container files.

For example: /dir0/dir1/foo.zip/d0/bar
The above represents a file named bar located in the d0 directory inside the foo.zip zip archive
located on the filesystem in the /dir0/dir1 directory.
'''

class FilePath(object):
    def __init__(self, name, parent=None, fd=None):
        '''
        Base path object for regular filesystems
        '''
        self.fd = fd
        self.name = name
        self._child = None
        self.tempfd = None
        self._parent = parent

    def open(self, mode='rb'):
        '''
        Returns a file-like object for this path
        This should return None if it doesn't make sense to open, i.e. a directory
        '''
        return None

    def isfile(self):
        '''
        Returns a boolean.  If it returns False, it may be assumed to be a directory
        '''
        return True

    def child(self, name):

        self._processNext(name)
        return self._child

    def parent(self):
        return self._parent

    def path(self):
        parts = []
        if self._parent != None:
            parts.append(self._parent.path())
        parts.append(self.name)
        return os.path.join(*parts)

    def list(self):
        return os.listdir(self.path())

    def _processNext(self, child_name):
        '''
        This is the workhorse method that can contain path specific processing of children.
        Override for container formats
        '''

        cls = _pathClass(self.path(), child_name)
        self._child = cls(child_name, parent=self)

class FpFile(FilePath):
    '''
    The base path object for filesystem files.
    '''
    def open(self, mode='rb'):
        if self.fd:
            return self.fd
        return open(self.path(), mode=mode)

    def list(self):
        return []

class FpDir(FilePath):
    '''
    The base dir object for filesystem files.
    '''
    def isfile(self):
        return False

class CntrPath(FilePath):
    def __init__(self, name, parent=None, fd=None):
        super(CntrPath, self).__init__(name, parent=parent, fd=fd)
        self._init()

    def isfile(self):
        return True

    def list(self):
        '''
        Return a list of files/directories immediately "inside" this path
        e.g.
        /foo/bar/baz
        /foo/bar/haz
        /foo/bar/naz/caz

        if the above the structure and the path is /foo/bar, baz,haz,naz should be returned
        '''
        dirs, files = self._cntrLs(self._cntrPath())
        return dirs + files

    def _init(self):
        return

    def _cntrPath(self):
        return ''

    def _normPath(self, *paths):
        '''
        Normalizes a path:
        1. uses forward-slashes
        2. removes leading slashes
        3. removes trailing slashes

        This is useful for container path enumeration
        '''
        path = '/'.join(paths)
        return path.replace('\\', '/').strip('/')

    def _pathList(self, path, members):
        '''
        Given a list of member paths, return the list of member names contained in path
        '''
        ls = []
        for mebr in members:
            if mebr == path:
                continue
            if os.path.dirname(mebr) != path:
                continue

            ls.append(os.path.basename(mebr))

        return ls

    def _cntrEnum(self, listfx):
        '''
        This function generically returns a list of files and directories from a container.
        Container files generally have 'members' and not typical files and directories.

        listfx -    listing function capable of returning a list of *all* the members of a container
                    and should take no arguments
        '''
        files = set()
        dirs = set()

        for path in listfx():
            for spath in self._cntrSubpaths(path):
                if self._cntrIsFile(spath):
                    files.add(spath)
                    continue
                dirs.add(spath)

        return dirs, files

    def _cntrSubpaths(self, path):
        '''
        Returns a list of subpaths in a path, one for each level in the path
        This is an internal function used for ONLY for iterating over paths in a container
        As such it should not be used for filesystem paths since separators will vary across platforms
        '''

        path_parts = getPathParts(path)

        for i in range(len(path_parts)):

            ipath = os.path.join(*path_parts[:i+1])
            yield ipath

class CntrPathDir(CntrPath):

    def __init__(self, name, parent=None, fd=None):
        self.cntr = parent.cntr
        super(CntrPathDir, self).__init__(name, parent=parent, fd=fd)

    def isfile(self):
        return False

    def open(self, mode='rb'):
        return None

    def _cntrPath(self):
        '''
        Returns the path of the member relative to the base of the container
        '''
        parts = []
        if self._parent != None:
            parts.append(self._parent._cntrPath())
        parts.append(self.name)
        return self._normPath(*parts)

class TarMixin(object):

    def _init(self):
        if hasattr(self, 'cntr'):
            return
        if not self.fd:
            self.fd = open(self.path(), 'rb')
        self.cntr = tarfile.open(fileobj=self.fd)

    def _processNext(self, child_name):

        tdirs, tfiles = self._cntrLs(self._cntrPath())

        if child_name in tdirs:
            self._child = FpTarDir(child_name, parent=self)

        elif child_name in tfiles:
            fptf = FpTarFile(child_name, parent=self)

            cls = _fdClass(fptf.open())
            self._child = cls(child_name, parent=self, fd=fptf.open())

    def _cntrLs(self, path):
        dirs, files = self._cntrEnum(self.cntr.getnames)
        dirs = self._pathList(path, dirs)
        files = self._pathList(path, files)
        return dirs, files

    def _cntrIsFile(self, path):
        info = self.cntr.getmember(path)
        if info.isfile():
            return True
        return False

class FpTar(TarMixin, CntrPath):
    def __init__(self, name, parent=None, fd=None):
        TarMixin.__init__(self)
        CntrPath.__init__(self, name, parent=parent, fd=fd)

    def open(self, mode='rb'):
        self.fd.seek(0)
        return self.fd

class FpTarDir(TarMixin, CntrPathDir):
    def __init__(self, name, parent=None, fd=None):
        TarMixin.__init__(self)
        CntrPathDir.__init__(self, name, parent=parent, fd=fd)

class FpTarFile(FpTarDir):

    def isfile(self):
        return True

    def open(self, mode='rb'):
        return self.cntr.extractfile(self._cntrPath())

class ZipMixin(object):

    def _init(self):
        if hasattr(self, 'cntr'):
            return
        if not self.fd:
            self.fd = open(self.path(), mode='rb')
        self.cntr = zipfile.ZipFile(self.fd)

    def _cntrLs(self, path):
        dirs, files = self._cntrEnum(self.cntr.namelist)
        dirs = self._pathList(path, dirs)
        files = self._pathList(path, files)
        return dirs, files

    def _cntrIsFile(self, path):
        try:
            info = self.cntr.getinfo(path)
            return True
        except KeyError as e:
            return False

    def _processNext(self, cname):

        zdirs, zfiles = self._cntrLs(self._cntrPath())

        if cname in zdirs:
            self._child = FpZipDir(cname, parent=self)

        if cname in zfiles:
            self.tempfd = tempfile.SpooledTemporaryFile(prefix='syn_sfp_', max_size=max_temp_sz)

            cpath = self._normPath(self._cntrPath(), cname)
            zfd = self.cntr.open(cpath, mode='r')
            zbuf = zfd.read(read_chunk_sz)
            while zbuf:
                self.tempfd.write(zbuf)
                zbuf = zfd.read(read_chunk_sz)

            self.tempfd.flush()
            cls = _fdClass(self.tempfd)
            self.tempfd.seek(0)

            self._child = cls(cname, parent=self, fd=self.tempfd)

class FpZip(ZipMixin, CntrPath):
    def __init__(self, name, parent=None, fd=None):
        ZipMixin.__init__(self)
        CntrPath.__init__(self, name, parent=parent, fd=fd)

    def open(self, mode='rb'):
        self.fd.seek(0)
        return self.fd

class FpZipDir(ZipMixin, CntrPathDir):
    def __init__(self, name, parent=None, fd=None):
        ZipMixin.__init__(self)
        CntrPathDir.__init__(self, name, parent=parent, fd=fd)

def _pathClass(*paths):
    '''
    Returns the class to handle the type of item located at path.  This function
    only operates on regular os.accessible paths
    '''
    path = genpath(*paths)
    if not os.path.exists(path):
        raise s_exc.NoSuchPath(path=path)

    if os.path.isdir(path):
        return path_ctors.get('fs.reg.dir')
    with open(path, 'rb') as fd:
        mime = _mimeFile(fd)
    return path_ctors.get(mime)

def _fdClass(fd):
    mime = _mimeFile(fd)
    fd.seek(0)
    return path_ctors.get(mime)

def _mimeFile(fd):
    '''
    returns reg.file unless it is a known container
    '''
    try:
        fd.seek(0)
        tarfile.open(fileobj=fd)
        return 'fs.tar.file'
    except Exception as e:
        pass

    # OMG order matters here, zipfile will return True on some tar files
    # check tar before zip
    fd.seek(0)
    if zipfile.is_zipfile(fd):
        return 'fs.zip.file'

    return 'fs.reg.file'

def getPathParts(path):
    '''
    Returns the elements of a path in order, w/o regard to their original separators
    '''

    parts = path.replace('\\', '/').rstrip('/').split('/')

    if parts[0] == '':
        parts[0] = '/'

    return parts

def parsePaths(*paths):
    '''
    function to parse the incoming path.
    lists of paths are joined prior to parsing
    The path supports python's fnmatch glob matching

    '''
    if None in paths:
        return None

    path = genpath(*paths)

    path_parts = getPathParts(path)

    cls = _pathClass(path_parts[0])
    base = cls(path_parts[0], parent=None)

    bases = [base]
    chld_bases = []
    for name in path_parts[1:]:
        chld_bases = []
        for base in bases:
            for member in base.list():
                if not fnmatch.fnmatch(member, name):
                    continue
                chld_bases.append(base.child(member))

        bases = chld_bases

    if not bases:
        return None

    return bases

def parsePath(*paths):
    '''
    function to parse the incoming path.
    lists of paths are joined prior to parsing
    '''
    if None in paths:
        return None

    path = genpath(*paths)

    path_parts = getPathParts(path)

    try:

        cls = _pathClass(path_parts[0])
        base = cls(path_parts[0], parent=None)

        for name in path_parts[1:]:
            base = base.child(name)
            if base == None:
                return None

    except s_exc.NoSuchPath as e:
        return None

    return base

def openfiles(*paths, **kwargs):
    '''
    Yields a read-only file-like object for each path even if the path terminates inside a container file.
    Paths may use python's fnmatch glob matching

    If the path is a regular os accessible path mode may be passed through as a keyword argument.
    If the path terminates in a container file, mode is ignored.

    If req=True (Default) NoSuchPath will also be raised if ANY matching path exists, but is a directory

    Example:
        for fd in openfiles('/foo/bar/*.egg/dir0/zz*/nest.zip'):
            fbuf = fd.read()
    '''
    reqd = kwargs.get('req', False)
    mode = kwargs.get('mode', 'r')
    fpaths = parsePaths(*paths)
    paths = [p for p in paths if p]

    if not fpaths:
        if not reqd:
            return
        raise s_exc.NoSuchPath(path='/'.join(paths))
    for fpath in fpaths:
        if not fpath.isfile():
            if not reqd:
                continue
            raise s_exc.NoSuchPath(path=fpath.path())
        yield fpath.open(mode=mode)

def openfile(*paths, **kwargs):
    '''
    Returns a read-only file-like object even if the path terminates inside a container file.

    If the path is a regular os accessible path mode may be passed through as a keyword argument.
    If the path terminates in a container file, mode is ignored.

    If req=True (Default) NoSuchPath will also be raised if the path exists, but is a directory

    Example:
        fd = openfile('/foo/bar/baz.egg/path/inside/zip/to/file')
        if fd == None:
            return
        fbuf = fd.read()
    '''
    reqd = kwargs.get('req', True)
    mode = kwargs.get('mode', 'r')
    fpath = parsePath(*paths)
    paths = [p for p in paths if p]

    if not fpath:
        if reqd:
            raise s_exc.NoSuchPath(path='/'.join(paths))
        return None
    if not fpath.isfile():
        if reqd:
            raise s_exc.NoSuchPath(path=fpath.path())
        return None

    return fpath.open(mode=mode)

def isfile(*paths):
    '''
    Determines if the path is a file, even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    fpath = parsePath(*paths)

    if not fpath:
        return False
    if fpath.isfile():
        return True
    return False

def isdir(*paths):
    '''
    Determines if the path is a directory, even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    fpath = parsePath(*paths)

    if not fpath:
        return False
    if fpath.isfile():
        return False
    return True

def exists(*paths):
    '''
    Determines if the path exists even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    if not parsePath(*paths):
        return False
    return True

path_ctors = {
    'fs.reg.dir': FpDir,
    'fs.reg.file': FpFile,
    'fs.tar.file': FpTar,
    'fs.zip.file': FpZip,
    'inner.tar.dir': FpTarDir,
    'inner.zip.dir': FpZipDir,
    'inner.tar.file': FpTarFile,
}
