
import os
import tarfile
import zipfile
import tempfile
import traceback

from synapse.common import *

# 10 MB
read_chunk_sz = 1048576*10

'''
Provide a generic opener API for paths that cross into supported container files.

For example: /dir0/dir1/foo.zip/d0/bar 
The above represents a file named bar located in the d0 directory inside the foo.zip zip archive
located on the filesystem in the /dir0/dir1 directory.
'''

class NoSuchPath(Exception):
    pass

def _get_path_class(path):
    '''
    Returns the class to handle the type of item located at path.  This function
    only operates on regular os. accessible paths
    '''
    
    if not os.path.exists(path):
        raise NoSuchPath('No Such Path: %r' % (path,))

    if os.path.isdir(path):
        return _path_ctors.get('reg.dir')
    mime = _mime_file(path)
    return _path_ctors.get(mime)

def _mime_file(path):
    '''
    Assumes the path exists and is a file. 
    returns reg.file unless it is a known container
    '''
    if zipfile.is_zipfile(path):
        return 'zip.file'
    if tarfile.is_tarfile(path):
        return 'tar.file'

    return 'reg.file'

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
        return 'reg.file'

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
        return 'reg.dir'

    def _process_next(self):

        next_part = self.remainder.strip('/').split('/')[0]
        next_path = os.path.join(self.path, next_part)
        next_remainder = '/'.join(self.remainder.strip('/').split('/')[1:])

        cls = _get_path_class(next_path)
        self.child = cls(next_path, next_remainder, parent=self)

class FilePathTarDir(FilePath):
    def __init__(self, tarfd, path, remainder, parent=None):
        '''
        This is a directory in a tar archive. 
        '''
        self.tarfd = tarfd
        super(FilePathTarDir, self).__init__(path, remainder, parent=parent)

    def _type(self):
        return 'tar.dir'

    def _process_next(self):
        '''
        This will only be called if the member from the remainder is a file or dir
        '''

        tar_dirs, tar_files = tar_enumerate(self.tarfd)

        # either it's either a file/dir or DNE
        next_part = self.remainder.strip('/').split('/')[0]
        child_path = os.path.join('/', self.path, next_part)
        child_remainder = '/'.join(self.remainder.strip('/').split('/')[1:])

        if child_path in tar_dirs:
            self.child = FilePathTarDir(self.tarfd, child_path, child_remainder, parent=self)

        elif child_path in tar_files:
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
            raise NoSuchPath('No Such Path: %r' % (os.path.join(self.path, self.remainder),))

class FilePathTarFile(FilePathTarDir):
    def _type(self):
        return 'tar.inner.file'

    def _open(self, mode='r'):
        return self.tarfd.extractfile(self.path.lstrip('/'))

class FilePathTar(FilePathTarDir):
    def __init__(self, path, remainder, parent=None):
        tarfd = tarfile.open(path)
        self.tarpath = path

        super(FilePathTar, self).__init__(tarfd, '/', remainder, parent=parent)

    def _type(self):
        return 'tar.file'

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
        return 'zip.dir'

    def _process_next(self):
        '''
        This will only be called if the member from the remainder is a file or dir
        '''

        zip_dirs, zip_files = zip_enumerate(self.zipfd)

        # either it's either a file/dir or DNE
        next_part = self.remainder.strip('/').split('/')[0]
        child_path = os.path.join('/', self.path, next_part)
        child_remainder = '/'.join(self.remainder.strip('/').split('/')[1:])

        if child_path in zip_dirs:
            self.child = FilePathZipDir(self.zipfd, child_path, child_remainder, parent=self)

        elif child_path in zip_files:
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
            raise NoSuchPath('No Such Path: %r' % (os.path.join(self.path, self.remainder),))

class FilePathZipFile(FilePathZipDir):
    def _type(self):
        return 'zip.inner.file'

    def _open(self, mode='r'):
        return self.zipfd.open(self.path.lstrip('/'), mode='r')

class FilePathZip(FilePathZipDir):
    def __init__(self, path, remainder, parent=None):
        zipfd = zipfile.ZipFile(path)
        self.zippath = path

        super(FilePathZip, self).__init__(zipfd, '/', remainder, parent=parent)

    def _type(self):
        return 'zip.file'

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
                info = zipfd.getinfo(spath.strip('/'))
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
            info = tarfd.getmember(spath.strip('/'))
            if info.isdir():
                dirs.add(spath)
            if info.isfile():
                files.add(spath)
                
    return dirs, files

def _get_subpaths(path):
    '''
    Returns a list of subpaths in a path, one for each level in the path
    '''
    path_parts = path.strip('/').split('/')

    paths = []
    for i in range(len(path_parts)):

        ipath = os.path.join('/', *path_parts[:i+1])
        paths.append(ipath)

    return paths

def _enum_path(path):
    fpobj = _parse_path(path)

    if fpobj:
        return fpobj._type()
    return None

def _parse_path(path):
    '''
    Internal function to parse the incoming path
    '''

    path = genpath(path)

    if not path:
        return None

    path_parts = path.strip('/').split('/')

    fpobj = None
    next_path = os.path.join('/', path_parts[0])
    remainder = '/'.join(path_parts[1:])

    try:
        cls = _get_path_class(next_path)
        fpobj = cls(next_path, remainder)

        while fpobj.getChild():
            fpobj = fpobj.getChild()
    except NoSuchPath as e:
        return None

    return fpobj

def _open(path, mode='r'):
    '''
    Returns a read-only file-like object even is the path terminates inside a container file.
    If the path is a regular os accessible path mode is passed through.  If the path terminates 
    in a container file mode is ignored.

    If the path does not exist a NoSuchPath exception is raised.
    If the path exists, but is not a file a FileNotFoundError exception is raised.

    ex.
    _open('/foo/bar/baz.egg/path/inside/zip/to/file')
    '''
    fpobj = _parse_path(path)
    if not fpobj._type().endswith('.file'):
        raise FileNotFoundError(path)

    fd = fpobj._open(mode=mode)
    return fd

def isfile(path):
    '''
    Determines if the path is a file, even if the path terminates inside a container file.
    Returns a boolean.
    '''
    ptype = _enum_path(path)
    if ptype and ptype.endswith('.file'):
        return True
    return False

def isdir(path):
    '''
    Determines if the path is a directory, even if the path terminates inside a container file.
    Returns a boolean.
    '''
    ptype = _enum_path(path)
    if ptype and ptype.endswith('.dir'):
        return True
    return False

def exists(path):
    '''
    Determines if the path exists even if the path terminates inside a container file.
    Returns a boolean.
    '''
    if _enum_path(path) == None:
        return False
    return True

_path_ctors = {
    'reg.dir': FilePathDir,
    'tar.dir': FilePathTarDir,
    'zip.dir': FilePathZipDir,
    'reg.file': FilePathFile,
    'tar.file': FilePathTar,
    'zip.file': FilePathZip,
    'tar.inner.file': FilePathTarFile,
    'zip.inner.file': FilePathZipFile,
}

