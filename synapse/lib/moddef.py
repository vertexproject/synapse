import dis
import sys
import collections
import distutils.sysconfig as sysconfig

import synapse.dyndeps as s_dyndeps

import synapse.lib.tags as s_tags

from synapse.common import *
from synapse.compat import iterbytes
from os.path import isdir, isfile, abspath

'''
A set of utilities for locating/inspecting python modules.
'''

IMPORT_NAME = dis.opname.index('IMPORT_NAME')
IMPORT_FROM = dis.opname.index('IMPORT_FROM')

modtypes = (
    tufo('.py', fmt='src'),
    tufo('.pyd', fmt=None),
    tufo('.pyo', fmt=None),
    tufo('.pyc', fmt=None),
)


skippfx = ('.',)
skipsfx = ('.pyc',)
skipfiles = ('.','..','__init__.py','__pycache__')

def isSkipName(name):
    '''
    Check if a file basename is a known "skipable".
    '''
    for pfx in skippfx:
        if name.startswith(pfx):
            return True

    for sfx in skipsfx:
        if name.endswith(sfx):
            return True

    if name in skipfiles:
        return True

def _getModInfo(name):
    '''
    Get module info for a given file name.
    '''
    modinfo = {}

    if name == '__init__.py':
        modinfo['pkg'] = True

    for sfx,info in modtypes:
        if name.endswith(sfx):
            modinfo.update(info)
            return modinfo

pymods = None
def getPyStdLib():
    '''
    Get a {name:moddef} dict for python stdlib.
    '''
    global pymods
    if pymods == None:
        pylib = sysconfig.get_python_lib(standard_lib=True)
        pymods = getModsByPath(pylib)
        # get the compiled in modules
        bins = sys.builtin_module_names
        pymods.update({ n:tufo(n,fmt='bin') for n in bins})
    return pymods

def isPyStdLib(name):
    '''
    Checks if a module name is part of the py stdlib.
    '''
    py = getPyStdLib()
    if py.get(name):
        return True

    # this accounts for things like os.path...
    pk = name.split('.')[0]
    if py.get(pk):
        return True

def getModDef(name):
    '''
    Build a moddef tufo for the given module name.

    Example:

        moddef = getModDef('synapse.mindmeld')

    '''
    mod = s_dyndeps.getDynMod(name)
    if mod == None:
        return None

    modpath = getattr(mod,'__file__',None)
    if modpath == None:
        return None

    if modpath.endswith('.pyc'):
        modpath = modpath[:-1]

    modbase = os.path.basename(modpath)
    modinfo = _getModInfo(modbase)

    if modinfo != None:
        return tufo(name, path=modpath, **modinfo)

    # hrm...  what now smart guy?!?!
    if name in sys.builtin_module_names:
        return tufo(name, fmt='bin')

def getModDefSrc(moddef):
    '''
    Get the source for a moddef ( if available ).

    Example:

        moddef = getModDef('synapse.mindmeld')

        src = getModDefSrc(moddef)
        if src != None:
            dostuff(src)

    '''
    fmt = moddef[1].get('fmt')
    path = moddef[1].get('path')

    if fmt == 'src' and path != None and os.path.isfile(path):
        with open(path,'rb') as fd:
            return fd.read()

def getModDefCode(moddef):
    '''
    Return a compiled code object for a moddef.
    '''
    if moddef[1].get('fmt') != 'src':
        return None

    path = moddef[1].get('path')
    modsrc = getModDefSrc(moddef)
    if modsrc == None:
        return None

    return compile(modsrc,path,'exec')

def getCallModDef(func):
    '''
    Return a dict of moddefs for the given callable.

    Example:

        moddef = getCallModDef(func)

    '''
    modname = getattr(func,'__module__',None)
    if modname != None:
        return getModDef(modname)

def getModsByPath(path, modtree=None):
    '''
    Return a list of (modname,info) tuples for a path entry.

    Example:

        for path in sys.path:
            mods = getModsByPath(path)
            dostuff(mods)

    '''
    path = abspath(path)
    if modtree == None:
        modtree = []

    if not os.path.isdir(path):
        raise NoSuchDir(path=path)

    mods = {}
    todo = [ (path, modtree) ]
    while todo:
        path,modtree = todo.pop()
        pkgname = '.'.join(modtree)

        for name in os.listdir(path):
            if isSkipName(name):
                continue

            subbase = name.rsplit('.')[0]
            subtree = modtree + [ subbase ]
            subpath = os.path.join(path,name)

            modname = '.'.join(subtree)

            # check for a pkg dir...
            if isdir(subpath):

                pkgfile = os.path.join(subpath,'__init__.py')
                if not isfile(pkgfile):
                    continue

                # pkg dir found!
                mods[modname] = tufo(modname, fmt='src', path=pkgfile, pkg=True)

                todo.append( (subpath,subtree) )

                continue

            modinfo = _getModInfo(name)
            if modinfo != None:
                # fmt=None for unhandled module types
                if not modinfo.get('fmt'):
                    continue

                mods[modname] = tufo(modname,path=subpath,**modinfo)
                continue

            # add dat files to our pkg moddef
            pmod = mods.get(pkgname)
            if pmod == None:
                continue

            dats = pmod[1].get('dats')
            if dats == None:
                dats = {}
                pmod[1]['dats'] = dats

            dats[name] = subpath

    return mods

def getModDefImps(moddef):
    '''
    Return a {name:moddef} dictionary for all
    modules imported by moddef.
    '''
    modcode = getModDefCode(moddef)
    if modcode == None:
        return ()

    i = 0
    ops = list( iterbytes( modcode.co_code ) )

    names = modcode.co_names
    lastname = None

    imps = []
    while i < len(ops):

        op = ops[i]
        oparg = None

        name = None

        if op >= dis.HAVE_ARGUMENT:
            i += 1
            oparg = ops[i]

        if op == IMPORT_NAME:
            lastname = names[oparg]
            imps.append(lastname)

        elif op == IMPORT_FROM:
            imps.append('%s.%s' % (lastname, names[oparg]))

        i += 1

    return imps

siteskip = ('msgpack','requests','tornado')
def getSiteDeps(moddef):
    '''
    Return a {name:moddef} dict for all deps of
    moddef ( recursively ) but *exclude* py stdlib.
    '''
    deps = {}
    pymods = getPyStdLib()

    todo = collections.deque()

    def addtodo(md):
        for tagname in s_tags.iterTagDown( md[0] ):
            todo.append( getModDef( tagname ) )

    addtodo(moddef)

    while todo:

        moddef = todo.popleft()
        modname = moddef[0]

        topname = modname.split('.')[0]
        if topname in siteskip:
            continue

        if deps.get(modname):
            continue

        deps[ modname ] = moddef

        for imp in getModDefImps(moddef):

            if isPyStdLib(imp):
                continue

            if imp in siteskip:
                continue

            if deps.get(imp):
                continue

            depmod = getModDef(imp)
            if depmod == None:
                continue

            addtodo(depmod)

    return deps
