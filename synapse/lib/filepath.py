
import os
import tarfile
import zipfile
import tempfile
import traceback

import synapse.exc as s_exc
from synapse.common import *

# 10 MB
read_chunk_sz = 1048576*10

'''
Provide a generic opener API for paths that cross into supported container files.

For example: /dir0/dir1/foo.zip/d0/bar
The above represents a file named bar located in the d0 directory inside the foo.zip zip archive
located on the filesystem in the /dir0/dir1 directory.
'''

class FilePath(object):
    def __init__(self, name, parent=None):
        '''
        Base path object for regular filesystems
        '''
        self.name = name
        self._child = None
        self.tempfd = None
        self._parent = parent

    def open(self, mode='r'):
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

    def child(self, name, end=False):

        self._process_next(name, end=end)
        return self._child

    def parent(self):
        return self._parent

    def _getpath(self):
        parts = []
        if self._parent != None:
            parts.append(self._parent._getpath())
        parts.append(self.name)
        return os.path.join(*parts)

    def _process_next(self, child_name, end=False):
        '''
        This is the workhorse method that can contain path specific processing of children.
        Override for container formats
        '''

        cls = _get_path_class(self._getpath(), child_name)
        self._child = cls(child_name, parent=self)

class FilePathFile(FilePath):
    '''
    The base path object for filesystem files.
    '''
    def open(self, mode='r'):
        return open(self._getpath(), mode=mode)

    def isfile(self):
        return True

class FilePathDir(FilePath):
    '''
    The base dir object for filesystem files.
    '''

    def isfile(self):
        return False

class FilePathTar(FilePath):
    def __init__(self, name, parent=None):
        super(FilePathTar, self).__init__(name, parent=parent)
        self._tar_init()

    def open(self, mode='r'):
        return open(self.tarpath, mode=mode)

    def _tar_init(self):
        if not hasattr(self, 'tarfd'):
            self.tarpath = self._getpath()
            self.tarfd = tarfile.open(self.tarpath)
        return

    def _tarpath(self):
        return ''

    def isfile(self):
        return True

    def _process_next(self, child_name, end=False):

        tar_dirs, tar_files = tar_ls(self._tarpath(), self.tarfd)

        if child_name in tar_dirs:
            self._child = FilePathTarDir(child_name, parent=self)

        elif child_name in tar_files:
            if end:
                self._child = FilePathTarFile(child_name, parent=self)
                return

            self.tempfd = tempfile.NamedTemporaryFile(prefix='syn_sfp_')

            child_path = _container_normpath(self._tarpath(), child_name)

            tfd = self.tarfd.extractfile(child_path)
            tbuf = tfd.read(read_chunk_sz)
            while tbuf:
                self.tempfd.write(tbuf)
                tbuf = tfd.read(read_chunk_sz)
            self.tempfd.flush()
            child_path = self.tempfd.name
            cls = _get_path_class(child_path)
            self._child = cls(child_path, parent=self)

class FilePathTarDir(FilePathTar):
    def __init__(self, name, parent=None):
        self.tarfd = parent.tarfd
        self.tarpath = parent.tarpath
        super(FilePathTarDir, self).__init__(name, parent=parent)

    def isfile(self):
        return False

    def _tarpath(self):
        parts = []
        if self._parent != None:
            parts.append(self._parent._tarpath())
        parts.append(self.name)
        return _container_normpath(*parts)

class FilePathTarFile(FilePathTarDir):

    def isfile(self):
        return True

    def open(self, mode='r'):
        return self.tarfd.extractfile(self._tarpath())

class FilePathZip(FilePath):
    def __init__(self, name, parent=None):
        super(FilePathZip, self).__init__(name, parent=parent)
        self._zip_init()

    def _zip_init(self):
        if not hasattr(self, 'zipfd'):
            self.zippath = self._getpath()
            self.zipfd = zipfile.ZipFile(self.zippath)

    def isfile(self):
        return True

    def _zippath(self):
        return ''

    def open(self, mode='r'):
        return open(self.zippath, mode=mode)

    def _process_next(self, child_name, end=False):

        zdirs, zfiles = zip_ls(self._zippath(), self.zipfd)

        if child_name in zdirs:
            self._child = FilePathZipDir(child_name, parent=self)

        elif child_name in zfiles:
            if end:
                self._child = FilePathZipFile(child_name, parent=self)
                return

            # extract the file to a directory and parse it
            self.tempfd = tempfile.NamedTemporaryFile(prefix='syn_sfp_')

            child_path = _container_normpath(self._zippath(), child_name)

            zfd = self.zipfd.open(child_path, mode='r')
            zbuf = zfd.read(read_chunk_sz)
            while zbuf:
                self.tempfd.write(zbuf)
                zbuf = zfd.read(read_chunk_sz)

            self.tempfd.flush()
            child_path = self.tempfd.name
            cls = _get_path_class(child_path)
            self._child = cls(child_path, parent=self)

        elif end:
            raise s_exc.NoSuchPath(path=os.path.join(self._getpath(), child_name))

class FilePathZipDir(FilePathZip):
    def __init__(self, name, parent=None):
        '''
        This is a directory in a zip.
        '''
        self.zippath = parent.zippath
        self.zipfd = parent.zipfd
        super(FilePathZipDir, self).__init__(name, parent=parent)

    def isfile(self):
        return False

    def _zippath(self):
        parts = []
        if self._parent != None:
            parts.append(self._parent._zippath())
        parts.append(self.name)
        return _container_normpath(*parts)

