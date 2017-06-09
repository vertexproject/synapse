
import os
import fnmatch
import tarfile
import zipfile
import tempfile
import traceback

import synapse.exc as s_exc
from synapse.compat import queue
from synapse.common import genpath

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

def normpath(*paths):
    '''
    Normalizes a path:
    1. uses forward-slashes
    2. removes leading slashes
    3. removes trailing slashes

    This is useful for container path enumeration
    '''
    path = '/'.join(paths)
    path = path.replace('\\', '/').strip('/')
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)

    return path

def subpaths(path):
    '''
    Returns a list of subpaths in a path, one for each level in the path
    This is an internal function used for ONLY for iterating over paths in a container
    As such it should not be used for filesystem paths since separators will vary across platforms
    '''

    path_parts = getPathParts(path)

    for i in range(len(path_parts)):

        ipath = os.path.join(*path_parts[:i+1])
        yield ipath

class FpOpener(object):
    def __init__(self, fpobj):
        self.fpobj = fpobj
        self.fd = fpobj.open()

    def seek(self, *args):
        return self.fd.seek(*args)

    def read(self, *args):
        return self.fd.read(*args)

    def close(self):
        self.fd.close()
        self.fpobj.close()

class FpFile(object):
    def __init__(self, pparts, idx, parent=None, fd=None):
        '''
        Base path object for regular filesystems
        '''
        self.fd = fd
        self.idx = idx
        self.end = False
        self.maxidx = idx+1
        self.pparts = pparts
        self._isfile = True

    def open(self, mode='rb'):
        '''
        Returns a file-like object for this path
        This should return None if it doesn't make sense to open, i.e. a directory
        '''

        if not self.isfile():
            return None

        if not self.fd:
            self.fd = open(genpath(*self.pparts[:self.maxidx]), mode=mode)

        return self.fd

    def close(self):
        '''
        Closes the file-like object if it has one
        '''
        if self.fd:
            self.fd.close()

    def isfile(self):
        '''
        Returns a boolean.  If it returns False, it may be assumed to be a directory
        '''
        return self._isfile

    def path(self):
        return genpath(*self.pparts[:self.maxidx])

    def nexts(self):
        # pparts up to *our* index should be discrete, anything after may still be a glob

        maxidx = self.idx
        spath = genpath(*self.pparts[:self.idx+1])

        # if itsa regular file
        if os.path.isfile(spath):
            if self.idx+1 == len(self.pparts)-1:
                self.end = True
                yield self
            return 

        spaths = [spath]

        ends = []
        nexts = []
        for idx in range(self.idx+1, len(self.pparts)):
            cpaths = []
            for spath in spaths:
                match = self.pparts[idx]

                for member in os.listdir(spath):
                    if not fnmatch.fnmatch(member, match):
                        continue
                    tpath = genpath(spath, member)

                    # discrete path with remaining wildcards
                    eparts = getPathParts(spath)
                    eparts.append(member)
                    eparts.extend(self.pparts[idx+1:])

                    if idx == len(self.pparts)-1:
                        cls = _pathClass(tpath)
                        if cls:
                            fp = cls(eparts, idx, parent=self)
                            fp.next()
                            fp.end = True
                            yield fp
                    else:
                        if os.path.isfile(tpath):
                            cls = _pathClass(tpath)
                            fp = cls(eparts, idx, parent=self)
                            yield fp
                        else:
                            cpaths.append(genpath(spath, member))
            spaths = cpaths

    def next(self):
        '''
        This is the workhorse method that can contain path specific processing of children.
        The object should consume as much as possible of the path before creating the 
        child class

        NOTE: Override for container formats
        '''

        # get longest consistent path
        partlen = len(self.pparts)
        # the end of the line
        if self.idx == partlen-1:
            if os.path.isdir(genpath(*self.pparts[:self.idx+1])):
                self._isfile = False
            return

        maxpath = None
        checkpath = genpath(*self.pparts[:self.idx+1])
        cidx = self.idx + 1

        while cidx < partlen:
            checkpath = genpath(*self.pparts[:cidx+1])
            if not os.path.exists(checkpath):
                break
            maxpath = checkpath
            cidx += 1

        self.maxidx = cidx

        # if the max path is a dir, we're finished
        if os.path.isdir(maxpath):
            self._isfile = False

            if self.maxidx != partlen:
                self.close()
                raise s_exc.NoSuchPath(path=os.path.join(*self.pparts))

        # if end of the path we're finished
        if self.maxidx == partlen:
            return

        # supported container file
        cls = _pathClass(*self.pparts[:self.maxidx])
        return cls(self.pparts, self.maxidx-1, parent=self)

