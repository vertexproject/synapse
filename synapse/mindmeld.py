import os
import imp
import sys
import marshal
import traceback
import collections

'''
The synapse mindmeld subsystem provides a mechanism for the
serialization and synchronization of code between processes.
'''

class NoSuchPath(Exception):pass

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

    def addPyPath(self, path, name=None):
        '''
        Add a path full of python code to the mind meld archive.
        If a directory is specififed, it is treated as a package.

        Example:

            meld.addPyPath('/home/visi/foobar/')
            meld.addPyPath('/home/visi/grok.py')

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

                    subpath = os.path.join(path,subname)
                    if os.path.isdir(subpath):
                        todo.append( (subpath,'%s.%s' % (pkgname,subname)) )
                        continue

                    if not os.path.isfile(subpath):
                        continue

                    if not subname.endswith('.py'):
                        continue

                    modname = subname.rsplit('.',1)[0]
                    self.addPyPath(subpath, name='%s.%s' % (pkgname,modname))

            return

        raise NoSuchPath(path)

    def addPySource(self, name, sorc):
        '''
        Add a python module to the MindMeld by name and source code.

        Example:

            meld.addPySource('woot','x = 10')

        '''
        code = compile(sorc,'','exec')
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
    return addMindMeld(meld)

def addMindMeld(meld):
    '''
    Add a MindMeld instance to the current python import hooks.

    Example:

        addMindMeld(meld)

    '''
    sys.meta_path.append(meld)
