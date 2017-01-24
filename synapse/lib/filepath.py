
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
    def __init__(self, path, remainder, parent=None):
        '''
        base path object for regular filesystems
        '''
        self.parent = parent
        self.path = path
        self.remainder = remainder

        self.child = None
        self.tempfd = None

        if self.remainder:
            self._process_next()

    def _type(self):
        return 'fs.reg.file'

    def isfile(self):
        return True

    def _process_next(self):
        return

    def getChild(self):
        return self.child

class FilePathFile(FilePath):
    '''
    The base path object for filesystem files.  
    '''
    def _open(self, mode='r'):
        return open(self.path, mode=mode)

class FilePathDir(FilePath):
    '''
    The base dir object for filesystem files.  
    '''
    def _type(self):
        return 'fs.reg.dir'

    def isfile(self):
        return False

    def _process_next(self):
        child_path, child_remainder = _get_child_paths(self.path, self.remainder)
        
        cls = _get_path_class(child_path)
        self.child = cls(child_path, child_remainder, parent=self)

class FilePathTarDir(FilePath):
    def __init__(self, tarfd, path, remainder, parent=None):
        '''
        This is a directory in a tar archive. 
        '''
        self.tarfd = tarfd
        super(FilePathTarDir, self).__init__(path, remainder, parent=parent)

    def _type(self):
        return 'inner.tar.dir'

    def isfile(self):
        return False

    def _process_next(self):
        '''
        This will only be called if the member from the remainder is a file or dir
        '''

        tar_dirs, tar_files = tar_enumerate(self.tarfd)

        child_path, child_remainder = _get_child_paths(self.path, self.remainder)

        child_tar_path = _container_pathnorm(child_path)
        if child_tar_path in tar_dirs:
            self.child = FilePathTarDir(self.tarfd, child_path, child_remainder, parent=self)

        elif child_tar_path in tar_files:
            if not child_remainder:
                self.child = FilePathTarFile(self.tarfd, child_path, child_remainder, parent=self)
                return

            # if the child has a remainder then extract otherwise, don't
            self.tempfd = tempfile.NamedTemporaryFile(prefix='syn_sfp_')

            tfd = self.tarfd.extractfile(child_path.strip('/'))
            tbuf = tfd.read(read_chunk_sz)
            while tbuf:
                self.tempfd.write(tbuf)
                tbuf = tfd.read(read_chunk_sz)
            self.tempfd.flush()
            child_path = self.tempfd.name
            self.child = _get_path_class(child_path)(child_path, child_remainder, parent=self)

        elif self.remainder:
            raise s_exc.NoSuchPath(path=os.path.join(self.path, self.remainder))

class FilePathTarFile(FilePathTarDir):
    def _type(self):
        return 'inner.tar.file'

    def isfile(self):
        return True

    def _open(self, mode='r'):
        return self.tarfd.extractfile(self.path.lstrip('/'))

class FilePathTar(FilePathTarDir):
    def __init__(self, path, remainder, parent=None):
        tarfd = tarfile.open(path)
        self.tarpath = path

        super(FilePathTar, self).__init__(tarfd, '/', remainder, parent=parent)

    def _type(self):
        return 'fs.tar.file'

    def isfile(self):
        return True

    def _open(self, mode='r'):
        return open(self.tarpath, mode=mode)

class FilePathZipDir(FilePath):
    def __init__(self, zipfd, path, remainder, parent=None):
        '''
        This is a directory in a zip. 
        '''
        self.zipfd = zipfd
        super(FilePathZipDir, self).__init__(path, remainder, parent=parent)

    def _type(self):
        return 'inner.zip.dir'

    def isfile(self):
        return False

    def _process_next(self):
        '''
        This will only be called if the member from the remainder is a file or dir
        '''

        zip_dirs, zip_files = zip_enumerate(self.zipfd)

        child_path, child_remainder = _get_child_paths(self.path, self.remainder)

        child_zip_path = _container_pathnorm(child_path)
        if child_zip_path in zip_dirs:
            self.child = FilePathZipDir(self.zipfd, child_path, child_remainder, parent=self)

        elif child_zip_path in zip_files:
            if not child_remainder:
                self.child = FilePathZipFile(self.zipfd, child_path, child_remainder, parent=self)
                return

            # extract the file to a directory and parse it
            self.tempfd = tempfile.NamedTemporaryFile(prefix='syn_sfp_')

            zfd = self.zipfd.open(child_path.strip('/'), mode='r')
            zbuf = zfd.read(read_chunk_sz)
            while zbuf:
                self.tempfd.write(zbuf)
                zbuf = zfd.read(read_chunk_sz)

            self.tempfd.flush()
            child_path = self.tempfd.name
            self.child = _get_path_class(child_path)(child_path, child_remainder, parent=self)

        elif self.remainder:
            raise s_exc.NoSuchPath(path=os.path.join(self.path, self.remainder))