class FpTar(FpFile):
    def __init__(self, pparts, idx, parent=None, fd=None):
        self.fd = fd
        self.inner_fd = None

        if not self.fd:
            self.fd = open(genpath(*pparts[:idx+1]), 'rb')
        self._init()

        self.innrEnum()

        super(FpTar, self).__init__(pparts, idx, parent=parent, fd=self.fd)

    def _init(self):
        self.cntr = tarfile.open(fileobj=self.fd)

    def innrOpen(self, *parts):
        return self.cntr.extractfile(normpath(*parts))

    def innrTmpExtract(self, path):
        '''
        Extract a file from within the container to a named temporary file
        '''
        tempfd = tempfile.NamedTemporaryFile(prefix='syn_sfp_')

        cfd = self.innrOpen(path)
        cbuf = cfd.read(read_chunk_sz)
        while cbuf:
            tempfd.write(cbuf)
            cbuf = cfd.read(read_chunk_sz)
        cfd.close()

        tempfd.flush()
        tempfd.seek(0)
        return tempfd

    def innrEnum(self):
        '''
        enumerate the files and directory paths in the container exactly once!
        creates a nested dict *and* a set of files and dirs... memory inefficient
        FIXME: consider abandoning sets
        '''
        self.files = set()
        self.dirs = set()
        self.dstruct = {}

        for info in self.cntr.getmembers():
            pparts = info.name.split('/')
            if info.isfile():
                self.files.add(info.name)

                dstruct = self.dstruct
                endidx = len(pparts)-1
                for i, elem in enumerate(pparts):
                    if i == endidx:
                        dstruct[elem] = 1
                        break
                    dstruct.setdefault(elem, {})
                    dstruct = dstruct[elem]
                tdirs = pparts[:-1]
                continue
            if info.isdir():
                self.dirs.add(info.name)

                dstruct = self.dstruct
                for elem in pparts:
                    dstruct.setdefault(elem, {})
                    dstruct = dstruct[elem]

    def innerLs(self, path):
        if not path:
            return [k for k in self.dstruct.keys()]

        pparts = path.split('/')
        dstruct = self.dstruct
        for p in pparts:
            if dstruct == None:
                return None
            dstruct = dstruct.get(p)

        return [k for k in dstruct.keys()]

    def innrExists(self, path):
        if path in self.files:
            return True
        if path in self.dirs:
            return True
        return False

    def innrIsfile(self, path):
        if path in self.files:
            return True
        return False

    def innrIsdir(self, path):
        if path in self.dirs:
            return True
        return False

    def open(self, mode='rb'):
        '''
        Returns a file-like object for the path inside the container
        This should return None if it doesn't make sense to open, i.e. a directory
        or if the container doesn't contain the end of the path
        '''

        if self.maxidx != len(self.pparts):
            return None

        inner_pparts = self.pparts[self.idx+1:self.maxidx]
        self.inner_fd = self.innrOpen(*inner_pparts) 
        return self.inner_fd

    def close(self):
        '''
        Closes the file-like object if it has one
        '''
        if self.inner_fd:
            self.inner_fd.close()

        self.cntr.close()

        self.fd.close()

    def path(self):
        return os.path.join(*self.pparts[:self.maxidx])

    def nexts(self):
        # pparts up to *our* index should be discrete, anything after may still be a glob
        maxidx = self.idx
        spaths = ['']

        ends = []
        nexts = []
        for idx in range(self.idx+1, len(self.pparts)):
            cpaths = []
            for spath in spaths:
                match = self.pparts[idx]

                for member in self.innerLs(spath):
                    if not fnmatch.fnmatch(member, match):
                        continue
                    tpath = normpath(spath, member)

                    if not self.innrIsfile(tpath):
                        cpaths.append(normpath(spath, member))
                        continue

                    tempfd = self.innrTmpExtract(tpath)
                    cls = _fdClass(tempfd)
                    if not cls:
                        continue

                    eparts = getPathParts(tempfd.name)
                    eidx = len(eparts)-1
                    eparts.extend(self.pparts[idx+1:])
                    fp = cls(eparts, eidx, parent=self, fd=tempfd)

                    if idx == len(self.pparts)-1:
                        fp.next()
                        fp.end = True
                    yield fp

            spaths = cpaths

    def next(self):
        '''
        This is the workhorse method for path specific processing of container children.
        The object should consume as much as possible of the path before instantiating a new
        object

        At a minimum, each container should override:
        innrOpen(path)
        innrEnum(path)
        '''

        # get longest consistent path
        partlen = len(self.pparts)

        # the end of the line
        if self.idx == partlen-1:
            return

        # since it's a container we only care about the "inner path"
        maxpath = None
        checkpath = None
        cidx = self.idx + 1

        while cidx < partlen:
            checkpath = normpath(*self.pparts[self.idx+1:cidx+1])
            if not self.innrExists(checkpath):
                break
            maxpath = checkpath
            cidx += 1

        if maxpath == None:
            self.close()
            raise s_exc.NoSuchPath(path=os.path.join(*self.pparts))
        self.maxidx = cidx

        # if the max path is a dir, we're finished
        if self.innrIsdir(maxpath):
            self._isfile = False

            if self.maxidx != partlen:
                self.close()
                raise s_exc.NoSuchPath(path=os.path.join(*self.pparts))

        # if end of the path we're finished
        if self.maxidx == partlen:
            return

        # supported file
        tempfd = self.innrTmpExtract(maxpath)

        cls = _fdClass(tempfd)
        if not cls:
            return
        tempfd.seek(0)

        return cls(self.pparts, self.maxidx-1, parent=self, fd=tempfd)

