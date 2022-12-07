import bz2
import copy
import gzip
import json
import time
import regex
import types
import base64
import pprint
import struct
import asyncio
import decimal
import inspect
import logging
import binascii
import datetime
import calendar
import functools
import collections
from typing import Any

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope
import synapse.lib.msgpack as s_msgpack
import synapse.lib.urlhelp as s_urlhelp
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.provenance as s_provenance

logger = logging.getLogger(__name__)

class Undef:
    pass

undef = Undef()

def confirm(perm, gateiden=None):
    s_scope.get('runt').confirm(perm, gateiden=gateiden)

def allowed(perm, gateiden=None):
    return s_scope.get('runt').allowed(perm, gateiden=gateiden)

class StormTypesRegistry:
    # The following types are currently undefined.
    base_undefined_types = (
        'any',
        'int',
        'null',
        'time',
        'prim',
        'undef',
        'float',
        'integer',
        'storm:lib',  # lib.import
        'generator',
    )
    undefined_types = set(base_undefined_types)
    known_types = set()
    rtypes = collections.defaultdict(set)  # callable -> return types, populated on demand.

    def __init__(self):
        self._LIBREG = {}
        self._TYPREG = {}

    def addStormLib(self, path, ctor):
        if path in self._LIBREG:
            raise Exception('cannot register a library twice')
        assert isinstance(path, tuple)
        self._LIBREG[path] = ctor

    def delStormLib(self, path):
        if not self._LIBREG.pop(path, None):
            raise Exception('no such path!')

    def addStormType(self, path, ctor):
        if path in self._TYPREG:
            raise Exception('cannot register a type twice')
        assert ctor._storm_typename is not None, f'path={path} ctor={ctor}'
        self._TYPREG[path] = ctor
        self.known_types.add(ctor._storm_typename)
        self.undefined_types.discard(ctor._storm_typename)

    def delStormType(self, path):
        ctor = self._TYPREG.pop(path, None)
        if ctor is None:
            raise Exception('no such path!')
        self.known_types.discard(ctor._storm_typename)
        self.undefined_types.add(ctor._storm_typename)

    def registerLib(self, ctor):
        '''Decorator to register a StormLib'''
        path = getattr(ctor, '_storm_lib_path', s_common.novalu)
        if path is s_common.novalu:
            raise Exception('no key!')
        self.addStormLib(path, ctor)

        return ctor

    def registerType(self, ctor):
        '''Decorator to register a StormPrim'''
        self.addStormType(ctor.__name__, ctor)
        return ctor

    def iterLibs(self):
        return list(self._LIBREG.items())

    def iterTypes(self):
        return list(self._TYPREG.items())

    def _validateInfo(self, obj, info, name):
        # Check the rtype of the info to see if its a dict; and  if so,
        # validate it has the _funcname key pointing to the to a
        # callable on the obj, and that the documented arguments match
        # those of the callable. The _funcname key is removed.

        rtype = info.get('type')
        if isinstance(rtype, dict):
            rname = rtype.get('type')
            rname = copy.deepcopy(rname)  # Make a mutable copy we're going to modify

            if isinstance(rname, tuple):
                rname = list(rname)

            isstor = False
            isfunc = False
            isgtor = False
            isctor = False

            if rname == 'ctor' or 'ctor' in rname:
                isctor = True
                if isinstance(rname, str):
                    rname = ''
                if isinstance(rname, list):
                    rname.remove('ctor')
                if isinstance(rname, dict):
                    rname.pop('ctor', None)
            if rname == 'function' or 'function' in rname:
                isfunc = True
                if isinstance(rname, str):
                    rname = ''
                if isinstance(rname, list):
                    rname.remove('function')
                if isinstance(rname, dict):
                    rname.pop('function', None)
            if rname == 'gtor' or 'gtor' in rname:
                isgtor = True
                if isinstance(rname, str):
                    rname = ''
                if isinstance(rname, list):
                    rname.remove('gtor')
                if isinstance(rname, dict):
                    rname.pop('gtor', None)
            if rname == 'stor' or 'stor' in rname:
                if isinstance(rname, str):
                    rname = ''
                if isinstance(rname, list):
                    rname.remove('stor')
                if isinstance(rname, dict):
                    rname.pop('stor', None)
                isstor = True

            invalid = (isgtor and isctor) or (isfunc and (isgtor or isctor))
            if invalid:
                mesg = f'Dictionary represents invalid combination of ctors, gtors, locls, and stors [{name} {obj} {info.get("name")}] [{rtype}].'
                raise AssertionError(mesg)

            if rname:
                mesg = f'Dictionary return types represents a unknown rtype [{name} {obj} {info.get("name")}] [{rtype}] [{rname}].'
                raise AssertionError(mesg)

            if isfunc:
                self._validateFunction(obj, info, name)
            if isstor:
                self._validateStor(obj, info, name)
            if isctor:
                self._validateCtor(obj, info, name)
            if isgtor:
                self._validateGtor(obj, info, name)

    def _validateFunction(self, obj, info, name):
        rtype = info.get('type')
        funcname = rtype.pop('_funcname')
        if funcname == '_storm_query':
            # Sentinel used for future validation of pure storm
            # functions defined in _storm_query data.
            return
        locl = getattr(obj, funcname, None)
        assert locl is not None, f'bad _funcname=[{funcname}] for {obj} {info.get("name")}'
        args = rtype.get('args', ())
        callsig = getCallSig(locl)
        # Assert the callsigs match
        callsig_args = [str(v).split('=')[0] for v in callsig.parameters.values()]
        assert [d.get('name') for d in
                args] == callsig_args, f'args / callsig args mismatch for {funcname} {name} {obj} {args} {callsig_args}'
        # ensure default values are provided
        for parameter, argdef in zip(callsig.parameters.values(), args):
            pdef = parameter.default  # defaults to inspect._empty for undefined default values.
            adef = argdef.get('default', inspect._empty)
            assert pdef == adef, \
                f'Default value mismatch for {obj} {funcname}, defvals {pdef} != {adef} for {parameter}'

    def _validateStor(self, obj, info, name):
        rtype = info.get('type')
        funcname = rtype.pop('_storfunc')
        locl = getattr(obj, funcname, None)
        assert locl is not None, f'bad _storfunc=[{funcname}] for {obj} {info.get("name")}'
        args = rtype.get('args')
        assert args is None, f'stors have no defined args funcname=[{funcname}] for {obj} {info.get("name")}'
        callsig = getCallSig(locl)
        # Assert the callsig for a stor has one argument
        callsig_args = [str(v).split('=')[0] for v in callsig.parameters.values()]
        assert len(callsig_args) == 1, f'stor funcs must only have one argument for {obj} {info.get("name")}'

    def _validateCtor(self, obj, info, name):
        rtype = info.get('type')
        funcname = rtype.pop('_ctorfunc')
        locl = getattr(obj, funcname, None)
        assert locl is not None, f'bad _ctorfunc=[{funcname}] for {obj} {info.get("name")}'
        args = rtype.get('args')
        assert args is None, f'ctors have no defined args funcname=[{funcname}] for {obj} {info.get("name")}'
        callsig = getCallSig(locl)
        # Assert the callsig for a stor has one argument
        callsig_args = [str(v).split('=')[0] for v in callsig.parameters.values()]
        assert len(callsig_args) == 1, f'stor funcs must only have one argument for {obj} {info.get("name")}'

    def _validateGtor(self, obj, info, name):
        rtype = info.get('type')
        funcname = rtype.pop('_gtorfunc')
        locl = getattr(obj, funcname, None)
        assert locl is not None, f'bad _gtorfunc=[{funcname}] for {obj} {info.get("name")}'
        args = rtype.get('args')
        assert args is None, f'gtors have no defined args funcname=[{funcname}] for {obj} {info.get("name")}'
        callsig = getCallSig(locl)
        # Assert the callsig for a stor has one argument
        callsig_args = [str(v).split('=')[0] for v in callsig.parameters.values()]
        assert len(callsig_args) == 0, f'gtor funcs must only have one argument for {obj} {info.get("name")}'

    def getLibDocs(self):
        # Ensure type docs are loaded/verified.
        _ = self.getTypeDocs()

        libs = self.iterLibs()
        libs.sort(key=lambda x: x[0])
        docs = []
        for (sname, slib) in libs:
            sname = slib.__class__.__name__
            locs = []
            tdoc = {
                'desc': getDoc(slib, sname),
                'locals': locs,
                'path': ('lib',) + slib._storm_lib_path,
            }
            for info in sorted(slib._storm_locals, key=lambda x: x.get('name')):
                info = s_msgpack.deepcopy(info)
                self._validateInfo(slib, info, sname)
                locs.append(info)

            docs.append(tdoc)

        for tdoc in docs:
            basepath = tdoc.get('path')
            assert basepath[0] == 'lib'
            locls = tdoc.get('locals')
            for info in locls:
                path = basepath + (info.get('name'),)
                ityp = info.get('type')
                if isinstance(ityp, str):
                    self.rtypes[path].add(ityp)
                    continue
                retv = ityp.get('returns')
                rtyp = retv.get('type')
                if isinstance(rtyp, (list, tuple)):
                    [self.rtypes[path].add(r) for r in rtyp]
                    continue
                self.rtypes[path].add(rtyp)

        for path, rtyps in self.rtypes.items():
            for rtyp in rtyps:
                if rtyp not in self.known_types and rtyp not in self.undefined_types:  # pragma: no cover
                    raise s_exc.NoSuchType(mesg=f'The return type {rtyp} for {path} is unknown.', type=rtyp)

        return docs

    def getTypeDocs(self):

        types = self.iterTypes()
        types.sort(key=lambda x: x[1]._storm_typename)

        docs = []
        for (sname, styp) in types:
            locs = []
            tdoc = {
                'desc': getDoc(styp, sname),
                'locals': locs,
                'path': (styp._storm_typename,),
            }
            for info in sorted(styp._storm_locals, key=lambda x: x.get('name')):
                info = s_msgpack.deepcopy(info)
                self._validateInfo(styp, info, sname)
                locs.append(info)

            docs.append(tdoc)

        for tdoc in docs:
            basepath = tdoc.get('path')
            assert len(basepath) == 1
            locls = tdoc.get('locals')
            for info in locls:
                path = basepath + (info.get('name'),)
                ityp = info.get('type')
                if isinstance(ityp, str):
                    self.rtypes[path].add(ityp)
                    continue
                retv = ityp.get('returns')
                rtyp = retv.get('type')
                if isinstance(rtyp, (list, tuple)):
                    [self.rtypes[path].add(r) for r in rtyp]
                    continue
                self.rtypes[path].add(rtyp)

        for path, rtyps in self.rtypes.items():
            for rtyp in rtyps:
                if rtyp not in self.known_types and rtyp not in self.undefined_types:  # pragma: no cover
                    raise s_exc.NoSuchType(mesg=f'The return type {rtyp} for {path} is unknown.', type=rtyp)

        return docs

registry = StormTypesRegistry()


def getDoc(obj, errstr):
    '''Helper to get __doc__'''
    doc = getattr(obj, '__doc__')
    if doc is None:
        doc = f'No doc for {errstr}'
        logger.warning(doc)
    return doc

def getCallSig(func) -> inspect.Signature:
    '''Get the callsig of a function, stripping self if present.'''
    callsig = inspect.signature(func)
    params = list(callsig.parameters.values())
    if params and params[0].name == 'self':
        callsig = callsig.replace(parameters=params[1:])
    return callsig


def stormfunc(readonly=False):
    def wrap(f):
        f._storm_readonly = readonly
        return f
    return wrap

def intify(x):

    if isinstance(x, str):

        x = x.lower()
        if x == 'true':
            return 1

        if x == 'false':
            return 0

        try:
            return int(x, 0)
        except ValueError as e:
            mesg = f'Failed to make an integer from "{x}".'
            raise s_exc.BadCast(mesg=mesg) from e

    try:
        return int(x)
    except Exception as e:
        mesg = f'Failed to make an integer from "{x}".'
        raise s_exc.BadCast(mesg=mesg) from e

async def kwarg_format(_text, **kwargs):
    '''
    Replaces instances curly-braced argument names in text with their values
    '''
    for name, valu in kwargs.items():
        temp = '{%s}' % (name,)
        _text = _text.replace(temp, await torepr(valu, usestr=True))

    return _text

class StormType:
    '''
    The base type for storm runtime value objects.
    '''
    _storm_locals = ()  # type: Any # To be overriden for deref constants that need documentation
    _ismutable = True
    _storm_typename = 'storm:unknown'

    def __init__(self, path=None):
        self.path = path

        # ctors take no arguments and are intended to return Prim objects. This must be sync.
        # These are intended for delayed Prim object construction until they are needed.
        self.ctors = {}

        # stors are setter functions which take a single value for setting.
        # These are intended to act similar to python @setter decorators.
        self.stors = {}

        # gtors are getter functions which are called without arguments. This must be async.
        # These are intended as to act similar to python @property decorators.
        self.gtors = {}

        # Locals are intended for storing callable functions and constants.
        self.locls = {}

    def getObjLocals(self):
        '''
        Get the default list of key-value pairs which may be added to the object ``.locls`` dictionary.

        Returns:
            dict: A key/value pairs.
        '''
        return {}

    async def _storm_copy(self):
        mesg = f'Type ({self._storm_typename}) does not support being copied!'
        raise s_exc.BadArg(mesg=mesg)

    async def setitem(self, name, valu):

        if not self.stors:
            mesg = f'{self.__class__.__name__} does not support assignment.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        name = await tostr(name)

        stor = self.stors.get(await tostr(name))
        if stor is None:
            mesg = f'Setting {name} is not supported on {self._storm_typename}.'
            raise s_exc.NoSuchName(name=name, mesg=mesg)

        await s_coro.ornot(stor, valu)

    async def deref(self, name):
        locl = self.locls.get(name, s_common.novalu)
        if locl is not s_common.novalu:
            return locl

        ctor = self.ctors.get(name)
        if ctor is not None:
            item = ctor(path=self.path)
            self.locls[name] = item
            return item

        valu = await self._derefGet(name)
        if valu is not s_common.novalu:
            return valu

        raise s_exc.NoSuchName(mesg=f'Cannot find name [{name}]', name=name, styp=self.__class__.__name__)

    async def _derefGet(self, name):
        gtor = self.gtors.get(name)
        if gtor is None:
            return s_common.novalu
        return await gtor()

    def ismutable(self):
        return self._ismutable

class Lib(StormType):
    '''
    A collection of storm methods under a name
    '''
    _ismutable = False
    _storm_query = None
    _storm_typename = 'storm:lib'

    def __init__(self, runt, name=()):
        StormType.__init__(self)
        self.runt = runt
        self.name = name
        self.auth = runt.snap.core.auth
        self.addLibFuncs()

    def addLibFuncs(self):
        self.locls.update(self.getObjLocals())

    async def initLibAsync(self):

        if self._storm_query is not None:

            query = await self.runt.snap.core.getStormQuery(self._storm_query)
            self.modrunt = await self.runt.getModRuntime(query)

            self.runt.onfini(self.modrunt)

            async for item in self.modrunt.execute():
                await asyncio.sleep(0)  # pragma: no cover

            self.locls.update(self.modrunt.vars)

    async def stormrepr(self):
        if '__module__' in self.locls:
            return f'Imported Module {".".join(self.name)}'
        return f'Library ${".".join(("lib",) + self.name)}'

    async def deref(self, name):
        try:
            return await StormType.deref(self, name)
        except s_exc.NoSuchName:
            pass

        path = self.name + (name,)

        slib = self.runt.snap.core.getStormLib(path)
        if slib is None:
            raise s_exc.NoSuchName(mesg=f'Cannot find name [{name}]', name=name)

        ctor = slib[2].get('ctor', Lib)
        libinst = ctor(self.runt, name=path)

        await libinst.initLibAsync()

        return libinst

    async def dyncall(self, iden, todo, gatekeys=()):
        return await self.runt.dyncall(iden, todo, gatekeys=gatekeys)

    async def dyniter(self, iden, todo, gatekeys=()):
        async for item in self.runt.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

@registry.registerLib
class LibPkg(Lib):
    '''
    A Storm Library for interacting with Storm Packages.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a Storm Package to the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgAdd',
                  'args': (
                      {'name': 'pkgdef', 'type': 'dict', 'desc': 'A Storm Package definition.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a Storm Package from the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'A Storm Package name.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The Storm package definition.', }}},
        {'name': 'has', 'desc': 'Check if a Storm Package is available in the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgHas',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'A Storm Package name to check for the existence of.', },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the package exists in the Cortex, False if it does not.', }}},
        {'name': 'del', 'desc': 'Delete a Storm Package from the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgDel',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the package to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of Storm Packages loaded in the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgList',
                  'returns': {'type': 'list', 'desc': 'A list of Storm Package definitions.', }}},
        {'name': 'deps', 'desc': 'Verify the dependencies for a Storm Package.',
         'type': {'type': 'function', '_funcname': '_libPkgDeps',
                  'args': (
                      {'name': 'pkgdef', 'type': 'dict', 'desc': 'A Storm Package definition.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary listing dependencies and if they are met.', }}},
    )
    _storm_lib_path = ('pkg',)

    def getObjLocals(self):
        return {
            'add': self._libPkgAdd,
            'get': self._libPkgGet,
            'has': self._libPkgHas,
            'del': self._libPkgDel,
            'list': self._libPkgList,
            'deps': self._libPkgDeps,
        }

    async def _libPkgAdd(self, pkgdef):
        self.runt.confirm(('pkg', 'add'), None)
        pkgdef = await toprim(pkgdef)
        await self.runt.snap.core.addStormPkg(pkgdef)

    async def _libPkgGet(self, name):
        name = await tostr(name)
        pkgdef = await self.runt.snap.core.getStormPkg(name)
        if pkgdef is None:
            return None

        return Dict(pkgdef)

    async def _libPkgHas(self, name):
        name = await tostr(name)
        pkgdef = await self.runt.snap.core.getStormPkg(name)
        if pkgdef is None:
            return False
        return True

    async def _libPkgDel(self, name):
        self.runt.confirm(('pkg', 'del'), None)
        await self.runt.snap.core.delStormPkg(name)

    async def _libPkgList(self):
        pkgs = await self.runt.snap.core.getStormPkgs()
        return list(sorted(pkgs, key=lambda x: x.get('name')))

    async def _libPkgDeps(self, pkgdef):
        pkgdef = await toprim(pkgdef)
        return await self.runt.snap.core.verifyStormPkgDeps(pkgdef)

@registry.registerLib
class LibDmon(Lib):
    '''
    A Storm Library for interacting with StormDmons.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': '''
        Add a Storm Dmon to the Cortex.

        Examples:
            Add a dmon that executes a query::

                $lib.dmon.add(${ myquery }, name='example dmon')
                ''',
         'type': {'type': 'function', '_funcname': '_libDmonAdd',
                  'args': (
                      {'name': 'text', 'type': ['str', 'storm:query'],
                       'desc': 'The Storm query to execute in the Dmon loop.', },
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Dmon.', 'default': 'noname', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the newly created Storm Dmon.', }}},
        {'name': 'get', 'desc': 'Get a Storm Dmon definition by iden.',
         'type': {'type': 'function', '_funcname': '_libDmonGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the Storm Dmon to get.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'A Storm Dmon definition dict.', }}},
        {'name': 'del', 'desc': 'Delete a Storm Dmon by iden.',
         'type': {'type': 'function', '_funcname': '_libDmonDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the Storm Dmon to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'log', 'desc': 'Get the messages from a Storm Dmon.',
         'type': {'type': 'function', '_funcname': '_libDmonLog',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the Storm Dmon to get logs for.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of messages from the StormDmon.', }}},
        {'name': 'list', 'desc': 'Get a list of Storm Dmons.',
         'type': {
             'type': 'function', '_funcname': '_libDmonList',
             'returns': {'type': 'list', 'desc': 'A list of Storm Dmon definitions.', }}},
        {'name': 'bump', 'desc': 'Restart the Dmon.',
         'type': {'type': 'function', '_funcname': '_libDmonBump',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The GUID of the dmon to restart.', },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the Dmon is restarted; False if the iden does not exist.', }}},
        {'name': 'stop', 'desc': 'Stop a Storm Dmon.',
         'type': {'type': 'function', '_funcname': '_libDmonStop',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The GUID of the Dmon to stop.', },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': '$lib.true unless the dmon does not exist or was already stopped.', }}},
        {'name': 'start', 'desc': 'Start a storm dmon.',
         'type': {'type': 'function', '_funcname': '_libDmonStart',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The GUID of the dmon to start.', },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': '$lib.true unless the dmon does not exist or was already started.', }}},
    )
    _storm_lib_path = ('dmon',)

    def getObjLocals(self):
        return {
            'add': self._libDmonAdd,
            'get': self._libDmonGet,
            'del': self._libDmonDel,
            'log': self._libDmonLog,
            'list': self._libDmonList,
            'bump': self._libDmonBump,
            'stop': self._libDmonStop,
            'start': self._libDmonStart,
        }

    async def _libDmonDel(self, iden):
        dmon = await self.runt.snap.core.getStormDmon(iden)
        if dmon is None:
            mesg = f'No storm dmon with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        if dmon.get('user') != self.runt.user.iden:
            self.runt.confirm(('dmon', 'del', iden))

        await self.runt.snap.core.delStormDmon(iden)

    async def _libDmonGet(self, iden):
        return await self.runt.snap.core.getStormDmon(iden)

    async def _libDmonList(self):
        return await self.runt.snap.core.getStormDmons()

    async def _libDmonLog(self, iden):
        self.runt.confirm(('dmon', 'log'))
        return await self.runt.snap.core.getStormDmonLog(iden)

    async def _libDmonAdd(self, text, name='noname'):
        text = await tostr(text)
        varz = await toprim(self.runt.vars)

        viewiden = self.runt.snap.view.iden
        self.runt.confirm(('dmon', 'add'), gateiden=viewiden)

        # closure style capture of runtime
        varz = {k: v for (k, v) in varz.items() if s_msgpack.isok(v)}

        opts = {'vars': varz, 'view': viewiden}

        ddef = {
            'name': name,
            'user': self.runt.user.iden,
            'storm': text,
            'enabled': True,
            'stormopts': opts,
        }

        return await self.runt.snap.core.addStormDmon(ddef)

    async def _libDmonBump(self, iden):
        iden = await tostr(iden)

        ddef = await self.runt.snap.core.getStormDmon(iden)
        if ddef is None:
            return False

        viewiden = ddef['stormopts']['view']
        self.runt.confirm(('dmon', 'add'), gateiden=viewiden)

        await self.runt.snap.core.bumpStormDmon(iden)
        return True

    async def _libDmonStop(self, iden):
        iden = await tostr(iden)

        ddef = await self.runt.snap.core.getStormDmon(iden)
        if ddef is None:
            return False

        viewiden = ddef['stormopts']['view']
        self.runt.confirm(('dmon', 'add'), gateiden=viewiden)

        return await self.runt.snap.core.disableStormDmon(iden)

    async def _libDmonStart(self, iden):
        iden = await tostr(iden)

        ddef = await self.runt.snap.core.getStormDmon(iden)
        if ddef is None:
            return False

        viewiden = ddef['stormopts']['view']
        self.runt.confirm(('dmon', 'add'), gateiden=viewiden)

        return await self.runt.snap.core.enableStormDmon(iden)

@registry.registerLib
class LibService(Lib):
    '''
    A Storm Library for interacting with Storm Services.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a Storm Service to the Cortex.',
         'type': {'type': 'function', '_funcname': '_libSvcAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the Storm Service to add.', },
                      {'name': 'url', 'type': 'str', 'desc': 'The Telepath URL to the Storm Service.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The Storm Service definition.', }}},
        {'name': 'del', 'desc': 'Remove a Storm Service from the Cortex.',
         'type': {'type': 'function', '_funcname': '_libSvcDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the service to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a Storm Service definition.',
         'type': {'type': 'function', '_funcname': '_libSvcGet',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The local name, local iden, or remote name, '
                               'of the service to get the definition for.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'A Storm Service definition.', }}},
        {'name': 'has', 'desc': 'Check if a Storm Service is available in the Cortex.',
         'type': {'type': 'function', '_funcname': '_libSvcHas',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The local name, local iden, or remote name, '
                               'of the service to check for the existence of.', },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the service exists in the Cortex, False if it does not.', }}},
        {'name': 'list',
         'desc': '''
            List the Storm Service definitions for the Cortex.

            Notes:
                The definition dictionaries have an additional ``ready`` key added to them to
                indicate if the Cortex is currently connected to the Storm Service or not.
            ''',
         'type': {'type': 'function', '_funcname': '_libSvcList',
                  'returns': {'type': 'list', 'desc': 'A list of Storm Service definitions.', }}},
        {'name': 'wait', 'desc': '''
        Wait for a given service to be ready.

        Notes:
            If a timeout value is not specified, this will block a Storm query until the service is available.
        ''',
         'type': {'type': 'function', '_funcname': '_libSvcWait',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name, or iden, of the service to wait for.', },
                      {'name': 'timeout', 'type': 'int', 'desc': 'Number of seconds to wait for the service.',
                       'default': None, }
                  ),
                  'returns': {'type': 'boolean', 'desc': 'Returns true if the service is available, false on a '
                                                         'timeout waiting for the service to be ready.', }}},
    )
    _storm_lib_path = ('service',)

    def getObjLocals(self):
        return {
            'add': self._libSvcAdd,
            'del': self._libSvcDel,
            'get': self._libSvcGet,
            'has': self._libSvcHas,
            'list': self._libSvcList,
            'wait': self._libSvcWait,
        }

    async def _checkSvcGetPerm(self, ssvc):
        '''
        Helper to handle service.get.* permissions
        '''
        try:
            self.runt.confirm(('service', 'get', ssvc.iden))
        except s_exc.AuthDeny as e:
            try:
                self.runt.confirm(('service', 'get', ssvc.name))
            except s_exc.AuthDeny:
                raise e from None
            else:
                mesg = 'Use of service.get.<servicename> permissions are deprecated.'
                await self.runt.warnonce(mesg, svcname=ssvc.name, svciden=ssvc.iden)

    async def _libSvcAdd(self, name, url):
        self.runt.confirm(('service', 'add'))
        sdef = {
            'name': name,
            'url': url,
        }
        return await self.runt.snap.core.addStormSvc(sdef)

    async def _libSvcDel(self, iden):
        self.runt.confirm(('service', 'del'))
        return await self.runt.snap.core.delStormSvc(iden)

    async def _libSvcGet(self, name):
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg)
        await self._checkSvcGetPerm(ssvc)
        return Service(self.runt, ssvc)

    async def _libSvcHas(self, name):
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            return False
        return True

    async def _libSvcList(self):
        self.runt.confirm(('service', 'list'))
        retn = []

        for ssvc in self.runt.snap.core.getStormSvcs():
            sdef = dict(ssvc.sdef)
            sdef['ready'] = ssvc.ready.is_set()
            sdef['svcname'] = ssvc.svcname
            sdef['svcvers'] = ssvc.svcvers
            retn.append(sdef)

        return retn

    async def _libSvcWait(self, name, timeout=None):
        name = await tostr(name)
        timeout = await toint(timeout, noneok=True)
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg, name=name)
        await self._checkSvcGetPerm(ssvc)

        # Short circuit asyncio.wait_for logic by checking the ready event
        # value. If we call wait_for with a timeout=0 we'll almost always
        # raise a TimeoutError unless the future previously had the option
        # to complete.
        if timeout == 0:
            return ssvc.ready.is_set()

        fut = ssvc.ready.wait()
        try:
            await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            return False
        else:
            return True