class FilePathZipFile(FilePathZipDir):

    def isfile(self):
        return True

    def open(self, mode='r'):
        return self.zipfd.open(self._zippath(), mode='r')

def ls_atlevel(path, dirs, files):

    lsdirs = []
    lsfiles = []
    for d in dirs:
        if d == path:
            continue
        if os.path.dirname(d) != path:
            continue

        lsdirs.append(os.path.basename(d))

    for f in files:
        if f == path:
            continue
        if os.path.dirname(f) != path:
            continue

        lsfiles.append(os.path.basename(f))

    return lsdirs, lsfiles

def zip_ls(path, zipfd):
    dirs, files = zip_enumerate(zipfd)
    return ls_atlevel(path, dirs, files)

def zip_enumerate(zipfd):
    '''
    Return the files and dirs in a zip file
    '''
    files = set()
    dirs = set()

    for path in zipfd.namelist():

        for spath in _get_subpaths(path):
            try:
                info = zipfd.getinfo(spath)
                files.add(spath)
            except KeyError as e:
                dirs.add(spath)

    return dirs, files

def tar_ls(path, tarfd):
    dirs, files = tar_enumerate(tarfd)
    return ls_atlevel(path, dirs, files)

def tar_enumerate(tarfd):
    '''
    Return the files and dirs in a tar archive
    '''
    files = set()
    dirs = set()

    for path in tarfd.getnames():

        for spath in _get_subpaths(path):
            info = tarfd.getmember(spath)

            if info.isdir():
                dirs.add(spath)
            if info.isfile():
                files.add(spath)

    return dirs, files

def _get_path_class(*paths):
    '''
    Returns the class to handle the type of item located at path.  This function
    only operates on regular os.accessible paths
    '''
    path = os.path.join(*paths)
    if not os.path.exists(path):
        raise s_exc.NoSuchPath(path=path)

    if os.path.isdir(path):
        return path_ctors.get('fs.reg.dir')
    mime = _mime_file(path)
    return path_ctors.get(mime)

def _mime_file(path):
    '''
    Assumes the path exists and is a file.
    returns reg.file unless it is a known container
    '''
    if zipfile.is_zipfile(path):
        return 'fs.zip.file'
    if tarfile.is_tarfile(path):
        return 'fs.tar.file'

    return 'fs.reg.file'

def _container_normpath(*paths):
    '''
    Normalizes a path:
    1. uses forward-slashes
    2. w/o a leading slash
    3. w/o a trailing slash

    This is useful for container path enumeration
    '''
    path = '/'.join(paths)
    return path.replace('\\', '/').strip('/')

def _get_path_parts(path):
    '''
    Returns the elements of a path in order, w/o regard to their original separaors
    '''

    parts = path.replace('\\', '/').rstrip('/').split('/')

    if parts[0] == '':
        parts[0] = '/'

    return parts

def _get_subpaths(path):
    '''
    Returns a list of subpaths in a path, one for each level in the path
    This is an internal function used for ONLY for iterating over paths in a container
    As such it should not be used for filesystem paths since separators will vary across platforms
    '''

    paths = []
    path_parts = _get_path_parts(path)

    for i in range(len(path_parts)):

        ipath = os.path.join(*path_parts[:i+1])
        paths.append(ipath)

    return paths

def _parse_path(*paths):
    '''
    Internal function to parse the incoming path.
    lists of paths are joined prior to parsing
    '''

    if not paths or None in paths:
        return None

    path = genpath(*paths)

    if not path:
        return None

    path_parts = _get_path_parts(path)

    try:
        cls = _get_path_class(path_parts[0])
        base = cls(path_parts[0], parent=None)

        for i, name in enumerate(path_parts[1:]):
            end = i == len(path_parts[1:]) - 1
            base = base.child(name, end=end)
            if base == None:
                return None
    except s_exc.NoSuchPath as e:
        return None

    return base

# KILL2.7 kwargs instead of mode='r' here because of python2.7
def openfile(*paths, **kwargs):
    '''
    Returns a read-only file-like object even if the path terminates inside a container file.

    If the path is a regular os accessible path mode may be passed through as a keyword argument.
    If the path terminates in a container file mode is ignored.

    If the path does not exist a NoSuchPath exception is raised.

    ex.
    openfile('/foo/bar/baz.egg/path/inside/zip/to/file')
    '''
    fpobj = _parse_path(*paths)
    if not fpobj:
        raise s_exc.NoSuchPath(path='%r' % (paths,))
    if not fpobj.isfile():
        path = genpath(*paths)
        raise s_exc.NoSuchPath(path=path)

    fd = fpobj.open(mode=kwargs.get('mode', 'r'))
    return fd

def isfile(*paths):
    '''
    Determines if the path is a file, even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    fpath = _parse_path(*paths)
    if fpath and fpath.isfile():
        return True
    return False

def isdir(*paths):
    '''
    Determines if the path is a directory, even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    fpath = _parse_path(*paths)
    if fpath and not fpath.isfile():
        return True
    return False

def exists(*paths):
    '''
    Determines if the path exists even if the path terminates inside a container file.
    If a list of paths are provided, they are joined first.
    Returns a boolean.
    '''
    if _parse_path(*paths) == None:
        return False
    return True

path_ctors = {
    'fs.reg.dir': FilePathDir,
    'fs.reg.file': FilePathFile,
    'fs.tar.file': FilePathTar,
    'fs.zip.file': FilePathZip,
    'inner.tar.dir': FilePathTarDir,
    'inner.zip.dir': FilePathZipDir,
    'inner.tar.file': FilePathTarFile,
    'inner.zip.file': FilePathZipFile,
}