class FilePathZipFile(FilePathZipDir):
    def _type(self):
        return 'inner.zip.file'

    def isfile(self):
        return True

    def _open(self, mode='r'):
        return self.zipfd.open(self.path.lstrip('/'), mode='r')

class FilePathZip(FilePathZipDir):
    def __init__(self, path, remainder, parent=None):
        zipfd = zipfile.ZipFile(path)
        self.zippath = path

        super(FilePathZip, self).__init__(zipfd, '/', remainder, parent=parent)

    def _type(self):
        return 'fs.zip.file'

    def isfile(self):
        return True

    def _open(self, mode='r'):
        return open(self.zippath, mode=mode)

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

def _get_path_class(path):
    '''
    Returns the class to handle the type of item located at path.  This function
    only operates on regular os. accessible paths
    '''
    
    if not os.path.exists(path):
        raise s_exc.NoSuchPath(path=path)

    if os.path.isdir(path):
        return _path_ctors.get('fs.reg.dir')
    mime = _mime_file(path)
    return _path_ctors.get(mime)

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

def _lsplit(path):
    '''
    Split a pathname.  Returns tuple "(head, tail)" where "tail" is everything after the 
    FIRST slash that is not at position 0.  Either part may be empty.

    It's the inverse of os.path.split
    '''

    drive, rpath = os.path.splitdrive(path)
    parts = os.path.normpath(rpath).split(os.path.sep)
    if parts[0] == '':
        parts[0] = os.path.sep
    head = os.path.join(drive, parts[0])

    tail = ''
    if parts[1:]:
        tail = os.path.join(*parts[1:])
    return head, tail

def _get_child_paths(headpath, tailpath):
    '''
    Take a split head/tail path and create a new head tail that is one directory lower
    in the joined path
    '''
    child_part, child_remainder = _lsplit(tailpath)
    child_headpath = os.path.join(headpath, child_part)
    return child_headpath, child_remainder

def _container_pathnorm(path):
    return path.replace('\\', '/').strip('/')

def _get_subpaths(path):
    '''
    Returns a list of subpaths in a path, one for each level in the path
    This is an internal function used for ONLY for iterating over paths in a container
    As such it should not be used for filesystem paths since separators will vary across platforms
    '''
    path = path.replace('\\', '/')
    path = path.rstrip('/')

    path_parts = path.split('/')
    if path_parts[0] == '':
        path_parts[0] = '/'

    paths = []
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

    fpobj = None
    child_path, child_remainder = _lsplit(path)
    
    try:
        cls = _get_path_class(child_path)
        fpobj = cls(child_path, child_remainder)

        while fpobj.getChild():
            fpobj = fpobj.getChild()
    except s_exc.NoSuchPath as e:
        return None

    return fpobj

def openfile(*paths, mode='r'):
    '''
    Returns a read-only file-like object even if the path terminates inside a container file.
    If the path is a regular os accessible path mode is passed through.  If the path terminates 
    in a container file mode is ignored.

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

    fd = fpobj._open(mode=mode)
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

_path_ctors = {
    'fs.reg.dir': FilePathDir,
    'fs.reg.file': FilePathFile,
    'fs.tar.file': FilePathTar,
    'fs.zip.file': FilePathZip,
    'inner.tar.dir': FilePathTarDir,
    'inner.zip.dir': FilePathZipDir,
    'inner.tar.file': FilePathTarFile,
    'inner.zip.file': FilePathZipFile,
}

