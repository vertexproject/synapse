import io
import os
import imp
import sys
import marshal
import traceback
import collections

import synapse.lib.moddef as s_moddef

from synapse.common import *
from synapse.compat import majmin

'''
The synapse mindmeld subsystem provides a mechanism for the
serialization and synchronization of code between processes.
'''

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

    def addModDef(self, moddef, dat=False, src=True):
        '''
        Add a moddef tufo to the meld.

        Example:

            moddef = synapse.lib.moddef.getModDef('foo')
            meld.addModDef(moddef)

        Notes:

            * This will add pkg submodules automatically

        '''
        name = moddef[0]
        mods = self.info.get('modules')
        if mods.get(name):
            return

        self._addModDef(moddef, dat=dat, src=src)
        if moddef[1].get('pkg'):
            path = moddef[1].get('path')
            pathdir = os.path.dirname(path)
            submods = s_moddef.getModsByPath(pathdir,modtree=[name])
            for subname,subdef in submods.items():
                self._addModDef(subdef, dat=dat, src=src)

    def _addModDef(self, moddef, dat=False, src=True):
        mods = self.info.get('modules')

        if src and moddef[1].get('src') == None:
            moddef[1]['src'] = s_moddef.getModDefSrc(moddef)

        # if asked, gather up dat file bytes
        if dat:
            dats = moddef[1].get('dats')
            for name,path in dats.items():
                # FIXME: path sep
                datpath = os.path.join( moddef[0], name )
                datbyts = open(path,'rb').read()
                self.info['datfiles'][datpath] = datbyts

        mods[ moddef[0] ] = moddef

        if not dat:
            return

    def addPyMod(self, name, dat=False):
        '''
        Add a python module/package to the meld.

        Example:

            meld.addPyMod('vivisect')

        '''
        moddef = s_moddef.getModDef(name)
        if moddef == None:
            raise NoSuchMod(name=name)

        self.addModDef(moddef)

    def addPyCall(self, func):
        '''
        A utility function which adds all non-stdlib dependances
        which are needed to run the given function/method.

        Example:

            meld.addPyCall( getFooByBar )

        '''
        moddef = s_moddef.getCallModDef(func)
        deps = s_moddef.getSiteDeps(moddef)
        for moddef in deps.values():
            self._addModDef(moddef)

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

        raise NoSuchPath(path=path)

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

            byts = marshal.dumps( compile( sorc ) )

        Note:

            This API is mostly for use by routines like
            addPySource.

        '''
        modinfo['fmt'] = 'pyc'
        modinfo['bytes'] = byts
        modinfo['pyver'] = majmin

        self.info['modules'][name] = tufo(name, **modinfo)

    def getMeldMod(self, name):
        '''
        Return the module information for the given name.

        Example:

            moddef = meld.getMeldMod('foo.bar')

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

            moddef = self.info['modules'].get(fullname)
            if moddef == None:
                raise ImportError(fullname)

            modcode = None

            # try bytecode first ( save on compile cycles )
            byts = moddef[1].get('bytes')
            if byts and moddef[1].get('pyver') == majmin:
                modcode = marshal.loads(byts)

            modsrc = moddef[1].get('src')
            # fall back on src if present
            if modcode == None and modsrc:
                modcode = compile(modsrc)

            # still None? bail...
            if modcode == None:
                raise ImportError(fullname)

            mod = imp.new_module(fullname)
            sys.modules[fullname] = mod

            exec(modcode,mod.__dict__)

            # populate loader provided module locals
            mod.__path__ = fullname
            mod.__file__ = moddef[1].get('path')

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

def getCallMeld(func,**info):
    '''
    Return a "site meld" for the given callable function.
    '''
    meld = MindMeld(**info)
    meld.addPyCall(func)
    return meld
