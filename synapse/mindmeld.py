import io
import os
import imp
import sys
import marshal
import traceback
import collections

from synapse.common import *

'''
The synapse mindmeld subsystem provides a mechanism for the
serialization and synchronization of code between processes.
'''
class NoSuchPath(Exception):pass
class BadPySource(Exception):pass

class MindMeld:
    '''
    The MindMeld class implements an archive format based
    on serializable primitives to allow apps to build/send
    code packages.
    '''
    def __init__(self, **info):

        self.info = info
        self.info.setdefault('salt',None)
        self.info.setdefault('crypto',None)
        self.info.setdefault('modules',{})
        self.info.setdefault('datfiles',{})

    def setVersion(self, ver):
        '''
        Set the meld version tuple.

        Example:

            meld.setVersion( (1,2,30) )

        '''
        self.info['version'] = ver

    def setName(self, name):
        '''
        Set the meld name.

        Example:

            meld.setName('foolib')

        '''
        self.info['name'] = name

    def openDatFile(self, datpath):
        '''
        Open a datfile embedded with the python code.

        Example:

            fd = meld.openDatFile('foo.bar.baz/blah.dat')

        '''
        byts = self.info['datfiles'].get(datpath)
        if byts != None:
            return io.BytesIO(byts)

    def addPyPath(self, path, name=None, datfiles=False):
        '''
        Add a path full of python code to the mind meld archive.
        If a directory is specififed, it is treated as a package.

        Example:

            meld.addPyPath('/home/visi/foobar/')
            meld.addPyPath('/home/visi/grok.py')

        Notes:

            * specify datfiles=True to pick up all binary files
              and allow access via synapse.datfile API.

        '''
        if os.path.isfile(path):
            if name == None:
                name = os.path.basename(path).rsplit('.',1)[0]

            with open(path,'rb') as fd:
                sorc = fd.read()

            self.addPySource(name,sorc)
            return

        if os.path.isdir(path):
            pkgname = os.path.basename(path)

            todo = collections.deque([ (path,pkgname) ])
            while todo:

                path,pkgname = todo.popleft()
                pkgfile = os.path.join(path,'__init__.py')
                if not os.path.isfile(pkgfile):
                    continue

                self.addPyPath(pkgfile,name=pkgname)
                for subname in os.listdir(path):
                    if subname in ('.','..','__init__.py','__pycache__'):
                        continue

                    if subname.startswith('.'):
                        continue

                    subpath = os.path.join(path,subname)
                    if os.path.isdir(subpath):
                        todo.append( (subpath,'%s.%s' % (pkgname,subname)) )
                        continue

                    if not os.path.isfile(subpath):
                        continue

                    # handle basic python module first...
                    if subname.endswith('.py'):
                        modname = subname.rsplit('.',1)[0]
                        modpath = '%s.%s' % (pkgname,modname)
                        self.addPyPath(subpath, name=modpath)
                        continue

                    # always skip pyc files for now...
                    if subname.endswith('.pyc'):
                        continue

                    # should we allow datfiles?
                    if not datfiles:
                        continue

                    # save up binary data into the meld info
                    with open(subpath,'rb') as fd:
                        datpath = '%s/%s' % (pkgname,subname)
                        self.info['datfiles'][ datpath ] = fd.read()

            return

        raise NoSuchPath(path)

    def addPySource(self, name, sorc):
        '''
        Add a python module to the MindMeld by name and source code.

        Example:

            meld.addPySource('woot','x = 10')

        '''
        try:
            code = compile(sorc,'','exec')
        except Exception as e:
            raise BadPySource('%s: %s' % (name,e))

        byts = marshal.dumps(code)
        self.addMeldMod(name,byts)

    def addMeldMod(self, name, byts, **modinfo):
        '''
        Add a MindMeld module by name and bytes.
        '''
        modinfo['name'] = name
        modinfo['bytes'] = byts
        self.info['modules'][name] = modinfo

    def getMeldMod(self, name):
        '''
        Return the module information for the given name.

        Example:

            modinfo = meld.getMeldMod('foo.bar')

        '''
        return self.info['modules'].get(name)

    def getMeldDict(self):
        '''
        Return the serializable internal state of the MindMeld.

        Example:

            info = meld.getMeldDict()

        Notes:

            * For perf, this does *not* copy.  Do not modify!

        '''
        return self.info

    def getMeldBytes(self):
        '''
        Return a msgpack packed copy of the MindMeld dictionary.
        '''
        return msgenpack(self.info)

    def getMeldBase64(self):
        '''
        Return a base64 encoded msgpack packed MindMeld dictionary.
        '''
        return enbase64( self.getMeldBytes() )

    # Implement the "loader" interface

    def find_module(self, name, path=None):
        #print('FIND: %r %r' % (name,path))
        if self.info['modules'].get(name) != None:
            return self

    def load_module(self, fullname):
        #print('LOAD: %r' % (fullname,))
        mod = sys.modules.get(fullname)
        if mod != None:
            return mod

        try:

            modinfo = self.info['modules'].get(fullname)
            if modinfo == None:
                raise ImportError(fullname)

            byts = modinfo.get('bytes')
            if byts == None:
                raise ImportError(fullname)

            mod = imp.new_module(fullname)
            sys.modules[fullname] = mod

            code = marshal.loads(byts)
            exec(code,mod.__dict__)

            # populate loader provided module locals
            mod.__path__ = fullname
            mod.__loader__ = self
            return mod

        except Exception as e:
            traceback.print_exc()
            raise ImportError(str(e))

def loadMindMeld(info):
    '''
    Load a MindMeld dictionary into the current python loader.

    Example:

        loadMindMeld(info)

    '''
    meld = MindMeld(**info)
    addMindMeld(meld)
    return meld

def loadMeldBytes(byts):
    '''
    Load a MindMeld instance from msgpack bytes.
    '''
    info = msgunpack(byts)
    return loadMindMeld(info)

def loadMeldBase64(b64):
    '''
    Load a MindMeld instance from base64 encoded msgpack bytes.
    '''
    byts = debase64(b64)
    return loadMeldBytes(byts)

def addMindMeld(meld):
    '''
    Add a MindMeld instance to the current python import hooks.

    Example:

        addMindMeld(meld)

    '''
    sys.meta_path.append(meld)