class FpZip(FpTar):
    def __init__(self, pparts, idx, parent=None, fd=None):
        super(FpZip, self).__init__(pparts, idx, parent=parent, fd=fd)

    def _init(self):
        self.cntr = zipfile.ZipFile(self.fd)

    def innrOpen(self, *parts):
        return self.cntr.open(normpath(*parts))

    def innrEnum(self):
        '''
        enumerate the files and directory paths in the container exactly once!
        '''
        self.files = set()
        self.dirs = set()
        self.dstruct = {}

        for cpath in self.cntr.namelist():
            self.files.add(cpath)

            dpath = os.path.dirname(cpath)
            self.dirs.update(subpaths(dpath))

            dstruct = self.dstruct
            pparts = cpath.split('/')
            endidx = len(pparts)-1
            for i, elem in enumerate(pparts):
                if i == endidx:
                    dstruct[elem] = 1
                    break
                dstruct.setdefault(elem, {})
                dstruct = dstruct[elem]

def _pathClass(*paths):
    '''
    Returns the class to handle the type of item located at path.  This function
    only operates on regular os.accessible paths
    '''
    path = genpath(*paths)
    if not os.path.exists(path):
        raise s_exc.NoSuchPath(path=path)

    if os.path.isdir(path):
        return path_ctors.get('fs.reg.file')
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
        return 
    path = genpath(*paths)

    pparts = getPathParts(path)
    cls = _pathClass('/')
    base = cls(pparts, 0, parent=None)

    ends_ct = 0

    bases = queue.Queue()
    bases.put(base)

    try:
        # iterate over each "matcher" in the path
        # pull out each member at that level that matches
        # and create a discrete path for that member to allow
        # traversal
        while True:
            try:
                base = bases.get_nowait()
                for nex in base.nexts():
                    if not nex.end:
                        bases.put(nex)
                        continue
                    yield nex
                    ends_ct += 1
                base.close()
            except queue.Empty as e:
                break

    except s_exc.NoSuchPath as e:
        return 

def parsePath(*paths):
    '''
    function to parse the incoming path.
    lists of paths are joined prior to parsing
    '''
    if None in paths:
        return None

    path = genpath(*paths)

    path_parts = getPathParts(path)

    base = None
    oldbases = []
    try:

        cls = _pathClass(path_parts[0])
        base = cls(path_parts, 0, parent=None)
        nbase = base.next()
        while nbase:
            base = nbase
            nbase = base.next()
            if nbase:
                oldbases.append(base)

    except s_exc.NoSuchPath as e:
        return None
    finally:
        [b.close() for b in oldbases]

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

    nopaths = True
    for fpath in parsePaths(*paths):
        nopaths = False
        if not fpath.isfile():
            if not reqd:
                continue
            fpath.close()
            raise s_exc.NoSuchPath(path=fpath.path())
        yield FpOpener(fpath)
    if nopaths and reqd:
        raise s_exc.NoSuchPath(path='/'.join(paths))

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
        fd.close()
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
            fpath.close()
            raise s_exc.NoSuchPath(path=fpath.path())
        return None

    return FpOpener(fpath)

def isfile(*paths):
    '''
    Determines if the path is a file, even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    fpath = parsePath(*paths)

    if not fpath:
        return False
    fpath.close()
    return fpath.isfile()

def isdir(*paths):
    '''
    Determines if the path is a directory, even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    fpath = parsePath(*paths)

    if not fpath:
        return False
    fpath.close()
    return not fpath.isfile()

def exists(*paths):
    '''
    Determines if the path exists even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    fpath = parsePath(*paths)
    if not fpath:
        return False
    fpath.close()
    return True

path_ctors = {
    'fs.reg.file': FpFile,
    'fs.tar.file': FpTar,
    'fs.zip.file': FpZip,
}