@registry.registerLib
class LibTags(Lib):
    '''
    Storm utility functions for tags.
    '''
    _storm_lib_path = ('tags',)

    _storm_locals = (
        {'name': 'prefix', 'desc': '''
            Normalize and prefix a list of syn:tag:part values so they can be applied.

            Examples:

                Add tag prefixes and then use them to tag nodes::

                    $tags = $lib.tags.prefix($result.tags, vtx.visi)
                    { for $tag in $tags { [ +#$tag ] } }

         ''',
         'type': {'type': 'function', '_funcname': 'prefix',
                  'args': (
                      {'name': 'names', 'type': 'list', 'desc': 'A list of syn:tag:part values to normalize and prefix.'},
                      {'name': 'prefix', 'type': 'str', 'desc': 'The string prefix to add to the syn:tag:part values.'},
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of normalized and prefixed syn:tag values.', }}},
    )

    def getObjLocals(self):
        return {
            'prefix': self.prefix,
        }

    async def prefix(self, names, prefix):

        prefix = await tostr(prefix)
        tagpart = self.runt.snap.core.model.type('syn:tag:part')

        retn = []
        async for part in toiter(names):
            try:
                partnorm = tagpart.norm(part)[0]
                retn.append(f'{prefix}.{partnorm}')
            except s_exc.BadTypeValu:
                pass

        return retn

@registry.registerLib
class LibBase(Lib):
    '''
    The Base Storm Library. This mainly contains utility functionality.
    '''
    _storm_lib_path = ()

    _storm_locals = (
        {'name': 'len', 'desc': '''
            Get the length of a item.

            This could represent the size of a string, or the number of keys in
            a dictionary, or the number of elements in an array. It may also be used
            to iterate an emitter or yield function and count the total.''',
         'type': {'type': 'function', '_funcname': '_len',
                  'args': (
                      {'name': 'item', 'desc': 'The item to get the length of.', 'type': 'prim', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The length of the item.', }}},
        {'name': 'min', 'desc': 'Get the minimum value in a list of arguments.',
         'type': {'type': 'function', '_funcname': '_min',
                  'args': (
                      {'name': '*args', 'type': 'any', 'desc': 'List of arguments to evaluate.', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The smallest argument.', }}},
        {'name': 'max', 'desc': 'Get the maximum value in a list of arguments.',
         'type': {'type': 'function', '_funcname': '_max',
                  'args': (
                      {'name': '*args', 'type': 'any', 'desc': 'List of arguments to evaluate.', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The largest argument.', }}},
        {'name': 'set', 'desc': 'Get a Storm Set object.',
         'type': {'type': 'function', '_funcname': '_set',
                  'args': (
                      {'name': '*vals', 'type': 'any', 'desc': 'Initial values to place in the set.', },
                  ),
                  'returns': {'type': 'set', 'desc': 'The new set.', }}},
        {'name': 'dict', 'desc': 'Get a Storm Dict object.',
         'type': {'type': 'function', '_funcname': '_dict',
                  'args': (
                      {'name': '**kwargs', 'type': 'any',
                       'desc': 'Initial set of keyword argumetns to place into the dict.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary object.', }}},
        {'name': 'exit', 'desc': 'Cause a Storm Runtime to stop running.',
         'type': {'type': 'function', '_funcname': '_exit',
                  'args': (
                      {'name': 'mesg', 'type': 'str', 'desc': 'Optional string to warn.', 'default': None, },
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Keyword arguments to substitute into the mesg.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'guid', 'desc': 'Get a random guid, or generate a guid from the arguments.',
         'type': {'type': 'function', '_funcname': '_guid',
                  'args': (
                      {'name': '*args', 'type': 'prim', 'desc': 'Arguments which are hashed to create a guid.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'A guid.', }}},
        {'name': 'fire', 'desc': '''
            Fire an event onto the runtime.

            Notes:
                This fires events as ``storm:fire`` event types. The name of the event is placed into a ``type`` key,
                and any additional keyword arguments are added to a dictionary under the ``data`` key.

            Examples:
                Fire an event called ``demo`` with some data::

                    cli> storm $foo='bar' $lib.fire('demo', foo=$foo, knight='ni')
                    ...
                    ('storm:fire', {'type': 'demo', 'data': {'foo': 'bar', 'knight': 'ni'}})
                    ...
            ''',
         'type': {'type': 'function', '_funcname': '_fire',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the event to fire.', },
                      {'name': '**info', 'type': 'any',
                       'desc': 'Additional keyword arguments containing data to add to the event.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a Storm List object.',
         'type': {'type': 'function', '_funcname': '_list',
                  'args': (
                      {'name': '*vals', 'type': 'any', 'desc': 'Initial values to place in the list.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A new list object.', }}},
        {'name': 'raise', 'desc': 'Raise an exception in the storm runtime.',
         'type': {'type': 'function', '_funcname': '_raise',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the error condition to raise.', },
                      {'name': 'mesg', 'type': 'str', 'desc': 'A friendly description of the specific error.', },
                      {'name': '**info', 'type': 'any', 'desc': 'Additional metadata to include in the exception.', },
                  ),
                  'returns': {'type': 'null', 'desc': 'This function does not return.', }}},
        {'name': 'null', 'desc': '''
            This constant represents a value of None that can be used in Storm.

            Examples:
                Create a dictionary object with a key whose value is null, and call ``$lib.fire()`` with it::

                    cli> storm $d=$lib.dict(key=$lib.null) $lib.fire('demo', d=$d)
                    ('storm:fire', {'type': 'demo', 'data': {'d': {'key': None}}})
            ''',
            'type': 'null', },
        {'name': 'undef', 'desc': '''
            This constant can be used to unset variables and derefs.

            Examples:
                Unset the variable $foo::

                    $foo = $lib.undef

                Remove a dictionary key bar::

                    $foo.bar = $lib.undef

                Remove a list index of 0::

                    $foo.0 = $lib.undef
            ''',
            'type': 'undef', },
        {'name': 'true', 'desc': '''
            This constant represents a value of True that can be used in Storm.

            Examples:
                Conditionally print a statement based on the constant value::

                    cli> storm if $lib.true { $lib.print('Is True') } else { $lib.print('Is False') }
                    Is True
                ''',
         'type': 'boolean', },
        {'name': 'false', 'desc': '''
            This constant represents a value of False that can be used in Storm.

            Examples:
                Conditionally print a statement based on the constant value::

                    cli> storm if $lib.false { $lib.print('Is True') } else { $lib.print('Is False') }
                    Is False''',
         'type': 'boolean', },
        {'name': 'text', 'desc': 'Get a Storm Text object.',
         'type': {'type': 'function', '_funcname': '_text',
                  'args': (
                      {'name': '*args', 'type': 'str',
                       'desc': 'An initial set of values to place in the Text. '
                               'These values are joined together with an empty string.', },
                  ),
                  'returns': {'type': 'storm:text', 'desc': 'The new Text object.', }}},
        {'name': 'cast', 'desc': 'Normalize a value as a Synapse Data Model Type.',
         'type': {'type': 'function', '_funcname': '_cast',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the model type to normalize the value as.', },
                      {'name': 'valu', 'type': 'any', 'desc': 'The value to normalize.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The normalized value.', }}},
        {'name': 'warn',
         'desc': '''
            Print a warning message to the runtime.

            Notes:
                Arbitrary objects can be warned as well. They will have their Python __repr()__ printed.
            ''',
         'type': {'type': 'function', '_funcname': '_warn',
                  'args': (
                      {'name': 'mesg', 'type': 'str', 'desc': 'String to warn.', },
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Keyword arguments to substitute into the mesg.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'print', 'desc': '''
            Print a message to the runtime.

            Examples:
                Print a simple string::

                    cli> storm $lib.print("Hello world!")
                    Hello world!

                Format and print string based on variables::

                    cli> storm $d=$lib.dict(key1=(1), key2="two")
                         for ($key, $value) in $d { $lib.print('{k} => {v}', k=$key, v=$value) }
                    key1 => 1
                    key2 => two

                Use values off of a node to format and print string::

                    cli> storm inet:ipv4:asn
                         $lib.print("node: {ndef}, asn: {asn}", ndef=$node.ndef(), asn=:asn) | spin
                    node: ('inet:ipv4', 16909060), asn: 1138

            Notes:
                Arbitrary objects can be printed as well. They will have their Python __repr()__ printed.

            ''',
         'type': {'type': 'function', '_funcname': '_print',
                  'args': (
                      {'name': 'mesg', 'type': 'str', 'desc': 'String to print.', },
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Keyword argumetns to substitue into the mesg.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'range', 'desc': '''
        Generate a range of integers.

        Examples:
            Generate a sequence of integers based on the size of an array::

                cli> storm $a=(foo,bar,(2)) for $i in $lib.range($lib.len($a)) {$lib.fire('test', indx=$i, valu=$a.$i)}
                Executing query at 2021/03/22 19:25:48.835
                ('storm:fire', {'type': 'test', 'data': {'index': 0, 'valu': 'foo'}})
                ('storm:fire', {'type': 'test', 'data': {'index': 1, 'valu': 'bar'}})
                ('storm:fire', {'type': 'test', 'data': {'index': 2, 'valu': 2}})

        Notes:
            The range behavior is the same as the Python3 ``range()`` builtin Sequence type.
        ''',
         'type': {'type': 'function', '_funcname': '_range',
                  'args': (
                      {'name': 'stop', 'type': 'int', 'desc': 'The value to stop at.', },
                      {'name': 'start', 'type': 'int', 'desc': 'The value to start at.', 'default': None, },
                      {'name': 'step', 'type': 'int', 'desc': 'The range step size.', 'default': None, },
                  ),
                  'returns': {'name': 'Yields', 'type': 'integer', 'desc': 'The sequence of integers.'}}},
        {'name': 'pprint', 'desc': 'The pprint API should not be considered a stable interface.',
         'type': {'type': 'function', '_funcname': '_pprint',
                  'args': (
                      {'name': 'item', 'type': 'any', 'desc': 'Item to pprint', },
                      {'name': 'prefix', 'type': 'str', 'desc': 'Line prefix.', 'default': '', },
                      {'name': 'clamp', 'type': 'int', 'desc': 'Line clamping length.', 'default': None, },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'sorted', 'desc': 'Yield sorted values.',
         'type': {'type': 'function', '_funcname': '_sorted',
                  'args': (
                      {'name': 'valu', 'type': 'any', 'desc': 'An iterable object to sort.', },
                      {'name': 'reverse', 'type': 'boolean', 'desc': 'Reverse the sort order.',
                       'default': False},
                  ),
                  'returns': {'name': 'Yields', 'type': 'any', 'desc': 'Yields the sorted output.', }}},
        {'name': 'import', 'desc': 'Import a Storm module.',
         'type': {'type': 'function', '_funcname': '_libBaseImport',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the module to import.', },
                      {'name': 'debug', 'type': 'boolean', 'default': False,
                       'desc': 'Enable debugging in the module.'},
                      {'name': 'reqvers', 'type': 'str', 'default': None,
                       'desc': 'Version requirement for the imported module.', },
                  ),
                  'returns': {'type': 'storm:lib',
                              'desc': 'A ``storm:lib`` instance representing the imported package.', }}},

        {'name': 'trycast', 'desc': '''
            Attempt to normalize a value and return status and the normalized value.

            Examples:
                Do something if the value is a valid IPV4::

                    ($ok, $ipv4) = $lib.trycast(inet:ipv4, 1.2.3.4)
                    if $ok { $dostuff($ipv4) }
         ''',
         'type': {'type': 'function', '_funcname': 'trycast',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the model type to normalize the value as.', },
                      {'name': 'valu', 'type': 'any', 'desc': 'The value to normalize.', },
                  ),
                  'returns': {'type': 'list',
                              'desc': 'A list of (<bool>, <prim>) for status and normalized value.', }}},
        {'name': 'debug', 'desc': '''
            True if the current runtime has debugging enabled.

            Note:
                The debug state is inherited by sub-runtimes at instantiation time.  Any
                changes to a runtime's debug state do not percolate automatically.

            Examples:
                Check if the runtime is in debug and print a message::

                    if $lib.debug {
                        $lib.print('Doing stuff!")
                    }

                Update the current runtime to enable debugging::

                    $lib.debug = $lib.true''',
         'type': {
             'type': ['gtor', 'stor'],
             '_storfunc': '_setRuntDebug',
             '_gtorfunc': '_getRuntDebug',
             'returns': {'type': 'boolean'}}},

        {'name': 'copy', 'desc': '''
            Create and return a deep copy of the given storm object.

            Note:
                This is currently limited to msgpack compatible primitives.

            Examples:
                Make a copy of a list or dict::

                    $copy = $lib.copy($item)
         ''',
         'type': {'type': 'function', '_funcname': '_copy',
                  'args': (
                      {'name': 'item', 'type': 'prim',
                       'desc': 'The item to make a copy of.', },
                  ),
                  'returns': {'type': 'prim',
                              'desc': 'A deep copy of the primitive object.', }}},
    )

    def __init__(self, runt, name=()):
        Lib.__init__(self, runt, name=name)
        self.stors['debug'] = self._setRuntDebug
        self.gtors['debug'] = self._getRuntDebug

    async def _getRuntDebug(self):
        return self.runt.debug

    async def _setRuntDebug(self, debug):
        self.runt.debug = await tobool(debug)

    def getObjLocals(self):
        return {
            'len': self._len,
            'min': self._min,
            'max': self._max,
            'set': self._set,
            'copy': self._copy,
            'dict': self._dict,
            'exit': self._exit,
            'guid': self._guid,
            'fire': self._fire,
            'list': self._list,
            'null': None,
            'undef': undef,
            'true': True,
            'false': False,
            'text': self._text,
            'cast': self._cast,
            'warn': self._warn,
            'print': self._print,
            'raise': self._raise,
            'range': self._range,
            'pprint': self._pprint,
            'sorted': self._sorted,
            'import': self._libBaseImport,
            'trycast': self.trycast,
        }

    async def _libBaseImport(self, name, debug=False, reqvers=None):

        name = await tostr(name)
        debug = await tobool(debug)
        reqvers = await tostr(reqvers, noneok=True)

        mdef = await self.runt.snap.core.getStormMod(name, reqvers=reqvers)
        if mdef is None:
            mesg = f'No storm module named {name} matching version requirement {reqvers}'
            raise s_exc.NoSuchName(mesg=mesg, name=name, reqvers=reqvers)

        text = mdef.get('storm')
        modconf = mdef.get('modconf')

        query = await self.runt.getStormQuery(text)

        asroot = False

        rootperms = mdef.get('asroot:perms')
        if rootperms is not None:

            for perm in rootperms:
                if self.runt.allowed(perm):
                    asroot = True
                    break

            if not asroot:
                permtext = ' or '.join(('.'.join(p) for p in rootperms))
                mesg = f'Module ({name}) requires permission: {permtext}'
                raise s_exc.AuthDeny(mesg=mesg)

        else:
            perm = ('storm', 'asroot', 'mod') + tuple(name.split('.'))
            asroot = self.runt.allowed(perm)

            if mdef.get('asroot', False) and not asroot:
                mesg = f'Module ({name}) elevates privileges.  You need perm: storm.asroot.mod.{name}'
                raise s_exc.AuthDeny(mesg=mesg)

        modr = await self.runt.getModRuntime(query, opts={'vars': {'modconf': modconf}})
        modr.asroot = asroot

        if debug:
            modr.debug = debug

        self.runt.onfini(modr)

        async for item in modr.execute():
            await asyncio.sleep(0)  # pragma: no cover

        modlib = Lib(modr)
        modlib.locls.update(modr.vars)
        modlib.locls['__module__'] = mdef
        modlib.name = (name,)

        return modlib

    @stormfunc(readonly=True)
    async def _copy(self, item):
        # short circuit a few python types
        if item is None:
            return None

        if isinstance(item, (int, str, bool)):
            return item

        try:
            valu = fromprim(item)
        except s_exc.NoSuchType:
            mesg = 'Type does not have a Storm primitive and cannot be copied.'
            raise s_exc.BadArg(mesg=mesg) from None

        try:
            return await valu._storm_copy()
        except s_exc.NoSuchType:
            mesg = 'Nested type does not support being copied!'
            raise s_exc.BadArg(mesg=mesg) from None

    @stormfunc(readonly=True)
    async def _cast(self, name, valu):
        name = await toprim(name)
        valu = await toprim(valu)

        typeitem = self.runt.snap.core.model.type(name)
        if typeitem is None:
            mesg = f'No type found for name {name}.'
            raise s_exc.NoSuchType(mesg=mesg)

        # TODO an eventual mapping between model types and storm prims

        norm, info = typeitem.norm(valu)
        return fromprim(norm, basetypes=False)

    @stormfunc(readonly=True)
    async def trycast(self, name, valu):
        name = await toprim(name)
        valu = await toprim(valu)

        typeitem = self.runt.snap.core.model.type(name)
        if typeitem is None:
            mesg = f'No type found for name {name}.'
            raise s_exc.NoSuchType(mesg=mesg)

        try:
            norm, info = typeitem.norm(valu)
            return (True, fromprim(norm, basetypes=False))
        except s_exc.BadTypeValu:
            return (False, None)

    @stormfunc(readonly=True)
    async def _exit(self, mesg=None, **kwargs):
        if mesg:
            mesg = await self._get_mesg(mesg, **kwargs)
            await self.runt.warn(mesg, log=False)
            raise s_stormctrl.StormExit(mesg)
        raise s_stormctrl.StormExit()

    @stormfunc(readonly=True)
    async def _sorted(self, valu, reverse=False):
        valu = await toprim(valu)
        if isinstance(valu, dict):
            valu = list(valu.items())
        for item in sorted(valu, reverse=reverse):
            yield item

    async def _set(self, *vals):
        return Set(vals)

    async def _list(self, *vals):
        return List(list(vals))

    async def _text(self, *args):
        valu = ''.join(args)
        return Text(valu)

    @stormfunc(readonly=True)
    async def _guid(self, *args):
        if args:
            args = await toprim(args)
            return s_common.guid(args)
        return s_common.guid()

    @stormfunc(readonly=True)
    async def _len(self, item):

        if isinstance(item, (types.GeneratorType, types.AsyncGeneratorType)):
            size = 0
            async for _ in s_coro.agen(item):
                size += 1
                await asyncio.sleep(0)
            return size

        try:
            return len(item)
        except TypeError:
            name = f'{item.__class__.__module__}.{item.__class__.__name__}'
            raise s_exc.StormRuntimeError(mesg=f'Object {name} does not have a length.', name=name) from None
        except Exception as e:  # pragma: no cover
            name = f'{item.__class__.__module__}.{item.__class__.__name__}'
            raise s_exc.StormRuntimeError(mesg=f'Unknown error during len(): {repr(e)}', name=name)

    @stormfunc(readonly=True)
    async def _min(self, *args):
        # allow passing in a list of ints
        vals = []
        for arg in args:
            if isinstance(arg, (list, tuple)):
                vals.extend(arg)
                continue
            vals.append(arg)

        ints = [await toint(x) for x in vals]
        return min(*ints)

    @stormfunc(readonly=True)
    async def _max(self, *args):
        # allow passing in a list of ints
        vals = []
        for arg in args:
            if isinstance(arg, (list, tuple)):
                vals.extend(arg)
                continue
            vals.append(arg)

        ints = [await toint(x) for x in vals]
        return max(*ints)

    @staticmethod
    async def _get_mesg(mesg, **kwargs):
        if not isinstance(mesg, str):
            mesg = await torepr(mesg)
        elif kwargs:
            mesg = await kwarg_format(mesg, **kwargs)
        return mesg

    @stormfunc(readonly=True)
    async def _print(self, mesg, **kwargs):
        mesg = await self._get_mesg(mesg, **kwargs)
        await self.runt.printf(mesg)

    @stormfunc(readonly=True)
    async def _raise(self, name, mesg, **info):
        name = await tostr(name)
        mesg = await tostr(mesg)
        info = await toprim(info)
        ctor = getattr(s_exc, name, None)
        if ctor is not None:
            raise ctor(mesg=mesg, **info)
        raise s_exc.StormRaise(name, mesg, info)

    @stormfunc(readonly=True)
    async def _range(self, stop, start=None, step=None):
        stop = await toint(stop)
        start = await toint(start, True)
        step = await toint(step, True)

        if start is not None:
            if step is not None:
                genr = range(start, stop, step)
            else:
                genr = range(start, stop)
        else:
            genr = range(stop)

        for valu in genr:
            yield valu
            await asyncio.sleep(0)

    @stormfunc(readonly=True)
    async def _pprint(self, item, prefix='', clamp=None):
        if clamp is not None:
            clamp = await toint(clamp)

            if clamp < 3:
                mesg = 'Invalid clamp length.'
                raise s_exc.StormRuntimeError(mesg=mesg, clamp=clamp)

        try:
            item = await toprim(item)
        except s_exc.NoSuchType:
            pass

        lines = pprint.pformat(item).splitlines()

        for line in lines:
            fline = f'{prefix}{line}'
            if clamp and len(fline) > clamp:
                await self.runt.printf(f'{fline[:clamp-3]}...')
            else:
                await self.runt.printf(fline)

    @stormfunc(readonly=True)
    async def _warn(self, mesg, **kwargs):
        mesg = await self._get_mesg(mesg, **kwargs)
        await self.runt.warn(mesg, log=False)

    @stormfunc(readonly=True)
    async def _dict(self, **kwargs):
        return Dict(kwargs)

    @stormfunc(readonly=True)
    async def _fire(self, name, **info):
        info = await toprim(info)
        s_common.reqjsonsafe(info)
        await self.runt.snap.fire('storm:fire', type=name, data=info)

@registry.registerLib
class LibPs(Lib):
    '''
    A Storm Library for interacting with running tasks on the Cortex.
    '''
    _storm_locals = (  # type:  ignore
        {'name': 'kill', 'desc': 'Stop a running task on the Cortex.',
         'type': {'type': 'function', '_funcname': '_kill',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'The prefix of the task to stop. '
                               'Tasks will only be stopped if there is a single prefix match.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': ' True if the task was cancelled, False otherwise.', }}},
        {'name': 'list', 'desc': 'List tasks the current user can access.',
         'type': {'type': 'function', '_funcname': '_list',
                  'returns': {'type': 'list', 'desc': 'A list of task definitions.', }}},
    )
    _storm_lib_path = ('ps',)

    def getObjLocals(self):
        return {
            'kill': self._kill,
            'list': self._list,
        }

    async def _kill(self, prefix):
        idens = []

        todo = s_common.todo('ps', self.runt.user)
        tasks = await self.dyncall('cell', todo)
        for task in tasks:
            iden = task.get('iden')
            if iden.startswith(prefix):
                idens.append(iden)

        if len(idens) == 0:
            mesg = 'Provided iden does not match any processes.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

        if len(idens) > 1:
            mesg = 'Provided iden matches more than one process.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

        todo = s_common.todo('kill', self.runt.user, idens[0])
        return await self.dyncall('cell', todo)

    async def _list(self):
        todo = s_common.todo('ps', self.runt.user)
        return await self.dyncall('cell', todo)

@registry.registerLib
class LibStr(Lib):
    '''
    A Storm Library for interacting with strings.
    '''
    _storm_locals = (
        {'name': 'join', 'desc': '''
            Join items into a string using a separator.

            Examples:
                Join together a list of strings with a dot separator::

                    cli> storm $foo=$lib.str.join('.', ('rep', 'vtx', 'tag')) $lib.print($foo)

                    rep.vtx.tag''',
         'type': {'type': 'function', '_funcname': 'join',
                  'args': (
                      {'name': 'sepr', 'type': 'str', 'desc': 'The separator used to join strings with.', },
                      {'name': 'items', 'type': 'list', 'desc': 'A list of items to join together.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The joined string.', }}},
        {'name': 'concat', 'desc': 'Concatenate a set of strings together.',
         'type': {'type': 'function', '_funcname': 'concat',
                  'args': (
                      {'name': '*args', 'type': 'any', 'desc': 'Items to join together.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The joined string.', }}},
        {'name': 'format', 'desc': '''
            Format a text string.

            Examples:
                Format a string with a fixed argument and a variable::

                    cli> storm $list=(1,2,3,4)
                         $str=$lib.str.format('Hello {name}, your list is {list}!', name='Reader', list=$list)
                         $lib.print($str)

                    Hello Reader, your list is ['1', '2', '3', '4']!''',
         'type': {'type': 'function', '_funcname': 'format',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The base text string.', },
                      {'name': '**kwargs', 'type': 'any',
                       'desc': 'Keyword values which are substituted into the string.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The new string.', }}},
    )
    _storm_lib_path = ('str',)

    def getObjLocals(self):
        return {
            'join': self.join,
            'concat': self.concat,
            'format': self.format,
        }

    async def concat(self, *args):
        strs = [await tostr(a) for a in args]
        return ''.join(strs)

    async def format(self, text, **kwargs):
        text = await kwarg_format(text, **kwargs)

        return text

    async def join(self, sepr, items):
        strs = [await tostr(item) async for item in toiter(items)]
        return sepr.join(strs)

@registry.registerLib
class LibAxon(Lib):
    '''
    A Storm library for interacting with the Cortex's Axon.
    '''
    _storm_locals = (
        {'name': 'wget', 'desc': """
            A method to download an HTTP(S) resource into the Cortex's Axon.

            Notes:
                The response body will be stored regardless of the status code. See the ``Axon.wget()`` API
                documentation to see the complete structure of the response dictionary.

            Example:
                Get the Vertex Project website::

                    $headers = $lib.dict()
                    $headers."User-Agent" = Foo/Bar

                    $resp = $lib.axon.wget("http://vertex.link", method=GET, headers=$headers)
                    if $resp.ok { $lib.print("Downloaded: {size} bytes", size=$resp.size) }
            """,
         'type': {'type': 'function', '_funcname': 'wget',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to download'},
                      {'name': 'headers', 'type': 'dict', 'desc': 'An optional dictionary of HTTP headers to send.',
                       'default': None},
                      {'name': 'params', 'type': 'dict', 'desc': 'An optional dictionary of URL parameters to add.',
                       'default': None},
                      {'name': 'method', 'type': 'str', 'desc': 'The HTTP method to use.', 'default': 'GET'},
                      {'name': 'json', 'type': 'dict', 'desc': 'A JSON object to send as the body.',
                       'default': None},
                      {'name': 'body', 'type': 'bytes', 'desc': 'Bytes to send as the body.', 'default': None},
                      {'name': 'ssl', 'type': 'boolean',
                       'desc': 'Set to False to disable SSL/TLS certificate verification.', 'default': True},
                      {'name': 'timeout', 'type': 'int', 'desc': 'Timeout for the download operation.',
                       'default': None},
                      {'name': 'proxy', 'type': ['bool', 'null', 'str'],
                       'desc': 'Set to a proxy URL string or $lib.false to disable proxy use.', 'default': None},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A status dictionary of metadata.'}}},
        {'name': 'wput', 'desc': """
            A method to upload a blob from the axon to an HTTP(S) endpoint.
            """,
         'type': {'type': 'function', '_funcname': 'wput',
                  'args': (
                      {'name': 'sha256', 'type': 'str', 'desc': 'The sha256 of the file blob to upload.'},
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to upload the file to.'},
                      {'name': 'headers', 'type': 'dict', 'desc': 'An optional dictionary of HTTP headers to send.',
                       'default': None},
                      {'name': 'params', 'type': 'dict', 'desc': 'An optional dictionary of URL parameters to add.',
                       'default': None},
                      {'name': 'method', 'type': 'str', 'desc': 'The HTTP method to use.', 'default': 'PUT'},
                      {'name': 'ssl', 'type': 'boolean',
                       'desc': 'Set to False to disable SSL/TLS certificate verification.', 'default': True},
                      {'name': 'timeout', 'type': 'int', 'desc': 'Timeout for the download operation.',
                       'default': None},
                      {'name': 'proxy', 'type': ['bool', 'null', 'str'],
                       'desc': 'Set to a proxy URL string or $lib.false to disable proxy use.', 'default': None},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A status dictionary of metadata.'}}},
        {'name': 'urlfile', 'desc': '''
            Retrive the target URL using the wget() function and construct an inet:urlfile node from the response.

            Notes:
                This accepts the same arguments as ``$lib.axon.wget()``.
                ''',
         'type': {'type': 'function', '_funcname': 'urlfile',
                  'args': (
                      {'name': '*args', 'type': 'any', 'desc': 'Args from ``$lib.axon.wget()``.'},
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Args from ``$lib.axon.wget()``.'},
                  ),
                  'returns': {'type': ['storm:node', 'null'],
                              'desc': 'The ``inet:urlfile`` node on success,  ``null`` on error.'}}},
        {'name': 'del', 'desc': '''
            Remove the bytes from the Cortex's Axon by sha256.

            Example:
                Delete files from the axon based on a tag::

                    file:bytes#foo +:sha256 $lib.axon.del(:sha256)
        ''',
         'type': {'type': 'function', '_funcname': 'del_',
                  'args': (
                      {'name': 'sha256', 'type': 'hash:sha256',
                       'desc': 'The sha256 of the bytes to remove from the Axon.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the bytes were found and removed.'}}},

        {'name': 'dels', 'desc': '''
            Remove multiple byte blobs from the Cortex's Axon by a list of sha256 hashes.

            Example:
                Delete a list of files (by hash) from the Axon::

                    $list = ($hash0, $hash1, $hash2)
                    $lib.axon.dels($list)
        ''',
         'type': {'type': 'function', '_funcname': 'dels',
                  'args': (
                      {'name': 'sha256s', 'type': 'list', 'desc': 'A list of sha256 hashes to remove from the Axon.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'A list of boolean values that are True if the bytes were found.'}}},

        {'name': 'list', 'desc': '''
        List (offset, sha256, size) tuples for files in the Axon in added order.

        Example:
            List files::

                for ($offs, $sha256, $size) in $lib.axon.list() {
                    $lib.print($sha256)
                }

            Start list from offset 10::

                for ($offs, $sha256, $size) in $lib.axon.list(10) {
                    $lib.print($sha256)
                }
        ''',
         'type': {'type': 'function', '_funcname': 'list',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'desc': 'The offset to start from.', 'default': 0},
                      {'name': 'wait', 'type': 'boolean', 'default': False,
                        'desc': 'Wait for new results and yield them in realtime.'},
                      {'name': 'timeout', 'type': 'int', 'default': None,
                        'desc': 'The maximum time to wait for a new result before returning.'},
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'Tuple of (offset, sha256, size) in added order.'}}},
        {'name': 'readlines', 'desc': '''
        Yields lines of text from a plain-text file stored in the Axon.

        Example:
            Get the lines for a given file::

                for $line in $lib.axon.readlines($sha256) {
                    $dostuff($line)
                }
        ''',
         'type': {'type': 'function', '_funcname': 'readlines',
                  'args': (
                      {'name': 'sha256', 'type': 'str', 'desc': 'The SHA256 hash of the file.'},
                  ),
                  'returns': {'name': 'yields', 'type': 'str',
                              'desc': 'A line of text from the file.'}}},

        {'name': 'jsonlines', 'desc': '''
        Yields JSON objects from a JSON-lines file stored in the Axon.

        Example:
            Get the JSON objects from a given JSONL file::

                for $item in $lib.axon.jsonlines($sha256) {
                    $dostuff($item)
                }
        ''',
         'type': {'type': 'function', '_funcname': 'jsonlines',
                  'args': (
                      {'name': 'sha256', 'type': 'str', 'desc': 'The SHA256 hash of the file.'},
                  ),
                  'returns': {'name': 'yields', 'type': 'any',
                              'desc': 'A JSON object parsed from a line of text.'}}},
        {'name': 'csvrows', 'desc': '''
            Yields CSV rows from a CSV file stored in the Axon.

            Notes:
                The dialect and fmtparams expose the Python csv.reader() parameters.

            Example:
                Get the rows from a given csv file::

                    for $row in $lib.axon.csvrows($sha256) {
                        $dostuff($row)
                    }

                Get the rows from a given tab separated file::

                    for $row in $lib.axon.csvrows($sha256, delimiter="\\t") {
                        $dostuff($row)
                    }
            ''',
         'type': {'type': 'function', '_funcname': 'csvrows',
                  'args': (
                      {'name': 'sha256', 'type': 'str', 'desc': 'The SHA256 hash of the file.'},
                      {'name': 'dialect', 'type': 'str', 'desc': 'The default CSV dialect to use.',
                       'default': 'excel'},
                      {'name': '**fmtparams', 'type': 'any', 'desc': 'Format arguments.'},
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'A list of strings from the CSV file.'}}},
        {'name': 'metrics', 'desc': '''
        Get runtime metrics of the Axon.

        Example:
            Print the total number of files stored in the Axon::

                $data = $lib.axon.metrics()
                $lib.print("The Axon has {n} files", n=$data."file:count")
        ''',
        'type': {'type': 'function', '_funcname': 'metrics',
                 'returns': {'type': 'dict', 'desc': 'A dictionary containing runtime data about the Axon.'}}},
    )
    _storm_lib_path = ('axon',)

    def getObjLocals(self):
        return {
            'wget': self.wget,
            'wput': self.wput,
            'urlfile': self.urlfile,
            'del': self.del_,
            'dels': self.dels,
            'list': self.list,
            'readlines': self.readlines,
            'jsonlines': self.jsonlines,
            'csvrows': self.csvrows,
            'metrics': self.metrics,
        }

    def strify(self, item):
        if isinstance(item, (list, tuple)):
            return [(str(k), str(v)) for (k, v) in item]
        elif isinstance(item, dict):
            return {str(k): str(v) for k, v in item.items()}
        return item

    async def readlines(self, sha256):
        self.runt.confirm(('storm', 'lib', 'axon', 'get'))
        await self.runt.snap.core.getAxon()

        sha256 = await tostr(sha256)
        async for line in self.runt.snap.core.axon.readlines(sha256):
            yield line

    async def jsonlines(self, sha256):
        self.runt.confirm(('storm', 'lib', 'axon', 'get'))
        await self.runt.snap.core.getAxon()

        sha256 = await tostr(sha256)
        async for line in self.runt.snap.core.axon.jsonlines(sha256):
            yield line

    async def dels(self, sha256s):

        self.runt.confirm(('storm', 'lib', 'axon', 'del'))

        sha256s = await toprim(sha256s)

        if not isinstance(sha256s, (list, tuple)):
            raise s_exc.BadArg()

        hashes = [s_common.uhex(s) for s in sha256s]

        await self.runt.snap.core.getAxon()

        axon = self.runt.snap.core.axon
        return await axon.dels(hashes)

    async def del_(self, sha256):

        self.runt.confirm(('storm', 'lib', 'axon', 'del'))
        sha256 = await tostr(sha256)

        sha256b = s_common.uhex(sha256)
        await self.runt.snap.core.getAxon()

        axon = self.runt.snap.core.axon
        return await axon.del_(sha256b)

    async def wget(self, url, headers=None, params=None, method='GET', json=None, body=None, ssl=True, timeout=None, proxy=None):

        self.runt.confirm(('storm', 'lib', 'axon', 'wget'))

        if proxy is not None and not self.runt.isAdmin():
            raise s_exc.AuthDeny(mesg=s_exc.proxy_admin_mesg)

        url = await tostr(url)
        method = await tostr(method)

        ssl = await tobool(ssl)
        body = await toprim(body)
        json = await toprim(json)
        params = await toprim(params)
        headers = await toprim(headers)
        timeout = await toprim(timeout)
        proxy = await toprim(proxy)

        params = self.strify(params)
        headers = self.strify(headers)

        await self.runt.snap.core.getAxon()

        kwargs = {}
        axonvers = self.runt.snap.core.axoninfo['synapse']['version']
        if axonvers >= (2, 97, 0):
            kwargs['proxy'] = proxy

        axon = self.runt.snap.core.axon
        return await axon.wget(url, headers=headers, params=params, method=method, ssl=ssl, body=body, json=json,
                               timeout=timeout, **kwargs)

    async def wput(self, sha256, url, headers=None, params=None, method='PUT', ssl=True, timeout=None, proxy=None):

        self.runt.confirm(('storm', 'lib', 'axon', 'wput'))

        if proxy is not None and not self.runt.isAdmin():
            raise s_exc.AuthDeny(mesg=s_exc.proxy_admin_mesg)

        url = await tostr(url)
        sha256 = await tostr(sha256)
        method = await tostr(method)
        proxy = await toprim(proxy)

        ssl = await tobool(ssl)
        params = await toprim(params)
        headers = await toprim(headers)
        timeout = await toprim(timeout)

        params = self.strify(params)
        headers = self.strify(headers)

        axon = self.runt.snap.core.axon
        sha256byts = s_common.uhex(sha256)

        kwargs = {}
        axonvers = self.runt.snap.core.axoninfo['synapse']['version']
        if axonvers >= (2, 97, 0):
            kwargs['proxy'] = proxy

        return await axon.wput(sha256byts, url, headers=headers, params=params, method=method, ssl=ssl, timeout=timeout, **kwargs)

    async def urlfile(self, *args, **kwargs):
        resp = await self.wget(*args, **kwargs)
        code = resp.get('code')

        if code != 200:
            if code is None:
                mesg = f'$lib.axon.urlfile(): {resp.get("mesg")}'
            else:
                mesg = f'$lib.axon.urlfile(): HTTP code {code} != 200'

            await self.runt.warn(mesg, log=False)
            return

        url = resp.get('url')
        hashes = resp.get('hashes')
        props = {
            'size': resp.get('size'),
            'md5': hashes.get('md5'),
            'sha1': hashes.get('sha1'),
            'sha256': hashes.get('sha256'),
            '.seen': 'now',
        }

        sha256 = hashes.get('sha256')
        filenode = await self.runt.snap.addNode('file:bytes', sha256, props=props)

        if not filenode.get('name'):
            info = s_urlhelp.chopurl(url)
            base = info.get('path').strip('/').split('/')[-1]
            if base:
                await filenode.set('name', base)

        props = {'.seen': 'now'}
        urlfile = await self.runt.snap.addNode('inet:urlfile', (url, sha256), props=props)

        return urlfile

    async def list(self, offs=0, wait=False, timeout=None):
        offs = await toint(offs)
        wait = await tobool(wait)
        timeout = await toint(timeout, noneok=True)

        self.runt.confirm(('storm', 'lib', 'axon', 'has'))

        await self.runt.snap.core.getAxon()
        axon = self.runt.snap.core.axon

        async for item in axon.hashes(offs, wait=wait, timeout=timeout):
            yield (item[0], s_common.ehex(item[1][0]), item[1][1])

    async def csvrows(self, sha256, dialect='excel', **fmtparams):

        self.runt.confirm(('storm', 'lib', 'axon', 'get'))
        await self.runt.snap.core.getAxon()

        sha256 = await tostr(sha256)
        dialect = await tostr(dialect)
        fmtparams = await toprim(fmtparams)
        async for item in self.runt.snap.core.axon.csvrows(s_common.uhex(sha256), dialect, **fmtparams):
            yield item
            await asyncio.sleep(0)

    async def metrics(self):
        self.runt.confirm(('storm', 'lib', 'axon', 'has'))
        return await self.runt.snap.core.axon.metrics()

@registry.registerLib
class LibBytes(Lib):
    '''
    A Storm Library for interacting with bytes storage.
    '''
    _storm_locals = (
        {'name': 'put', 'desc': '''
            Save the given bytes variable to the Axon the Cortex is configured to use.

            Examples:
                Save a base64 encoded buffer to the Axon::

                    cli> storm $s='dGVzdA==' $buf=$lib.base64.decode($s) ($size, $sha256)=$lib.bytes.put($buf)
                         $lib.print('size={size} sha256={sha256}', size=$size, sha256=$sha256)

                    size=4 sha256=9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08''',
         'type': {'type': 'function', '_funcname': '_libBytesPut',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to save.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A tuple of the file size and sha256 value.', }}},
        {'name': 'has', 'desc': '''
            Check if the Axon the Cortex is configured to use has a given sha256 value.

            Examples:
                Check if the Axon has a given file::

                    # This example assumes the Axon does have the bytes
                    cli> storm if $lib.bytes.has(9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08) {
                            $lib.print("Has bytes")
                        } else {
                            $lib.print("Does not have bytes")
                        }

                    Has bytes
            ''',
         'type': {'type': 'function', '_funcname': '_libBytesHas',
                  'args': (
                      {'name': 'sha256', 'type': 'str', 'desc': 'The sha256 value to check.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the Axon has the file, false if it does not.', }}},
        {'name': 'size', 'desc': '''
            Return the size of the bytes stored in the Axon for the given sha256.

            Examples:
                Get the size for a file given a variable named ``$sha256``::

                    $size = $lib.bytes.size($sha256)
            ''',
         'type': {'type': 'function', '_funcname': '_libBytesSize',
                  'args': (
                      {'name': 'sha256', 'type': 'str', 'desc': 'The sha256 value to check.', },
                  ),
                  'returns': {'type': ['int', 'null'],
                              'desc': 'The size of the file or ``null`` if the file is not found.', }}},
        {'name': 'hashset', 'desc': '''
            Return additional hashes of the bytes stored in the Axon for the given sha256.

            Examples:
                Get the md5 hash for a file given a variable named ``$sha256``::

                    $hashset = $lib.bytes.hashset($sha256)
                    $md5 = $hashset.md5
            ''',
         'type': {'type': 'function', '_funcname': '_libBytesHashset',
                  'args': (
                      {'name': 'sha256', 'type': 'str', 'desc': 'The sha256 value to calculate hashes for.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary of additional hashes.', }}},
        {'name': 'upload', 'desc': '''
            Upload a stream of bytes to the Axon as a file.

            Examples:
                Upload bytes from a generator::

                    ($size, $sha256) = $lib.bytes.upload($getBytesChunks())
            ''',
         'type': {'type': 'function', '_funcname': '_libBytesUpload',
                  'args': (
                      {'name': 'genr', 'type': 'generator', 'desc': 'A generator which yields bytes.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A tuple of the file size and sha256 value.', }}},
    )
    _storm_lib_path = ('bytes',)

    def getObjLocals(self):
        return {
            'put': self._libBytesPut,
            'has': self._libBytesHas,
            'size': self._libBytesSize,
            'upload': self._libBytesUpload,
            'hashset': self._libBytesHashset,
        }

    async def _libBytesUpload(self, genr):
        await self.runt.snap.core.getAxon()
        async with await self.runt.snap.core.axon.upload() as upload:
            async for byts in s_coro.agen(genr):
                await upload.write(byts)
            size, sha256 = await upload.save()
            return size, s_common.ehex(sha256)

    async def _libBytesHas(self, sha256):
        sha256 = await tostr(sha256, noneok=True)
        if sha256 is None:
            return None

        await self.runt.snap.core.getAxon()
        todo = s_common.todo('has', s_common.uhex(sha256))
        ret = await self.dyncall('axon', todo)
        return ret

    async def _libBytesSize(self, sha256):
        sha256 = await tostr(sha256)
        await self.runt.snap.core.getAxon()
        todo = s_common.todo('size', s_common.uhex(sha256))
        ret = await self.dyncall('axon', todo)
        return ret

    async def _libBytesPut(self, byts):
        if not isinstance(byts, bytes):
            mesg = '$lib.bytes.put() requires a bytes argument'
            raise s_exc.BadArg(mesg=mesg)

        await self.runt.snap.core.getAxon()
        todo = s_common.todo('put', byts)
        size, sha2 = await self.dyncall('axon', todo)

        return (size, s_common.ehex(sha2))

    async def _libBytesHashset(self, sha256):
        sha256 = await tostr(sha256)
        await self.runt.snap.core.getAxon()
        todo = s_common.todo('hashset', s_common.uhex(sha256))
        ret = await self.dyncall('axon', todo)
        return ret

@registry.registerLib
class LibLift(Lib):
    '''
    A Storm Library for interacting with lift helpers.
    '''
    _storm_locals = (
        {'name': 'byNodeData', 'desc': 'Lift nodes which have a given nodedata name set on them.',
         'type': {'type': 'function', '_funcname': '_byNodeData',
                  'args': (
                      {'name': 'name', 'desc': 'The name to of the nodedata key to lift by.', 'type': 'str', },
                  ),
                  'returns': {'name': 'Yields', 'type': 'storm:node',
                              'desc': 'Yields nodes to the pipeline. '
                                      'This must be used in conjunction with the ``yield`` keyword.', }}},
    )
    _storm_lib_path = ('lift',)

    def getObjLocals(self):
        return {
            'byNodeData': self._byNodeData,
        }

    async def _byNodeData(self, name):
        async for node in self.runt.snap.nodesByDataName(name):
            yield node

@registry.registerLib
class LibTime(Lib):
    '''
    A Storm Library for interacting with timestamps.
    '''
    _storm_locals = (
        {'name': 'now', 'desc': 'Get the current epoch time in milliseconds.',
         'type': {
             'type': 'function', '_funcname': '_now',
             'returns': {'desc': 'Epoch time in milliseconds.', 'type': 'int', }}},
        {'name': 'fromunix',
         'desc': '''
            Normalize a timestamp from a unix epoch time in seconds to milliseconds.

            Examples:
                Convert a timestamp from seconds to millis and format it::

                    cli> storm $seconds=1594684800 $millis=$lib.time.fromunix($seconds)
                         $str=$lib.time.format($millis, '%A %d, %B %Y') $lib.print($str)

                    Tuesday 14, July 2020''',
         'type': {'type': 'function', '_funcname': '_fromunix',
                  'args': (
                      {'name': 'secs', 'type': 'int', 'desc': 'Unix epoch time in seconds.', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The normalized time in milliseconds.', }}},
        {'name': 'parse', 'desc': '''
            Parse a timestamp string using ``datetime.strptime()`` into an epoch timestamp.

            Examples:
                Parse a string as for its month/day/year value into a timestamp::

                    cli> storm $s='06/01/2020' $ts=$lib.time.parse($s, '%m/%d/%Y') $lib.print($ts)

                    1590969600000''',
         'type': {'type': 'function', '_funcname': '_parse',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The timestamp string to parse.', },
                      {'name': 'format', 'type': 'str', 'desc': 'The format string to use for parsing.', },
                      {'name': 'errok', 'type': 'boolean', 'default': False,
                       'desc': 'If set, parsing errors will return ``$lib.null`` instead of raising an exception.'}
                  ),
                  'returns': {'type': 'int', 'desc': 'The epoch timetsamp for the string.', }}},
        {'name': 'format', 'desc': '''
            Format a Synapse timestamp into a string value using ``datetime.strftime()``.

            Examples:
                Format a timestamp into a string::

                    cli> storm $now=$lib.time.now() $str=$lib.time.format($now, '%A %d, %B %Y') $lib.print($str)

                    Tuesday 14, July 2020''',
         'type': {'type': 'function', '_funcname': '_format',
                  'args': (
                      {'name': 'valu', 'type': 'int', 'desc': 'A timestamp in epoch milliseconds.', },
                      {'name': 'format', 'type': 'str', 'desc': 'The strftime format string.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The formatted time string.', }}},
        {'name': 'sleep', 'desc': '''
            Pause the processing of data in the storm query.

            Notes:
                This has the effect of clearing the Snap's cache, so any node lifts performed
                after the ``$lib.time.sleep(...)`` executes will be lifted directly from storage.
            ''',
         'type': {'type': 'function', '_funcname': '_sleep',
                  'args': (
                      {'name': 'valu', 'type': 'int', 'desc': 'The number of seconds to pause for.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'ticker', 'desc': '''
        Periodically pause the processing of data in the storm query.

        Notes:
            This has the effect of clearing the Snap's cache, so any node lifts performed
            after each tick will be lifted directly from storage.
        ''',
         'type': {'type': 'function', '_funcname': '_ticker',
                  'args': (
                      {'name': 'tick',
                       'desc': 'The amount of time to wait between each tick, in seconds.', 'type': 'int', },
                      {'name': 'count', 'default': None, 'type': 'int',
                       'desc': 'The number of times to pause the query before exiting the loop. '
                               'This defaults to None and will yield forever if not set.', }
                  ),
                  'returns': {'name': 'Yields', 'type': 'int',
                              'desc': 'This yields the current tick count after each time it wakes up.', }}},

        {'name': 'year', 'desc': '''
        Returns the year part of a time value.
        ''',
         'type': {'type': 'function', '_funcname': 'year',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The year part of the time expression.', }}},

        {'name': 'month', 'desc': '''
        Returns the month part of a time value.
        ''',
         'type': {'type': 'function', '_funcname': 'month',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The month part of the time expression.', }}},

        {'name': 'day', 'desc': '''
        Returns the day part of a time value.
        ''',
         'type': {'type': 'function', '_funcname': 'day',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The day part of the time expression.', }}},

        {'name': 'hour', 'desc': '''
        Returns the hour part of a time value.
        ''',
         'type': {'type': 'function', '_funcname': 'hour',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The hour part of the time expression.', }}},

        {'name': 'minute', 'desc': '''
        Returns the minute part of a time value.
        ''',
         'type': {'type': 'function', '_funcname': 'minute',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The minute part of the time expression.', }}},

        {'name': 'second', 'desc': '''
        Returns the second part of a time value.
        ''',
         'type': {'type': 'function', '_funcname': 'second',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The second part of the time expression.', }}},

        {'name': 'dayofweek', 'desc': '''
        Returns the index (beginning with monday as 0) of the day within the week.
        ''',
         'type': {'type': 'function', '_funcname': 'dayofweek',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The index of the day within week.', }}},

        {'name': 'dayofyear', 'desc': '''
        Returns the index (beginning with 0) of the day within the year.
        ''',
         'type': {'type': 'function', '_funcname': 'dayofyear',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The index of the day within year.', }}},

        {'name': 'dayofmonth', 'desc': '''
        Returns the index (beginning with 0) of the day within the month.
        ''',
         'type': {'type': 'function', '_funcname': 'dayofmonth',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The index of the day within month.', }}},

        {'name': 'monthofyear', 'desc': '''
        Returns the index (beginning with 0) of the month within the year.
        ''',
         'type': {'type': 'function', '_funcname': 'monthofyear',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The index of the month within year.', }}},
        {'name': 'toUTC', 'desc': '''
        Adjust an epoch milliseconds timestamp to UTC from the given timezone.
        ''',
         'type': {'type': 'function', '_funcname': 'toUTC',
                  'args': (
                      {'name': 'tick', 'desc': 'A time value.', 'type': 'time'},
                      {'name': 'timezone', 'desc': 'A timezone name. See python pytz docs for options.', 'type': 'str'},
                  ),
                  'returns': {'type': 'list', 'desc': 'An ($ok, $valu) tuple.', }}},
    )
    _storm_lib_path = ('time',)

    def getObjLocals(self):
        return {
            'now': self._now,
            'toUTC': self.toUTC,
            'fromunix': self._fromunix,
            'parse': self._parse,
            'format': self._format,
            'sleep': self._sleep,
            'ticker': self._ticker,

            'day': self.day,
            'hour': self.hour,
            'year': self.year,
            'month': self.month,
            'minute': self.minute,
            'second': self.second,

            'dayofweek': self.dayofweek,
            'dayofyear': self.dayofyear,
            'dayofmonth': self.dayofmonth,
            'monthofyear': self.monthofyear,
        }

    async def toUTC(self, tick, timezone):

        tick = await toprim(tick)
        timezone = await tostr(timezone)

        timetype = self.runt.snap.core.model.type('time')

        norm, info = timetype.norm(tick)
        try:
            return (True, s_time.toUTC(norm, timezone))
        except s_exc.BadArg as e:
            return (False, s_common.excinfo(e))

    def _now(self):
        return s_common.now()

    async def day(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.day(norm)

    async def hour(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.hour(norm)

    async def year(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.year(norm)

    async def month(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.month(norm)

    async def minute(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.minute(norm)

    async def second(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.second(norm)

    async def dayofweek(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.dayofweek(norm)

    async def dayofyear(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.dayofyear(norm)

    async def dayofmonth(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.dayofmonth(norm)

    async def monthofyear(self, tick):
        tick = await toprim(tick)
        timetype = self.runt.snap.core.model.type('time')
        norm, info = timetype.norm(tick)
        return s_time.month(norm) - 1

    async def _format(self, valu, format):
        timetype = self.runt.snap.core.model.type('time')
        # Give a times string a shot at being normed prior to formatting.
        try:
            norm, _ = timetype.norm(valu)
        except s_exc.BadTypeValu as e:
            mesg = f'Failed to norm a time value prior to formatting - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu,
                                          format=format) from None

        if norm == timetype.futsize:
            mesg = 'Cannot format a timestamp for ongoing/future time.'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu, format=format)

        try:
            dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=norm)
            ret = dt.strftime(format)
        except Exception as e:
            mesg = f'Error during time format - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu,
                                          format=format) from None
        return ret

    async def _parse(self, valu, format, errok=False):
        errok = await tobool(errok)
        try:
            dt = datetime.datetime.strptime(valu, format)
        except ValueError as e:
            if errok:
                return None
            mesg = f'Error during time parsing - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu,
                                          format=format) from None
        if dt.tzinfo is not None:
            # Convert the aware dt to UTC, then strip off the tzinfo
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return int((dt - s_time.EPOCH).total_seconds() * 1000)

    async def _sleep(self, valu):
        await self.runt.snap.waitfini(timeout=float(valu))
        await self.runt.snap.clearCache()

    async def _ticker(self, tick, count=None):
        if count is not None:
            count = await toint(count)

        tick = float(tick)

        offs = 0
        while True:

            await self.runt.snap.waitfini(timeout=tick)
            await self.runt.snap.clearCache()
            yield offs

            offs += 1
            if count is not None and offs == count:
                break

    async def _fromunix(self, secs):
        secs = float(secs)
        return int(secs * 1000)

@registry.registerLib
class LibRegx(Lib):
    '''
    A Storm library for searching/matching with regular expressions.
    '''
    _storm_locals = (
        {'name': 'search', 'desc': '''
            Search the given text for the pattern and return the matching groups.

            Note:
                In order to get the matching groups, patterns must use parentheses
                to indicate the start and stop of the regex to return portions of.
                If groups are not used, a successful match will return a empty list
                and a unsuccessful match will return ``$lib.null``.

            Example:
                Extract the matching groups from a piece of text::

                    $m = $lib.regex.search("^([0-9])+.([0-9])+.([0-9])+$", $text)
                    if $m {
                        ($maj, $min, $pat) = $m
                    }''',
         'type': {'type': 'function', '_funcname': 'search',
                  'args': (
                      {'name': 'pattern', 'type': 'str', 'desc': 'The regular expression pattern.', },
                      {'name': 'text', 'type': 'str', 'desc': 'The text to match.', },
                      {'name': 'flags', 'type': 'int', 'desc': 'Regex flags to control the match behavior.',
                       'default': 0},
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of strings for the matching groups in the pattern.', }}},
        {'name': 'findall', 'desc': '''
            Search the given text for the patterns and return a list of matching strings.

            Note:
                If multiple matching groups are specified, the return value is a
                list of lists of strings.

            Example:

                Extract the matching strings from a piece of text::

                    for $x in $lib.regex.findall("G[0-9]{4}", "G0006 and G0001") {
                        $dostuff($x)
                    }
                    ''',
         'type': {'type': 'function', '_funcname': 'findall',
                  'args': (
                      {'name': 'pattern', 'type': 'str', 'desc': 'The regular expression pattern.', },
                      {'name': 'text', 'type': 'str', 'desc': 'The text to match.', },
                      {'name': 'flags', 'type': 'int', 'desc': 'Regex flags to control the match behavior.',
                       'default': 0},
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of lists of strings for the matching groups in the pattern.', }}},
        {'name': 'matches', 'desc': '''
            Check if text matches a pattern.
            Returns $lib.true if the text matches the pattern, otherwise $lib.false.

            Notes:
                This API requires the pattern to match at the start of the string.

            Example:
                Check if the variable matches a expression::

                    if $lib.regex.matches("^[0-9]+.[0-9]+.[0-9]+$", $text) {
                        $lib.print("It's semver! ...probably")
                    }
            ''',
         'type': {'type': 'function', '_funcname': 'matches',
                  'args': (
                      {'name': 'pattern', 'type': 'str', 'desc': 'The regular expression pattern.', },
                      {'name': 'text', 'type': 'str', 'desc': 'The text to match.', },
                      {'name': 'flags', 'type': 'int', 'desc': 'Regex flags to control the match behavior.',
                       'default': 0, },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if there is a match, False otherwise.', }}},
        {'name': 'replace', 'desc': '''
            Replace any substrings that match the given regular expression with the specified replacement.

            Example:
                Replace a portion of a string with a new part based on a regex::

                    $norm = $lib.regex.replace("\\sAND\\s", " & ", "Ham and eggs!", $lib.regex.flags.i)
            ''',
         'type': {'type': 'function', '_funcname': 'replace',
                  'args': (
                      {'name': 'pattern', 'type': 'str', 'desc': 'The regular expression pattern.', },
                      {'name': 'replace', 'type': 'str', 'desc': 'The text to replace matching sub strings.', },
                      {'name': 'text', 'type': 'str', 'desc': 'The input text to search/replace.', },
                      {'name': 'flags', 'type': 'int', 'desc': 'Regex flags to control the match behavior.',
                       'default': 0, },
                  ),
                  'returns': {'type': 'str', 'desc': 'The new string with matches replaced.', }}},
        {'name': 'flags.i', 'desc': 'Regex flag to indicate that case insensitive matches are allowed.',
         'type': 'int', },
        {'name': 'flags.m', 'desc': 'Regex flag to indicate that multiline matches are allowed.', 'type': 'int', },
    )
    _storm_lib_path = ('regex',)

    def __init__(self, runt, name=()):
        Lib.__init__(self, runt, name=name)
        self.compiled = {}

    def getObjLocals(self):
        return {
            'search': self.search,
            'matches': self.matches,
            'findall': self.findall,
            'replace': self.replace,
            'flags': {'i': regex.IGNORECASE,
                      'm': regex.MULTILINE,
                      },
        }

    async def _getRegx(self, pattern, flags):
        lkey = (pattern, flags)
        regx = self.compiled.get(lkey)
        if regx is None:
            regx = self.compiled[lkey] = regex.compile(pattern, flags=flags)
        return regx

    async def replace(self, pattern, replace, text, flags=0):
        text = await tostr(text)
        flags = await toint(flags)
        pattern = await tostr(pattern)
        replace = await tostr(replace)
        regx = await self._getRegx(pattern, flags)
        return regx.sub(replace, text)

    async def matches(self, pattern, text, flags=0):
        text = await tostr(text)
        flags = await toint(flags)
        pattern = await tostr(pattern)
        regx = await self._getRegx(pattern, flags)
        return regx.match(text) is not None

    async def search(self, pattern, text, flags=0):
        text = await tostr(text)
        flags = await toint(flags)
        pattern = await tostr(pattern)
        regx = await self._getRegx(pattern, flags)

        m = regx.search(text)
        if m is None:
            return None

        return m.groups()

    async def findall(self, pattern, text, flags=0):
        text = await tostr(text)
        flags = await toint(flags)
        pattern = await tostr(pattern)
        regx = await self._getRegx(pattern, flags)
        return regx.findall(text)

@registry.registerLib
class LibCsv(Lib):
    '''
    A Storm Library for interacting with csvtool.
    '''
    _storm_locals = (
        {'name': 'emit', 'desc': 'Emit a ``csv:row`` event to the Storm runtime for the given args.',
         'type': {'type': 'function', '_funcname': '_libCsvEmit',
                  'args': (
                      {'name': '*args', 'type': 'any', 'desc': 'Items which are emitted as a ``csv:row`` event.', },
                      {'name': 'table', 'type': 'str', 'default': None,
                       'desc': 'The name of the table to emit data too. Optional.', },
                  ),
                  'returns': {'type': 'null', }}},
    )
    _storm_lib_path = ('csv',)

    def getObjLocals(self):
        return {
            'emit': self._libCsvEmit,
        }

    async def _libCsvEmit(self, *args, table=None):
        row = [await toprim(a) for a in args]
        await self.runt.snap.fire('csv:row', row=row, table=table)

@registry.registerLib
class LibExport(Lib):
    '''
    A Storm Library for exporting data.
    '''
    _storm_lib_path = ('export',)
    _storm_locals = (
        {'name': 'toaxon', 'desc': '''
            Run a query as an export (fully resolving relationships between nodes in the output set)
            and save the resulting stream of packed nodes to the axon.
            ''',
         'type': {'type': 'function', '_funcname': 'toaxon',
                  'args': (
                      {'name': 'query', 'type': 'str', 'desc': 'A query to run as an export.', },
                      {'name': 'opts', 'type': 'dict', 'desc': 'Storm runtime query option params.',
                       'default': None, },
                  ),
                  'returns': {'type': 'list', 'desc': 'Returns a tuple of (size, sha256).', }}},
    )

    def getObjLocals(self):
        return {
            'toaxon': self.toaxon,
        }

    async def toaxon(self, query, opts=None):

        query = await tostr(query)

        opts = await toprim(opts)
        if opts is None:
            opts = {}

        if not isinstance(opts, dict):
            mesg = '$lib.export.toaxon() opts argument must be a dictionary.'
            raise s_exc.BadArg(mesg=mesg)

        opts['user'] = self.runt.snap.user.iden
        opts.setdefault('view', self.runt.snap.view.iden)
        return await self.runt.snap.core.exportStormToAxon(query, opts=opts)

@registry.registerLib
class LibFeed(Lib):
    '''
    A Storm Library for interacting with Cortex feed functions.
    '''
    _storm_locals = (
        {'name': 'genr', 'desc': '''
            Yield nodes being added to the graph by adding data with a given ingest type.

            Notes:
                This is using the Runtimes's Snap to call addFeedNodes().
                This only yields nodes if the feed function yields nodes.
                If the generator is not entirely consumed there is no guarantee
                that all of the nodes which should be made by the feed function
                will be made.
            ''',
         'type': {'type': 'function', '_funcname': '_libGenr',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the ingest function to send data too.', },
                      {'name': 'data', 'type': 'prim', 'desc': 'Data to send to the ingest function.', },
                  ),
                  'returns': {'name': 'Yields', 'type': 'storm:node',
                              'desc': 'Yields Nodes as they are created by the ingest function.', }}},
        {'name': 'list', 'desc': 'Get a list of feed functions.',
         'type': {'type': 'function', '_funcname': '_libList',
                  'returns': {'type': 'list', 'desc': 'A list of feed functions.', }}},
        {'name': 'ingest', 'desc': '''
            Add nodes to the graph with a given ingest type.

            Notes:
                This is using the Runtimes's Snap to call addFeedData(), after setting
                the snap.strict mode to False. This will cause node creation and property
                setting to produce warning messages, instead of causing the Storm Runtime
                to be torn down.''',
         'type': {'type': 'function', '_funcname': '_libIngest',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the ingest function to send data too.', },
                      {'name': 'data', 'type': 'prim', 'desc': 'Data to send to the ingest function.', },
                  ),
                  'returns': {'type': 'null', }}},
    )
    _storm_lib_path = ('feed',)

    def getObjLocals(self):
        return {
            'genr': self._libGenr,
            'list': self._libList,
            'ingest': self._libIngest,
            'fromAxon': self._fromAxon,
        }

    async def _fromAxon(self, sha256):
        '''
        Use the feed API to load a syn.nodes formatted export from the axon.

        Args:
            sha256 (str): The sha256 of the file saved in the axon.

        Returns:
            int: The number of nodes loaded.
        '''
        sha256 = await tostr(sha256)
        opts = {
            'user': self.runt.snap.user.iden,
            'view': self.runt.snap.view.iden,
        }
        return await self.runt.snap.core.feedFromAxon(sha256, opts=opts)

    async def _libGenr(self, name, data):
        name = await tostr(name)
        data = await toprim(data)

        self.runt.layerConfirm(('feed:data', *name.split('.')))
        with s_provenance.claim('feed:data', name=name):
            #  small work around for the feed API consistency
            if name == 'syn.nodes':
                async for node in self.runt.snap.addNodes(data):
                    yield node
                return
            await self.runt.snap.addFeedData(name, data)

    async def _libList(self):
        todo = ('getFeedFuncs', (), {})
        return await self.runt.dyncall('cortex', todo)

    async def _libIngest(self, name, data):
        name = await tostr(name)
        data = await toprim(data)

        self.runt.layerConfirm(('feed:data', *name.split('.')))
        with s_provenance.claim('feed:data', name=name):
            strict = self.runt.snap.strict
            self.runt.snap.strict = False
            await self.runt.snap.addFeedData(name, data)
            self.runt.snap.strict = strict

@registry.registerLib
class LibPipe(Lib):
    '''
    A Storm library for interacting with non-persistent queues.
    '''
    _storm_locals = (
        {'name': 'gen', 'desc': '''
            Generate and return a Storm Pipe.

            Notes:
                The filler query is run in parallel with $pipe. This requires the permission
                ``storm.pipe.gen`` to use.

            Examples:
                Fill a pipe with a query and consume it with another::

                    $pipe = $lib.pipe.gen(${ $pipe.puts((1, 2, 3)) })

                    for $items in $pipe.slices(size=2) {
                        $dostuff($items)
                    }
            ''',
         'type': {'type': 'function', '_funcname': '_methPipeGen',
                  'args': (
                      {'name': 'filler', 'type': ['str', 'storm:query'],
                       'desc': 'A Storm query to fill the Pipe.', },
                      {'name': 'size', 'type': 'int', 'default': 10000,
                       'desc': 'Maximum size of the pipe.', },
                  ),
                  'returns': {'type': 'storm:pipe', 'desc': 'The pipe containing query results.', }}},
    )

    _storm_lib_path = ('pipe',)

    def getObjLocals(self):
        return {
            'gen': self._methPipeGen,
        }

    async def _methPipeGen(self, filler, size=10000):
        size = await toint(size)
        text = await tostr(filler)

        if size < 1 or size > 10000:
            mesg = '$lib.pipe.gen() size must be 1-10000'
            raise s_exc.BadArg(mesg=mesg)

        pipe = Pipe(self.runt, size)

        varz = self.runt.vars.copy()
        varz['pipe'] = pipe

        opts = {'vars': varz}

        query = await self.runt.getStormQuery(text)
        runt = await self.runt.getModRuntime(query, opts=opts)

        async def coro():
            try:
                async with runt:
                    async for item in runt.execute():
                        await asyncio.sleep(0)

            except asyncio.CancelledError:  # pragma: no cover
                raise

            except Exception as e:
                await self.runt.warn(f'pipe filler error: {e}', log=False)

            await pipe.close()

        self.runt.snap.schedCoro(coro())

        return pipe

@registry.registerType
class Pipe(StormType):
    '''
    A Storm Pipe provides fast ephemeral queues.
    '''
    _storm_locals = (
        {'name': 'put', 'desc': 'Add a single item to the Pipe.',
         'type': {'type': 'function', '_funcname': '_methPipePut',
                  'args': (
                      {'name': 'item', 'type': 'any', 'desc': ' An object to add to the Pipe.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'puts', 'desc': 'Add a list of items to the Pipe.',
         'type': {'type': 'function', '_funcname': '_methPipePuts',
                  'args': (
                      {'name': 'items', 'type': 'list', 'desc': 'A list of items to add.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'slice', 'desc': 'Return a list of up to size items from the Pipe.',
         'type': {'type': 'function', '_funcname': '_methPipeSlice',
                  'args': (
                      {'name': 'size', 'type': 'int', 'default': 1000,
                       'desc': 'The max number of items to return.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of at least 1 item from the Pipe.', }}},
        {'name': 'slices', 'desc': '''
            Yield lists of up to size items from the Pipe.

            Notes:
                The loop will exit when the Pipe is closed and empty.

            Examples:
                Operation on slices from a pipe one at a time::

                    for $slice in $pipe.slices(1000) {
                        for $item in $slice { $dostuff($item) }
                    }

                Operate on slices from a pipe in bulk::

                    for $slice in $pipe.slices(1000) {
                        $dostuff_batch($slice)
                    }''',
         'type': {'type': 'function', '_funcname': '_methPipeSlices',
                  'args': (
                      {'name': 'size', 'type': 'int', 'default': 1000,
                       'desc': 'The max number of items to yield per slice.', },
                  ),
                  'returns': {'name': 'Yields', 'type': 'any', 'desc': 'Yields objects from the Pipe.', }}},
        {'name': 'size', 'desc': 'Retrieve the number of items in the Pipe.',
         'type': {'type': 'function', '_funcname': '_methPipeSize',
                  'returns': {'type': 'int', 'desc': 'The number of items in the Pipe.', }}},
    )
    _storm_typename = 'storm:pipe'

    def __init__(self, runt, size):
        StormType.__init__(self)
        self.runt = runt

        self.locls.update(self.getObjLocals())
        self.queue = s_queue.Queue(maxsize=size)

    def getObjLocals(self):
        return {
            'put': self._methPipePut,
            'puts': self._methPipePuts,
            'slice': self._methPipeSlice,
            'slices': self._methPipeSlices,
            'size': self._methPipeSize,
        }

    async def _methPipePuts(self, items):
        items = await toprim(items)
        return await self.queue.puts(items)

    async def _methPipePut(self, item):
        item = await toprim(item)
        return await self.queue.put(item)

    async def close(self):
        '''
        Close the pipe for writing.  This will cause
        the slice()/slices() API to return once drained.
        '''
        await self.queue.close()

    async def _methPipeSize(self):
        return await self.queue.size()

    async def _methPipeSlice(self, size=1000):

        size = await toint(size)
        if size < 1 or size > 10000:
            mesg = '$pipe.slice() size must be 1-10000'
            raise s_exc.BadArg(mesg=mesg)

        items = await self.queue.slice(size=size)
        if items is None:
            return None

        return List(items)

    async def _methPipeSlices(self, size=1000):
        size = await toint(size)
        if size < 1 or size > 10000:
            mesg = '$pipe.slice() size must be 1-10000'
            raise s_exc.BadArg(mesg=mesg)

        async for items in self.queue.slices(size=size):
            yield List(items)

@registry.registerLib
class LibQueue(Lib):
    '''
    A Storm Library for interacting with persistent Queues in the Cortex.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a Queue to the Cortex with a given name.',
         'type': {'type': 'function', '_funcname': '_methQueueAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the queue to add.', },
                  ),
                  'returns': {'type': 'storm:queue', }}},
        {'name': 'gen', 'desc': 'Add or get a Storm Queue in a single operation.',
         'type': {'type': 'function', '_funcname': '_methQueueGen',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Queue to add or get.', },
                  ),
                  'returns': {'type': 'storm:queue', }}},
        {'name': 'del', 'desc': 'Delete a given named Queue.',
         'type': {'type': 'function', '_funcname': '_methQueueDel',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the queue to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get an existing Storm Queue object.',
         'type': {'type': 'function', '_funcname': '_methQueueGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Queue to get.', },
                  ),
                  'returns': {'type': 'storm:queue', 'desc': 'A ``storm:queue`` object.', }}},
        {'name': 'list', 'desc': 'Get a list of the Queues in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methQueueList',
                  'returns': {'type': 'list',
                              'desc': 'A list of queue definitions the current user is allowed to interact with.', }}},
    )
    _storm_lib_path = ('queue',)

    def getObjLocals(self):
        return {
            'add': self._methQueueAdd,
            'gen': self._methQueueGen,
            'del': self._methQueueDel,
            'get': self._methQueueGet,
            'list': self._methQueueList,
        }

    async def _methQueueAdd(self, name):

        info = {
            'time': s_common.now(),
            'creator': self.runt.snap.user.iden,
        }

        todo = s_common.todo('addCoreQueue', name, info)
        gatekeys = ((self.runt.user.iden, ('queue', 'add'), None),)
        info = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return Queue(self.runt, name, info)

    async def _methQueueGet(self, name):
        todo = s_common.todo('getCoreQueue', name)
        gatekeys = ((self.runt.user.iden, ('queue', 'get'), f'queue:{name}'),)
        info = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return Queue(self.runt, name, info)

    async def _methQueueGen(self, name):
        try:
            return await self._methQueueGet(name)
        except s_exc.NoSuchName:
            return await self._methQueueAdd(name)

    async def _methQueueDel(self, name):
        todo = s_common.todo('delCoreQueue', name)
        gatekeys = ((self.runt.user.iden, ('queue', 'del',), f'queue:{name}'), )
        await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueList(self):
        retn = []

        todo = s_common.todo('listCoreQueues')
        qlist = await self.dyncall('cortex', todo)

        for queue in qlist:
            if not allowed(('queue', 'get'), f"queue:{queue['name']}"):
                continue

            retn.append(queue)

        return retn

@registry.registerType
class Queue(StormType):
    '''
    A StormLib API instance of a named channel in the Cortex multiqueue.
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the Queue.', 'type': 'str', },
        {'name': 'get', 'desc': 'Get a particular item from the Queue.',
         'type': {'type': 'function', '_funcname': '_methQueueGet',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'desc': 'The offset to retrieve an item from.', 'default': 0, },
                      {'name': 'cull', 'type': 'boolean', 'default': True,
                       'desc': 'Culls items up to, but not including, the specified offset.', },
                      {'name': 'wait', 'type': 'boolean', 'default': True,
                       'desc': 'Wait for the offset to be available before returning the item.', },
                  ),
                  'returns': {'type': 'list',
                              'desc': 'A tuple of the offset and the item from the queue. If wait is false and '
                                      'the offset is not present, null is returned.', }}},
        {'name': 'pop', 'desc': 'Pop a item from the Queue at a specific offset.',
         'type': {'type': 'function', '_funcname': '_methQueuePop',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'default': None,
                        'desc': 'Offset to pop the item from. If not specified, the first item in the queue will be'
                                ' popped.', },
                      {'name': 'wait', 'type': 'boolean', 'default': False,
                        'desc': 'Wait for an item to be available to pop.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'The offset and item popped from the queue. If there is no item at the '
                                      'offset or the  queue is empty and wait is false, it returns null.', }}},
        {'name': 'put', 'desc': 'Put an item into the queue.',
         'type': {'type': 'function', '_funcname': '_methQueuePut',
                  'args': (
                      {'name': 'item', 'type': 'prim', 'desc': 'The item being put into the queue.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'puts', 'desc': 'Put multiple items into the Queue.',
         'type': {'type': 'function', '_funcname': '_methQueuePuts',
                  'args': (
                      {'name': 'items', 'type': 'list', 'desc': 'The items to put into the Queue.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'gets', 'desc': 'Get multiple items from the Queue as a iterator.',
         'type': {'type': 'function', '_funcname': '_methQueueGets',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'desc': 'The offset to retrieve an items from.', 'default': 0, },
                      {'name': 'wait', 'type': 'boolean', 'default': True,
                       'desc': 'Wait for the offset to be available before returning the item.', },
                      {'name': 'cull', 'type': 'boolean', 'default': False,
                       'desc': 'Culls items up to, but not including, the specified offset.', },
                      {'name': 'size', 'type': 'int', 'desc': 'The maximum number of items to yield',
                       'default': None, },
                  ),
                  'returns': {'name': 'Yields', 'type': 'list', 'desc': 'Yields tuples of the offset and item.', }}},
        {'name': 'cull', 'desc': 'Remove items from the queue up to, and including, the offset.',
         'type': {'type': 'function', '_funcname': '_methQueueCull',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'desc': 'The offset which to cull records from the queue.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'size', 'desc': 'Get the number of items in the Queue.',
         'type': {'type': 'function', '_funcname': '_methQueueSize',
                  'returns': {'type': 'int', 'desc': 'The number of items in the Queue.', }}},
    )
    _storm_typename = 'storm:queue'
    _ismutable = False

    def __init__(self, runt, name, info):

        StormType.__init__(self)
        self.runt = runt
        self.name = name
        self.info = info

        self.gateiden = f'queue:{name}'

        self.locls.update(self.getObjLocals())
        self.locls['name'] = self.name

    def __hash__(self):
        return hash((self._storm_typename, self.name))

    def __eq__(self, othr):
        if not isinstance(othr, type(self)):
            return False
        return self.name == othr.name

    def getObjLocals(self):
        return {
            'get': self._methQueueGet,
            'pop': self._methQueuePop,
            'put': self._methQueuePut,
            'puts': self._methQueuePuts,
            'gets': self._methQueueGets,
            'cull': self._methQueueCull,
            'size': self._methQueueSize,
        }

    async def _methQueueCull(self, offs):
        offs = await toint(offs)
        gatekeys = self._getGateKeys('get')
        await self.runt.reqGateKeys(gatekeys)
        await self.runt.snap.core.coreQueueCull(self.name, offs)

    async def _methQueueSize(self):
        gatekeys = self._getGateKeys('get')
        await self.runt.reqGateKeys(gatekeys)
        return await self.runt.snap.core.coreQueueSize(self.name)

    async def _methQueueGets(self, offs=0, wait=True, cull=False, size=None):
        wait = await toint(wait)
        offs = await toint(offs)
        size = await toint(size, noneok=True)

        gatekeys = self._getGateKeys('get')
        await self.runt.reqGateKeys(gatekeys)

        async for item in self.runt.snap.core.coreQueueGets(self.name, offs, cull=cull, wait=wait, size=size):
            yield item

    async def _methQueuePuts(self, items):
        items = await toprim(items)
        gatekeys = self._getGateKeys('put')
        await self.runt.reqGateKeys(gatekeys)
        return await self.runt.snap.core.coreQueuePuts(self.name, items)

    async def _methQueueGet(self, offs=0, cull=True, wait=True):
        offs = await toint(offs)
        wait = await toint(wait)

        gatekeys = self._getGateKeys('get')
        await self.runt.reqGateKeys(gatekeys)

        return await self.runt.snap.core.coreQueueGet(self.name, offs, cull=cull, wait=wait)

    async def _methQueuePop(self, offs=None, wait=False):
        offs = await toint(offs, noneok=True)
        wait = await tobool(wait)

        gatekeys = self._getGateKeys('get')
        await self.runt.reqGateKeys(gatekeys)

        # emulate the old behavior on no argument
        core = self.runt.snap.core
        if offs is None:
            async for item in core.coreQueueGets(self.name, 0, wait=wait):
                return await core.coreQueuePop(self.name, item[0])
            return

        return await core.coreQueuePop(self.name, offs)

    async def _methQueuePut(self, item):
        return await self._methQueuePuts((item,))

    def _getGateKeys(self, perm):
        return ((self.runt.user.iden, ('queue', perm), self.gateiden),)

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.name}'

@registry.registerLib
class LibTelepath(Lib):
    '''
    A Storm Library for making Telepath connections to remote services.
    '''
    _storm_locals = (
        {'name': 'open', 'desc': 'Open and return a Telepath RPC proxy.',
         'type': {'type': 'function', '_funcname': '_methTeleOpen',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The Telepath URL to connect to.', },
                  ),
                  'returns': {'type': 'storm:proxy', 'desc': 'A object representing a Telepath Proxy.', }}},
    )
    _storm_lib_path = ('telepath',)

    def getObjLocals(self):
        return {
            'open': self._methTeleOpen,
        }

    async def _methTeleOpen(self, url):
        url = await tostr(url)
        scheme = url.split('://')[0]
        self.runt.confirm(('lib', 'telepath', 'open', scheme))
        return Proxy(self.runt, await self.runt.getTeleProxy(url))

@registry.registerType
class Proxy(StormType):
    '''
    Implements the Storm API for a Telepath proxy.

    These can be created via ``$lib.telepath.open()``. Storm Service objects
    are also Telepath proxy objects.

    Methods called off of these objects are executed like regular Telepath RMI
    calls.

    An example of calling a method which returns data::

        $prox = $lib.telepath.open($url)
        $result = $prox.doWork($data)
        return ( $result )

    An example of calling a method which is a generator::

        $prox = $lib.telepath.open($url)
        for $item in = $prox.genrStuff($data) {
            $doStuff($item)
        }

    '''
    _storm_typename = 'storm:proxy'

    def __init__(self, runt, proxy, path=None):
        StormType.__init__(self, path=path)
        self.runt = runt
        self.proxy = proxy

    async def deref(self, name):

        if name[0] == '_':
            mesg = f'No proxy method named {name}'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        meth = getattr(self.proxy, name, None)

        if isinstance(meth, s_telepath.GenrMethod):
            return ProxyGenrMethod(meth)

        if isinstance(meth, s_telepath.Method):
            return ProxyMethod(self.runt, meth)

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.proxy}'

# @registry.registerType
class ProxyMethod(StormType):

    _storm_typename = 'storm:proxy:method'

    def __init__(self, runt, meth, path=None):
        StormType.__init__(self, path=path)
        self.runt = runt
        self.meth = meth

    async def __call__(self, *args, **kwargs):
        args = await toprim(args)
        kwargs = await toprim(kwargs)
        # TODO: storm types fromprim()
        ret = await self.meth(*args, **kwargs)
        if isinstance(ret, s_telepath.Share):
            self.runt.snap.onfini(ret)
            return Proxy(self.runt, ret)
        return ret

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.meth}'

# @registry.registerType
class ProxyGenrMethod(StormType):

    _storm_typename = 'storm:proxy:genrmethod'

    def __init__(self, meth, path=None):
        StormType.__init__(self, path=path)
        self.meth = meth

    async def __call__(self, *args, **kwargs):
        args = await toprim(args)
        kwargs = await toprim(kwargs)
        async for prim in self.meth(*args, **kwargs):
            # TODO: storm types fromprim()
            yield prim

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.meth}'

# @registry.registerType
class Service(Proxy):

    def __init__(self, runt, ssvc):
        Proxy.__init__(self, runt, ssvc.proxy)
        self.name = ssvc.name

    async def deref(self, name):
        try:
            await self.proxy.waitready()
            return await Proxy.deref(self, name)
        except asyncio.TimeoutError:
            mesg = f'Timeout waiting for storm service {self.name}.{name}'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name, service=self.name) from None
        except AttributeError as e:  # pragma: no cover
            # possible client race condition seen in the real world
            mesg = f'Error dereferencing storm service - {self.name}.{name} - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name, service=self.name) from None

@registry.registerLib
class LibBase64(Lib):
    '''
    A Storm Library for encoding and decoding base64 data.
    '''
    _storm_locals = (
        {'name': 'encode', 'desc': 'Encode a bytes object to a base64 encoded string.',
         'type': {'type': 'function', '_funcname': '_encode',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The object to encode.', },
                      {'name': 'urlsafe', 'type': 'boolean', 'default': True,
                       'desc': 'Perform the encoding in a urlsafe manner if true.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'A base64 encoded string.', }}},
        {'name': 'decode', 'desc': 'Decode a base64 string into a bytes object.',
         'type': {'type': 'function', '_funcname': '_decode',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The string to decode.', },
                      {'name': 'urlsafe', 'type': 'boolean', 'default': True,
                       'desc': 'Perform the decoding in a urlsafe manner if true.', },
                  ),
                  'returns': {'type': 'bytes', 'desc': 'A bytes object for the decoded data.', }}},
    )
    _storm_lib_path = ('base64',)

    def getObjLocals(self):
        return {
            'encode': self._encode,
            'decode': self._decode
        }

    async def _encode(self, valu, urlsafe=True):
        try:
            if urlsafe:
                return base64.urlsafe_b64encode(valu).decode('ascii')
            return base64.b64encode(valu).decode('ascii')
        except TypeError as e:
            mesg = f'Error during base64 encoding - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu, urlsafe=urlsafe) from None

    async def _decode(self, valu, urlsafe=True):
        try:
            if urlsafe:
                return base64.urlsafe_b64decode(valu)
            return base64.b64decode(valu)
        except binascii.Error as e:
            mesg = f'Error during base64 decoding - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu, urlsafe=urlsafe) from None

@functools.total_ordering
class Prim(StormType):
    '''
    The base type for all Storm primitive values.
    '''

    def __init__(self, valu, path=None):
        StormType.__init__(self, path=path)
        self.valu = valu

    def __int__(self):
        mesg = 'Storm type {__class__.__name__.lower()} cannot be cast to an int'
        raise s_exc.BadCast(mesg)

    def __len__(self):
        name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        raise s_exc.StormRuntimeError(mesg=f'Object {name} does not have a length.', name=name)

    def __eq__(self, othr):
        if not isinstance(othr, type(self)):
            return False
        return self.valu == othr.valu

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            mesg = f"'<' not supported between instance of {self.__class__.__name__} and {other.__class__.__name__}"
            raise TypeError(mesg)
        return self.valu < other.valu

    def value(self):
        return self.valu

    async def iter(self):  # pragma: no cover
        for x in ():
            yield x
        name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        raise s_exc.StormRuntimeError(mesg=f'Object {name} is not iterable.', name=name)

    async def nodes(self):  # pragma: no cover
        for x in ():
            yield x

    async def bool(self):
        return bool(await s_coro.ornot(self.value))

    async def stormrepr(self):  # pragma: no cover
        return f'{self._storm_typename}: {await s_coro.ornot(self.value)}'

@registry.registerType
class Str(Prim):
    '''
    Implements the Storm API for a String object.
    '''
    _storm_locals = (
        {'name': 'split', 'desc': '''
            Split the string into multiple parts based on a separator.

            Example:
                Split a string on the colon character::

                    ($foo, $bar) = $baz.split(":")''',
         'type': {'type': 'function', '_funcname': '_methStrSplit',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text to split the string up with.', },
                      {'name': 'maxsplit', 'type': 'int', 'default': -1, 'desc': 'The max number of splits.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of parts representing the split string.', }}},
        {'name': 'rsplit', 'desc': '''
            Split the string into multiple parts, from the right, based on a separator.

            Example:
                Split a string on the colon character::

                    ($foo, $bar) = $baz.rsplit(":", maxsplit=1)''',
         'type': {'type': 'function', '_funcname': '_methStrRsplit',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text to split the string up with.', },
                      {'name': 'maxsplit', 'type': 'int', 'default': -1, 'desc': 'The max number of splits.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of parts representing the split string.', }}},
        {'name': 'endswith', 'desc': 'Check if a string ends with text.',
         'type': {'type': 'function', '_funcname': '_methStrEndswith',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text to check.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the text ends with the string, false otherwise.', }}},
        {'name': 'startswith', 'desc': 'Check if a string starts with text.',
         'type': {'type': 'function', '_funcname': '_methStrStartswith',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text to check.', },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the text starts with the string, false otherwise.', }}},
        {'name': 'ljust', 'desc': 'Left justify the string.',
         'type': {'type': 'function', '_funcname': '_methStrLjust',
                  'args': (
                      {'name': 'size', 'type': 'int', 'desc': 'The length of character to left justify.', },
                      {'name': 'fillchar', 'type': 'str', 'default': ' ',
                       'desc': 'The character to use for padding.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The left justified string.', }}},
        {'name': 'rjust', 'desc': 'Right justify the string.',
         'type': {'type': 'function', '_funcname': '_methStrRjust',
                  'args': (
                      {'name': 'size', 'type': 'int', 'desc': 'The length of character to right justify.', },
                      {'name': 'fillchar', 'type': 'str', 'default': ' ',
                       'desc': 'The character to use for padding.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The right justified string.', }}},
        {'name': 'encode', 'desc': 'Encoding a string value to bytes.',
         'type': {'type': 'function', '_funcname': '_methEncode',
                  'args': (
                      {'name': 'encoding', 'type': 'str', 'desc': 'Encoding to use. Defaults to utf8.',
                       'default': 'utf8', },
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The encoded string.', }}},
        {'name': 'replace', 'desc': '''
            Replace occurrences of a string with a new string, optionally restricting the number of replacements.

            Example:
                Replace instances of the string "bar" with the string "baz"::

                    $foo.replace('bar', 'baz')''',
         'type': {'type': 'function', '_funcname': '_methStrReplace',
                  'args': (
                      {'name': 'oldv', 'type': 'str', 'desc': 'The value to replace.', },
                      {'name': 'newv', 'type': 'str', 'desc': 'The value to add into the string.', },
                      {'name': 'maxv', 'type': 'int', 'desc': 'The maximum number of occurances to replace.',
                       'default': None, },
                  ),
                  'returns': {'type': 'str', 'desc': 'The new string with replaced instances.', }}},
        {'name': 'strip', 'desc': '''
            Remove leading and trailing characters from a string.

            Examples:
                Removing whitespace and specific characters::

                    $strippedFoo = $foo.strip()
                    $strippedBar = $bar.strip(asdf)''',
         'type': {'type': 'function', '_funcname': '_methStrStrip',
                  'args': (
                      {'name': 'chars', 'type': 'str', 'default': None,
                       'desc': 'A list of characters to remove. If not specified, whitespace is stripped.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The stripped string.', }}},
        {'name': 'lstrip', 'desc': '''
            Remove leading characters from a string.

            Examples:
                Removing whitespace and specific characters::

                    $strippedFoo = $foo.lstrip()
                    $strippedBar = $bar.lstrip(w)''',
         'type': {'type': 'function', '_funcname': '_methStrLstrip',
                  'args': (
                      {'name': 'chars', 'type': 'str', 'default': None,
                       'desc': 'A list of characters to remove. If not specified, whitespace is stripped.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The stripped string.', }}},
        {'name': 'rstrip', 'desc': '''
            Remove trailing characters from a string.

            Examples:
                Removing whitespace and specific characters::

                    $strippedFoo = $foo.rstrip()
                    $strippedBar = $bar.rstrip(asdf)
                ''',
         'type': {'type': 'function', '_funcname': '_methStrRstrip',
                  'args': (
                      {'name': 'chars', 'type': 'str', 'default': None,
                       'desc': 'A list of characters to remove. If not specified, whitespace is stripped.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The stripped string.', }}},
        {'name': 'lower', 'desc': '''
            Get a lowercased copy the of the string.

            Examples:
                Printing a lowercased string::

                    $foo="Duck"
                    $lib.print($foo.lower())''',
         'type': {'type': 'function', '_funcname': '_methStrLower',
                  'returns': {'type': 'str', 'desc': 'The lowercased string.', }}},
        {'name': 'upper', 'desc': '''
                Get a uppercased copy the of the string.

                Examples:
                    Printing a uppercased string::

                        $foo="Duck"
                        $lib.print($foo.upper())''',
         'type': {'type': 'function', '_funcname': '_methStrUpper',
                  'returns': {'type': 'str', 'desc': 'The uppercased string.', }}},
        {'name': 'slice', 'desc': '''
            Get a substring slice of the string.

            Examples:
                Slice from index to 1 to 5::

                    $x="foobar"
                    $y=$x.slice(1,5)  // "ooba"

                Slice from index 3 to the end of the string::

                    $y=$x.slice(3)  // "bar"
            ''',
         'type': {'type': 'function', '_funcname': '_methStrSlice',
                  'args': (
                      {'name': 'start', 'type': 'int', 'desc': 'The starting character index.'},
                      {'name': 'end', 'type': 'int', 'default': None,
                       'desc': 'The ending character index. If not specified, slice to the end of the string'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The slice substring.'}}},
        {'name': 'reverse', 'desc': '''
        Get a reversed copy of the string.

        Examples:
            Printing a reversed string::

                $foo="foobar"
                $lib.print($foo.reverse())''',
         'type': {'type': 'function', '_funcname': '_methStrReverse',
                  'returns': {'type': 'str', 'desc': 'The reversed string.', }}},

        {'name': 'find', 'desc': '''
            Find the offset of a given string within another.

            Examples:
                Find values in the string ``asdf``::

                    $x = asdf
                    $x.find(d) // returns 2
                    $x.find(v) // returns null

            ''',
         'type': {'type': 'function', '_funcname': '_methStrFind',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The substring to find.'},
                  ),
                  'returns': {'type': 'int', 'desc': 'The first offset of subsgring or null.'}}},
        {'name': 'size', 'desc': 'Return the length of the string.',
         'type': {'type': 'function', '_funcname': '_methStrSize',
                  'returns': {'type': 'int', 'desc': 'The size of the string.', }}},
        {'name': 'format', 'desc': '''
        Format a text string from an existing string.

        Examples:
            Format a string with a fixed argument and a variable::

                $template='Hello {name}, list is {list}!' $list=(1,2,3,4) $new=$template.format(name='Reader', list=$list)

                ''',
         'type': {'type': 'function', '_funcname': '_methStrFormat',
                  'args': (
                      {'name': '**kwargs', 'type': 'any',
                       'desc': 'Keyword values which are substituted into the string.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The new string.', }}},
    )
    _storm_typename = 'str'
    _ismutable = False

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'find': self._methStrFind,
            'size': self._methStrSize,
            'split': self._methStrSplit,
            'rsplit': self._methStrRsplit,
            'endswith': self._methStrEndswith,
            'startswith': self._methStrStartswith,
            'ljust': self._methStrLjust,
            'rjust': self._methStrRjust,
            'encode': self._methEncode,
            'replace': self._methStrReplace,
            'strip': self._methStrStrip,
            'lstrip': self._methStrLstrip,
            'rstrip': self._methStrRstrip,
            'lower': self._methStrLower,
            'upper': self._methStrUpper,
            'slice': self._methStrSlice,
            'reverse': self._methStrReverse,
            'format': self._methStrFormat,
        }

    def __int__(self):
        return int(self.value(), 0)

    def __str__(self):
        return self.value()

    def __len__(self):
        return len(self.valu)

    def __hash__(self):
        # As a note, this hash of the typename and the value means that s_stormtypes.Str('foo') != 'foo'
        return hash((self._storm_typename, self.valu))

    def __eq__(self, othr):
        if isinstance(othr, (Str, str)):
            return str(self) == str(othr)
        return False

    async def _methStrFind(self, valu):
        text = await tostr(valu)
        retn = self.valu.find(text)
        if retn == -1:
            retn = None
        return retn

    async def _methStrFormat(self, **kwargs):
        text = await kwarg_format(self.valu, **kwargs)
        return text

    async def _methStrSize(self):
        return len(self.valu)

    async def _methEncode(self, encoding='utf8'):
        try:
            return self.valu.encode(encoding, 'surrogatepass')
        except UnicodeEncodeError as e:
            raise s_exc.StormRuntimeError(mesg=str(e), valu=self.valu[:1024]) from None

    async def _methStrSplit(self, text, maxsplit=-1):
        maxsplit = await toint(maxsplit)
        return self.valu.split(text, maxsplit=maxsplit)

    async def _methStrRsplit(self, text, maxsplit=-1):
        maxsplit = await toint(maxsplit)
        return self.valu.rsplit(text, maxsplit=maxsplit)

    async def _methStrEndswith(self, text):
        return self.valu.endswith(text)

    async def _methStrStartswith(self, text):
        return self.valu.startswith(text)

    async def _methStrRjust(self, size, fillchar=' '):
        return self.valu.rjust(await toint(size), await tostr(fillchar))

    async def _methStrLjust(self, size, fillchar=' '):
        return self.valu.ljust(await toint(size), await tostr(fillchar))

    async def _methStrReplace(self, oldv, newv, maxv=None):
        if maxv is None:
            return self.valu.replace(oldv, newv)
        else:
            return self.valu.replace(oldv, newv, int(maxv))

    async def _methStrStrip(self, chars=None):
        return self.valu.strip(chars)

    async def _methStrLstrip(self, chars=None):
        return self.valu.lstrip(chars)

    async def _methStrRstrip(self, chars=None):
        return self.valu.rstrip(chars)

    async def _methStrLower(self):
        return self.valu.lower()

    async def _methStrUpper(self):
        return self.valu.upper()

    async def _methStrSlice(self, start, end=None):
        start = await toint(start)

        if end is None:
            return self.valu[start:]

        end = await toint(end)
        return self.valu[start:end]

    async def _methStrReverse(self):
        return self.valu[::-1]

@registry.registerType
class Bytes(Prim):
    '''
    Implements the Storm API for a Bytes object.
    '''
    _storm_locals = (
        {'name': 'decode', 'desc': 'Decode bytes to a string.',
         'type': {'type': 'function', '_funcname': '_methDecode',
                  'args': (
                      {'name': 'encoding', 'type': 'str', 'desc': 'The encoding to use.', 'default': 'utf8', },
                      {'name': 'errors', 'type': 'str', 'desc': 'The error handling scheme to use.', 'default': 'surrogatepass', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The decoded string.', }}},
        {'name': 'bunzip', 'desc': '''
            Decompress the bytes using bzip2.

            Example:
                Decompress bytes with bzip2::

                    $foo = $mybytez.bunzip()''',
         'type': {'type': 'function', '_funcname': '_methBunzip',
                  'returns': {'type': 'bytes', 'desc': 'Decompressed bytes.', }}},
        {'name': 'gunzip', 'desc': '''
            Decompress the bytes using gzip and return them.

            Example:
                Decompress bytes with bzip2::

                $foo = $mybytez.gunzip()''',
         'type': {'type': 'function', '_funcname': '_methGunzip',
                  'returns': {'type': 'bytes', 'desc': 'Decompressed bytes.', }}},
        {'name': 'bzip', 'desc': '''
            Compress the bytes using bzip2 and return them.

            Example:
                Compress bytes with bzip::

                    $foo = $mybytez.bzip()''',
         'type': {'type': 'function', '_funcname': '_methBzip',
                  'returns': {'type': 'bytes', 'desc': 'The bzip2 compressed bytes.', }}},
        {'name': 'gzip', 'desc': '''
            Compress the bytes using gzip and return them.

            Example:
                Compress bytes with gzip::
                    $foo = $mybytez.gzip()''',
         'type': {'type': 'function', '_funcname': '_methGzip',
                  'returns': {'type': 'bytes', 'desc': 'The gzip compressed bytes.', }}},
        {'name': 'json', 'desc': '''
            Load JSON data from bytes.

            Notes:
                The bytes must be UTF8, UTF16 or UTF32 encoded.

            Example:
                Load bytes to a object::
                    $foo = $mybytez.json()''',
         'type': {'type': 'function', '_funcname': '_methJsonLoad',
                  'returns': {'type': 'prim', 'desc': 'The deserialized object.', }}},

        {'name': 'slice', 'desc': '''
            Slice a subset of bytes from an existing bytes.

            Examples:
                Slice from index to 1 to 5::

                    $subbyts = $byts.slice(1,5)

                Slice from index 3 to the end of the bytes::

                    $subbyts = $byts.slice(3)
            ''',
         'type': {'type': 'function', '_funcname': 'slice',
                  'args': (
                      {'name': 'start', 'type': 'int', 'desc': 'The starting byte index.'},
                      {'name': 'end', 'type': 'int', 'default': None,
                       'desc': 'The ending byte index. If not specified, slice to the end.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The slice of bytes.', }}},

        {'name': 'unpack', 'desc': '''
            Unpack structures from bytes using python struct.unpack syntax.

            Examples:
                # unpack 3 unsigned 16 bit integers in little endian format
                ($x, $y, $z) = $byts.unpack("<HHH")
            ''',
         'type': {'type': 'function', '_funcname': 'unpack',
                  'args': (
                      {'name': 'fmt', 'type': 'str', 'desc': 'A python struck.pack format string.'},
                      {'name': 'offset', 'type': 'int', 'desc': 'An offset to begin unpacking from.', 'default': 0},
                  ),
                  'returns': {'type': 'list', 'desc': 'The unpacked primitive values.', }}},
    )
    _storm_typename = 'bytes'
    _ismutable = False

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'decode': self._methDecode,
            'bunzip': self._methBunzip,
            'gunzip': self._methGunzip,
            'bzip': self._methBzip,
            'gzip': self._methGzip,
            'json': self._methJsonLoad,
            'slice': self.slice,
            'unpack': self.unpack,
        }

    def __len__(self):
        return len(self.valu)

    def __str__(self):
        return self.valu.decode()

    def __hash__(self):
        return hash((self._storm_typename, self.valu))

    def __eq__(self, othr):
        if isinstance(othr, Bytes):
            return self.valu == othr.valu
        return False

    async def _storm_copy(self):
        item = await s_coro.ornot(self.value)
        return s_msgpack.deepcopy(item, use_list=True)

    async def slice(self, start, end=None):
        start = await toint(start)
        if end is None:
            return self.valu[start:]

        end = await toint(end)
        return self.valu[start:end]

    async def unpack(self, fmt, offset=0):
        fmt = await tostr(fmt)
        offset = await toint(offset)
        try:
            return struct.unpack_from(fmt, self.valu, offset=offset)
        except struct.error as e:
            raise s_exc.BadArg(mesg=f'unpack() error: {e}')

    async def _methDecode(self, encoding='utf8', errors='surrogatepass'):
        encoding = await tostr(encoding)
        errors = await tostr(errors)
        try:
            return self.valu.decode(encoding, errors)
        except UnicodeDecodeError as e:
            raise s_exc.StormRuntimeError(mesg=str(e), valu=self.valu[:1024]) from None

    async def _methBunzip(self):
        return bz2.decompress(self.valu)

    async def _methBzip(self):
        return bz2.compress(self.valu)

    async def _methGunzip(self):
        return gzip.decompress(self.valu)

    async def _methGzip(self):
        return gzip.compress(self.valu)

    async def _methJsonLoad(self):
        return json.loads(self.valu)

@registry.registerType
class Dict(Prim):
    '''
    Implements the Storm API for a Dictionary object.
    '''
    _storm_typename = 'dict'
    _ismutable = True

    def __len__(self):
        return len(self.valu)

    async def _storm_copy(self):
        item = await s_coro.ornot(self.value)
        return s_msgpack.deepcopy(item, use_list=True)

    async def iter(self):
        for item in tuple(self.valu.items()):
            yield item

    async def setitem(self, name, valu):

        if valu is undef:
            self.valu.pop(name, None)
            return

        self.valu[name] = valu

    async def deref(self, name):
        return self.valu.get(name)

    async def value(self):
        return {await toprim(k): await toprim(v) for (k, v) in self.valu.items()}

    async def stormrepr(self):
        reprs = ["{}: {}".format(await torepr(k), await torepr(v)) for (k, v) in list(self.valu.items())]
        rval = ', '.join(reprs)
        return f'{{{rval}}}'

@registry.registerType
class CmdOpts(Dict):
    '''
    A dictionary like object that holds a reference to a command options namespace.
    ( This allows late-evaluation of command arguments rather than forcing capture )
    '''
    _storm_typename = 'storm:cmdopts'
    _ismutable = False

    def __len__(self):
        valu = vars(self.valu.opts)
        return len(valu)

    def __hash__(self):
        valu = vars(self.valu.opts)
        return hash((self._storm_typename, tuple(valu.items())))

    async def setitem(self, name, valu):
        # due to self.valu.opts potentially being replaced
        # we disallow setitem() to prevent confusion
        mesg = 'CmdOpts may not be modified by the runtime'
        raise s_exc.StormRuntimeError(mesg=mesg, name=name)

    async def deref(self, name):
        return getattr(self.valu.opts, name, None)

    async def value(self):
        valu = vars(self.valu.opts)
        return {await toprim(k): await toprim(v) for (k, v) in valu.items()}

    async def iter(self):
        valu = vars(self.valu.opts)
        for item in valu.items():
            yield item

    async def stormrepr(self):
        valu = vars(self.valu.opts)
        reprs = ["{}: {}".format(await torepr(k), await torepr(v)) for (k, v) in valu.items()]
        rval = ', '.join(reprs)
        return f'{self._storm_typename}: {{{rval}}}'

@registry.registerType
class Set(Prim):
    '''
    Implements the Storm API for a Set object.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a item to the set. Each argument is added to the set.',
         'type': {'type': 'function', '_funcname': '_methSetAdd',
                  'args': (
                      {'name': '*items', 'type': 'any', 'desc': 'The items to add to the set.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'has', 'desc': 'Check if a item is a member of the set.',
         'type': {'type': 'function', '_funcname': '_methSetHas',
                  'args': (
                      {'name': 'item', 'type': 'any', 'desc': 'The item to check the set for membership.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the item is in the set, false otherwise.', }}},
        {'name': 'rem', 'desc': 'Remove an item from the set.',
         'type': {'type': 'function', '_funcname': '_methSetRem',
                  'args': (
                      {'name': '*items', 'type': 'any', 'desc': 'Items to be removed from the set.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'adds', 'desc': 'Add the contents of a iterable items to the set.',
         'type': {'type': 'function', '_funcname': '_methSetAdds',
                  'args': (
                      {'name': '*items', 'type': 'any', 'desc': 'Iterables items to add to the set.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'rems', 'desc': 'Remove the contents of a iterable object from the set.',
         'type': {'type': 'function', '_funcname': '_methSetRems',
                  'args': (
                      {'name': '*items', 'type': 'any', 'desc': 'Iterables items to remove from the set.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of the current members of the set.',
         'type': {'type': 'function', '_funcname': '_methSetList',
                  'returns': {'type': 'list', 'desc': 'A list containing the members of the set.', }}},
        {'name': 'size', 'desc': 'Get the size of the set.',
         'type': {'type': 'function', '_funcname': '_methSetSize',
                  'returns': {'type': 'int', 'desc': 'The size of the set.', }}},
    )
    _storm_typename = 'set'
    _ismutable = True

    def __init__(self, valu, path=None):
        valu = list(valu)
        for item in valu:
            if ismutable(item):
                mesg = f'{repr(item)} is mutable and cannot be used in a set.'
                raise s_exc.StormRuntimeError(mesg=mesg)

        Prim.__init__(self, set(valu), path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'add': self._methSetAdd,
            'has': self._methSetHas,
            'rem': self._methSetRem,
            'adds': self._methSetAdds,
            'rems': self._methSetRems,
            'list': self._methSetList,
            'size': self._methSetSize,
        }

    async def iter(self):
        for item in self.valu:
            yield item

    def __len__(self):
        return len(self.valu)

    async def _methSetSize(self):
        return len(self)

    async def _methSetHas(self, item):
        return item in self.valu

    async def _methSetAdd(self, *items):
        for i in items:
            if ismutable(i):
                mesg = f'{await torepr(i)} is mutable and cannot be used in a set.'
                raise s_exc.StormRuntimeError(mesg=mesg)
            self.valu.add(i)

    async def _methSetAdds(self, *items):
        for item in items:
            async for i in toiter(item):
                if ismutable(i):
                    mesg = f'{await torepr(i)} is mutable and cannot be used in a set.'
                    raise s_exc.StormRuntimeError(mesg=mesg)
                self.valu.add(i)

    async def _methSetRem(self, *items):
        [self.valu.discard(i) for i in items]

    async def _methSetRems(self, *items):
        for item in items:
            [self.valu.discard(i) async for i in toiter(item)]

    async def _methSetList(self):
        return list(self.valu)

    async def stormrepr(self):
        reprs = [await torepr(k) for k in self.valu]
        rval = ', '.join(reprs)
        return f'{{{rval}}}'

@registry.registerType
class List(Prim):
    '''
    Implements the Storm API for a List instance.
    '''
    _storm_locals = (
        {'name': 'has', 'desc': 'Check it a value is in the list.',
         'type': {'type': 'function', '_funcname': '_methListHas',
                  'args': (
                      {'name': 'valu', 'type': 'any', 'desc': 'The value to check.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the item is in the list, false otherwise.', }}},
        {'name': 'pop', 'desc': 'Pop and return the last entry in the list.',
         'type': {'type': 'function', '_funcname': '_methListPop',
                  'returns': {'type': 'any', 'desc': 'The last item from the list.', }}},
        {'name': 'size', 'desc': 'Return the length of the list.',
         'type': {'type': 'function', '_funcname': '_methListSize',
                  'returns': {'type': 'int', 'desc': 'The size of the list.', }}},
        {'name': 'sort', 'desc': 'Sort the list in place.',
         'type': {'type': 'function', '_funcname': '_methListSort',
                  'args': (
                      {'name': 'reverse', 'type': 'bool', 'desc': 'Sort the list in reverse order.',
                       'default': False},
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'index', 'desc': 'Return a single field from the list by index.',
         'type': {'type': 'function', '_funcname': '_methListIndex',
                  'args': (
                      {'name': 'valu', 'type': 'int', 'desc': 'The list index value.', },
                  ),
                  'returns': {'type': 'any', 'desc': 'The item present in the list at the index position.', }}},
        {'name': 'length', 'desc': 'Get the length of the list. This is deprecated; please use ``.size()`` instead.',
         'type': {'type': 'function', '_funcname': '_methListLength',
                  'returns': {'type': 'int', 'desc': 'The size of the list.', }}},
        {'name': 'append', 'desc': 'Append a value to the list.',
         'type': {'type': 'function', '_funcname': '_methListAppend',
                  'args': (
                      {'name': 'valu', 'type': 'any', 'desc': 'The item to append to the list.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'reverse', 'desc': 'Reverse the order of the list in place',
         'type': {'type': 'function', '_funcname': '_methListReverse',
                  'returns': {'type': 'null', }}},
        {'name': 'slice', 'desc': '''
            Get a slice of the list.

            Examples:
                Slice from index to 1 to 5::

                    $x=(f, o, o, b, a, r)
                    $y=$x.slice(1,5)  // (o, o, b, a)

                Slice from index 3 to the end of the list::

                    $y=$x.slice(3)  // (b, a, r)
            ''',
         'type': {'type': 'function', '_funcname': 'slice',
                  'args': (
                      {'name': 'start', 'type': 'int', 'desc': 'The starting index.'},
                      {'name': 'end', 'type': 'int', 'default': None,
                       'desc': 'The ending index. If not specified, slice to the end of the list.'},
                  ),
                  'returns': {'type': 'list', 'desc': 'The slice of the list.'}}},

        {'name': 'extend', 'desc': '''
            Extend a list using another iterable.

            Examples:
                Populate a list by extending it with to other lists::

                    $list = $lib.list()

                    $foo = (f, o, o)
                    $bar = (b, a, r)

                    $list.extend($foo)
                    $list.extend($bar)

                    // $list is now (f, o, o, b, a, r)
            ''',
         'type': {'type': 'function', '_funcname': 'extend',
                  'args': (
                      {'name': 'valu', 'type': 'list', 'desc': 'A list or other iterable.'},
                  ),
                  'returns': {'type': 'null'}}},
    )
    _storm_typename = 'list'
    _ismutable = True

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'has': self._methListHas,
            'pop': self._methListPop,
            'size': self._methListSize,
            'sort': self._methListSort,
            'index': self._methListIndex,
            'length': self._methListLength,
            'append': self._methListAppend,
            'reverse': self._methListReverse,

            'slice': self.slice,
            'extend': self.extend,
        }

    async def setitem(self, name, valu):

        indx = await toint(name)

        if valu is undef:
            try:
                self.valu.pop(indx)
            except IndexError:
                pass
            return

        self.valu[indx] = valu

    async def _storm_copy(self):
        item = await s_coro.ornot(self.value)
        return s_msgpack.deepcopy(item, use_list=True)

    async def _derefGet(self, name):
        return await self._methListIndex(name)

    def __len__(self):
        return len(self.valu)

    async def _methListHas(self, valu):
        if valu in self.valu:
            return True

        prim = await toprim(valu)
        if prim == valu:
            return False

        return prim in self.valu

    async def _methListPop(self):
        try:
            return self.valu.pop()
        except IndexError:
            mesg = 'The list is empty.  Nothing to pop.'
            raise s_exc.StormRuntimeError(mesg=mesg)

    async def _methListAppend(self, valu):
        '''
        '''
        self.valu.append(valu)

    async def _methListIndex(self, valu):
        indx = await toint(valu)
        try:
            return self.valu[indx]
        except IndexError as e:
            raise s_exc.StormRuntimeError(mesg=str(e), valurepr=await self.stormrepr(),
                                          len=len(self.valu), indx=indx) from None

    async def _methListReverse(self):
        self.valu.reverse()

    async def _methListLength(self):
        s_common.deprecated('StormType List.length()')
        return len(self)

    async def _methListSort(self, reverse=False):
        reverse = await tobool(reverse, noneok=True)
        try:
            self.valu.sort(reverse=reverse)
        except TypeError as e:
            raise s_exc.StormRuntimeError(mesg=f'Error sorting list: {str(e)}',
                                          valurepr=await self.stormrepr()) from None

    async def _methListSize(self):
        return len(self)

    async def slice(self, start, end=None):
        start = await toint(start)

        if end is None:
            return self.valu[start:]

        end = await toint(end)
        return self.valu[start:end]

    async def extend(self, valu):
        async for item in toiter(valu):
            self.valu.append(item)

    async def value(self):
        return tuple([await toprim(v) for v in self.valu])

    async def iter(self):
        for item in self.valu:
            yield item

    async def stormrepr(self):
        reprs = [await torepr(k) for k in self.valu]
        rval = ', '.join(reprs)
        return f'[{rval}]'

@registry.registerType
class Bool(Prim):
    '''
    Implements the Storm API for a boolean instance.
    '''
    _storm_typename = 'boolean'
    _ismutable = False

    def __str__(self):
        return str(self.value()).lower()

    def __int__(self):
        return int(self.value())

    def __hash__(self):
        return hash((self._storm_typename, self.value()))

@registry.registerType
class Number(Prim):
    '''
    Implements the Storm API for a number instance.
    '''
    _storm_locals = (
        {'name': 'scaleb', 'desc': '''
            Return the number multiplied by 10**other.

            Example:
                Multiply the value by 10**-18::

                    $baz.scaleb(-18)''',
         'type': {'type': 'function', '_funcname': '_methScaleb',
                  'args': (
                      {'name': 'other', 'type': 'int', 'desc': 'The amount to adjust the exponent.', },
                  ),
                  'returns': {'type': 'number', 'desc': 'The exponent adjusted number.', }}},
        {'name': 'toint', 'desc': '''
            Return the number as an integer.

            By default, decimal places will be truncated. Optionally, rounding rules
            can be specified by providing the name of a Python decimal rounding mode
            to the 'rounding' argument.

            Example:
                Round the value stored in $baz up instead of truncating::

                    $baz.toint(rounding=ROUND_UP)''',
         'type': {'type': 'function', '_funcname': '_methToInt',
                  'args': (
                      {'name': 'rounding', 'type': 'str', 'default': None,
                       'desc': 'An optional rounding mode to use.', },
                  ),
                  'returns': {'type': 'int', 'desc': 'The number as an integer.', }}},
        {'name': 'tostr', 'desc': 'Return the number as a string.',
         'type': {'type': 'function', '_funcname': '_methToStr',
                  'returns': {'type': 'str', 'desc': 'The number as a string.', }}},
        {'name': 'tofloat', 'desc': 'Return the number as a float.',
         'type': {'type': 'function', '_funcname': '_methToFloat',
                  'returns': {'type': 'float', 'desc': 'The number as a float.', }}},
    )
    _storm_typename = 'number'
    _ismutable = False

    def __init__(self, valu, path=None):
        try:
            valu = s_common.hugenum(valu)
        except decimal.DecimalException as e:
            mesg = f'Failed to make number from {valu!r}'
            raise s_exc.BadCast(mesg=mesg) from e

        Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'toint': self._methToInt,
            'tostr': self._methToStr,
            'tofloat': self._methToFloat,
            'scaleb': self._methScaleb,
        }

    async def _methScaleb(self, other):
        newv = s_common.hugescaleb(self.value(), await toint(other))
        return Number(newv)

    async def _methToInt(self, rounding=None):
        if rounding is None:
            return int(self.valu)

        try:
            return int(self.valu.quantize(decimal.Decimal('1'), rounding=rounding))
        except TypeError as e:
            raise s_exc.StormRuntimeError(mesg=f'Error rounding number: {str(e)}',
                                          valurepr=await self.stormrepr()) from None

    async def _methToStr(self):
        return str(self.valu)

    async def _methToFloat(self):
        return float(self.valu)

    def __str__(self):
        return str(self.value())

    def __int__(self):
        return int(self.value())

    def __float__(self):
        return float(self.value())

    def __hash__(self):
        return hash((self._storm_typename, self.value()))

    def __eq__(self, othr):
        if isinstance(othr, float):
            othr = s_common.hugenum(othr)
            return self.value() == othr
        elif isinstance(othr, (int, decimal.Decimal)):
            return self.value() == othr
        elif isinstance(othr, Number):
            return self.value() == othr.value()
        return False

    def __lt__(self, othr):
        if isinstance(othr, float):
            othr = s_common.hugenum(othr)
            return self.value() < othr
        elif isinstance(othr, (int, decimal.Decimal)):
            return self.value() < othr
        elif isinstance(othr, Number):
            return self.value() < othr.value()

        mesg = f"comparison not supported between instance of {self.__class__.__name__} and {othr.__class__.__name__}"
        raise TypeError(mesg)

    def __add__(self, othr):
        if isinstance(othr, float):
            othr = s_common.hugenum(othr)
            return Number(s_common.hugeadd(self.value(), othr))
        elif isinstance(othr, (int, decimal.Decimal)):
            return Number(s_common.hugeadd(self.value(), othr))
        elif isinstance(othr, Number):
            return Number(s_common.hugeadd(self.value(), othr.value()))

        mesg = f"'+' not supported between instance of {self.__class__.__name__} and {othr.__class__.__name__}"
        raise TypeError(mesg)

    __radd__ = __add__

    def __sub__(self, othr):
        if isinstance(othr, float):
            othr = s_common.hugenum(othr)
            return Number(s_common.hugesub(self.value(), othr))
        elif isinstance(othr, (int, decimal.Decimal)):
            return Number(s_common.hugesub(self.value(), othr))
        elif isinstance(othr, Number):
            return Number(s_common.hugesub(self.value(), othr.value()))

        mesg = f"'-' not supported between instance of {self.__class__.__name__} and {othr.__class__.__name__}"
        raise TypeError(mesg)

    def __rsub__(self, othr):
        othr = Number(othr)
        return othr.__sub__(self)

    def __mul__(self, othr):
        if isinstance(othr, float):
            othr = s_common.hugenum(othr)
            return Number(s_common.hugemul(self.value(), othr))
        elif isinstance(othr, (int, decimal.Decimal)):
            return Number(s_common.hugemul(self.value(), othr))
        elif isinstance(othr, Number):
            return Number(s_common.hugemul(self.value(), othr.value()))

        mesg = f"'*' not supported between instance of {self.__class__.__name__} and {othr.__class__.__name__}"
        raise TypeError(mesg)

    __rmul__ = __mul__

    def __truediv__(self, othr):
        if isinstance(othr, float):
            othr = s_common.hugenum(othr)
            return Number(s_common.hugediv(self.value(), othr))
        elif isinstance(othr, (int, decimal.Decimal)):
            return Number(s_common.hugediv(self.value(), othr))
        elif isinstance(othr, Number):
            return Number(s_common.hugediv(self.value(), othr.value()))

        mesg = f"'/' not supported between instance of {self.__class__.__name__} and {othr.__class__.__name__}"
        raise TypeError(mesg)

    def __rtruediv__(self, othr):
        othr = Number(othr)
        return othr.__truediv__(self)

    def __pow__(self, othr):
        if isinstance(othr, float):
            othr = s_common.hugenum(othr)
            return Number(s_common.hugepow(self.value(), othr))
        elif isinstance(othr, (int, decimal.Decimal)):
            return Number(s_common.hugepow(self.value(), othr))
        elif isinstance(othr, Number):
            return Number(s_common.hugepow(self.value(), othr.value()))

        mesg = f"'**' not supported between instance of {self.__class__.__name__} and {othr.__class__.__name__}"
        raise TypeError(mesg)

    __rpow__ = __pow__

    async def stormrepr(self):
        return str(self.value())

@registry.registerLib
class LibUser(Lib):
    '''
    A Storm Library for interacting with data about the current user.
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'Get the name of the current runtime user.',
         'type': {'type': 'function', '_funcname': '_libUserName',
                  'returns': {'type': 'str', 'desc': 'The username.', }}},
        {'name': 'allowed', 'desc': 'Check if the current user has a given permission.',
         'type': {'type': 'function', '_funcname': '_libUserAllowed',
                  'args': (
                      {'name': 'permname', 'type': 'str', 'desc': 'The permission string to check.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The authgate iden.', 'default': None, },
                      {'name': 'default', 'type': 'boolean', 'desc': 'The default value.', 'default': False, },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the user has the requested permission, false otherwise.', }}},
        {'name': 'vars', 'desc': 'Get a Hive dictionary representing the current users persistent variables.',
         'type': 'storm:hive:dict', },
        {'name': 'profile', 'desc': 'Get a Hive dictionary representing the current users profile information.',
         'type': 'storm:hive:dict', },
        {'name': 'iden', 'desc': 'The user GUID for the current storm user.', 'type': 'str'},
    )
    _storm_lib_path = ('user', )

    def getObjLocals(self):
        return {
            'name': self._libUserName,
            'iden': self.runt.user.iden,
            'allowed': self._libUserAllowed,
        }

    def addLibFuncs(self):
        super().addLibFuncs()
        self.locls.update({
            'vars': StormHiveDict(self.runt, self.runt.user.vars),
            'json': UserJson(self.runt, self.runt.user.iden),
            'profile': StormHiveDict(self.runt, self.runt.user.profile),
        })

    async def _libUserName(self):
        return self.runt.user.name

    async def _libUserAllowed(self, permname, gateiden=None, default=False):
        permname = await toprim(permname)
        gateiden = await tostr(gateiden, noneok=True)
        default = await tobool(default)

        perm = permname.split('.')
        return self.runt.user.allowed(perm, gateiden=gateiden, default=default)

@registry.registerLib
class LibGlobals(Lib):
    '''
    A Storm Library for interacting with global variables which are persistent across the Cortex.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get a Cortex global variables.',
         'type': {'type': 'function', '_funcname': '_methGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the variable.', },
                      {'name': 'default', 'type': 'prim', 'default': None,
                       'desc': 'Default value to return if the variable is not set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The variable value.', }}},
        {'name': 'pop', 'desc': 'Delete a variable value from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methPop',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the variable.', },
                      {'name': 'default', 'type': 'prim', 'default': None,
                       'desc': 'Default value to return if the variable is not set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The variable value.', }}},
        {'name': 'set', 'desc': 'Set a variable value in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methSet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the variable to set.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The value to set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The variable value.', }}},
        {'name': 'list', 'desc': 'Get a list of variable names and values.',
         'type': {'type': 'function', '_funcname': '_methList',
                  'returns': {'type': 'list',
                              'desc': 'A list of tuples with variable names and values that the user can access.', }}},
    )
    _storm_lib_path = ('globals', )

    def __init__(self, runt, name):
        Lib.__init__(self, runt, name)

    def getObjLocals(self):
        return {
            'get': self._methGet,
            'pop': self._methPop,
            'set': self._methSet,
            'list': self._methList,
        }

    def _reqStr(self, name):
        if not isinstance(name, str):
            mesg = 'The name of a persistent variable must be a string.'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name)

    async def _methGet(self, name, default=None):
        self._reqStr(name)

        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('globals', 'get', name), None),)
        todo = s_common.todo('getStormVar', name, default=default)
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methPop(self, name, default=None):
        self._reqStr(name)
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('globals', 'pop', name), None),)
        todo = s_common.todo('popStormVar', name, default=default)
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methSet(self, name, valu):
        self._reqStr(name)
        valu = await toprim(valu)
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('globals', 'set', name), None),)
        todo = s_common.todo('setStormVar', name, valu)
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methList(self):
        ret = []

        todo = ('itemsStormVar', (), {})

        async for key, valu in self.runt.dyniter('cortex', todo):
            if allowed(('globals', 'get', key)):
                ret.append((key, valu))
        return ret

@registry.registerType
class StormHiveDict(Prim):
    '''
    A Storm Primitive representing a HiveDict.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get the named value from the HiveDict.',
         'type': {'type': 'function', '_funcname': '_get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the value.', },
                      {'name': 'default', 'type': 'prim', 'default': None,
                       'desc': 'The default value to return if the name is not set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'pop', 'desc': 'Remove a value out of the HiveDict.',
         'type': {'type': 'function', '_funcname': '_pop',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the value.', },
                      {'name': 'default', 'type': 'prim', 'default': None,
                       'desc': 'The default value to return if the name is not set.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'set', 'desc': 'Set a value in the HiveDict.',
         'type': {'type': 'function', '_funcname': '_set',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the value to set', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The value to store in the HiveDict', },
                  ),
                  'returns': {'type': ['null', 'prim'],
                              'desc': 'Old value of the dictionary if the value was previously set, or none.', }}},
        {'name': 'list', 'desc': 'List the keys and values in the HiveDict.',
         'type': {'type': 'function', '_funcname': '_list',
                  'returns': {'type': 'list', 'desc': 'A list of tuples containing key, value pairs.', }}},
    )
    _storm_typename = 'storm:hive:dict'
    _ismutable = True

    def __init__(self, runt, info):
        Prim.__init__(self, None)
        self.runt = runt
        self.info = info
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._get,
            'pop': self._pop,
            'set': self._set,
            'list': self._list,
        }

    async def _get(self, name, default=None):
        return self.info.get(name, default)

    async def _pop(self, name, default=None):
        return await self.info.pop(name, default)

    async def _set(self, name, valu):
        if not isinstance(name, str):
            mesg = 'The name of a variable must be a string.'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name)

        valu = await toprim(valu)

        return await self.info.set(name, valu)

    def _list(self):
        return list(self.info.items())

    async def iter(self):
        for item in list(self.info.items()):
            yield item

    def value(self):
        return self.info.pack()

@registry.registerLib
class LibVars(Lib):
    '''
    A Storm Library for interacting with runtime variables.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get the value of a variable from the current Runtime.',
         'type': {'type': 'function', '_funcname': '_libVarsGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the variable to get.', },
                      {'name': 'defv', 'type': 'prim', 'default': None,
                       'desc': 'The default value returned if the variable is not set in the runtime.', },
                  ),
                  'returns': {'type': 'any', 'desc': 'The value of the variable.', }}},
        {'name': 'del', 'desc': 'Unset a variable in the current Runtime.',
         'type': {'type': 'function', '_funcname': '_libVarsDel',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The variable name to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'set', 'desc': 'Set the value of a variable in the current Runtime.',
         'type': {'type': 'function', '_funcname': '_libVarsSet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the variable to set.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The value to set the variable too.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of variables from the current Runtime.',
         'type': {'type': 'function', '_funcname': '_libVarsList',
                  'returns': {'type': 'list',
                              'desc': 'A list of variable names and their values for the current Runtime.', }}},
    )
    _storm_lib_path = ('vars',)

    def getObjLocals(self):
        return {
            'get': self._libVarsGet,
            'set': self._libVarsSet,
            'del': self._libVarsDel,
            'list': self._libVarsList,
        }

    async def _libVarsGet(self, name, defv=None):
        return self.runt.getVar(name, defv=defv)

    async def _libVarsSet(self, name, valu):
        await self.runt.setVar(name, valu)

    async def _libVarsDel(self, name):
        await self.runt.popVar(name)

    async def _libVarsList(self):
        return list(self.runt.vars.items())

@registry.registerType
class Query(Prim):
    '''
    A storm primitive representing an embedded query.
    '''
    _storm_locals = (
        {'name': 'exec', 'desc': '''
            Execute the Query in a sub-runtime.

            Notes:
                The ``.exec()`` method can return a value if the Storm query
                contains a ``return( ... )`` statement in it.''',
         'type': {'type': 'function', '_funcname': '_methQueryExec',
                  'returns': {'type': ['null', 'any'],
                              'desc': 'A value specified with a return statement, or none.', }}},
        {'name': 'size',
         'desc': 'Execute the Query in a sub-runtime and return the number of nodes yielded.',
         'type': {'type': 'function', '_funcname': '_methQuerySize',
                  'args': (
                      {'name': 'limit', 'type': 'int', 'default': 1000,
                       'desc': 'Limit the maximum number of nodes produced by the query.', },
                  ),
                  'returns': {'type': 'int',
                              'desc': 'The number of nodes yielded by the query.', }}},
    )

    _storm_typename = 'storm:query'

    def __init__(self, text, varz, runt, path=None):

        text = text.strip()

        Prim.__init__(self, text, path=path)

        self.text = text
        self.varz = varz
        self.runt = runt

        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'exec': self._methQueryExec,
            'size': self._methQuerySize,
        }

    def __str__(self):
        return self.text

    async def _getRuntGenr(self):
        opts = {'vars': self.varz}
        query = await self.runt.getStormQuery(self.text)
        async with self.runt.getSubRuntime(query, opts=opts) as runt:
            async for item in runt.execute():
                yield item

    async def nodes(self):
        async with s_common.aclosing(self._getRuntGenr()) as genr:
            async for node, path in genr:
                yield node

    async def iter(self):
        async for node, path in self._getRuntGenr():
            yield Node(node)

    async def _methQueryExec(self):
        logger.info(f'Executing storm query via exec() {{{self.text}}} as [{self.runt.user.name}]')
        try:
            async for item in self._getRuntGenr():
                await asyncio.sleep(0)
        except s_stormctrl.StormReturn as e:
            return e.item
        except asyncio.CancelledError:  # pragma: no cover
            raise

    async def _methQuerySize(self, limit=1000):
        limit = await toint(limit)

        logger.info(f'Executing storm query via size(limit={limit}) {{{self.text}}} as [{self.runt.user.name}]')
        size = 0
        try:
            async for item in self._getRuntGenr():
                size += 1
                if size >= limit:
                    break
                await asyncio.sleep(0)

        except s_stormctrl.StormReturn as e:
            pass
        except asyncio.CancelledError:  # pragma: no cover
            raise
        return size

    async def stormrepr(self):
        return f'{self._storm_typename}: "{self.text}"'

@registry.registerType
class NodeProps(Prim):
    # TODO How to document setitem ?
    '''
    A Storm Primitive representing the properties on a Node.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get a specific property value by name.',
         'type': {'type': 'function', '_funcname': 'get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the property to return.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'set', 'desc': 'Set a specific property value by name.',
         'type': {'type': 'function', '_funcname': 'set',
                  'args': (
                      {'name': 'prop', 'type': 'str', 'desc': 'The name of the property to set.'},
                      {'name': 'valu', 'type': 'prim', 'desc': 'The value to set the property to.'}
                  ),
                  'returns': {'type': 'prim', 'desc': 'The set value.'}}},
        {'name': 'list', 'desc': 'List the properties and their values from the ``$node``.',
         'type': {'type': 'function', '_funcname': 'list',
                  'returns': {'type': 'list', 'desc': 'A list of (name, value) tuples.', }}},
    )
    _storm_typename = 'storm:node:props'
    _ismutable = True

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self.get,
            'set': self.set,
            'list': self.list,
        }

    async def _derefGet(self, name):
        return self.valu.get(name)

    async def setitem(self, name, valu):
        '''
        Set a property on a Node.

        Args:
            name (str): The name of the property to set.
            valu: The value being set.

        Raises:
            s_exc:NoSuchProp: If the property being set is not valid for the node.
            s_exc.BadTypeValu: If the value of the proprerty fails to normalize.
        '''
        name = await tostr(name)
        valu = await toprim(valu)
        return await self.valu.set(name, valu)

    async def iter(self):
        # Make copies of property values since array types are mutable
        items = tuple((key, copy.deepcopy(valu)) for key, valu in self.valu.props.items())
        for item in items:
            yield item

    async def set(self, prop, valu):
        formprop = self.valu.form.prop(prop)
        if formprop is None:
            mesg = f'No prop {self.valu.form.name}:{prop}'
            raise s_exc.NoSuchProp(mesg=mesg, name=prop, form=self.valu.form.name)
        gateiden = self.valu.snap.wlyr.iden
        confirm(('node', 'prop', 'set', formprop.full), gateiden=gateiden)
        return await self.valu.set(prop, valu)

    @stormfunc(readonly=True)
    async def get(self, name):
        return self.valu.get(name)

    @stormfunc(readonly=True)
    async def list(self):
        return list(self.valu.props.items())

    @stormfunc(readonly=True)
    def value(self):
        return dict(self.valu.props)

@registry.registerType
class NodeData(Prim):
    '''
    A Storm Primitive representing the NodeData stored for a Node.
    '''
    _storm_locals = (
        {'name': 'has', 'desc': 'Check if the Node data has the given key set on it',
         'type': {'type': 'function', '_funcname': '_hasNodeData',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the data to check for.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the key is found, otherwise false.', }}},
        {'name': 'get', 'desc': 'Get the Node data for a given name for the Node.',
         'type': {'type': 'function', '_funcname': '_getNodeData',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the data to get.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The stored node data.', }}},
        {'name': 'pop', 'desc': ' Pop (remove) a the Node data from the Node.',
         'type': {'type': 'function', '_funcname': '_popNodeData',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the data to remove from the node.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The data removed.', }}},
        {'name': 'set', 'desc': 'Set the Node data for a given name on the Node.',
         'type': {'type': 'function', '_funcname': '_setNodeData',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the data.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The data to store.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of the Node data names on the Node.',
         'type': {'type': 'function', '_funcname': '_listNodeData',
                  'returns': {'type': 'list', 'desc': 'List of the names of values stored on the node.', }}},
        {'name': 'load',
         'desc': 'Load the Node data onto the Node so that the Node data is packed and returned by the runtime.',
         'type': {'type': 'function', '_funcname': '_loadNodeData',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the data to load.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'cacheget',
         'desc': 'Retrieve data stored with cacheset() if it was stored more recently than the asof argument.',
         'type': {'type': 'function', '_funcname': 'cacheget',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the data to load.', },
                      {'name': 'asof', 'type': 'time', 'default': 'now', 'desc': 'The max cache age.'},
                  ),
                  'returns': {'type': 'prim', 'desc': 'The cached value or null.'}}},
        {'name': 'cacheset',
         'desc': 'Set a node data value with an envelope that tracks time for cache use.',
         'type': {'type': 'function', '_funcname': 'cacheset',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the data to set.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The data to store.', },
                  ),
                  'returns': {'type': 'null', }}},
    )
    _storm_typename = 'storm:node:data'
    _ismutable = True

    def __init__(self, node, path=None):

        Prim.__init__(self, node, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._getNodeData,
            'set': self._setNodeData,
            'has': self._hasNodeData,
            'pop': self._popNodeData,
            'list': self._listNodeData,
            'load': self._loadNodeData,
            'cacheget': self.cacheget,
            'cacheset': self.cacheset,
        }

    @stormfunc(readonly=True)
    async def cacheget(self, name, asof='now'):
        envl = await self._getNodeData(name)
        if not envl:
            return None

        timetype = self.valu.snap.core.model.type('time')

        asoftick = timetype.norm(asof)[0]
        if envl.get('asof') >= asoftick:
            return envl.get('data')

        return None

    async def cacheset(self, name, valu):
        envl = {'asof': s_common.now(), 'data': valu}
        return await self._setNodeData(name, envl)

    @stormfunc(readonly=True)
    async def _hasNodeData(self, name):
        name = await tostr(name)
        return await self.valu.hasData(name)

    @stormfunc(readonly=True)
    async def _getNodeData(self, name):
        name = await tostr(name)
        return await self.valu.getData(name)

    async def _setNodeData(self, name, valu):
        name = await tostr(name)
        gateiden = self.valu.snap.wlyr.iden
        confirm(('node', 'data', 'set', name), gateiden=gateiden)
        valu = await toprim(valu)
        s_common.reqjsonsafe(valu)
        return await self.valu.setData(name, valu)

    async def _popNodeData(self, name):
        name = await tostr(name)
        gateiden = self.valu.snap.wlyr.iden
        confirm(('node', 'data', 'pop', name), gateiden=gateiden)
        return await self.valu.popData(name)

    @stormfunc(readonly=True)
    async def _listNodeData(self):
        return [x async for x in self.valu.iterData()]

    @stormfunc(readonly=True)
    async def _loadNodeData(self, name):
        name = await tostr(name)
        valu = await self.valu.getData(name)
        # set the data value into the nodedata dict so it gets sent
        self.valu.nodedata[name] = valu

@registry.registerType
class Node(Prim):
    '''
    Implements the Storm api for a node instance.
    '''
    _storm_locals = (
        {'name': 'form', 'desc': 'Get the form of the Node.',
         'type': {'type': 'function', '_funcname': '_methNodeForm',
                  'returns': {'type': 'str', 'desc': 'The form of the Node.', }}},
        {'name': 'iden', 'desc': 'Get the iden of the Node.',
         'type': {'type': 'function', '_funcname': '_methNodeIden',
                  'returns': {'type': 'str', 'desc': 'The nodes iden.', }}},
        {'name': 'ndef', 'desc': 'Get the form and primary property of the Node.',
         'type': {'type': 'function', '_funcname': '_methNodeNdef',
                  'returns': {'type': 'list', 'desc': 'A tuple of the form and primary property.', }}},
        {'name': 'pack', 'desc': 'Return the serializable/packed version of the Node.',
         'type': {'type': 'function', '_funcname': '_methNodePack',
                  'args': (
                      {'name': 'dorepr', 'type': 'boolean', 'default': False,
                       'desc': 'Include repr information for human readable versions of properties.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A tuple containing the ndef and property bag of the node.', }}},
        {'name': 'repr', 'desc': 'Get the repr for the primary property or secondary property of a Node.',
         'type': {'type': 'function', '_funcname': '_methNodeRepr',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the secondary property to get the repr for.', 'default': None, },
                      {'name': 'defv', 'type': 'str',
                       'desc': 'The default value to return if the secondary property does not exist',
                       'default': None, },
                  ),
                  'returns': {'type': 'str', 'desc': 'The string representation of the requested value.', }}},
        {'name': 'tags', 'desc': '''
         Get a list of the tags on the Node.

         Notes:
            When providing a glob argument, the following rules are used. A single asterisk(*) will replace exactly
            one dot-delimited component of a tag. A double asterisk(**) will replace one or more of any character.
         ''',
         'type': {'type': 'function', '_funcname': '_methNodeTags',
                  'args': (
                      {'name': 'glob', 'type': 'str', 'default': None,
                       'desc': 'A tag glob expression. If this is provided, only tags which match the expression '
                               'are returned.'},
                      {'name': 'leaf', 'type': 'bool', 'default': False,
                       'desc': 'If true, only leaf tags are included in the returned tags.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'A list of tags on the node. '
                              'If a glob match is provided, only matching tags are returned.', }}},
        {'name': 'edges', 'desc': 'Yields the (verb, iden) tuples for this nodes edges.',
         'type': {'type': 'function', '_funcname': '_methNodeEdges',
                  'args': (
                      {'name': 'verb', 'type': 'str', 'desc': 'If provided, only return edges with this verb.',
                       'default': None, },
                      {'name': 'reverse', 'type': 'boolean', 'desc': 'If true, yield edges with this node as the dest rather than source.',
                       'default': False, },
                  ),
                  'returns': {'name': 'Yields', 'type': 'list',
                              'desc': 'A tuple of (verb, iden) values for this nodes edges.', }}},
        {'name': 'addEdge', 'desc': 'Add a light-weight edge.',
         'type': {'type': 'function', '_funcname': '_methNodeAddEdge',
                  'args': (
                      {'name': 'verb', 'type': 'str', 'desc': 'The edge verb to add.'},
                      {'name': 'iden', 'type': 'str', 'desc': 'The node id of the destination node.'},
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delEdge', 'desc': 'Remove a light-weight edge.',
         'type': {'type': 'function', '_funcname': '_methNodeDelEdge',
                  'args': (
                      {'name': 'verb', 'type': 'str', 'desc': 'The edge verb to remove.'},
                      {'name': 'iden', 'type': 'str', 'desc': 'The node id of the destination node to remove.'},
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'globtags', 'desc': 'Get a list of the tag components from a Node which match a tag glob expression.',
         'type': {'type': 'function', '_funcname': '_methNodeGlobTags',
                  'args': (
                      {'name': 'glob', 'type': 'str', 'desc': 'The glob expression to match.', },
                  ),
                  'returns':
                      {'type': 'list',
                       'desc': 'The components of tags which match the wildcard component of a glob expression.', }}},
        {'name': 'difftags', 'desc': 'Get and optionally apply the difference between the current set of tags and another set.',
         'type': {'type': 'function', '_funcname': '_methNodeDiffTags',
                  'args': (
                      {'name': 'tags', 'type': 'list', 'desc': 'The set to compare against.', },
                      {'name': 'prefix', 'type': 'str', 'default': None,
                       'desc': 'An optional prefix to match tags under.', },
                      {'name': 'apply', 'type': 'boolean', 'desc': 'If true, apply the diff.',
                       'default': False, },
                  ),
                  'returns':
                      {'type': 'dict',
                       'desc': 'The tags which have been added/deleted in the new set.', }}},
        {'name': 'isform', 'desc': 'Check if a Node is a given form.',
         'type': {'type': 'function', '_funcname': '_methNodeIsForm',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The form to compare the Node against.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the form matches, false otherwise.', }}},
        {'name': 'value', 'desc': 'Get the value of the primary property of the Node.',
         'type': {'type': 'function', '_funcname': '_methNodeValue',
                  'returns': {'type': 'prim', 'desc': 'The primary property.', }}},
        {'name': 'getByLayer', 'desc': 'Return a dict you can use to lookup which props/tags came from which layers.',
         'type': {'type': 'function', '_funcname': 'getByLayer',
                  'returns': {'type': 'dict', 'desc': 'property / tag lookup dictionary.', }}},
        {'name': 'getStorNodes',
         'desc': 'Return a list of "storage nodes" which were fused from the layers to make this node.',
         'type': {'type': 'function', '_funcname': 'getStorNodes',
                  'returns': {'type': 'list', 'desc': 'List of storage node objects.', }}},
    )
    _storm_typename = 'storm:node'
    _ismutable = False

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)

        self.ctors['data'] = self._ctorNodeData
        self.ctors['props'] = self._ctorNodeProps

        self.locls.update(self.getObjLocals())

    def __hash__(self):
        return hash((self._storm_typename, self.valu.iden))

    def getObjLocals(self):
        return {
            'form': self._methNodeForm,
            'iden': self._methNodeIden,
            'ndef': self._methNodeNdef,
            'pack': self._methNodePack,
            'repr': self._methNodeRepr,
            'tags': self._methNodeTags,
            'edges': self._methNodeEdges,
            'addEdge': self._methNodeAddEdge,
            'delEdge': self._methNodeDelEdge,
            'value': self._methNodeValue,
            'globtags': self._methNodeGlobTags,
            'difftags': self._methNodeDiffTags,
            'isform': self._methNodeIsForm,
            'getByLayer': self.getByLayer,
            'getStorNodes': self.getStorNodes,
        }

    async def getStorNodes(self):
        return await self.valu.getStorNodes()

    def getByLayer(self):
        return self.valu.getByLayer()

    def _ctorNodeData(self, path=None):
        return NodeData(self.valu, path=path)

    def _ctorNodeProps(self, path=None):
        return NodeProps(self.valu, path=path)

    @stormfunc(readonly=True)
    async def _methNodePack(self, dorepr=False):
        return self.valu.pack(dorepr=dorepr)

    @stormfunc(readonly=True)
    async def _methNodeEdges(self, verb=None, reverse=False):
        verb = await toprim(verb)
        reverse = await tobool(reverse)

        if reverse:
            async for edge in self.valu.iterEdgesN2(verb=verb):
                yield edge
        else:
            async for edge in self.valu.iterEdgesN1(verb=verb):
                yield edge

    async def _methNodeAddEdge(self, verb, iden):
        verb = await tostr(verb)
        iden = await tobuidhex(iden)

        gateiden = self.valu.snap.wlyr.iden
        confirm(('node', 'edge', 'add', verb), gateiden=gateiden)

        await self.valu.addEdge(verb, iden)

    async def _methNodeDelEdge(self, verb, iden):
        verb = await tostr(verb)
        iden = await tobuidhex(iden)

        gateiden = self.valu.snap.wlyr.iden
        confirm(('node', 'edge', 'del', verb), gateiden=gateiden)

        await self.valu.delEdge(verb, iden)

    @stormfunc(readonly=True)
    async def _methNodeIsForm(self, name):
        return self.valu.form.name == name

    @stormfunc(readonly=True)
    async def _methNodeTags(self, glob=None, leaf=False):
        glob = await tostr(glob, noneok=True)
        leaf = await tobool(leaf)

        tags = list(self.valu.tags.keys())
        if leaf:
            _tags = []
            # brute force rather than build a tree.  faster in small sets.
            for tag in sorted((t for t in tags), reverse=True, key=lambda x: len(x)):
                look = tag + '.'
                if any([r.startswith(look) for r in _tags]):
                    continue
                _tags.append(tag)
            tags = _tags

        if glob is not None:
            regx = s_cache.getTagGlobRegx(glob)
            tags = [t for t in tags if regx.fullmatch(t)]
        return tags

    @stormfunc(readonly=True)
    async def _methNodeGlobTags(self, glob):
        glob = await tostr(glob)
        if glob.find('***') != -1:
            mesg = f'Tag globs may not be adjacent: {glob}'
            raise s_exc.BadArg(mesg=mesg)

        tags = list(self.valu.tags.keys())
        regx = s_cache.getTagGlobRegx(glob)
        ret = []
        for tag in tags:
            match = regx.fullmatch(tag)
            if match is not None:
                groups = match.groups()
                # Per discussion: The simple use case of a single match is
                # intuitive for a user to simply loop over as a raw list.
                # In contrast, a glob match which yields multiple matching
                # values would have to be unpacked.
                if len(groups) == 1:
                    ret.append(groups[0])
                else:
                    ret.append(groups)
        return ret

    async def _methNodeDiffTags(self, tags, prefix=None, apply=False):
        tags = set(await toprim(tags))

        if prefix:
            prefix = tuple((await tostr(prefix)).split('.'))
            plen = len(prefix)

            tags = set([prefix + tuple(tag.split('.')) for tag in tags if tag])
            curtags = set()
            for tag in list(self.valu.tags.keys()):
                parts = tuple(tag.split('.'))
                if parts[:plen] == prefix:
                    curtags.add(parts)
        else:
            tags = set([tuple(tag.split('.')) for tag in tags if tag])
            curtags = set([tuple(tag.split('.')) for tag in self.valu.tags.keys()])

        adds = set([tag for tag in tags if tag not in curtags])
        dels = set()
        for cur in curtags:
            clen = len(cur)
            for tag in tags:
                if tag[:clen] == cur:
                    break
            else:
                dels.add(cur)

        adds = ['.'.join(tag) for tag in adds]
        dels = ['.'.join(tag) for tag in dels]
        if apply:
            for tag in adds:
                await self.valu.addTag(tag)

            for tag in dels:
                await self.valu.delTag(tag)

        return {'adds': adds, 'dels': dels}

    @stormfunc(readonly=True)
    async def _methNodeValue(self):
        return self.valu.ndef[1]

    @stormfunc(readonly=True)
    async def _methNodeForm(self):
        return self.valu.ndef[0]

    @stormfunc(readonly=True)
    async def _methNodeNdef(self):
        return self.valu.ndef

    @stormfunc(readonly=True)
    async def _methNodeRepr(self, name=None, defv=None):
        return self.valu.repr(name=name, defv=defv)

    @stormfunc(readonly=True)
    async def _methNodeIden(self):
        return self.valu.iden()

@registry.registerType
class PathMeta(Prim):
    '''
    Put the storm deref/setitem/iter convention on top of path meta information.
    '''
    _storm_typename = 'storm:node:path:meta'
    _ismutable = True

    def __init__(self, path):
        Prim.__init__(self, None, path=path)

    async def deref(self, name):
        return self.path.metadata.get(name)

    async def setitem(self, name, valu):
        if valu is undef:
            self.path.metadata.pop(name, None)
            return
        self.path.meta(name, valu)

    async def iter(self):
        # prevent "edit while iter" issues
        for item in list(self.path.metadata.items()):
            yield item

@registry.registerType
class PathVars(Prim):
    '''
    Put the storm deref/setitem/iter convention on top of path variables.
    '''
    _storm_typename = 'storm:node:path:vars'
    _ismutable = True

    def __init__(self, path):
        Prim.__init__(self, None, path=path)

    async def deref(self, name):

        valu = self.path.getVar(name)
        if valu is not s_common.novalu:
            return valu

        mesg = f'No var with name: {name}.'
        raise s_exc.StormRuntimeError(mesg=mesg)

    async def setitem(self, name, valu):
        if valu is undef:
            await self.path.popVar(name)
            return
        await self.path.setVar(name, valu)

    async def iter(self):
        # prevent "edit while iter" issues
        for item in list(self.path.vars.items()):
            yield item

@registry.registerType
class Path(Prim):
    '''
    Implements the Storm API for the Path object.
    '''
    _storm_locals = (
        {'name': 'vars', 'desc': 'The PathVars object for the Path.', 'type': 'storm:node:path:vars', },
        {'name': 'meta', 'desc': 'The PathMeta object for the Path.', 'type': 'storm:node:path:meta', },
        {'name': 'idens', 'desc': 'The list of Node idens which this Path has been forked from during pivot operations.',
         'type': {'type': 'function', '_funcname': '_methPathIdens',
                  'returns': {'type': 'list', 'desc': 'A list of node idens.', }}},
        {'name': 'listvars', 'desc': 'List variables available in the path of a storm query.',
         'type': {'type': 'function', '_funcname': '_methPathListVars',
                  'returns': {'type': 'list',
                              'desc': 'List of tuples containing the name and value of path variables.', }}},
    )
    _storm_typename = 'storm:path'
    _ismutable = True

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update(self.getObjLocals())
        self.locls.update({
            'vars': PathVars(path),
            'meta': PathMeta(path),
        })

    def getObjLocals(self):
        return {
            'idens': self._methPathIdens,
            'listvars': self._methPathListVars,
        }

    async def _methPathIdens(self):
        return [n.iden() for n in self.valu.nodes]

    async def _methPathListVars(self):
        return list(self.path.vars.items())

@registry.registerType
class Text(Prim):
    '''
    A mutable text type for simple text construction.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add text to the Text object.',
         'type': {'type': 'function', '_funcname': '_methTextAdd',
                  'args': (
                      {'name': 'text', 'desc': 'The text to add.', 'type': 'str', },
                      {'name': '**kwargs', 'desc': 'Keyword arguments used to format the text.', 'type': 'any', }
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'str', 'desc': 'Get the text content as a string.',
         'type': {'type': 'function', '_funcname': '_methTextStr',
                  'returns': {'desc': 'The current string of the text object.', 'type': 'str', }}},
    )
    _storm_typename = 'storm:text'
    _ismutable = True

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'add': self._methTextAdd,
            'str': self._methTextStr,
        }

    def __len__(self):
        return len(self.valu)

    async def _methTextAdd(self, text, **kwargs):
        text = await kwarg_format(text, **kwargs)
        self.valu += text

    async def _methTextStr(self):
        return self.valu

@registry.registerLib
class LibStats(Lib):
    '''
    A Storm Library for statistics related functionality.
    '''
    _storm_locals = (
        {'name': 'tally', 'desc': 'Get a Tally object.',
         'type': {'type': 'function', '_funcname': 'tally',
                  'returns': {'type': 'storm:stat:tally', 'desc': 'A new tally object.', }}},
    )
    _storm_lib_path = ('stats',)

    def getObjLocals(self):
        return {
            'tally': self.tally,
        }

    async def tally(self):
        return StatTally(path=self.path)

@registry.registerType
class StatTally(Prim):
    '''
    A tally object.

    An example of using it::

        $tally = $lib.stats.tally()

        $tally.inc(foo)

        for $name, $total in $tally {
            $doStuff($name, $total)
        }

    '''
    _storm_typename = 'storm:stat:tally'
    _storm_locals = (
        {'name': 'inc', 'desc': 'Increment a given counter.',
         'type': {'type': 'function', '_funcname': 'inc',
                  'args': (
                      {'name': 'name', 'desc': 'The name of the counter to increment.', 'type': 'str', },
                      {'name': 'valu', 'desc': 'The value to increment the counter by.', 'type': 'int', 'default': 1, },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get the value of a given counter.',
         'type': {'type': 'function', '_funcname': 'get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the counter to get.', },
                  ),
                  'returns': {'type': 'int',
                              'desc': 'The value of the counter, or 0 if the counter does not exist.', }}},
        {'name': 'sorted', 'desc': 'Get a list of (counter, value) tuples in sorted order.',
         'type': {'type': 'function', '_funcname': 'sorted',
                  'args': (
                      {'name': 'byname', 'desc': 'Sort by counter name instead of value.',
                       'type': 'bool', 'default': False},
                      {'name': 'reverse', 'desc': 'Sort in descending order instead of ascending order.',
                       'type': 'bool', 'default': False},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'List of (counter, value) tuples in sorted order.'}}},
    )
    _ismutable = True

    def __init__(self, path=None):
        Prim.__init__(self, {}, path=path)
        self.counters = collections.defaultdict(int)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'inc': self.inc,
            'get': self.get,
            'sorted': self.sorted,
        }

    async def __aiter__(self):
        for name, valu in self.counters.items():
            yield name, valu

    def __len__(self):
        return len(self.counters)

    async def inc(self, name, valu=1):
        valu = await toint(valu)
        self.counters[name] += valu

    async def get(self, name):
        return self.counters.get(name, 0)

    def value(self):
        return dict(self.counters)

    async def iter(self):
        for item in tuple(self.counters.items()):
            yield item

    async def sorted(self, byname=False, reverse=False):
        if byname:
            return list(sorted(self.counters.items(), reverse=reverse))
        else:
            return list(sorted(self.counters.items(), key=lambda x: x[1], reverse=reverse))

@registry.registerLib
class LibLayer(Lib):
    '''
    A Storm Library for interacting with Layers in the Cortex.
    '''
    _storm_lib_path = ('layer',)
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a layer to the Cortex.',
         'type': {'type': 'function', '_funcname': '_libLayerAdd',
                  'args': (
                      {'name': 'ldef', 'type': 'dict', 'desc': 'The layer definition dictionary.', 'default': None, },
                  ),
                  'returns': {'type': 'storm:layer',
                              'desc': 'A ``storm:layer`` object representing the new layer.', }}},
        {'name': 'del', 'desc': 'Delete a layer from the Cortex.',
         'type': {'type': 'function', '_funcname': '_libLayerDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the layer to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a Layer from the Cortex.',
         'type': {'type': 'function', '_funcname': '_libLayerGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'default': None,
                       'desc': 'The iden of the layer to get. '
                               'If not set, this defaults to the top layer of the current View.', },
                  ),
                  'returns': {'type': 'storm:layer', 'desc': 'The storm layer object.', }}},
        {'name': 'list', 'desc': 'List the layers in a Cortex',
         'type': {'type': 'function', '_funcname': '_libLayerList',
                  'returns': {'type': 'list', 'desc': 'List of ``storm:layer`` objects.', }}},
    )

    def getObjLocals(self):
        return {
            'add': self._libLayerAdd,
            'del': self._libLayerDel,
            'get': self._libLayerGet,
            'list': self._libLayerList,
        }

    async def _libLayerAdd(self, ldef=None):
        if ldef is None:
            ldef = {}
        else:
            ldef = await toprim(ldef)

        ldef['creator'] = self.runt.user.iden

        useriden = self.runt.user.iden

        gatekeys = ((useriden, ('layer', 'add'), None),)
        todo = ('addLayer', (ldef,), {})

        ldef = await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

        return Layer(self.runt, ldef, path=self.path)

    async def _libLayerDel(self, iden):
        todo = s_common.todo('getLayerDef', iden)
        ldef = await self.runt.dyncall('cortex', todo)
        if ldef is None:
            mesg = f'No layer with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        layriden = ldef.get('iden')
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('layer', 'del'), iden),)

        todo = ('delLayer', (layriden,), {})
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _libLayerGet(self, iden=None):

        iden = await tostr(iden, noneok=True)
        if iden is None:
            iden = self.runt.snap.view.layers[0].iden

        ldef = await self.runt.snap.core.getLayerDef(iden=iden)
        if ldef is None:
            mesg = f'No layer with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        return Layer(self.runt, ldef, path=self.path)

    async def _libLayerList(self):
        todo = s_common.todo('getLayerDefs')
        defs = await self.runt.dyncall('cortex', todo)
        return [Layer(self.runt, ldef, path=self.path) for ldef in defs]

@registry.registerType
class Layer(Prim):
    '''
    Implements the Storm api for a layer instance.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The iden of the Layer.', 'type': 'str', },
        {'name': 'set', 'desc': 'Set a arbitrary value in the Layer definition.',
         'type': {'type': 'function', '_funcname': '_methLayerSet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name to set.', },
                      {'name': 'valu', 'type': 'any', 'desc': 'The value to set.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a arbitrary value in the Layer definition.',
         'type': {'type': 'function', '_funcname': '_methLayerGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the value to get.', },
                      {'name': 'defv', 'type': 'prim', 'default': None,
                       'desc': 'The default value returned if the name is not set in the Layer.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The value requested or the default value.', }}},
        {'name': 'pack', 'desc': 'Get the Layer definition.',
         'type': {'type': 'function', '_funcname': '_methLayerPack',
                  'returns': {'type': 'dict', 'desc': 'Dictionary containing the Layer definition.', }}},
        {'name': 'repr', 'desc': 'Get a string representation of the Layer.',
         'type': {'type': 'function', '_funcname': '_methLayerRepr',
                  'returns': {'type': 'str', 'desc': 'A string that can be printed, representing a Layer.', }}},
        {'name': 'edits', 'desc': 'Yield (offs, nodeedits) tuples from the given offset.',
         'type': {'type': 'function', '_funcname': '_methLayerEdits',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'desc': 'Offset to start getting nodeedits from the layer at.',
                       'default': 0, },
                      {'name': 'wait', 'type': 'boolean', 'default': True,
                       'desc': 'If true, wait for new edits, '
                               'otherwise exit the generator when there are no more edits.', },
                      {'name': 'size', 'type': 'int', 'desc': 'The maximum number of nodeedits to yield.',
                       'default': None, },
                  ),
                  'returns': {'name': 'Yields', 'type': 'list',
                              'desc': 'Yields offset, nodeedit tuples from a given offset.', }}},
        {'name': 'addPush', 'desc': 'Configure the layer to push edits to a remote layer/feed.',
         'type': {'type': 'function', '_funcname': '_addPush',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'A telepath URL of the target layer/feed.', },
                      {'name': 'offs', 'type': 'int', 'desc': 'The local layer offset to begin pushing from',
                       'default': 0, },
                  ),
                  'returns': {'type': 'dict', 'desc': 'Dictionary containing the push definition.', }}},
        {'name': 'delPush', 'desc': 'Remove a push config from the layer.',
         'type': {'type': 'function', '_funcname': '_delPush',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the push config to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'addPull', 'desc': 'Configure the layer to pull edits from a remote layer/feed.',
         'type': {'type': 'function', '_funcname': '_addPull',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The telepath URL to a layer/feed.', },
                      {'name': 'offs', 'type': 'int', 'desc': 'The offset to begin from.', 'default': 0, },
                  ),
                  'returns': {'type': 'dict', 'desc': 'Dictionary containing the pull definition.', }}},
        {'name': 'delPull', 'desc': 'Remove a pull config from the layer.',
         'type': {'type': 'function', '_funcname': '_delPull',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the push config to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'getTagCount', 'desc': '''
            Return the number of tag rows in the layer for the given tag and optional form.

            Examples:
                Get the number of ``inet:ipv4`` nodes with the ``$foo.bar`` tag::

                    $count = $lib.layer.get().getTagCount(foo.bar, formname=inet:ipv4)''',
         'type': {'type': 'function', '_funcname': '_methGetTagCount',
                  'args': (
                      {'name': 'tagname', 'type': 'str', 'desc': 'The name of the tag to look up.', },
                      {'name': 'formname', 'type': 'str', 'desc': 'The form to constrain the look up by.',
                       'default': None, },
                  ),
                  'returns': {'type': 'int', 'desc': 'The count of tag rows.', }}},
        {'name': 'getPropCount',
         'desc': 'Get the number of property rows in the layer for the given full form or property name.',
         'type': {'type': 'function', '_funcname': '_methGetPropCount',
                  'args': (
                      {'name': 'propname', 'type': 'str', 'desc': 'The property or form name to look up.', },
                      {'name': 'maxsize', 'type': 'int', 'desc': 'The maximum number of rows to look up.',
                       'default': None, },
                  ),
                  'returns': {'type': 'int', 'desc': 'The count of rows.', }}},
        {'name': 'getFormCounts', 'desc': '''
            Get the formcounts for the Layer.

            Example:
                Get the formcounts for the current Layer::

                    $counts = $lib.layer.get().getFormCounts()''',
         'type': {'type': 'function', '_funcname': '_methGetFormcount',
                  'returns': {'type': 'dict',
                              'desc': 'Dictionary containing form names and the count of the nodes in the Layer.', }}},
        {'name': 'getStorNodes', 'desc': '''
            Get buid, sode tuples representing the data stored in the layer.

            Notes:
                The storage nodes represent **only** the data stored in the layer
                and may not represent whole nodes.
            ''',
         'type': {'type': 'function', '_funcname': 'getStorNodes',
                  'returns': {'name': 'Yields', 'type': 'list', 'desc': 'Tuple of buid, sode values.', }}},
        {'name': 'getMirrorStatus', 'desc': '''
            Return a dictionary of the mirror synchronization status for the layer.
            ''',
         'type': {'type': 'function', '_funcname': 'getMirrorStatus',
                  'returns': {'type': 'dict', 'desc': 'An info dictionary describing mirror sync status.', }}},

        {'name': 'verify', 'desc': '''
            Verify consistency between the node storage and indexes in the given layer.

            Example:
                Get all messages about consistency issues in the default layer::

                    for $mesg in $lib.layer.get().verify() {
                        $lib.print($mesg)
                    }

            Notes:
                The config format argument and message format yielded by this API is considered BETA
                and may be subject to change! The formats will be documented when the convention stabilizes.
            ''',
         'type': {'type': 'function', '_funcname': 'verify',
                  'args': (
                      {'name': 'config', 'type': 'dict', 'desc': 'The scan config to use (default all enabled).', 'default': None},
                  ),
                  'returns': {'name': 'Yields', 'type': 'list',
                              'desc': 'Yields messages describing any index inconsistencies.', }}},
        {'name': 'getStorNode', 'desc': '''
            Retrieve the raw storage node for the specified node id.
            ''',
         'type': {'type': 'function', '_funcname': 'getStorNode',
                  'args': (
                      {'name': 'nodeid', 'type': 'str', 'desc': 'The hex string of the node id.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The storage node dictionary.', }}},
        {'name': 'liftByProp', 'desc': '''
            Lift and yield nodes with the property and optional value set within the layer.

            Example:
                Yield all nodes with the property ``ou:org:name`` set in the top layer::

                    yield $lib.layer.get().liftByProp(ou:org:name)

                Yield all nodes with the property ``ou:org:name=woot`` in the top layer::

                    yield $lib.layer.get().liftByProp(ou:org:name, woot)

                Yield all nodes with the property ``ou:org:name^=woot`` in the top layer::

                    yield $lib.layer.get().liftByProp(ou:org:name, woot, "^=")

            ''',
         'type': {'type': 'function', '_funcname': 'liftByProp',
                  'args': (
                      {'name': 'propname', 'type': 'str', 'desc': 'The full property name to lift by.'},
                      {'name': 'propvalu', 'type': 'obj', 'desc': 'The value for the property.', 'default': None},
                      {'name': 'propcmpr', 'type': 'str', 'desc': 'The comparison operation to use on the value.', 'default': '='},
                  ),
                  'returns': {'name': 'Yields', 'type': 'storm:node',
                              'desc': 'Yields nodes.', }}},
        {'name': 'liftByTag', 'desc': '''
            Lift and yield nodes with the tag set within the layer.

            Example:
                Yield all nodes with the tag #foo set in the layer::

                    yield $lib.layer.get().liftByTag(foo)

                Yield all inet:fqdn with the tag #foo set in the layer::

                    yield $lib.layer.get().liftByTag(foo, inet:fqdn)

            ''',
         'type': {'type': 'function', '_funcname': 'liftByTag',
                  'args': (
                      {'name': 'tagname', 'type': 'str', 'desc': 'The tag name to lift by.'},
                      {'name': 'formname', 'type': 'str', 'desc': 'The optional form to lift.', 'default': None},
                  ),
                  'returns': {'name': 'Yields', 'type': 'storm:node',
                              'desc': 'Yields nodes.', }}},
    )
    _storm_typename = 'storm:layer'
    _ismutable = False

    def __init__(self, runt, ldef, path=None):
        Prim.__init__(self, ldef, path=path)
        self.runt = runt

        # hide any passwd in push URLs
        pushs = ldef.get('pushs')
        if pushs is not None:
            for pdef in pushs.values():
                url = pdef.get('url')
                if url is not None:
                    pdef['url'] = s_urlhelp.sanitizeUrl(url)

        pulls = ldef.get('pulls')
        if pulls is not None:
            for pdef in pulls.values():
                url = pdef.get('url')
                if url is not None:
                    pdef['url'] = s_urlhelp.sanitizeUrl(url)

        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu.get('iden')

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

    def getObjLocals(self):
        return {
            'set': self._methLayerSet,
            'get': self._methLayerGet,
            'pack': self._methLayerPack,
            'repr': self._methLayerRepr,
            'edits': self._methLayerEdits,
            'verify': self.verify,
            'addPush': self._addPush,
            'delPush': self._delPush,
            'addPull': self._addPull,
            'delPull': self._delPull,
            'liftByTag': self.liftByTag,
            'liftByProp': self.liftByProp,
            'getTagCount': self._methGetTagCount,
            'getPropCount': self._methGetPropCount,
            'getFormCounts': self._methGetFormcount,
            'getStorNode': self.getStorNode,
            'getStorNodes': self.getStorNodes,
            'getMirrorStatus': self.getMirrorStatus,
        }

    async def liftByTag(self, tagname, formname=None):
        tagname = await tostr(tagname)
        formname = await tostr(formname, noneok=True)

        if formname is not None and self.runt.snap.core.model.form(formname) is None:
            mesg = f'The form {formname} does not exist.'
            raise s_exc.NoSuchForm(mesg=mesg)

        iden = self.valu.get('iden')
        layr = self.runt.snap.core.getLayer(iden)

        await self.runt.reqUserCanReadLayer(iden)
        async for _, buid, sode in layr.liftByTag(tagname, form=formname):
            yield await self.runt.snap._joinStorNode(buid, {iden: sode})

    async def liftByProp(self, propname, propvalu=None, propcmpr='='):

        propname = await tostr(propname)
        propvalu = await toprim(propvalu)
        propcmpr = await tostr(propcmpr)

        iden = self.valu.get('iden')
        layr = self.runt.snap.core.getLayer(iden)

        await self.runt.reqUserCanReadLayer(iden)

        prop = self.runt.snap.core.model.prop(propname)
        if prop is None:
            mesg = f'The property {propname} does not exist.'
            raise s_exc.NoSuchProp(mesg=mesg)

        if prop.isform:
            liftform = prop.name
            liftprop = None
        elif prop.isuniv:
            liftform = None
            liftprop = prop.name
        else:
            liftform = prop.form.name
            liftprop = prop.name

        if propvalu is None:
            async for _, buid, sode in layr.liftByProp(liftform, liftprop):
                yield await self.runt.snap._joinStorNode(buid, {iden: sode})
            return

        norm, info = prop.type.norm(propvalu)
        cmprvals = prop.type.getStorCmprs(propcmpr, norm)
        async for _, buid, sode in layr.liftByPropValu(liftform, liftprop, cmprvals):
            yield await self.runt.snap._joinStorNode(buid, {iden: sode})

    async def getMirrorStatus(self):
        iden = self.valu.get('iden')
        layr = self.runt.snap.core.getLayer(iden)
        return await layr.getMirrorStatus()

    async def _addPull(self, url, offs=0):
        url = await tostr(url)
        offs = await toint(offs)

        useriden = self.runt.user.iden
        layriden = self.valu.get('iden')

        if not self.runt.isAdmin(gateiden=layriden):
            mesg = '$layr.addPull() requires admin privs on the layer.'
            raise s_exc.AuthDeny(mesg=mesg)

        scheme = url.split('://')[0]
        self.runt.confirm(('lib', 'telepath', 'open', scheme))

        async with await s_telepath.openurl(url):
            pass

        pdef = {
            'url': url,
            'offs': offs,
            'user': useriden,
            'time': s_common.now(),
            'iden': s_common.guid(),
        }
        todo = s_common.todo('addLayrPull', layriden, pdef)
        await self.runt.dyncall('cortex', todo)
        return pdef

    async def _delPull(self, iden):
        iden = await tostr(iden)

        layriden = self.valu.get('iden')
        if not self.runt.isAdmin(gateiden=layriden):
            mesg = '$layr.delPull() requires admin privs on the top layer.'
            raise s_exc.AuthDeny(mesg=mesg)

        todo = s_common.todo('delLayrPull', layriden, iden)
        await self.runt.dyncall('cortex', todo)

    async def _addPush(self, url, offs=0):
        url = await tostr(url)
        offs = await toint(offs)

        useriden = self.runt.user.iden
        layriden = self.valu.get('iden')

        if not self.runt.isAdmin(gateiden=layriden):
            mesg = '$layer.addPush() requires admin privs on the layer.'
            raise s_exc.AuthDeny(mesg=mesg)

        scheme = url.split('://')[0]
        self.runt.confirm(('lib', 'telepath', 'open', scheme))

        async with await s_telepath.openurl(url):
            pass

        pdef = {
            'url': url,
            'offs': offs,
            'user': useriden,
            'time': s_common.now(),
            'iden': s_common.guid(),
        }
        todo = s_common.todo('addLayrPush', layriden, pdef)
        await self.runt.dyncall('cortex', todo)
        return pdef

    async def _delPush(self, iden):
        iden = await tostr(iden)
        layriden = self.valu.get('iden')

        if not self.runt.isAdmin(gateiden=layriden):
            mesg = '$layer.delPush() requires admin privs on the layer.'
            raise s_exc.AuthDeny(mesg=mesg)

        todo = s_common.todo('delLayrPush', layriden, iden)
        await self.runt.dyncall('cortex', todo)

    @stormfunc(readonly=True)
    async def _methGetFormcount(self):
        layriden = self.valu.get('iden')
        await self.runt.reqUserCanReadLayer(layriden)
        layr = self.runt.snap.core.getLayer(layriden)
        return await layr.getFormCounts()

    async def _methGetTagCount(self, tagname, formname=None):
        tagname = await tostr(tagname)
        formname = await tostr(formname, noneok=True)
        layriden = self.valu.get('iden')
        await self.runt.reqUserCanReadLayer(layriden)
        layr = self.runt.snap.core.getLayer(layriden)
        return await layr.getTagCount(tagname, formname=formname)

    async def _methGetPropCount(self, propname, maxsize=None):
        propname = await tostr(propname)
        maxsize = await toint(maxsize, noneok=True)

        prop = self.runt.snap.core.model.prop(propname)
        if prop is None:
            mesg = f'No property named {propname}'
            raise s_exc.NoSuchProp(mesg=mesg)

        layriden = self.valu.get('iden')
        await self.runt.reqUserCanReadLayer(layriden)
        layr = self.runt.snap.core.getLayer(layriden)

        if prop.isform:
            return await layr.getPropCount(prop.name, None, maxsize=maxsize)

        if prop.isuniv:
            return await layr.getUnivPropCount(prop.name, maxsize=maxsize)

        return await layr.getPropCount(prop.form.name, prop.name, maxsize=maxsize)

    async def _methLayerEdits(self, offs=0, wait=True, size=None):
        offs = await toint(offs)
        wait = await tobool(wait)
        layriden = self.valu.get('iden')
        gatekeys = ((self.runt.user.iden, ('layer', 'edits', 'read'), layriden),)
        todo = s_common.todo('syncNodeEdits', offs, wait=wait)

        count = 0
        async for item in self.runt.dyniter(layriden, todo, gatekeys=gatekeys):

            yield item

            count += 1
            if size is not None and size == count:
                break

    async def getStorNode(self, nodeid):
        nodeid = await tostr(nodeid)
        layriden = self.valu.get('iden')
        await self.runt.reqUserCanReadLayer(layriden)
        layr = self.runt.snap.core.getLayer(layriden)
        return await layr.getStorNode(s_common.uhex(nodeid))

    async def getStorNodes(self):
        layriden = self.valu.get('iden')
        await self.runt.reqUserCanReadLayer(layriden)
        layr = self.runt.snap.core.getLayer(layriden)
        async for item in layr.getStorNodes():
            yield item

    async def _methLayerGet(self, name, defv=None):
        return self.valu.get(name, defv)

    async def _methLayerSet(self, name, valu):
        name = await tostr(name)

        if name == 'name':
            valu = await tostr(valu)
        elif name == 'desc':
            valu = await tostr(valu)
        elif name == 'logedits':
            valu = await tobool(valu)
        else:
            mesg = f'Layer does not support setting: {name}'
            raise s_exc.BadOptValu(mesg=mesg)

        useriden = self.runt.user.iden
        layriden = self.valu.get('iden')
        gatekeys = ((useriden, ('layer', 'set', name), layriden),)
        todo = s_common.todo('setLayerInfo', name, valu)
        valu = await self.runt.dyncall(layriden, todo, gatekeys=gatekeys)
        self.valu[name] = valu

    async def _methLayerPack(self):
        ldef = copy.deepcopy(self.valu)
        pushs = ldef.get('pushs')
        if pushs is not None:
            for iden, pdef in pushs.items():
                gvar = f'push:{iden}'
                pdef['offs'] = await self.runt.snap.core.getStormVar(gvar, -1)

        pulls = ldef.get('pulls')
        if pulls is not None:
            for iden, pdef in pulls.items():
                gvar = f'push:{iden}'
                pdef['offs'] = await self.runt.snap.core.getStormVar(gvar, -1)

        return ldef

    async def _methLayerRepr(self):
        iden = self.valu.get('iden')
        name = self.valu.get('name', 'unnamed')
        creator = self.valu.get('creator')
        readonly = self.valu.get('readonly')
        return f'Layer: {iden} (name: {name}) readonly: {readonly} creator: {creator}'

    async def verify(self, config=None):

        config = await toprim(config)

        iden = self.valu.get('iden')
        layr = self.runt.snap.core.getLayer(iden)
        async for mesg in layr.verify(config=config):
            yield mesg

@registry.registerLib
class LibView(Lib):
    '''
    A Storm Library for interacting with Views in the Cortex.
    '''
    _storm_lib_path = ('view',)
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a View to the Cortex.',
         'type': {'type': 'function', '_funcname': '_methViewAdd',
                  'args': (
                      {'name': 'layers', 'type': 'list', 'desc': 'A list of layer idens which make up the view.', },
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the view.', 'default': None, }
                  ),
                  'returns': {'type': 'storm:view', 'desc': 'A ``storm:view`` object representing the new View.', }}},
        {'name': 'del', 'desc': 'Delete a View from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methViewDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the View to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a View from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methViewGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'default': None,
                        'desc': 'The iden of the View to get. If not specified, returns the current View.', },
                  ),
                  'returns': {'type': 'storm:view', 'desc': 'The storm view object.', }}},
        {'name': 'list', 'desc': 'List the Views in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methViewList',
                  'args': (
                      {'name': 'deporder', 'type': 'bool', 'default': False,
                        'desc': 'Return the lists in bottom-up dependency order.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'List of ``storm:view`` objects.', }}},
    )

    def getObjLocals(self):
        return {
            'add': self._methViewAdd,
            'del': self._methViewDel,
            'get': self._methViewGet,
            'list': self._methViewList,
        }

    async def _methViewAdd(self, layers, name=None):
        name = await tostr(name, noneok=True)
        layers = await toprim(layers)

        vdef = {
            'creator': self.runt.user.iden,
            'layers': layers
        }

        if name is not None:
            vdef['name'] = name

        useriden = self.runt.user.iden
        gatekeys = [(useriden, ('view', 'add'), None)]

        for layriden in layers:
            gatekeys.append((useriden, ('layer', 'read'), layriden))

        todo = ('addView', (vdef,), {})

        vdef = await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)
        return View(self.runt, vdef, path=self.path)

    async def _methViewDel(self, iden):
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('view', 'del'), iden),)
        todo = ('delView', (iden,), {})
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    @stormfunc(readonly=True)
    async def _methViewGet(self, iden=None):
        if iden is None:
            iden = self.runt.snap.view.iden
        todo = s_common.todo('getViewDef', iden)
        vdef = await self.runt.dyncall('cortex', todo)
        if vdef is None:
            raise s_exc.NoSuchView(mesg=iden)

        return View(self.runt, vdef, path=self.path)

    @stormfunc(readonly=True)
    async def _methViewList(self, deporder=False):
        deporder = await tobool(deporder)
        viewdefs = await self.runt.snap.core.getViewDefs(deporder=deporder)
        return [View(self.runt, vdef, path=self.path) for vdef in viewdefs]

@registry.registerType
class View(Prim):
    '''
    Implements the Storm api for a View instance.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The iden of the View.', 'type': 'str', },
        {'name': 'layers', 'desc': 'The ``storm:layer`` objects associated with the ``storm:view``.', 'type': 'list', },
        {'name': 'parent', 'desc': 'The parent View. Will be ``$lib.null`` if the view is not a fork.', 'type': 'str'},
        {'name': 'triggers', 'desc': 'The ``storm:trigger`` objects associated with the ``storm:view``.',
         'type': 'list', },
        {'name': 'set', 'desc': '''
            Set a view configuration option.

            Current runtime updatable view options include:

                name (str)
                    A terse name for the View.

                desc (str)
                    A description of the View.

                parent (str)
                    The parent View iden.

                nomerge (bool)
                    Setting to $lib.true will prevent the layer from being merged.

                layers (list(str))
                    Set the list of layer idens for a non-forked view. Layers are specified
                    in precedence order with the first layer in the list being the write layer.

            To maintain consistency with the view.fork() semantics, setting the "parent"
            option on a view has a few limitations:

                * The view must not already have a parent
                * The view must not have more than 1 layer
         ''',
         'type': {'type': 'function', '_funcname': '_methViewSet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the value to set.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The value to set.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a view configuration option.',
         'type': {'type': 'function', '_funcname': '_methViewGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the value to get.', },
                      {'name': 'defv', 'type': 'prim', 'default': None,
                       'desc': 'The default value returned if the name is not set in the View.', }
                  ),
                  'returns': {'type': 'prim', 'desc': 'The value requested or the default value.', }}},
        {'name': 'fork', 'desc': 'Fork a View in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methViewFork',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the new view.', 'default': None, },
                  ),
                  'returns': {'type': 'storm:view', 'desc': 'The ``storm:view`` object for the new View.', }}},
        {'name': 'pack', 'desc': 'Get the View definition.',
         'type': {'type': 'function', '_funcname': '_methViewPack',
                  'returns': {'type': 'dict', 'desc': 'Dictionary continaing the View definition.', }}},
        {'name': 'repr', 'desc': 'Get a string representation of the View.',
         'type': {'type': 'function', '_funcname': '_methViewRepr',
                  'returns': {'type': 'list', 'desc': 'A list of lines that can be printed, representing a View.', }}},
        {'name': 'merge', 'desc': 'Merge a forked View back into its parent View.',
         'type': {'type': 'function', '_funcname': '_methViewMerge',
                  'args': (
                    {'name': 'force', 'type': 'boolean', 'default': False, 'desc': 'Force the view to merge if possible.'},
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'getEdges', 'desc': 'Get node information for Edges in the View.',
         'type': {'type': 'function', '_funcname': '_methGetEdges',
                  'args': (
                      {'name': 'verb', 'type': 'str', 'desc': 'The name of the Edges verb to iterate over.',
                       'default': None, },
                  ),
                  'returns': {'name': 'Yields', 'type': 'list',
                              'desc': 'Yields tuples containing the source iden, verb, and destination iden.', }}},
        {'name': 'wipeLayer', 'desc': 'Delete all nodes and nodedata from the write layer. Triggers will be run.',
         'type': {'type': 'function', '_funcname': '_methWipeLayer',
                  'returns': {'type': 'null', }}},
        {'name': 'addNode', 'desc': '''Transactionally add a single node and all it's properties. If any validation fails, no changes are made.''',
         'type': {'type': 'function', '_funcname': 'addNode',
                  'args': (
                      {'name': 'form', 'type': 'str', 'desc': 'The form name.'},
                      {'name': 'valu', 'type': 'prim', 'desc': 'The primary property value.'},
                      {'name': 'props', 'type': 'dict', 'desc': 'An optional dictionary of props.', 'default': None},
                  ),
                  'returns': {'type': 'storm:node', 'desc': 'The node which may have been just constructed.', }}},
        {'name': 'addNodeEdits', 'desc': 'Add NodeEdits to the view.',
         'type': {'type': 'function', '_funcname': '_methAddNodeEdits',
                  'args': (
                      {'name': 'edits', 'type': 'list', 'desc': 'A list of nodeedits.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'getEdgeVerbs', 'desc': 'Get the Edge verbs which exist in the View.',
         'type': {'type': 'function', '_funcname': '_methGetEdgeVerbs',
                  'returns': {'name': 'Yields', 'type': 'str',
                              'desc': 'Yields the edge verbs used by Layers which make up the View.', }}},
        {'name': 'getFormCounts', 'desc': '''
            Get the formcounts for the View.

            Example:
                Get the formcounts for the current View::

                    $counts = $lib.view.get().getFormCounts()''',
         'type': {'type': 'function', '_funcname': '_methGetFormcount',
                  'returns':
                      {'type': 'dict',
                       'desc': "Dictionary containing form names and the count of the nodes in the View's Layers.", }}},
    )
    _storm_typename = 'storm:view'
    _ismutable = False

    def __init__(self, runt, vdef, path=None):
        Prim.__init__(self, vdef, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())
        self.locls.update({
            'iden': self.valu.get('iden'),
            'parent': self.valu.get('parent'),
            'triggers': [Trigger(self.runt, tdef) for tdef in self.valu.get('triggers')],
            'layers': [Layer(self.runt, ldef, path=self.path) for ldef in self.valu.get('layers')],
        })

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

    def getObjLocals(self):
        return {
            'set': self._methViewSet,
            'get': self._methViewGet,
            'fork': self._methViewFork,
            'pack': self._methViewPack,
            'repr': self._methViewRepr,
            'merge': self._methViewMerge,
            'addNode': self.addNode,
            'getEdges': self._methGetEdges,
            'wipeLayer': self._methWipeLayer,
            'addNodeEdits': self._methAddNodeEdits,
            'getEdgeVerbs': self._methGetEdgeVerbs,
            'getFormCounts': self._methGetFormcount,
        }

    async def addNode(self, form, valu, props=None):
        form = await tostr(form)
        valu = await toprim(valu)
        props = await toprim(props)

        viewiden = self.valu.get('iden')

        view = self.runt.snap.core.getView(viewiden)

        self.runt.layerConfirm(('node', 'add', form))

        for propname in props.keys():
            fullname = f'{form}:{propname}'
            self.runt.layerConfirm(('node', 'prop', 'set', fullname))

        return await self.runt.snap.addNode(form, valu, props=props)

    async def _methAddNodeEdits(self, edits):
        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')
        layriden = self.valu.get('layers')[0].get('iden')

        meta = {'user': useriden}
        todo = s_common.todo('addNodeEdits', edits, meta)

        # ensure the user may make *any* node edits
        gatekeys = ((useriden, ('node',), layriden),)
        await self.runt.dyncall(viewiden, todo, gatekeys=gatekeys)

    @stormfunc(readonly=True)
    async def _methGetFormcount(self):
        todo = s_common.todo('getFormCounts')
        return await self.viewDynCall(todo, ('view', 'read'))

    @stormfunc(readonly=True)
    async def _methGetEdges(self, verb=None):
        verb = await toprim(verb)
        todo = s_common.todo('getEdges', verb=verb)
        async for edge in self.viewDynIter(todo, ('view', 'read')):
            yield edge

    @stormfunc(readonly=True)
    async def _methGetEdgeVerbs(self):
        todo = s_common.todo('getEdgeVerbs')
        async for verb in self.viewDynIter(todo, ('view', 'read')):
            yield verb

    async def viewDynIter(self, todo, perm):
        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')
        gatekeys = ((useriden, perm, viewiden),)
        async for item in self.runt.dyniter(viewiden, todo, gatekeys=gatekeys):
            yield item

    async def viewDynCall(self, todo, perm):
        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')
        gatekeys = ((useriden, perm, viewiden),)
        return await self.runt.dyncall(viewiden, todo, gatekeys=gatekeys)

    @stormfunc(readonly=True)
    async def _methViewGet(self, name, defv=None):
        return self.valu.get(name, defv)

    async def _methViewSet(self, name, valu):

        name = await tostr(name)

        if name == 'name':
            valu = await tostr(valu)
        elif name == 'desc':
            valu = await tostr(valu)
        elif name == 'parent':
            valu = await tostr(valu)
        elif name == 'nomerge':
            valu = await tobool(valu)
        elif name == 'layers':

            view = self.runt.snap.core.getView(self.valu.get('iden'))
            if view is None: # pragma: no cover
                mesg = f'No view with iden: {self.valu.get("iden")}'
                raise s_exc.NoSuchView(mesg=mesg)

            layers = await toprim(valu)
            layers = tuple(str(x) for x in layers)

            for layriden in layers:

                layr = self.runt.snap.core.getLayer(layriden)
                if layr is None:
                    mesg = f'No layer with iden: {layriden}'
                    raise s_exc.NoSuchLayer(mesg=mesg)

                self.runt.confirm(('layer', 'read'), gateiden=layr.iden)

            if not self.runt.isAdmin(gateiden=view.iden):
                mesg = 'You must be an admin of the view to set the layers.'
                raise s_exc.AuthDeny(mesg=mesg)

            await view.setLayers(layers)
            self.valu['layers'] = layers
            return

        else:
            mesg = f'View does not support setting: {name}'
            raise s_exc.BadOptValu(mesg=mesg)

        todo = s_common.todo('setViewInfo', name, valu)
        valu = await self.viewDynCall(todo, ('view', 'set', name))
        self.valu[name] = valu

    @stormfunc(readonly=True)
    async def _methViewRepr(self):
        iden = self.valu.get('iden')
        name = self.valu.get('name', 'unnamed')
        creator = self.valu.get('creator')

        lines = [
            f'View: {iden} (name: {name})',
            f'  Creator: {creator}',
            '  Layers:',
        ]
        for layr in self.valu.get('layers', ()):
            layriden = layr.get('iden')
            readonly = layr.get('readonly')
            layrname = layr.get('name', 'unnamed')

            lines.append(f'    {layriden}: {layrname} readonly: {readonly}')

        return '\n'.join(lines)

    @stormfunc(readonly=True)
    async def _methViewPack(self):
        return copy.deepcopy(self.valu)

    async def _methViewFork(self, name=None):
        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')

        gatekeys = (
            (useriden, ('view', 'add'), None),
            (useriden, ('view', 'read'), viewiden),
        )

        ldef = {'creator': self.runt.user.iden}
        vdef = {'creator': self.runt.user.iden}

        if name is not None:
            vdef['name'] = name

        todo = s_common.todo('fork', ldef=ldef, vdef=vdef)

        newv = await self.runt.dyncall(viewiden, todo, gatekeys=gatekeys)

        return View(self.runt, newv, path=self.path)

    async def _methViewMerge(self, force=False):
        '''
        Merge a forked view back into its parent.
        '''
        force = await tobool(force)
        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')
        todo = s_common.todo('merge', useriden=useriden, force=force)
        await self.runt.dyncall(viewiden, todo)

    async def _methWipeLayer(self):
        '''
        Delete nodes and nodedata from the view's write layer.
        '''
        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')
        view = self.runt.snap.core.getView(viewiden)
        await view.wipeLayer(useriden=useriden)

@registry.registerLib
class LibTrigger(Lib):
    '''
    A Storm Library for interacting with Triggers in the Cortex.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a Trigger to the Cortex.',
         'type': {'type': 'function', '_funcname': '_methTriggerAdd',
                  'args': (
                      {'name': 'tdef', 'type': 'dict', 'desc': 'A Trigger definition.', },
                  ),
                  'returns': {'type': 'storm:trigger', 'desc': 'The new trigger.', }}},
        {'name': 'del', 'desc': 'Delete a Trigger from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methTriggerDel',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a trigger to delete. '
                               'Only a single matching prefix will be deleted.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the deleted trigger which matched the prefix.', }}},
        {'name': 'list', 'desc': 'Get a list of Triggers in the current view.',
         'type': {'type': 'function', '_funcname': '_methTriggerList',
                  'returns': {'type': 'list',
                              'desc': 'A list of ``storm:trigger`` objects the user is allowed to access.', }}},
        {'name': 'get', 'desc': 'Get a Trigger in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methTriggerGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the Trigger to get.', },
                  ),
                  'returns': {'type': 'storm:trigger', 'desc': 'The requested ``storm:trigger`` object.', }}},
        {'name': 'enable', 'desc': 'Enable a Trigger in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methTriggerEnable',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a trigger to enable. '
                               'Only a single matching prefix will be enabled.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the trigger that was enabled.', }}},
        {'name': 'disable', 'desc': 'Disable a Trigger in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methTriggerDisable',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a trigger to disable. '
                               'Only a single matching prefix will be disabled.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the trigger that was disabled.', }}},
        {'name': 'mod', 'desc': 'Modify an existing Trigger in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methTriggerMod',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a trigger to modify. '
                               'Only a single matching prefix will be modified.', },
                      {'name': 'query', 'type': ['str', 'storm:query'],
                       'desc': 'The new Storm query to set as the trigger query.', }
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the modified Trigger', }}},
    )
    _storm_lib_path = ('trigger',)

    def getObjLocals(self):
        return {
            'add': self._methTriggerAdd,
            'del': self._methTriggerDel,
            'list': self._methTriggerList,
            'get': self._methTriggerGet,
            'enable': self._methTriggerEnable,
            'disable': self._methTriggerDisable,
            'mod': self._methTriggerMod,
        }

    async def _matchIdens(self, prefix):
        '''
        Returns the iden that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        match = None
        trigs = await self.runt.snap.view.listTriggers()

        for iden, trig in trigs:
            if iden.startswith(prefix):
                if match is not None:
                    mesg = 'Provided iden matches more than one trigger.'
                    raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

                if not allowed(('trigger', 'get'), gateiden=iden):
                    continue

                match = trig

        if match is None:
            mesg = 'Provided iden does not match any valid authorized triggers.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

        return match

    async def _methTriggerAdd(self, tdef):
        tdef = await toprim(tdef)

        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden

        tdef['user'] = useriden
        tdef['view'] = viewiden

        # query is kept to keep this API backwards compatible.
        query = tdef.pop('query', None)
        if query is not None:  # pragma: no cover
            s_common.deprecated('$lib.trigger.add() with "query" argument instead of "storm"', curv='2.95.0')
            await self.runt.warn('$lib.trigger.add() called with query argument, this is deprecated. Use storm instead.')
            tdef['storm'] = query

        cond = tdef.pop('condition', None)
        if cond is not None:
            tdef['cond'] = cond

        tag = tdef.pop('tag', None)
        if tag is not None:
            if tag[0] == '#':
                tdef['tag'] = tag[1:]
            else:
                tdef['tag'] = tag

        form = tdef.pop('form', None)
        if form is not None:
            tdef['form'] = form

        prop = tdef.pop('prop', None)
        if prop is not None:
            tdef['prop'] = prop

        gatekeys = ((useriden, ('trigger', 'add'), viewiden),)
        todo = ('addTrigger', (tdef,), {})
        tdef = await self.dyncall(viewiden, todo, gatekeys=gatekeys)

        return Trigger(self.runt, tdef)

    async def _methTriggerDel(self, prefix):
        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden
        trig = await self._matchIdens(prefix)
        iden = trig.iden

        todo = s_common.todo('delTrigger', iden)
        gatekeys = ((useriden, ('trigger', 'del'), iden),)
        await self.dyncall(viewiden, todo, gatekeys=gatekeys)

        return iden

    async def _methTriggerMod(self, prefix, query):
        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden
        query = await tostr(query)
        trig = await self._matchIdens(prefix)
        iden = trig.iden
        gatekeys = ((useriden, ('trigger', 'set'), iden),)
        todo = s_common.todo('setTriggerInfo', iden, 'storm', query)
        await self.dyncall(viewiden, todo, gatekeys=gatekeys)

        return iden

    async def _methTriggerList(self):
        view = self.runt.snap.view
        triggers = []

        for iden, trig in await view.listTriggers():
            if not allowed(('trigger', 'get'), gateiden=iden):
                continue
            triggers.append(Trigger(self.runt, trig.pack()))

        return triggers

    async def _methTriggerGet(self, iden):
        trigger = await self.runt.snap.view.getTrigger(iden)
        if trigger is None:
            return None

        self.runt.confirm(('trigger', 'get'), gateiden=iden)

        return Trigger(self.runt, trigger.pack())

    async def _methTriggerEnable(self, prefix):
        return await self._triggerendisable(prefix, True)

    async def _methTriggerDisable(self, prefix):
        return await self._triggerendisable(prefix, False)

    async def _triggerendisable(self, prefix, state):
        trig = await self._matchIdens(prefix)
        iden = trig.iden

        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden
        gatekeys = ((useriden, ('trigger', 'set'), iden),)
        todo = s_common.todo('setTriggerInfo', iden, 'enabled', state)
        await self.dyncall(viewiden, todo, gatekeys=gatekeys)

        return iden

@registry.registerType
class Trigger(Prim):
    '''
    Implements the Storm API for a Trigger.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The Trigger iden.', 'type': 'str', },
        {'name': 'set', 'desc': 'Set information in the Trigger.',
         'type': {'type': 'function', '_funcname': 'set',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'Name of the key to set.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The data to set', }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'move', 'desc': 'Modify the Trigger to run in a different View.',
         'type': {'type': 'function', '_funcname': 'move',
                  'args': (
                      {'name': 'viewiden', 'type': 'str',
                       'desc': 'The iden of the new View for the Trigger to run in.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'pack', 'desc': 'Get the trigger definition.',
         'type': {'type': 'function', '_funcname': 'pack',
                  'returns': {'type': 'dict', 'desc': 'The definition.', }}},
    )
    _storm_typename = 'storm:trigger'
    _ismutable = False

    def __init__(self, runt, tdef):

        Prim.__init__(self, tdef)
        self.runt = runt

        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu.get('iden')

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

    def getObjLocals(self):
        return {
            'set': self.set,
            'move': self.move,
            'pack': self.pack,
        }

    async def pack(self):
        return copy.deepcopy(self.valu)

    async def deref(self, name):
        valu = self.valu.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        return self.locls.get(name)

    async def set(self, name, valu):
        trigiden = self.valu.get('iden')
        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden

        name = await tostr(name)
        if name in ('async', 'enabled', ):
            valu = await tobool(valu)
        if name in ('user', 'doc', 'name', 'storm', ):
            valu = await tostr(valu)

        if name == 'user':
            self.runt.user.confirm(('trigger', 'set', 'user'))
        else:
            self.runt.user.confirm(('trigger', 'set', name), gateiden=viewiden)

        await self.runt.snap.view.setTriggerInfo(trigiden, name, valu)

        self.valu[name] = valu

        return self

    async def move(self, viewiden):
        trigiden = self.valu.get('iden')
        viewiden = await tostr(viewiden)

        todo = s_common.todo('getViewDef', viewiden)
        vdef = await self.runt.dyncall('cortex', todo)
        if vdef is None:
            raise s_exc.NoSuchView(mesg=viewiden)

        trigview = self.valu.get('view')
        self.runt.confirm(('view', 'read'), gateiden=viewiden)
        self.runt.confirm(('trigger', 'add'), gateiden=viewiden)
        self.runt.confirm(('trigger', 'del'), gateiden=trigiden)

        useriden = self.runt.user.iden
        tdef = dict(self.valu)
        tdef['view'] = viewiden
        tdef['user'] = useriden

        gatekeys = ((useriden, ('trigger', 'del'), trigiden),)
        todo = s_common.todo('delTrigger', trigiden)
        await self.runt.dyncall(trigview, todo, gatekeys=gatekeys)

        gatekeys = ((useriden, ('trigger', 'add'), viewiden),)
        todo = ('addTrigger', (tdef,), {})
        tdef = await self.runt.dyncall(viewiden, todo, gatekeys=gatekeys)

        self.valu = tdef

def ruleFromText(text):
    '''
    Get a rule tuple from a text string.

    Args:
        text (str): The string to process.

    Returns:
        (bool, tuple): A tuple containing a bool and a list of permission parts.
    '''

    allow = True
    if text.startswith('!'):
        text = text[1:]
        allow = False

    return (allow, tuple(text.split('.')))

@registry.registerLib
class LibAuth(Lib):
    '''
    A Storm Library for interacting with Auth in the Cortex.
    '''
    _storm_locals = (
        {'name': 'ruleFromText', 'desc': 'Get a rule tuple from a text string.',
         'type': {'type': 'function', '_funcname': 'ruleFromText',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The string to process.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'A tuple containing a bool and a list of permission parts.', }}},
    )
    _storm_lib_path = ('auth',)

    def getObjLocals(self):
        return {
            'ruleFromText': self.ruleFromText,
        }

    @staticmethod
    def ruleFromText(text):
        return ruleFromText(text)

@registry.registerLib
class LibUsers(Lib):
    '''
    A Storm Library for interacting with Auth Users in the Cortex.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a User to the Cortex.',
         'type': {'type': 'function', '_funcname': '_methUsersAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the user.', },
                      {'name': 'passwd', 'type': 'str', 'desc': 'The users password.', 'default': None, },
                      {'name': 'email', 'type': 'str', 'desc': 'The users email address.', 'default': None, },
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden to use to create the user.', 'default': None, }
                  ),
                  'returns': {'type': 'storm:auth:user',
                              'desc': 'The ``storm:auth:user`` object for the new user.', }}},
        {'name': 'del', 'desc': 'Delete a User from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methUsersDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the user to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of Users in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methUsersList',
                  'returns': {'type': 'list', 'desc': 'A list of ``storm:auth:user`` objects.', }}},
        {'name': 'get', 'desc': 'Get a specific User by iden.',
         'type': {'type': 'function', '_funcname': '_methUsersGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the user to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'storm:auth:user'],
                              'desc': 'The ``storm:auth:user`` object, or none if the user does not exist.', }}},
        {'name': 'byname', 'desc': 'Get a specific user by name.',
         'type': {'type': 'function', '_funcname': '_methUsersByName',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the user to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'storm:auth:user'],
                              'desc': 'The ``storm:auth:user`` object, or none if the user does not exist.', }}},
    )
    _storm_lib_path = ('auth', 'users')

    def getObjLocals(self):
        return {
            'add': self._methUsersAdd,
            'del': self._methUsersDel,
            'list': self._methUsersList,
            'get': self._methUsersGet,
            'byname': self._methUsersByName,
        }

    async def _methUsersList(self):
        return [User(self.runt, udef['iden']) for udef in await self.runt.snap.core.getUserDefs()]

    async def _methUsersGet(self, iden):
        udef = await self.runt.snap.core.getUserDef(iden)
        if udef is not None:
            return User(self.runt, udef['iden'])

    async def _methUsersByName(self, name):
        udef = await self.runt.snap.core.getUserDefByName(name)
        if udef is not None:
            return User(self.runt, udef['iden'])

    async def _methUsersAdd(self, name, passwd=None, email=None, iden=None):
        self.runt.confirm(('auth', 'user', 'add'))
        name = await tostr(name)
        iden = await tostr(iden, True)
        email = await tostr(email, True)
        passwd = await tostr(passwd, True)
        udef = await self.runt.snap.core.addUser(name, passwd=passwd, email=email, iden=iden,)
        return User(self.runt, udef['iden'])

    async def _methUsersDel(self, iden):
        self.runt.confirm(('auth', 'user', 'del'))
        await self.runt.snap.core.delUser(iden)

@registry.registerLib
class LibRoles(Lib):
    '''
    A Storm Library for interacting with Auth Roles in the Cortex.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a Role to the Cortex.',
         'type': {'type': 'function', '_funcname': '_methRolesAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the role.', },
                  ),
                  'returns': {'type': 'storm:auth:role', 'desc': 'The new role object.', }}},
        {'name': 'del', 'desc': 'Delete a Role from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methRolesDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the role to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of Roles in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methRolesList',
                  'returns': {'type': 'list', 'desc': 'A list of ``storm:auth:role`` objects.', }}},
        {'name': 'get', 'desc': 'Get a specific Role by iden.',
         'type': {'type': 'function', '_funcname': '_methRolesGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the role to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'storm:auth:role'],
                              'desc': 'The ``storm:auth:role`` object; or null if the role does not exist.', }}},
        {'name': 'byname', 'desc': 'Get a specific Role by name.',
         'type': {'type': 'function', '_funcname': '_methRolesByName',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the role to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'storm:auth:role'],
                              'desc': 'The role by name, or null if it does not exist.', }}},
    )
    _storm_lib_path = ('auth', 'roles')

    def getObjLocals(self):
        return {
            'add': self._methRolesAdd,
            'del': self._methRolesDel,
            'list': self._methRolesList,
            'get': self._methRolesGet,
            'byname': self._methRolesByName,
        }

    async def _methRolesList(self):
        return [Role(self.runt, rdef['iden']) for rdef in await self.runt.snap.core.getRoleDefs()]

    async def _methRolesGet(self, iden):
        rdef = await self.runt.snap.core.getRoleDef(iden)
        if rdef is not None:
            return Role(self.runt, rdef['iden'])

    async def _methRolesByName(self, name):
        rdef = await self.runt.snap.core.getRoleDefByName(name)
        if rdef is not None:
            return Role(self.runt, rdef['iden'])

    async def _methRolesAdd(self, name):
        self.runt.confirm(('auth', 'role', 'add'))
        rdef = await self.runt.snap.core.addRole(name)
        return Role(self.runt, rdef['iden'])

    async def _methRolesDel(self, iden):
        self.runt.confirm(('auth', 'role', 'del'))
        await self.runt.snap.core.delRole(iden)

@registry.registerLib
class LibGates(Lib):
    '''
    A Storm Library for interacting with Auth Gates in the Cortex.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get a specific Gate by iden.',
         'type': {'type': 'function', '_funcname': '_methGatesGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the gate to retrieve.', },
                  ),
                  'returns': {'type': ['null', 'storm:auth:gate'],
                              'desc': 'The ``storm:auth:gate`` if it exists, otherwise null.', }}},
        {'name': 'list', 'desc': 'Get a list of Gates in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methGatesList',
                  'returns': {'type': 'list', 'desc': 'A list of ``storm:auth:gate`` objects.', }}},
    )
    _storm_lib_path = ('auth', 'gates')

    def getObjLocals(self):
        return {
            'get': self._methGatesGet,
            'list': self._methGatesList,
        }

    async def _methGatesList(self):
        todo = s_common.todo('getAuthGates')
        gates = await self.runt.coreDynCall(todo)
        return [Gate(self.runt, g) for g in gates]

    async def _methGatesGet(self, iden):
        iden = await toprim(iden)
        todo = s_common.todo('getAuthGate', iden)
        gate = await self.runt.coreDynCall(todo)
        if gate:
            return Gate(self.runt, gate)

@registry.registerType
class Gate(Prim):
    '''
    Implements the Storm API for an AuthGate.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The iden of the AuthGate.', 'type': 'str', },
        {'name': 'type', 'desc': 'The type of the AuthGate.', 'type': 'str', },
        {'name': 'roles', 'desc': 'The role idens which are a member of the Authgate.', 'type': 'list', },
        {'name': 'users', 'desc': 'The user idens which are a member of the Authgate.', 'type': 'list', },
    )
    _storm_typename = 'storm:auth:gate'
    _ismutable = False

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt
        self.locls.update({
            'iden': self.valu.get('iden'),
            'type': self.valu.get('type'),
            'roles': self.valu.get('roles', ()),
            'users': self.valu.get('users', ()),
        })

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

@registry.registerLib
class LibJsonStor(Lib):
    '''
    Implements cortex JSON storage.
    '''
    _storm_lib_path = ('jsonstor',)
    _storm_locals = (
        {'name': 'get', 'desc': 'Return a stored JSON object or object property.',
         'type': {'type': 'function', '_funcname': 'get',
                   'args': (
                        {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.'},
                        {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                    ),
                    'returns': {'type': 'prim', 'desc': 'The previously stored value or $lib.null'}}},

        {'name': 'set', 'desc': 'Set a JSON object or object property.',
         'type': {'type': 'function', '_funcname': 'set',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path elements.'},
                       {'name': 'valu', 'type': 'prim', 'desc': 'The value to set as the JSON object or object property.'},
                       {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                   ),
                   'returns': {'type': 'boolean', 'desc': 'True if the set operation was successful.'}}},

        {'name': 'del', 'desc': 'Delete a stored JSON object or object.',
         'type': {'type': 'function', '_funcname': '_del',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.'},
                       {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                   ),
                   'returns': {'type': 'boolean', 'desc': 'True if the del operation was successful.'}}},

        {'name': 'iter', 'desc': 'Yield (<path>, <valu>) tuples for the JSON objects.',
         'type': {'type': 'function', '_funcname': 'iter',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.', 'default': None},
                   ),
                   'returns': {'name': 'Yields', 'type': 'list', 'desc': '(<path>, <item>) tuples.'}}},
        {'name': 'cacheget',
         'desc': 'Retrieve data stored with cacheset() if it was stored more recently than the asof argument.',
         'type': {'type': 'function', '_funcname': 'cacheget',
                  'args': (
                      {'name': 'path', 'type': 'str|list', 'desc': 'The base path to use for the cache key.', },
                      {'name': 'key', 'type': 'prim', 'desc': 'The value to use for the GUID cache key.', },
                      {'name': 'asof', 'type': 'time', 'default': 'now', 'desc': 'The max cache age.'},
                      {'name': 'envl', 'type': 'boolean', 'default': False, 'desc': 'Return the full cache envelope.'},
                  ),
                  'returns': {'type': 'prim', 'desc': 'The cached value (or envelope) or null.'}}},
        {'name': 'cacheset',
         'desc': 'Set cache data with an envelope that tracks time for cacheget() use.',
         'type': {'type': 'function', '_funcname': 'cacheset',
                  'args': (
                      {'name': 'path', 'type': 'str|list', 'desc': 'The base path to use for the cache key.', },
                      {'name': 'key', 'type': 'prim', 'desc': 'The value to use for the GUID cache key.', },
                      {'name': 'valu', 'type': 'prim', 'desc': 'The data to store.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The cached asof time and path.'}}},
    )

    def addLibFuncs(self):
        self.locls.update({
            'get': self.get,
            'set': self.set,
            'has': self.has,
            'del': self._del,
            'iter': self.iter,
            'cacheget': self.cacheget,
            'cacheset': self.cacheset,
        })

    async def has(self, path):

        if not self.runt.isAdmin():
            mesg = '$lib.jsonstor.has() requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

        path = await toprim(path)
        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('cells', self.runt.snap.core.iden) + path
        return await self.runt.snap.core.hasJsonObj(fullpath)

    async def get(self, path, prop=None):

        if not self.runt.isAdmin():
            mesg = '$lib.jsonstor.get() requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

        path = await toprim(path)
        prop = await toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('cells', self.runt.snap.core.iden) + path

        if prop is None:
            return await self.runt.snap.core.getJsonObj(fullpath)

        return await self.runt.snap.core.getJsonObjProp(fullpath, prop=prop)

    async def set(self, path, valu, prop=None):

        if not self.runt.isAdmin():
            mesg = '$lib.jsonstor.set() requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

        path = await toprim(path)
        valu = await toprim(valu)
        prop = await toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('cells', self.runt.snap.core.iden) + path

        if prop is None:
            await self.runt.snap.core.setJsonObj(fullpath, valu)
            return True

        return await self.runt.snap.core.setJsonObjProp(fullpath, prop, valu)

    async def _del(self, path, prop=None):

        if not self.runt.isAdmin():
            mesg = '$lib.jsonstor.del() requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

        path = await toprim(path)
        prop = await toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('cells', self.runt.snap.core.iden) + path

        if prop is None:
            await self.runt.snap.core.delJsonObj(fullpath)
            return True

        return await self.runt.snap.core.delJsonObjProp(fullpath, prop=prop)

    async def iter(self, path=None):

        if not self.runt.isAdmin():
            mesg = '$lib.jsonstor.iter() requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

        path = await toprim(path)

        fullpath = ('cells', self.runt.snap.core.iden)
        if path is not None:
            if isinstance(path, str):
                path = tuple(path.split('/'))
            fullpath += path

        async for path, item in self.runt.snap.core.getJsonObjs(fullpath):
            yield path, item

    async def cacheget(self, path, key, asof='now', envl=False):

        if not self.runt.isAdmin():
            mesg = '$lib.jsonstor.cacheget() requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

        key = await toprim(key)
        path = await toprim(path)
        envl = await tobool(envl)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('cells', self.runt.snap.core.iden) + path + (s_common.guid(key),)

        cachetick = await self.runt.snap.core.getJsonObjProp(fullpath, prop='asof')
        if cachetick is None:
            return None

        timetype = self.runt.snap.core.model.type('time')
        asoftick = timetype.norm(asof)[0]

        if cachetick >= asoftick:
            if envl:
                return await self.runt.snap.core.getJsonObj(fullpath)
            return await self.runt.snap.core.getJsonObjProp(fullpath, prop='data')

        return None

    async def cacheset(self, path, key, valu):

        if not self.runt.isAdmin():
            mesg = '$lib.jsonstor.cacheset() requires admin privileges.'
            raise s_exc.AuthDeny(mesg=mesg)

        key = await toprim(key)
        path = await toprim(path)
        valu = await toprim(valu)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        cachepath = path + (s_common.guid(key),)
        fullpath = ('cells', self.runt.snap.core.iden) + cachepath

        now = s_common.now()

        envl = {
            'key': key,
            'asof': now,
            'data': valu,
        }

        await self.runt.snap.core.setJsonObj(fullpath, envl)

        return {
            'asof': now,
            'path': cachepath,
        }

@registry.registerType
class UserProfile(Prim):
    '''
    The Storm deref/setitem/iter convention on top of User profile information.
    '''
    _storm_typename = 'storm:auth:user:profile'
    _ismutable = True

    def __init__(self, runt, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.runt = runt

    async def deref(self, name):
        self.runt.confirm(('auth', 'user', 'get', 'profile', name))
        return copy.deepcopy(await self.runt.snap.core.getUserProfInfo(self.valu, name))

    async def setitem(self, name, valu):
        if valu is undef:
            self.runt.confirm(('auth', 'user', 'pop', 'profile', name))
            await self.runt.snap.core.popUserProfInfo(self.valu, name)
            return

        valu = await toprim(valu)
        self.runt.confirm(('auth', 'user', 'set', 'profile', name))
        await self.runt.snap.core.setUserProfInfo(self.valu, name, valu)

    async def iter(self):
        profile = await self.value()
        for item in list(profile.items()):
            yield item

    async def value(self):
        self.runt.confirm(('auth', 'user', 'get', 'profile'))
        return copy.deepcopy(await self.runt.snap.core.getUserProfile(self.valu))

@registry.registerType
class UserJson(Prim):
    '''
    Implements per-user JSON storage.
    '''
    _storm_typename = 'storm:auth:user:json'
    _ismutable = False
    _storm_locals = (
        {'name': 'get', 'desc': 'Return a stored JSON object or object property for the user.',
         'type': {'type': 'function', '_funcname': 'get',
                   'args': (
                        {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.'},
                        {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                    ),
                    'returns': {'type': 'prim', 'desc': 'The previously stored value or $lib.null'}}},

        {'name': 'set', 'desc': 'Set a JSON object or object property for the user.',
         'type': {'type': 'function', '_funcname': 'set',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path elements.'},
                       {'name': 'valu', 'type': 'prim', 'desc': 'The value to set as the JSON object or object property.'},
                       {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                   ),
                   'returns': {'type': 'boolean', 'desc': 'True if the set operation was successful.'}}},

        {'name': 'del', 'desc': 'Delete a stored JSON object or object property for the user.',
         'type': {'type': 'function', '_funcname': '_del',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.'},
                       {'name': 'prop', 'type': 'str|list', 'desc': 'A property name or list of name parts.', 'default': None},
                   ),
                   'returns': {'type': 'boolean', 'desc': 'True if the del operation was successful.'}}},

        {'name': 'iter', 'desc': 'Yield (<path>, <valu>) tuples for the users JSON objects.',
         'type': {'type': 'function', '_funcname': 'iter',
                  'args': (
                       {'name': 'path', 'type': 'str|list', 'desc': 'A path string or list of path parts.', 'default': None},
                   ),
                   'returns': {'name': 'Yields', 'type': 'list', 'desc': '(<path>, <item>) tuples.'}}},
    )

    def __init__(self, runt, valu):
        Prim.__init__(self, valu)
        self.runt = runt
        self.locls.update({
            'get': self.get,
            'set': self.set,
            'has': self.has,
            'del': self._del,
            'iter': self.iter,
        })

    async def has(self, path):

        path = await toprim(path)
        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('users', self.valu, 'json') + path
        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'get'))

        return await self.runt.snap.core.hasJsonObj(fullpath)

    async def get(self, path, prop=None):
        path = await toprim(path)
        prop = await toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('users', self.valu, 'json') + path

        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'get'))

        if prop is None:
            return await self.runt.snap.core.getJsonObj(fullpath)

        return await self.runt.snap.core.getJsonObjProp(fullpath, prop=prop)

    async def set(self, path, valu, prop=None):
        path = await toprim(path)
        valu = await toprim(valu)
        prop = await toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('users', self.valu, 'json') + path

        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'set'))

        if prop is None:
            await self.runt.snap.core.setJsonObj(fullpath, valu)
            return True

        return await self.runt.snap.core.setJsonObjProp(fullpath, prop, valu)

    async def _del(self, path, prop=None):
        path = await toprim(path)
        prop = await toprim(prop)

        if isinstance(path, str):
            path = tuple(path.split('/'))

        fullpath = ('users', self.valu, 'json') + path

        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'set'))

        if prop is None:
            await self.runt.snap.core.delJsonObj(fullpath)
            return True

        return await self.runt.snap.core.delJsonObjProp(fullpath, prop=prop)

    async def iter(self, path=None):

        path = await toprim(path)

        if self.runt.user.iden != self.valu:
            self.runt.confirm(('user', 'json', 'get'))

        fullpath = ('users', self.valu, 'json')
        if path is not None:
            if isinstance(path, str):
                path = tuple(path.split('/'))
            fullpath += path

        async for path, item in self.runt.snap.core.getJsonObjs(fullpath):
            yield path, item

@registry.registerType
class User(Prim):
    '''
    Implements the Storm API for a User.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The User iden.', 'type': 'str', },
        {'name': 'get', 'desc': 'Get a arbitrary property from the User definition.',
         'type': {'type': 'function', '_funcname': '_methUserGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the property to return.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'roles', 'desc': 'Get the Roles for the User.',
         'type': {'type': 'function', '_funcname': '_methUserRoles',
                  'returns': {'type': 'list',
                              'desc': 'A list of ``storm:auth:roles`` with the user is a member of.', }}},
        {'name': 'pack', 'desc': 'Get the packed version of the User.',
         'type': {'type': 'function', '_funcname': '_methUserPack', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'The packed User definition.', }}},
        {'name': 'allowed', 'desc': 'Check if the user has a given permission.',
         'type': {'type': 'function', '_funcname': '_methUserAllowed',
                  'args': (
                      {'name': 'permname', 'type': 'str', 'desc': 'The permission string to check.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The authgate iden.', 'default': None, },
                      {'name': 'default', 'type': 'boolean', 'desc': 'The default value.', 'default': False, },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the rule is allowed, False otherwise.', }}},
        {'name': 'grant', 'desc': 'Grant a Role to the User.',
         'type': {'type': 'function', '_funcname': '_methUserGrant',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the Role.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setRoles', 'desc': '''
        Replace all the Roles of the User with a new list of roles.

        Notes:
            The roleiden for the "all" role must be present in the new list of roles. This replaces all existing roles
            that the user has with the new roles.
        ''',
         'type': {'type': 'function', '_funcname': '_methUserSetRoles',
                  'args': (
                      {'name': 'idens', 'type': 'list', 'desc': 'The idens to  of the Role.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'revoke', 'desc': 'Remove a Role from the User',
         'type': {'type': 'function', '_funcname': '_methUserRevoke',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the Role.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'tell', 'desc': 'Send a tell notification to a user.',
         'type': {'type': 'function', '_funcname': '_methUserTell',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text of the message to send.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'notify', 'desc': 'Send an arbitrary user notification.',
         'type': {'type': 'function', '_funcname': '_methUserNotify',
                  'args': (
                      {'name': 'mesgtype', 'type': 'str', 'desc': 'The notfication type.', },
                      {'name': 'mesgdata', 'type': 'dict', 'desc': 'The notification data.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'addRule', 'desc': 'Add a rule to the User.',
         'type': {'type': 'function', '_funcname': '_methUserAddRule',
                  'args': (
                      {'name': 'rule', 'type': 'list', 'desc': 'The rule tuple to add to the User.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.', 'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delRule', 'desc': 'Remove a rule from the User.',
         'type': {'type': 'function', '_funcname': '_methUserDelRule',
                  'args': (
                      {'name': 'rule', 'type': 'list', 'desc': 'The rule tuple to removed from the User.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.', 'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setRules', 'desc': 'Replace the rules on the User with new rules.',
         'type': {'type': 'function', '_funcname': '_methUserSetRules',
                  'args': (
                      {'name': 'rules', 'type': 'list', 'desc': 'A list of rule tuples.', },
                      {'name': 'gateiden', 'type': 'str',
                       'desc': 'The gate iden used for the rules.', 'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setAdmin', 'desc': 'Set the Admin flag for the user.',
         'type': {'type': 'function', '_funcname': '_methUserSetAdmin',
                  'args': (
                      {'name': 'admin', 'type': 'boolean',
                       'desc': 'True to make the User an admin, false to remove their admin status.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the operation.',
                       'default': None, }
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setEmail', 'desc': 'Set the email address of the User.',
         'type': {'type': 'function', '_funcname': '_methUserSetEmail',
                  'args': (
                      {'name': 'email', 'type': 'str', 'desc': 'The email address to set for the User.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setLocked', 'desc': 'Set the locked status for a user.',
         'type': {'type': 'function', '_funcname': '_methUserSetLocked',
                  'args': (
                      {'name': 'locked', 'type': 'boolean', 'desc': 'True to lock the user, false to unlock them.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'setPasswd', 'desc': 'Set the Users password.',
         'type': {'type': 'function', '_funcname': '_methUserSetPasswd',
                  'args': (
                      {'name': 'passwd', 'type': 'str',
                       'desc': 'The new password for the user. This is best passed into the runtime as a variable.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'name', 'desc': '''
        A users name. This can also be used to set a users name.

        Example:
                Change a users name::

                    $user=$lib.auth.users.byname(bob) $user.name=robert
        ''',
         'type': {'type': 'stor', '_storfunc': '_storUserName',
                  'returns': {'type': 'str', }}},
        {'name': 'email', 'desc': '''
        A users email. This can also be used to set the users email.

        Example:
                Change a users email address::

                    $user=$lib.auth.users.byname(bob) $user.email="robert@bobcorp.net"
        ''',
         'type': {'type': ['stor'], '_storfunc': '_methUserSetEmail',
                  'returns': {'type': ['str', 'null'], }}},
        {'name': 'profile', 'desc': '''
        A user profile dictionary. This can be used as an application level key-value store.

        Example:
            Set a value::

                $user=$lib.auth.users.byname(bob) $user.profile.somekey="somevalue"

            Get a value::

                $user=$lib.auth.users.byname(bob) $value = $user.profile.somekey
        ''',
        'type': {'type': ['ctor'], '_ctorfunc': '_ctorUserProfile',
                  'returns': {'type': 'storm:auth:user:profile', }}},
    )
    _storm_typename = 'storm:auth:user'
    _ismutable = False

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt

        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu
        self.stors.update({
            'name': self._storUserName,
            'email': self._methUserSetEmail,
        })
        self.ctors.update({
            'json': self._ctorUserJson,
            'profile': self._ctorUserProfile,
        })

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

    def _ctorUserJson(self, path=None):
        return UserJson(self.runt, self.valu)

    def _ctorUserProfile(self, path=None):
        return UserProfile(self.runt, self.valu)

    def getObjLocals(self):
        return {
            'get': self._methUserGet,
            'pack': self._methUserPack,
            'tell': self._methUserTell,
            'notify': self._methUserNotify,
            'roles': self._methUserRoles,
            'allowed': self._methUserAllowed,
            'grant': self._methUserGrant,
            'revoke': self._methUserRevoke,
            'addRule': self._methUserAddRule,
            'delRule': self._methUserDelRule,
            'setRoles': self._methUserSetRoles,
            'setRules': self._methUserSetRules,
            'setAdmin': self._methUserSetAdmin,
            'setEmail': self._methUserSetEmail,
            'setLocked': self._methUserSetLocked,
            'setPasswd': self._methUserSetPasswd,
        }

    async def _methUserPack(self):
        return await self.value()

    async def _methUserTell(self, text):
        mesgdata = {
            'text': await tostr(text),
            'from': self.runt.user.iden,
        }
        self.runt.confirm(('tell', self.valu), default=True)
        return await self.runt.snap.core.addUserNotif(self.valu, 'tell', mesgdata)

    async def _methUserNotify(self, mesgtype, mesgdata):
        mesgtype = await tostr(mesgtype)
        mesgdata = await toprim(mesgdata)
        if not self.runt.isAdmin():
            mesg = '$user.notify() method requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.addUserNotif(self.valu, mesgtype, mesgdata)

    async def _storUserName(self, name):

        name = await tostr(name)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'name'), default=True)
            await self.runt.snap.core.setUserName(self.valu, name)
            return

        self.runt.confirm(('auth', 'user', 'set', 'name'))
        await self.runt.snap.core.setUserName(self.valu, name)

    async def _derefGet(self, name):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return udef.get(name, s_common.novalu)

    async def _methUserGet(self, name):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return udef.get(name)

    async def _methUserRoles(self):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return [Role(self.runt, rdef['iden']) for rdef in udef.get('roles')]

    async def _methUserAllowed(self, permname, gateiden=None, default=False):
        permname = await tostr(permname)
        gateiden = await tostr(gateiden)
        default = await tobool(default)

        perm = tuple(permname.split('.'))
        user = await self.runt.snap.core.auth.reqUser(self.valu)
        return user.allowed(perm, gateiden=gateiden, default=default)

    async def _methUserGrant(self, iden):
        self.runt.confirm(('auth', 'user', 'grant'))
        await self.runt.snap.core.addUserRole(self.valu, iden)

    async def _methUserSetRoles(self, idens):
        self.runt.confirm(('auth', 'user', 'grant'))
        self.runt.confirm(('auth', 'user', 'revoke'))
        idens = await toprim(idens)
        await self.runt.snap.core.setUserRoles(self.valu, idens)

    async def _methUserRevoke(self, iden):
        self.runt.confirm(('auth', 'user', 'revoke'))
        await self.runt.snap.core.delUserRole(self.valu, iden)

    async def _methUserSetRules(self, rules, gateiden=None):
        self.runt.confirm(('auth', 'user', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.setUserRules(self.valu, rules, gateiden=gateiden)

    async def _methUserAddRule(self, rule, gateiden=None):
        self.runt.confirm(('auth', 'user', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.addUserRule(self.valu, rule, gateiden=gateiden)

    async def _methUserDelRule(self, rule, gateiden=None):
        self.runt.confirm(('auth', 'user', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.delUserRule(self.valu, rule, gateiden=gateiden)

    async def _methUserSetEmail(self, email):
        email = await tostr(email)
        if self.runt.user.iden == self.valu:
            self.runt.confirm(('auth', 'self', 'set', 'email'), default=True)
            await self.runt.snap.core.setUserEmail(self.valu, email)
            return

        self.runt.confirm(('auth', 'user', 'set', 'email'))
        await self.runt.snap.core.setUserEmail(self.valu, email)

    async def _methUserSetAdmin(self, admin, gateiden=None):
        self.runt.confirm(('auth', 'user', 'set', 'admin'), gateiden=gateiden)
        admin = await tobool(admin)

        await self.runt.snap.core.setUserAdmin(self.valu, admin, gateiden=gateiden)

    async def _methUserSetPasswd(self, passwd):
        if self.runt.user.iden == self.valu:
            passwd = await tostr(passwd, noneok=True)
            self.runt.confirm(('auth', 'self', 'set', 'passwd'), default=True)
            return await self.runt.snap.core.setUserPasswd(self.valu, passwd)

        self.runt.confirm(('auth', 'user', 'set', 'passwd'))
        return await self.runt.snap.core.setUserPasswd(self.valu, passwd)

    async def _methUserSetLocked(self, locked):
        self.runt.confirm(('auth', 'user', 'set', 'locked'))
        await self.runt.snap.core.setUserLocked(self.valu, await tobool(locked))

    async def value(self):
        return await self.runt.snap.core.getUserDef(self.valu)

    async def stormrepr(self):
        return f'{self._storm_typename}: {await self.value()}'

@registry.registerType
class Role(Prim):
    '''
    Implements the Storm API for a Role.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The Role iden.', 'type': 'str', },
        {'name': 'get', 'desc': 'Get a arbitrary property from the Role definition.',
         'type': {'type': 'function', '_funcname': '_methRoleGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the property to return.', },
                  ),
                  'returns': {'type': 'prim', 'desc': 'The requested value.', }}},
        {'name': 'pack', 'desc': 'Get the packed version of the Role.',
         'type': {'type': 'function', '_funcname': '_methRolePack', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'The packed Role definition.', }}},
        {'name': 'addRule', 'desc': 'Add a rule to the Role',
         'type': {'type': 'function', '_funcname': '_methRoleAddRule',
                  'args': (
                      {'name': 'rule', 'type': 'list', 'desc': 'The rule tuple to added to the Role.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'delRule', 'desc': 'Remove a rule from the Role.',
         'type': {'type': 'function', '_funcname': '_methRoleDelRule',
                  'args': (
                      {'name': 'rule', 'type': 'list', 'desc': 'The rule tuple to removed from the Role.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'The gate iden used for the rule.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null', }
                  }},
        {'name': 'setRules', 'desc': 'Replace the rules on the Role with new rules.',
         'type': {'type': 'function', '_funcname': '_methRoleSetRules',
                  'args': (
                      {'name': 'rules', 'type': 'list', 'desc': 'A list of rules to set on the Role.', },
                      {'name': 'gateiden', 'type': 'str', 'desc': 'Ahe gate iden used for the rules.',
                       'default': None, },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'name', 'desc': '''
            A roles name. This can also be used to set the role name.

            Example:
                    Change a roles name::

                        $role=$lib.auth.roles.byname(analyst) $role.name=superheroes
            ''',
         'type': {'type': 'stor', '_storfunc': '_setRoleName',
                  'returns': {'type': 'str', }}},
    )
    _storm_typename = 'storm:auth:role'
    _ismutable = False

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu
        self.stors.update({
            'name': self._setRoleName,
        })

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

    def getObjLocals(self):
        return {
            'get': self._methRoleGet,
            'pack': self._methRolePack,
            'addRule': self._methRoleAddRule,
            'delRule': self._methRoleDelRule,
            'setRules': self._methRoleSetRules,
        }

    async def _derefGet(self, name):
        rdef = await self.runt.snap.core.getRoleDef(self.valu)
        return rdef.get(name, s_common.novalu)

    async def _setRoleName(self, name):
        name = await tostr(name)

        self.runt.confirm(('auth', 'role', 'set', 'name'))
        await self.runt.snap.core.setRoleName(self.valu, name)

    async def _methRoleGet(self, name):
        rdef = await self.runt.snap.core.getRoleDef(self.valu)
        return rdef.get(name)

    async def _methRolePack(self):
        return await self.value()

    async def _methRoleSetRules(self, rules, gateiden=None):
        self.runt.confirm(('auth', 'role', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.setRoleRules(self.valu, rules, gateiden=gateiden)

    async def _methRoleAddRule(self, rule, gateiden=None):
        self.runt.confirm(('auth', 'role', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.addRoleRule(self.valu, rule, gateiden=gateiden)

    async def _methRoleDelRule(self, rule, gateiden=None):
        self.runt.confirm(('auth', 'role', 'set', 'rules'), gateiden=gateiden)
        await self.runt.snap.core.delRoleRule(self.valu, rule, gateiden=gateiden)

    async def value(self):
        return await self.runt.snap.core.getRoleDef(self.valu)

    async def stormrepr(self):
        return f'{self._storm_typename}: {await self.value()}'

@registry.registerLib
class LibCron(Lib):
    '''
    A Storm Library for interacting with Cron Jobs in the Cortex.
    '''
    _storm_locals = (
        {'name': 'at', 'desc': 'Add a non-recurring Cron Job to the Cortex.',
         'type': {'type': 'function', '_funcname': '_methCronAt',
                  'args': (
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Key-value parameters used to add the cron job.', },
                  ),
                  'returns': {'type': 'storm:cronjob', 'desc': 'The new Cron Job.', }}},
        {'name': 'add', 'desc': 'Add a recurring Cron Job to the Cortex.',
         'type': {'type': 'function', '_funcname': '_methCronAdd',
                  'args': (
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Key-value parameters used to add the cron job.', },
                  ),
                  'returns': {'type': 'storm:cronjob', 'desc': 'The new Cron Job.', }}},
        {'name': 'del', 'desc': 'Delete a CronJob from the Cortex.',
         'type': {'type': 'function', '_funcname': '_methCronDel',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a cron job to delete. '
                               'Only a single matching prefix will be deleted.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a CronJob in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methCronGet',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a cron job to get. '
                               'Only a single matching prefix will be retrieved.', },
                  ),
                  'returns': {'type': 'storm:cronjob', 'desc': 'The requested cron job.', }}},
        {'name': 'mod', 'desc': 'Modify the Storm query for a CronJob in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methCronMod',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a cron job to modify. '
                               'Only a single matching prefix will be modified.', },
                      {'name': 'query', 'type': ['str', 'storm:query'],
                       'desc': 'The new Storm query for the Cron Job.', }
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the CronJob which was modified.'}}},
        {'name': 'move', 'desc': 'Move a cron job to a new view.',
         'type': {'type': 'function', '_funcname': '_methCronMove',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a cron job to move. '
                               'Only a single matching prefix will be modified.', },
                      {'name': 'view', 'type': 'str',
                       'desc': 'The iden of the view to move the CrobJob to', }
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the CronJob which was moved.'}}},
        {'name': 'list', 'desc': 'List CronJobs in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methCronList',
                  'returns': {'type': 'list', 'desc': 'A list of ``storm:cronjob`` objects..', }}},
        {'name': 'enable', 'desc': 'Enable a CronJob in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methCronEnable',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a cron job to enable. '
                               'Only a single matching prefix will be enabled.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the CronJob which was enabled.', }}},
        {'name': 'disable', 'desc': 'Disable a CronJob in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methCronDisable',
                  'args': (
                      {'name': 'prefix', 'type': 'str',
                       'desc': 'A prefix to match in order to identify a cron job to disable. '
                               'Only a single matching prefix will be disabled.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The iden of the CronJob which was disabled.', }}},
    )
    _storm_lib_path = ('cron',)

    def getObjLocals(self):
        return {
            'at': self._methCronAt,
            'add': self._methCronAdd,
            'del': self._methCronDel,
            'get': self._methCronGet,
            'mod': self._methCronMod,
            'list': self._methCronList,
            'move': self._methCronMove,
            'enable': self._methCronEnable,
            'disable': self._methCronDisable,
        }

    async def _matchIdens(self, prefix, perm):
        '''
        Returns the cron that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        todo = s_common.todo('listCronJobs')
        crons = await self.dyncall('cortex', todo)
        matchcron = None

        for cron in crons:
            iden = cron.get('iden')

            if iden.startswith(prefix) and allowed(perm, gateiden=iden):
                if matchcron is not None:
                    mesg = 'Provided iden matches more than one cron job.'
                    raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)
                matchcron = cron

        if matchcron is not None:
            return matchcron

        mesg = 'Provided iden does not match any valid authorized cron job.'
        raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

    def _parseWeekday(self, val):
        ''' Try to match a day-of-week abbreviation, then try a day-of-week full name '''
        val = val.title()
        try:
            return list(calendar.day_abbr).index(val)
        except ValueError:
            try:
                return list(calendar.day_name).index(val)
            except ValueError:
                return None

    def _parseIncval(self, incval):
        ''' Parse a non-day increment value. Should be an integer or a comma-separated integer list. '''
        try:
            retn = [int(val) for val in incval.split(',')]
        except ValueError:
            return None

        return retn[0] if len(retn) == 1 else retn

    def _parseReq(self, requnit, reqval):
        ''' Parse a non-day fixed value '''
        assert reqval[0] != '='

        try:
            retn = []
            for val in reqval.split(','):
                if requnit == 'month':
                    if reqval[0].isdigit():
                        retn.append(int(reqval))  # must be a month (1-12)
                    else:
                        try:
                            retn.append(list(calendar.month_abbr).index(val.title()))
                        except ValueError:
                            retn.append(list(calendar.month_name).index(val.title()))
                else:
                    retn.append(int(val))
        except ValueError:
            return None

        return retn[0] if len(retn) == 1 else retn

    def _parseDay(self, optval):
        ''' Parse a --day argument '''
        isreq = not optval.startswith('+')
        if not isreq:
            optval = optval[1:]

        try:
            retnval = []
            unit = None
            for val in optval.split(','):
                if not val:
                    raise ValueError
                if val[-1].isdigit():
                    newunit = 'dayofmonth' if isreq else 'day'
                    if unit is None:
                        unit = newunit
                    elif newunit != unit:
                        raise ValueError
                    retnval.append(int(val))
                else:
                    newunit = 'dayofweek'
                    if unit is None:
                        unit = newunit
                    elif newunit != unit:
                        raise ValueError

                    weekday = self._parseWeekday(val)
                    if weekday is None:
                        raise ValueError
                    retnval.append(weekday)
            if len(retnval) == 0:
                raise ValueError
        except ValueError:
            return None, None
        if len(retnval) == 1:
            retnval = retnval[0]
        return unit, retnval

    def _parseAlias(self, opts):
        retn = {}

        hourly = opts.get('hourly')
        if hourly is not None:
            retn['hour'] = '+1'
            retn['minute'] = str(int(hourly))
            return retn

        daily = opts.get('daily')
        if daily is not None:
            fields = time.strptime(daily, '%H:%M')
            retn['day'] = '+1'
            retn['hour'] = str(fields.tm_hour)
            retn['minute'] = str(fields.tm_min)
            return retn

        monthly = opts.get('monthly')
        if monthly is not None:
            day, rest = monthly.split(':', 1)
            fields = time.strptime(rest, '%H:%M')
            retn['month'] = '+1'
            retn['day'] = day
            retn['hour'] = str(fields.tm_hour)
            retn['minute'] = str(fields.tm_min)
            return retn

        yearly = opts.get('yearly')
        if yearly is not None:
            fields = yearly.split(':')
            if len(fields) != 4:
                raise ValueError(f'Failed to parse parameter {yearly}')
            retn['year'] = '+1'
            retn['month'], retn['day'], retn['hour'], retn['minute'] = fields
            return retn

        return None

    async def _methCronAdd(self, **kwargs):
        incunit = None
        incval = None
        reqdict = {}
        valinfo = {  # unit: (minval, next largest unit)
            'month': (1, 'year'),
            'dayofmonth': (1, 'month'),
            'hour': (0, 'day'),
            'minute': (0, 'hour'),
        }

        query = kwargs.get('query', None)
        if query is None:
            mesg = 'Query parameter is required.'
            raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

        try:
            alias_opts = self._parseAlias(kwargs)
        except ValueError as e:
            mesg = f'Failed to parse ..ly parameter: {" ".join(e.args)}'
            raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

        if alias_opts:
            year = kwargs.get('year')
            month = kwargs.get('month')
            day = kwargs.get('day')
            hour = kwargs.get('hour')
            minute = kwargs.get('minute')

            if year or month or day or hour or minute:
                mesg = 'May not use both alias (..ly) and explicit options at the same time'
                raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
            opts = alias_opts
        else:
            opts = kwargs

        for optname in ('year', 'month', 'day', 'hour', 'minute'):
            optval = opts.get(optname)

            if optval is None:
                if incunit is None and not reqdict:
                    continue
                # The option isn't set, but a higher unit is.  Go ahead and set the required part to the lowest valid
                # value, e.g. so --month 2 would run on the *first* of every other month at midnight
                if optname == 'day':
                    reqdict['dayofmonth'] = 1
                else:
                    reqdict[optname] = valinfo[optname][0]
                continue

            isreq = not optval.startswith('+')

            if optname == 'day':
                unit, val = self._parseDay(optval)
                if val is None:
                    mesg = f'Failed to parse day value "{optval}"'
                    raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
                if unit == 'dayofweek':
                    if incunit is not None:
                        mesg = 'May not provide a recurrence value with day of week'
                        raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
                    if reqdict:
                        mesg = 'May not fix month or year with day of week'
                        raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
                    incunit, incval = unit, val
                elif unit == 'day':
                    incunit, incval = unit, val
                else:
                    assert unit == 'dayofmonth'
                    reqdict[unit] = val
                continue

            if not isreq:
                if incunit is not None:
                    mesg = 'May not provide more than 1 recurrence parameter'
                    raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
                if reqdict:
                    mesg = 'Fixed unit may not be larger than recurrence unit'
                    raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
                incunit = optname
                incval = self._parseIncval(optval)
                if incval is None:
                    mesg = 'Failed to parse parameter'
                    raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
                continue

            if optname == 'year':
                mesg = 'Year may not be a fixed value'
                raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

            reqval = self._parseReq(optname, optval)
            if reqval is None:
                mesg = f'Failed to parse fixed parameter "{optval}"'
                raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
            reqdict[optname] = reqval

        # If not set, default (incunit, incval) to (1, the next largest unit)
        if incunit is None:
            if not reqdict:
                mesg = 'Must provide at least one optional argument'
                raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)
            requnit = next(iter(reqdict))  # the first key added is the biggest unit
            incunit = valinfo[requnit][1]
            incval = 1

        cdef = {'storm': query,
                'reqs': reqdict,
                'incunit': incunit,
                'incvals': incval,
                'creator': self.runt.user.iden
                }

        iden = kwargs.get('iden')
        if iden:
            cdef['iden'] = iden

        view = kwargs.get('view')
        if not view:
            view = self.runt.snap.view.iden
        cdef['view'] = view

        todo = s_common.todo('addCronJob', cdef)
        gatekeys = ((self.runt.user.iden, ('cron', 'add'), view),)
        cdef = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return CronJob(self.runt, cdef, path=self.path)

    async def _methCronAt(self, **kwargs):
        tslist = []
        now = time.time()

        query = kwargs.get('query', None)
        if query is None:
            mesg = 'Query parameter is required.'
            raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

        for optname in ('day', 'hour', 'minute'):
            opts = kwargs.get(optname)

            if not opts:
                continue

            for optval in opts.split(','):
                try:
                    arg = f'{optval} {optname}'
                    ts = now + s_time.delta(arg) / 1000.0
                    tslist.append(ts)
                except (ValueError, s_exc.BadTypeValu):
                    mesg = f'Trouble parsing "{arg}"'
                    raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

        dts = kwargs.get('dt')
        if dts:
            for dt in dts.split(','):
                try:
                    ts = s_time.parse(dt) / 1000.0
                    tslist.append(ts)
                except (ValueError, s_exc.BadTypeValu):
                    mesg = f'Trouble parsing "{dt}"'
                    raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

        def _ts_to_reqdict(ts):
            dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
            return {
                'minute': dt.minute,
                'hour': dt.hour,
                'dayofmonth': dt.day,
                'month': dt.month,
                'year': dt.year
            }

        atnow = kwargs.get('now')

        if not tslist and not atnow:
            mesg = 'At least one requirement must be provided'
            raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

        reqdicts = [_ts_to_reqdict(ts) for ts in tslist]

        if atnow:
            reqdicts.append({'now': True})

        cdef = {'storm': query,
                'reqs': reqdicts,
                'incunit': None,
                'incvals': None,
                'creator': self.runt.user.iden
                }

        iden = kwargs.get('iden')
        if iden:
            cdef['iden'] = iden

        view = kwargs.get('view')
        if not view:
            view = self.runt.snap.view.iden
        cdef['view'] = view

        todo = s_common.todo('addCronJob', cdef)
        gatekeys = ((self.runt.user.iden, ('cron', 'add'), view),)
        cdef = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return CronJob(self.runt, cdef, path=self.path)

    async def _methCronDel(self, prefix):
        cron = await self._matchIdens(prefix, ('cron', 'del'))
        iden = cron['iden']

        todo = s_common.todo('delCronJob', iden)
        gatekeys = ((self.runt.user.iden, ('cron', 'del'), iden),)
        return await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methCronMod(self, prefix, query):
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = s_common.todo('updateCronJob', iden, query)
        gatekeys = ((self.runt.user.iden, ('cron', 'set'), iden),)
        await self.dyncall('cortex', todo, gatekeys=gatekeys)
        return iden

    async def _methCronMove(self, prefix, view):
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        self.runt.confirm(('cron', 'set'), gateiden=iden)
        return await self.runt.snap.core.moveCronJob(self.runt.user.iden, iden, view)

    async def _methCronList(self):
        todo = s_common.todo('listCronJobs')
        gatekeys = ((self.runt.user.iden, ('cron', 'get'), None),)
        defs = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return [CronJob(self.runt, cdef, path=self.path) for cdef in defs]

    async def _methCronGet(self, prefix):
        cdef = await self._matchIdens(prefix, ('cron', 'get'))

        return CronJob(self.runt, cdef, path=self.path)

    async def _methCronEnable(self, prefix):
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = ('enableCronJob', (iden,), {})
        await self.runt.dyncall('cortex', todo)

        return iden

    async def _methCronDisable(self, prefix):
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = ('disableCronJob', (iden,), {})
        await self.runt.dyncall('cortex', todo)

        return iden

@registry.registerType
class CronJob(Prim):
    '''
    Implements the Storm api for a cronjob instance.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The iden of the Cron Job.', 'type': 'str', },
        {'name': 'set', 'desc': '''
            Set an editable field in the cron job definition.

            Example:
                Change the name of a cron job::

                    $lib.cron.get($iden).set(name, "foo bar cron job")''',
         'type': {'type': 'function', '_funcname': '_methCronJobSet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the field being set', },
                      {'name': 'valu', 'type': 'any', 'desc': 'The value to set on the definition.', },
                  ),
                  'returns': {'type': 'storm:cronjob', 'desc': 'The ``storm:cronjob``', }}},
        {'name': 'pack', 'desc': 'Get the Cronjob definition.',
         'type': {'type': 'function', '_funcname': '_methCronJobPack',
                  'returns': {'type': 'dict', 'desc': 'The definition.', }}},
        {'name': 'pprint', 'desc': 'Get a dictionary containing user friendly strings for printing the CronJob.',
         'type': {'type': 'function', '_funcname': '_methCronJobPprint',
                  'returns':
                      {'type': 'dict',
                       'desc': 'A dictionary containing structured data about a cronjob for display purposes.', }}},
    )
    _storm_typename = 'storm:cronjob'
    _ismutable = False

    def __init__(self, runt, cdef, path=None):
        Prim.__init__(self, cdef, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())
        self.locls['iden'] = self.valu.get('iden')

    def __hash__(self):
        return hash((self._storm_typename, self.locls['iden']))

    def getObjLocals(self):
        return {
            'set': self._methCronJobSet,
            'pack': self._methCronJobPack,
            'pprint': self._methCronJobPprint,
        }

    async def _methCronJobSet(self, name, valu):
        name = await tostr(name)
        valu = await toprim(valu)
        iden = self.valu.get('iden')

        if name == 'creator':
            # this permission must be granted cortex wide
            # to prevent abuse...
            self.runt.user.confirm(('cron', 'set', 'creator'))
        else:
            self.runt.user.confirm(('cron', 'set', name), gateiden=iden)

        self.valu = await self.runt.snap.core.editCronJob(iden, name, valu)

        return self

    async def _methCronJobPack(self):
        return copy.deepcopy(self.valu)

    @staticmethod
    def _formatTimestamp(ts):
        # N.B. normally better to use fromtimestamp with UTC timezone,
        # but we don't want timezone to print out
        return datetime.datetime.utcfromtimestamp(ts).isoformat(timespec='minutes')

    async def _methCronJobPprint(self):
        user = self.valu.get('username')
        view = self.valu.get('view')
        if not view:
            view = self.runt.snap.core.view.iden

        laststart = self.valu.get('laststarttime')
        lastend = self.valu.get('lastfinishtime')
        result = self.valu.get('lastresult')
        iden = self.valu.get('iden')

        job = {
            'iden': iden,
            'idenshort': iden[:8] + '..',
            'user': user or '<None>',
            'view': view,
            'viewshort': view[:8] + '..',
            'query': self.valu.get('query') or '<missing>',
            'isrecur': 'Y' if self.valu.get('recur') else 'N',
            'isrunning': 'Y' if self.valu.get('isrunning') else 'N',
            'enabled': 'Y' if self.valu.get('enabled', True) else 'N',
            'startcount': self.valu.get('startcount') or 0,
            'errcount': self.valu.get('errcount') or 0,
            'laststart': 'Never' if laststart is None else self._formatTimestamp(laststart),
            'lastend': 'Never' if lastend is None else self._formatTimestamp(lastend),
            'lastresult': self.valu.get('lastresult') or '<None>',
            'lasterrs': self.valu.get('lasterrs') or [],
            'iserr': 'X' if result is not None and not result.startswith('finished successfully') else ' ',
            'recs': []
        }

        for reqdict, incunit, incval in self.valu.get('recs', []):
            job['recs'].append({
                'reqdict': reqdict or '<None>',
                'incunit': incunit or '<None>',
                'incval': incval or '<None>'
            })

        return job

# These will go away once we have value objects in storm runtime
async def toprim(valu, path=None):

    if isinstance(valu, (str, int, bool, float, bytes, types.AsyncGeneratorType, types.GeneratorType)) or valu is None:
        return valu

    if isinstance(valu, (tuple, list)):
        retn = []
        for v in valu:
            try:
                retn.append(await toprim(v))
            except s_exc.NoSuchType:
                pass
        return tuple(retn)

    if isinstance(valu, dict):
        retn = {}
        for k, v in valu.items():
            try:
                retn[k] = await toprim(v)
            except s_exc.NoSuchType:
                pass
        return retn

    if isinstance(valu, Number):
        return float(valu.value())

    if isinstance(valu, Prim):
        return await s_coro.ornot(valu.value)

    if isinstance(valu, s_node.Node):
        return valu.ndef[1]

    mesg = 'Unable to convert object to Storm primitive.'
    raise s_exc.NoSuchType(mesg=mesg, name=valu.__class__.__name__)

def fromprim(valu, path=None, basetypes=True):

    if valu is None:
        return valu

    if basetypes:

        if isinstance(valu, str):
            return Str(valu, path=path)

    # TODO: make s_node.Node a storm type itself?
    if isinstance(valu, s_node.Node):
        return Node(valu, path=path)

    if isinstance(valu, s_node.Path):
        return Path(valu, path=path)

    if isinstance(valu, tuple):
        return List(list(valu), path=path)

    if isinstance(valu, list):
        return List(valu, path=path)

    if isinstance(valu, dict):
        return Dict(valu, path=path)

    if isinstance(valu, bytes):
        return Bytes(valu, path=path)

    if isinstance(valu, bool):
        return Bool(valu, path=path)

    if isinstance(valu, (float, decimal.Decimal)):
        return Number(valu, path=path)

    if isinstance(valu, StormType):
        return valu

    if basetypes:
        mesg = 'Unable to convert python primitive to StormType.'
        raise s_exc.NoSuchType(mesg=mesg, python_type=valu.__class__.__name__)

    return valu

async def tostor(valu):

    if isinstance(valu, Number):
        return str(valu.value())

    if isinstance(valu, (tuple, list)):
        retn = []
        for v in valu:
            try:
                retn.append(await tostor(v))
            except s_exc.NoSuchType:
                pass
        return tuple(retn)

    if isinstance(valu, dict):
        retn = {}
        for k, v in valu.items():
            try:
                retn[k] = await tostor(v)
            except s_exc.NoSuchType:
                pass
        return retn

    return await toprim(valu)

async def tocmprvalu(valu):

    if isinstance(valu, (str, int, bool, float, bytes, types.AsyncGeneratorType, types.GeneratorType, Number)) or valu is None:
        return valu

    if isinstance(valu, (tuple, list)):
        retn = []
        for v in valu:
            retn.append(await tocmprvalu(v))
        return tuple(retn)

    if isinstance(valu, dict):
        retn = {}
        for k, v in valu.items():
            retn[k] = await tocmprvalu(v)
        return retn

    if isinstance(valu, Prim):
        return await s_coro.ornot(valu.value)

    if isinstance(valu, s_node.Node):
        return valu.ndef[1]

    return valu

def ismutable(valu):
    if isinstance(valu, StormType):
        return valu.ismutable()

    # N.B. In Python, tuple is immutable, but in Storm, gets converted in toprim to a storm List
    return isinstance(valu, (set, dict, list, s_node.Path))

async def tostr(valu, noneok=False):

    if noneok and valu is None:
        return None

    try:
        if isinstance(valu, bytes):
            return valu.decode('utf8', 'surrogatepass')

        return str(valu)
    except Exception as e:
        mesg = f'Failed to make a string from {valu!r}.'
        raise s_exc.BadCast(mesg=mesg) from e

async def tobool(valu, noneok=False):

    if noneok and valu is None:
        return None

    if isinstance(valu, Prim):
        return await valu.bool()

    try:
        return bool(valu)
    except Exception:
        mesg = f'Failed to make a boolean from {valu!r}.'
        raise s_exc.BadCast(mesg=mesg)

async def tonumber(valu, noneok=False):

    if noneok and valu is None:
        return None

    if isinstance(valu, Number):
        return valu

    if isinstance(valu, (float, decimal.Decimal)) or (isinstance(valu, str) and '.' in valu):
        return Number(valu)

    return await toint(valu, noneok=noneok)

async def toint(valu, noneok=False):

    if noneok and valu is None:
        return None

    if isinstance(valu, str):
        try:
            return int(valu, 0)
        except ValueError as e:
            mesg = f'Failed to make an integer from {valu!r}.'
            raise s_exc.BadCast(mesg=mesg) from e

    try:
        return int(valu)
    except Exception as e:
        mesg = f'Failed to make an integer from {valu!r}.'
        raise s_exc.BadCast(mesg=mesg) from e

async def toiter(valu, noneok=False):
    if noneok and valu is None:
        return

    if isinstance(valu, Prim):
        async for item in valu.iter():
            yield item
        return

    for item in valu:
        yield item

async def torepr(valu, usestr=False):
    if hasattr(valu, 'stormrepr') and callable(valu.stormrepr):
        return await valu.stormrepr()
    if usestr:
        return str(valu)
    return repr(valu)

async def tobuidhex(valu, noneok=False):

    if noneok and valu is None:
        return None

    if isinstance(valu, Node):
        return valu.valu.iden()

    if isinstance(valu, s_node.Node):
        return valu.iden()

    valu = await tostr(valu)
    if not s_common.isbuidhex(valu):
        mesg = f'Invalid buid string: {valu}'
        raise s_exc.BadCast(mesg=mesg)

    return valu
