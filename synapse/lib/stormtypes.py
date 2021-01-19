import bz2
import copy
import gzip
import json
import time
import regex
import types
import base64
import pprint
import asyncio
import logging
import binascii
import datetime
import calendar
import functools
import collections

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
import synapse.lib.version as s_version
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.provenance as s_provenance

logger = logging.getLogger(__name__)

class Undef: pass
undef = Undef()

def confirm(perm, gateiden=None):
    s_scope.get('runt').confirm(perm, gateiden=gateiden)

def allowed(perm, gateiden=None):
    return s_scope.get('runt').allowed(perm, gateiden=gateiden)

class StormTypesRegistry:
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
        self._TYPREG[path] = ctor

    def delStormType(self, path):
        if not self._TYPREG.pop(path, None):
            raise Exception('no such path!')

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

registry = StormTypesRegistry()

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

def kwarg_format(_text, **kwargs):
    '''
    Replaces instances curly-braced argument names in text with their values
    '''
    for name, valu in kwargs.items():
        temp = '{%s}' % (name,)
        _text = _text.replace(temp, str(valu))

    return _text

class StormType:
    '''
    The base type for storm runtime value objects.
    '''
    def __init__(self, path=None):
        self.path = path
        self.ctors = {}
        self.locls = {}

    def getObjLocals(self):
        '''
        Get the default list of key-value pairs which may be added to the object ``.locls`` dictionary.

        Notes:
            These values are exposed in autodoc generated documentation.

        Returns:
            dict: A key/value pairs.
        '''
        return {}

    async def setitem(self, name, valu):
        mesg = f'{self.__class__.__name__} does not support assignment.'
        raise s_exc.StormRuntimeError(mesg=mesg)

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
            self.locls[name] = valu
            return valu

        raise s_exc.NoSuchName(name=name, styp=self.__class__.__name__)

    async def _derefGet(self, name):
        return s_common.novalu

class Lib(StormType):
    '''
    A collection of storm methods under a name
    '''

    def __init__(self, runt, name=()):
        StormType.__init__(self)
        self.runt = runt
        self.name = name
        self.auth = runt.snap.core.auth
        self.addLibFuncs()

    def addLibFuncs(self):
        self.locls.update(self.getObjLocals())

    async def deref(self, name):
        try:
            return await StormType.deref(self, name)
        except s_exc.NoSuchName:
            pass

        path = self.name + (name,)

        slib = self.runt.snap.core.getStormLib(path)
        if slib is None:
            raise s_exc.NoSuchName(name=name)

        ctor = slib[2].get('ctor', Lib)
        return ctor(self.runt, name=path)

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
    _storm_lib_path = ('pkg',)

    def getObjLocals(self):
        return {
            'add': self._libPkgAdd,
            'get': self._libPkgGet,
            'del': self._libPkgDel,
            'list': self._libPkgList,
        }

    async def _libPkgAdd(self, pkgdef):
        '''
        Add a Storm Package to the Cortex.

        Args:
            pkgdef (dict): A Storm Package definition.

        Returns:
            dict: The validated storm package definition.
        '''
        self.runt.confirm(('pkg', 'add'), None)
        await self.runt.snap.core.addStormPkg(pkgdef)

    async def _libPkgGet(self, name):
        '''
        Get a Storm package from the Cortex.

        Args:
            name (str): A Storm Package name.

        Returns:
            dict: The Storm package definition.
        '''
        name = await tostr(name)
        pkgdef = await self.runt.snap.core.getStormPkg(name)
        if pkgdef is None:
            return None

        return Dict(pkgdef)

    async def _libPkgDel(self, name):
        '''
        Delete a Storm Package from the Cortex.

        Args:
            name (str): The name of the package to delete.

        Returns:
            None
        '''
        self.runt.confirm(('pkg', 'del'), None)
        await self.runt.snap.core.delStormPkg(name)

    async def _libPkgList(self):
        '''
        Get a list of Storm Packages loaded in the Cortex.

        Returns:
            list: A list of Storm Package definitions.
        '''
        return await self.runt.snap.core.getStormPkgs()

@registry.registerLib
class LibDmon(Lib):
    '''
    A Storm Library for interacting with StormDmons.
    '''
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
        '''
        Delete a StormDmon by iden.

        Args:
            iden (str): The iden of the StormDmon to delete.

        Returns:
            None: Returns None.
        '''
        dmon = await self.runt.snap.core.getStormDmon(iden)
        if dmon is None:
            mesg = f'No storm dmon with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        if dmon.get('user') != self.runt.user.iden:
            self.runt.confirm(('dmon', 'del', iden))

        await self.runt.snap.core.delStormDmon(iden)

    async def _libDmonGet(self, iden):
        '''
        Return a Storm Dmon definition dict by iden.

        Args:
            iden (str): The iden of the Storm Dmon.

        Returns:
            (dict): A Storm daemon definition dict.
        '''
        return await self.runt.snap.core.getStormDmon(iden)

    async def _libDmonList(self):
        '''
        Get a list of StormDmons.

        Returns:
            list: A list of StormDmons.
        '''
        return await self.runt.snap.core.getStormDmons()

    async def _libDmonLog(self, iden):
        '''
        Get the messages from a StormDmon.

        Args:
            iden (str): The iden of the StormDmon to get logs for.

        Returns:
            list: A list of messages from the StormDmon.
        '''
        self.runt.confirm(('dmon', 'log'))
        return await self.runt.snap.core.getStormDmonLog(iden)

    async def _libDmonAdd(self, text, name='noname'):
        '''
        Add a StormDmon to the Cortex.

        Args:
            text (str): The Storm query to execute.
            name (str): The name of the Dmon.

        Examples:

            Add a dmon that executes a query::

                $lib.dmon.add(${ myquery }, name='example dmon')

        Returns:
            str: The iden of the newly created StormDmon.
        '''
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
        '''
        Restart the daemon

        Args:
            iden (str): The GUID of the dmon to restart.
        '''
        iden = await tostr(iden)

        ddef = await self.runt.snap.core.getStormDmon(iden)
        if ddef is None:
            return False

        viewiden = ddef['stormopts']['view']
        self.runt.confirm(('dmon', 'add'), gateiden=viewiden)

        await self.runt.snap.core.bumpStormDmon(iden)
        return True

    async def _libDmonStop(self, iden):
        '''
        Stop a storm dmon.

        Args:
            iden (str): The GUID of the dmon to stop.
        '''
        iden = await tostr(iden)

        ddef = await self.runt.snap.core.getStormDmon(iden)
        if ddef is None:
            return False

        viewiden = ddef['stormopts']['view']
        self.runt.confirm(('dmon', 'add'), gateiden=viewiden)

        await self.runt.snap.core.disableStormDmon(iden)
        return True

    async def _libDmonStart(self, iden):
        '''
        Start a storm dmon.

        Args:
            iden (str): The GUID of the dmon to start.
        '''
        iden = await tostr(iden)

        ddef = await self.runt.snap.core.getStormDmon(iden)
        if ddef is None:
            return False

        viewiden = ddef['stormopts']['view']
        self.runt.confirm(('dmon', 'add'), gateiden=viewiden)

        await self.runt.snap.core.enableStormDmon(iden)
        return True

@registry.registerLib
class LibService(Lib):
    '''
    A Storm Library for interacting with Storm Services.
    '''
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
            except s_exc.AuthDeny as sub_e:
                raise e from None
            else:
                mesg = 'Use of service.get.<servicename> permissions are deprecated.'
                await self.runt.warnonce(mesg, svcname=ssvc.name, svciden=ssvc.iden)

    async def _libSvcAdd(self, name, url):
        '''
        Add a Storm Service to the Cortex.

        Args:
            name (str): Name of the Storm Service to add.

            url (str): The Telepath URL to the Storm Service.

        Returns:
            dict: The Storm Service definition.
        '''

        self.runt.confirm(('service', 'add'))
        sdef = {
            'name': name,
            'url': url,
        }
        return await self.runt.snap.core.addStormSvc(sdef)

    async def _libSvcDel(self, iden):
        '''
        Remove a Storm Service from the Cortex.

        Args:
            iden (str): The iden of the service to remove.

        Returns:
            None: Returns None.
        '''
        self.runt.confirm(('service', 'del'))
        return await self.runt.snap.core.delStormSvc(iden)

    async def _libSvcGet(self, name):
        '''
        Get a Storm Service definition.

        Args:
            name (str): The local name, local iden, or remote name, of the service to get the definition for.

        Returns:
            dict: A Storm Service definition.
        '''
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg)
        await self._checkSvcGetPerm(ssvc)
        return ssvc

    async def _libSvcHas(self, name):
        '''
        Check if a storm service is available in the Cortex.

        Args:
            name (str): The local name, local iden, or remote name, of the service to check for the existance of.

        Returns:
            bool: True if the service exists in the Cortex, False if it does not.
        '''
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            return False
        return True

    async def _libSvcList(self):
        '''
        List the Storm Service definitions for the Cortex.

        Notes:
            The definition dictionaries have an additional ``ready`` key added to them to
            indicate if the Cortex is currently connected to the Storm Service or not.

        Returns:
            list: A list of Storm Service definitions.
        '''
        self.runt.confirm(('service', 'list'))
        retn = []

        for ssvc in self.runt.snap.core.getStormSvcs():
            sdef = dict(ssvc.sdef)
            sdef['ready'] = ssvc.ready.is_set()
            sdef['svcname'] = ssvc.svcname
            retn.append(sdef)

        return retn

    async def _libSvcWait(self, name):
        '''
        Wait for a given service to be ready.

        Args:
            name (str): The name, or iden, of the service to wait for.

        Returns:
            True: When the service is ready.
        '''
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg, name=name)
        await self._checkSvcGetPerm(ssvc)
        await ssvc.ready.wait()

@registry.registerLib
class LibBase(Lib):
    '''
    The Base Storm Library. This mainly contains utility functionality.
    '''
    _storm_lib_path = ()

    def getObjLocals(self):
        return {
            'len': self._len,
            'min': self._min,
            'max': self._max,
            'set': self._set,
            'dict': self._dict,
            'exit': self._exit,
            'guid': self._guid,
            'fire': self._fire,
            'list': self._list,
            'null': self._null,
            'undef': self._undef,
            'true': self._true,
            'false': self._false,
            'text': self._text,
            'cast': self._cast,
            'warn': self._warn,
            'print': self._print,
            'pprint': self._pprint,
            'sorted': self._sorted,
            'import': self._libBaseImport,
        }

    @property
    def _undef(self):
        '''
        This constant can be used to unset variables and derefs.

        Examples:

            // Unset the variable $foo
            $foo = $lib.undef

            // Remove a dictionary key bar
            $foo.bar = $lib.undef

            // Remove a list index of 0
            $foo.0 = $lib.undef
        '''
        return undef

    @property
    def _true(self):
        '''
        This constant represents a value of True that can be used in Storm. It is not called like a function, it can
        be directly used.

        Examples:
            Conditionally print a statement based on the constant value::

                cli> storm if $lib.true { $lib.print('Is True') } else { $lib.print('Is False') }
                Is True

        '''
        return True

    @property
    def _false(self):
        '''
        This constant represents a value of True that can be used in Storm. It is not called like a function, it can
        be directly used.

        Examples:
            Conditionally print a statement based on the constant value::

                cli> storm if $lib.false { $lib.print('Is True') } else { $lib.print('Is False') }
                Is False

        '''
        return False

    @property
    def _null(self):
        '''
        This constant represents a value of None that can be used in Storm. It is not called like a function, it can
        be directly used.

        Examples:
            Create a dictionary object with a key whose value is null, and call ``$lib.fire()`` with it::

                cli> storm $d=$lib.dict(key=$lib.null) $lib.fire('demo', d=$d)
                ('storm:fire', {'type': 'demo', 'data': {'d': {'key': None}}})

        '''
        return None

    @stormfunc(readonly=True)
    async def _libBaseImport(self, name):
        '''
        Import a Storm Package.

        Args:
            name (str): Name of the package to import.

        Returns:
            Lib: A StormLib instance representing the imported Package.
        '''
        mdef = await self.runt.snap.core.getStormMod(name)
        if mdef is None:
            mesg = f'No storm module named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        text = mdef.get('storm')
        modconf = mdef.get('modconf')

        query = await self.runt.getStormQuery(text)

        perm = ('storm', 'asroot', 'mod') + tuple(name.split('.'))

        asroot = self.runt.allowed(perm)
        if mdef.get('asroot', False) and not asroot:
            mesg = f'Module ({name}) elevates privileges.  You need perm: storm.asroot.mod.{name}'
            raise s_exc.AuthDeny(mesg=mesg)

        modr = self.runt.getModRuntime(query, opts={'vars': {'modconf': modconf}})
        modr.asroot = asroot

        async for item in modr.execute():
            await asyncio.sleep(0) # pragma: no cover

        modlib = Lib(modr)
        modlib.locls.update(modr.vars)
        modlib.locls['__module__'] = mdef

        return modlib

    @stormfunc(readonly=True)
    async def _cast(self, name, valu):
        '''
        Normalize a value as a Synapse Data Model Type.

        Args:
            name (str): The name of the model type to normalize the value as.
            valu: The value to normalize.

        Returns:
            A object representing the normalized value.
        '''

        name = await toprim(name)
        valu = await toprim(valu)

        typeitem = self.runt.snap.core.model.type(name)
        if typeitem is None:
            mesg = f'No type found for name {name}.'
            raise s_exc.NoSuchType(mesg=mesg)

        #TODO an eventual mapping between model types and storm prims

        norm, info = typeitem.norm(valu)
        return fromprim(norm, basetypes=False)

    @stormfunc(readonly=True)
    async def _exit(self):
        raise s_stormctrl.StormExit()

    @stormfunc(readonly=True)
    async def _sorted(self, valu):
        '''
        Yield sorted values.

        Args:
            valu: An iterable oject to sort.

        Returns:
            Yields the sorted output.
        '''
        valu = await toiter(valu)
        for item in sorted(valu):
            yield item

    async def _set(self, *vals):
        '''
        Get a Storm Set object.

        Args:
            *vals: Initial values to place in the set.

        Returns:
            Set: A Storm Set object.
        '''
        return Set(set(vals))

    async def _list(self, *vals):
        '''
        Get a Storm List object.

        Args:
            *vals: Initial values to place in the list.

        Returns:
            List: A Storm List object.
        '''
        return List(list(vals))

    async def _text(self, *args):
        '''
        Get a Storm Text object.

        Args:
            *args: An initial set of values to place in the Text. These values are joined together with an empty string.

        Returns:
            Text: A Storm Text object.

        '''
        valu = ''.join(args)
        return Text(valu)

    @stormfunc(readonly=True)
    async def _guid(self, *args):
        '''
        Get a random guid, or generate a guid from the arguments.

        Args:
            *args: Arguments which are hashed to create a guid.

        Returns:
            str: A guid.
        '''
        if args:
            return s_common.guid(args)
        return s_common.guid()

    @stormfunc(readonly=True)
    async def _len(self, item):
        '''
        Get the length of a item.

        This could represent the size of a string, or the number of keys in
        a dictionary, or the number of elements in an array.

        Args:
            item: The item to get the length of.

        Returns:
            int: The length.
        '''
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
        '''
        Get the minimum value in a list of arguments

        Args:
            *args: List of arguments to evaluate.

        Returns:
            The smallest argument.
        '''
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
        '''
        Get the maximum value in a list of arguments

        Args:
            *args: List of arguments to evaluate.

        Returns:
            The largest argument.
        '''
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
    def _get_mesg(mesg, **kwargs):
        if not isinstance(mesg, str):
            mesg = repr(mesg)
        elif kwargs:
            mesg = kwarg_format(mesg, **kwargs)
        return mesg

    @stormfunc(readonly=True)
    async def _print(self, mesg, **kwargs):
        '''
        Print a message to the runtime.

        Args:
            mesg (str): String to print.

            **kwargs: Keyword arguments to substitute into the mesg.

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

        Returns:
            None: Returns None.
        '''
        mesg = self._get_mesg(mesg, **kwargs)
        await self.runt.printf(mesg)

    @stormfunc(readonly=True)
    async def _pprint(self, item, prefix='', clamp=None):
        '''
        The pprint API should not be considered a stable interface.
        '''
        if clamp is not None:
            clamp = await toint(clamp)

            if clamp < 3:
                mesg = 'Invalid clamp length.'
                raise s_exc.StormRuntimeError(mesg=mesg, clamp=clamp)

        lines = pprint.pformat(item).splitlines()

        for line in lines:
            fline = f'{prefix}{line}'
            if clamp and len(fline) > clamp:
                await self.runt.printf(f'{fline[:clamp-3]}...')
            else:
                await self.runt.printf(fline)

    @stormfunc(readonly=True)
    async def _warn(self, mesg, **kwargs):
        '''
        Print a warning message to the runtime.

        Args:
            mesg (str): String to warn.

            **kwargs: Keyword arguments to substitute into the mesg.

        Notes:
            Arbitrary objects can be warned as well. They will have their Python __repr()__ printed.

        Returns:
            None: Returns None.
        '''
        mesg = self._get_mesg(mesg, **kwargs)
        await self.runt.warn(mesg, log=False)

    @stormfunc(readonly=True)
    async def _dict(self, **kwargs):
        '''
        Get a Storm Dict object.

        Args:
            **kwargs: An initial set of keyword arguments to place in the Dict.

        Returns:
            Dict: A Storm Dict object.
        '''
        return Dict(kwargs)

    @stormfunc(readonly=True)
    async def _fire(self, name, **info):
        '''
        Fire an event onto the runtime.

        Args:
            name: The type of the event to fire.

            **info: Additional keyword arguments containing data to add to the event.

        Notes:
            This fires events as ``storm:fire`` event types. The name of the event is placed into a ``type`` key,
            and any additional keyword arguments are added to a dictionary under the ``data`` key.

        Examples:
            Fire an event called ``demo`` with some data::

                cli> storm $foo='bar' $lib.fire('demo', foo=$foo, knight='ni')
                ...
                ('storm:fire', {'type': 'demo', 'data': {'foo': 'bar', 'knight': 'ni'}})
                ...

        Returns:
            None: Returns None
        '''
        info = await toprim(info)
        s_common.reqjsonsafe(info)
        await self.runt.snap.fire('storm:fire', type=name, data=info)

@registry.registerLib
class LibPs(Lib):
    '''
    A Storm Library for interacting with running tasks on the Cortex.
    '''
    _storm_lib_path = ('ps',)

    def getObjLocals(self):
        return {
            'kill': self._kill,
            'list': self._list,
        }

    async def _kill(self, prefix):
        '''
        Stop a running task on the cortex.

        Args:
            prefix (str): The prefix of the task to stop. Tasks will only be stopped if there is a single prefix match.

        Returns:
            bool: True if the task was cancelled, false otherwise.
        '''
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
        '''
        List tasks the current user can access.

        Returns:
            list: A list of task dictionaries.
        '''
        todo = s_common.todo('ps', self.runt.user)
        return await self.dyncall('cell', todo)

@registry.registerLib
class LibStr(Lib):
    '''
    A Storm Library for interacting with strings.
    '''
    _storm_lib_path = ('str',)

    def getObjLocals(self):
        return {
            'join': self.join,
            'concat': self.concat,
            'format': self.format,
        }

    async def concat(self, *args):
        '''
        Concatenate a set of strings together.

        Args:
            *args: Items to join togther.

        Returns:
            str: The joined string.
        '''
        strs = [str(a) for a in args]
        return ''.join(strs)

    async def format(self, text, **kwargs):
        '''
        Format a text string.

        Args:
            text: The base text string.
            **kwargs: Keyword values which are substituted into the string.

        Examples:
            Format a string with a fixed argument and a variable::

                cli> storm $list=(1,2,3,4)
                     $str=$lib.str.format('Hello {name}, your list is {list}!', name='Reader', list=$list)
                     $lib.print($str)

                Hello Reader, your list is ['1', '2', '3', '4']!

        Returns:
            str: The new string.
        '''
        text = kwarg_format(text, **kwargs)

        return text

    async def join(self, sepr, items):
        '''
        Join items into a string using a separator.

        Args:
            sepr (str): The separator used to join things with.
            items (list): A list of items to join together.

        Examples:
            Join together a list of strings with a dot separator::

                cli> storm $foo=$lib.str.join('.', ('rep', 'vtx', 'tag')) $lib.print($foo)

                rep.vtx.tag

        Returns:
            str: The joined string.
        '''
        strs = [str(item) for item in items]
        return sepr.join(strs)

@registry.registerLib
class LibAxon(Lib):
    '''
    A Storm library for interacting with the Cortex's Axon.
    '''
    _storm_lib_path = ('axon',)

    def getObjLocals(self):
        return {
            'wget': self.wget,
            'urlfile': self.urlfile,
        }

    async def wget(self, url, headers=None, params=None, method='GET', json=None, body=None, ssl=True, timeout=None):
        '''
        A method to download an HTTP(S) resource into the Cortex's Axon.

        Args:
            url (str): The URL to download
            headers (dict): An optional dictionary of HTTP headers to send.
            params (dict): An optional dictionary of URL parameters to add.
            method (str): The HTTP method to use ( default: GET ).
            json (dict): A JSON object to send as the body.
            body (bytes): A bytes to send as the body.
            ssl (bool): Set to False to disable SSL/TLS certificate verification.
            timeout (int): Timeout for the download operation.

        Returns:
            dict: A status dictionary of metadata

        Example:

            $headers = $lib.dict()
            $headers."User-Agent" = Foo/Bar

            $resp = $lib.axon.wget(http://vertex.link, method=GET, headers=$headers)
            if $resp.ok { $lib.print("Downloaded: {size} bytes", size=$resp.size) }

        '''

        self.runt.confirm(('storm', 'lib', 'axon', 'wget'))

        url = await tostr(url)
        method = await tostr(method)

        ssl = await tobool(ssl)
        body = await toprim(body)
        json = await toprim(json)
        params = await toprim(params)
        headers = await toprim(headers)
        timeout = await toprim(timeout)

        await self.runt.snap.core.getAxon()

        axon = self.runt.snap.core.axon
        return await axon.wget(url, headers=headers, params=params, method=method, ssl=ssl, body=body, json=json, timeout=timeout)

    async def urlfile(self, *args, **kwargs):
        '''
        Retrive the target URL using the wget() function and construct an inet:urlfile node from the response.

        Args: see $lib.axon.wget()

        Returns:
            inet:urlfile node on success.  $lib.null on error.
        '''
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

@registry.registerLib
class LibBytes(Lib):
    '''
    A Storm Library for interacting with bytes storage.
    '''
    _storm_lib_path = ('bytes',)

    def getObjLocals(self):
        return {
            'put': self._libBytesPut,
            'has': self._libBytesHas,
            'size': self._libBytesSize,
            'upload': self._libBytesUpload,
        }

    async def _libBytesUpload(self, genr):
        '''
        Upload a stream of bytes to the Axon as a file.

        Examples:
            ($size, $sha256) = $lib.bytes.upload($getBytesChunks())

        Returns:
            (int, str): Returns a tuple of the file size and sha256.
        '''
        await self.runt.snap.core.getAxon()
        async with await self.runt.snap.core.axon.upload() as upload:
            async for byts in s_coro.agen(genr):
                await upload.write(byts)
            size, sha256 = await upload.save()
            return size, s_common.ehex(sha256)

    async def _libBytesHas(self, sha256):
        '''
        Check if the Axon the Cortex is configured to use has a given sha256 value.

        Args:
            sha256 (str): The sha256 value to check.

        Examples:
            Check if the Axon has a given file::

                # This example assumes the Axon does have the bytes
                cli> storm if $lib.bytes.has(9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08) {
                        $lib.print("Has bytes")
                    } else {
                        $lib.print("Does not have bytes")
                    }

                Has bytes

        Returns:
            bool: True if the Axon has the file, false if it does not.
        '''
        await self.runt.snap.core.getAxon()
        todo = s_common.todo('has', s_common.uhex(sha256))
        ret = await self.dyncall('axon', todo)
        return ret

    async def _libBytesSize(self, sha256):
        '''
        Return the size of the bytes stored in the Axon for the given sha256.

        Args:
            sha256 (str): The sha256 value to check.

        Examples:

            $size = $lib.bytes.size($sha256)

        Returns:
            int: The size of the file or $lib.null if the file is not found.
        '''
        await self.runt.snap.core.getAxon()
        todo = s_common.todo('size', s_common.uhex(sha256))
        ret = await self.dyncall('axon', todo)
        return ret

    async def _libBytesPut(self, byts):
        '''
        Save the given bytes variable to the Axon the Cortex is configured to use.

        Args:
            byts (bytes): The bytes to save.

        Examples:
            Save a base64 encoded buffer to the Axon::

                cli> storm $s='dGVzdA==' $buf=$lib.base64.decode($s) ($size, $sha256)=$lib.bytes.put($buf)
                     $lib.print('size={size} sha256={sha256}', size=$size, sha256=$sha256)

                size=4 sha256=9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08

        Returns:
            (int, str): The size of the bytes and the sha256 hash for the bytes.
        '''
        if not isinstance(byts, bytes):
            mesg = '$lib.bytes.put() requires a bytes argument'
            raise s_exc.BadArg(mesg=mesg)

        await self.runt.snap.core.getAxon()
        todo = s_common.todo('put', byts)
        size, sha2 = await self.dyncall('axon', todo)

        return (size, s_common.ehex(sha2))

@registry.registerLib
class LibLift(Lib):
    '''
    A Storm Library for interacting with lift helpers.
    '''
    _storm_lib_path = ('lift',)

    def getObjLocals(self):
        return {
            'byNodeData': self._byNodeData,
        }

    async def _byNodeData(self, name):
        '''
        Lift nodes which have a given nodedata name set on them.

        Args:
            name (str): The name to of the nodedata key to lift by.

        Returns:
            Yields nodes to the pipeline. This must be used in conjunction with the ``yield`` keyword.
        '''
        async for node in self.runt.snap.nodesByDataName(name):
            yield node

@registry.registerLib
class LibTime(Lib):
    '''
    A Storm Library for interacting with timestamps.
    '''
    _storm_lib_path = ('time',)

    def getObjLocals(self):
        return {
            'now': self._now,
            'fromunix': self._fromunix,
            'parse': self._parse,
            'format': self._format,
            'sleep': self._sleep,
            'ticker': self._ticker,
        }

    # TODO from other iso formats!
    def _now(self):
        '''
        Get the current epoch time in milliseconds.

        Returns:
            int: Epoch time in milliseconds.
        '''
        return s_common.now()

    async def _format(self, valu, format):
        '''
        Format a Synapse timestamp into a string value using ``datetime.strftime()``.

        Args:
            valu (int): A timestamp in epoch milliseconds.
            format (str): The strftime format string.

        Examples:
            Format a timestamp into a string::

                cli> storm $now=$lib.time.now() $str=$lib.time.format($now, '%A %d, %B %Y') $lib.print($str)

                Tuesday 14, July 2020

        Returns:
            str: The formatted time string.
        '''
        timetype = self.runt.snap.core.model.type('time')
        # Give a times string a shot at being normed prior to formating.
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

    async def _parse(self, valu, format):
        '''
        Parse a timestamp string using ``datetime.strptime()`` into an epoch timestamp.

        Args:
            valu (str): The timestamp string to parse.
            format (str): The format string to use for parsing.

        Examples:
            Parse a string as for its month/day/year value into a timestamp::

                cli> storm $s='06/01/2020' $ts=$lib.time.parse($s, '%m/%d/%Y') $lib.print($ts)

                1590969600000

        Returns:
            int: The epoch timetsamp for the string.
        '''
        try:
            dt = datetime.datetime.strptime(valu, format)
        except ValueError as e:
            mesg = f'Error during time parsing - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu,
                                          format=format) from None
        return int((dt - s_time.EPOCH).total_seconds() * 1000)

    async def _sleep(self, valu):
        '''
        Pause the processing of data in the storm query.

        Args:
            valu (int): The number of seconds to pause for.

        Notes:
            This has the effect of clearing the Snap's cache, so any node lifts performed
            after the ``$lib.time.sleep(...)`` executes will be lifted directly from storage.

        Returns:

        '''
        await self.runt.snap.waitfini(timeout=float(valu))
        await self.runt.snap.clearCache()

    async def _ticker(self, tick, count=None):
        '''
        Periodically pause the processing of data in the storm query.

        Args:
            tick (int): The amount of time to wait between each tick, in seconds.

            count (int): The number of times to pause the query before exiting the loop. This defaults to None and will
            yield forever if not set.

        Notes:
            This has the effect of clearing the Snap's cache, so any node lifts performed
            after each tick will be lifted directly from storage.

        Returns:
            int: This yields the current tick count after each time it wakes up.
        '''

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
        '''
        Normalize a timestamp from a unix epoch time in seconds to milliseconds.

        Args:
            secs (int): Unix epoch time in seconds.

        Examples:
            Convert a timestamp from seconds to millis and format it::

                cli> storm $seconds=1594684800 $millis=$lib.time.fromunix($seconds)
                     $str=$lib.time.format($millis, '%A %d, %B %Y') $lib.print($str)

                Tuesday 14, July 2020

        Returns:
            int: The normalized time in milliseconds.
        '''
        secs = float(secs)
        return int(secs * 1000)

@registry.registerLib
class LibRegx(Lib):
    '''
    A Storm library for searching/matching with regular expressions.
    '''
    _storm_lib_path = ('regex',)

    def __init__(self, runt, name=()):
        Lib.__init__(self, runt, name=name)
        self.compiled = {}

    def getObjLocals(self):
        return {
            'search': self.search,
            'matches': self.matches,
            'flags': {'i': regex.I, 'm': regex.M},
        }

    async def _getRegx(self, pattern, flags):
        lkey = (pattern, flags)
        regx = self.compiled.get(lkey)
        if regx is None:
            regx = self.compiled[lkey] = regex.compile(pattern, flags=flags)
        return regx

    async def matches(self, pattern, text, flags=0):
        '''
        Returns $lib.true if the text matches the pattern, otherwise $lib.false.

        Notes:

            This API requires the pattern to match at the start of the string.

        Example:

            if $lib.regex.matches("^[0-9]+.[0-9]+.[0-9]+$", $text) {
                $lib.print("It's semver! ...probably")
            }

        '''
        text = await tostr(text)
        flags = await toint(flags)
        pattern = await tostr(pattern)
        regx = await self._getRegx(pattern, flags)
        return regx.match(text) is not None

    async def search(self, pattern, text, flags=0):
        '''
        Search the given text for the pattern and return the matching groups.

        Note:

            In order to get the matching groups, patterns must use parentheses
            to indicate the start and stop of the regex to return portions of.
            If groups are not used, a successful match will return a empty list
            and a unsuccessful match will return ``$lib.null``.

        Example:

            $m = $lib.regex.search("^([0-9])+.([0-9])+.([0-9])+$", $text)
            if $m {
                ($maj, $min, $pat) = $m
            }

        '''
        text = await tostr(text)
        flags = await toint(flags)
        pattern = await tostr(pattern)
        regx = await self._getRegx(pattern, flags)

        m = regx.search(text)
        if m is None:
            return None

        return m.groups()

@registry.registerLib
class LibCsv(Lib):
    '''
    A Storm Library for interacting with csvtool.
    '''
    _storm_lib_path = ('csv',)

    def getObjLocals(self):
        return {
            'emit': self._libCsvEmit,
        }

    async def _libCsvEmit(self, *args, table=None):
        '''
        Emit a csv:row event for the given args.

        Args:
            *args: A list of items which are emitted as a ``csv:row`` event.

            table (str): The name of the table to emit data too. Optional.

        Returns:
            None: Returns None.
        '''
        row = [await toprim(a) for a in args]
        await self.runt.snap.fire('csv:row', row=row, table=table)

@registry.registerLib
class LibFeed(Lib):
    '''
    A Storm Library for interacting with Cortex feed functions.
    '''
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
        '''
        Yield nodes being added to the graph by adding data with a given ingest type.

        Args:
            name (str): Name of the ingest function to send data too.

            data: Data to feed to the ingest function.

        Notes:
            This is using the Runtimes's Snap to call addFeedNodes().
            This only yields nodes if the feed function yields nodes.
            If the generator is not entirely consumed there is no guarantee
            that all of the nodes which should be made by the feed function
            will be made.

        Returns:
            s_node.Node: An async generator that yields nodes.
        '''
        name = await tostr(name)
        data = await toprim(data)

        self.runt.layerConfirm(('feed:data', *name.split('.')))
        with s_provenance.claim('feed:data', name=name):
            return self.runt.snap.addFeedNodes(name, data)

    async def _libList(self):
        '''
        Get a list of feed functions.

        Returns:
            list: A list of feed functions.
        '''
        todo = ('getFeedFuncs', (), {})
        return await self.runt.dyncall('cortex', todo)

    async def _libIngest(self, name, data):
        '''
        Add nodes to the graph with a given ingest type.

        Args:
            name (str): Name of the ingest function to send data too.

            data: Data to feed to the ingest function.

        Notes:
            This is using the Runtimes's Snap to call addFeedData(), after setting
            the snap.strict mode to False. This will cause node creation and property
            setting to produce warning messages, instead of causing the Storm Runtime
            to be torn down.
        '''
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

    _storm_lib_path = ('pipe',)

    def getObjLocals(self):
        return {
            'gen': self._methPipeGen,
        }

    async def _methPipeGen(self, filler, size=10000):
        '''
        Generate and return a Storm Pipe by name.

        Args:
            filler (storm): A storm query to fill the Pipe.
            name (str): A name for the pipe (for IPC).

        Perms:
            storm.pipe.gen

        Notes:
            The filler query is run in parallel with $pipe.

        Examples:

            $pipe = $lib.pipe.gen(${ $pipe.puts((1, 2, 3)) })

            for $items in $pipe.slices(size=2) {
                $dostuff($items)
            }
        '''

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
        runt = self.runt.getModRuntime(query, opts=opts)

        async def coro():
            try:
                async for item in runt.execute():
                    await asyncio.sleep(0)

            except asyncio.CancelledError: # pragma: no cover
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
        '''
        Add a list of items to the Pipe.

        Args:
            items (list): A list of items to add.
        '''
        items = await toprim(items)
        return await self.queue.puts(items)

    async def _methPipePut(self, item):
        '''
        Add a single item to the Pipe.

        Args:
            item: An object to add to the Pipe.
        '''
        item = await toprim(item)
        return await self.queue.put(item)

    async def close(self):
        '''
        Close the pipe for writing.  This will cause
        the slice()/slices() API to return once drained.
        '''
        await self.queue.close()

    async def _methPipeSize(self):
        '''
        Retrieve the number of items in the Pipe.

        Returns:
            int: The number of items in the Pipe.
        '''
        return await self.queue.size()

    async def _methPipeSlice(self, size=1000):
        '''
        Return a list of up to size items from the Pipe.

        Args:
            size: The max number of items to return (default 1000)

        Returns:
            list: A list of at least 1 item from the Pipe.
        '''
        size = await toint(size)
        if size < 1 or size > 10000:
            mesg = '$pipe.slice() size must be 1-10000'
            raise s_exc.BadArg(mesg=mesg)

        items = await self.queue.slice(size=size)
        if items is None:
            return None

        return List(items)

    async def _methPipeSlices(self, size=1000):
        '''
        Yield lists of up to size items from the Pipe.
        The loop will exit when the Pipe is closed and empty.

        Args:
            size (int): The max number of items to yield per slice.

        Returns:
            generator

        Examples:

            for $slice in $pipe.slices(1000) {
                for $item in $slice { $dostuff($item) }
            }

            for $slice in $pipe.slices(1000) {
                $dostuff_batch($slice)
            }
        '''
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
        '''
        Add a Queue to the Cortex with a given name.

        Args:
            name (str): The name of the queue.

        Returns:
            Queue: A Storm Queue object.
        '''

        info = {
            'time': s_common.now(),
            'creator': self.runt.snap.user.iden,
        }

        todo = s_common.todo('addCoreQueue', name, info)
        gatekeys = ((self.runt.user.iden, ('queue', 'add'), None),)
        info = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return Queue(self.runt, name, info)

    async def _methQueueGet(self, name):
        '''
        Get an existing Storm Queue object.

        Args:
            name (str): The name of the Queue to get.

        Returns:
            Queue: A Storm Queue object.
        '''
        todo = s_common.todo('getCoreQueue', name)
        gatekeys = ((self.runt.user.iden, ('queue', 'get'), f'queue:{name}'),)
        info = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return Queue(self.runt, name, info)

    async def _methQueueGen(self, name):
        '''
        Get/add a Storm Queue in a single operation.

        Args:
            name (str): The name of the Queue to get/add.

        Returns:
            Queue: A Storm Queue object.
        '''
        try:
            return await self._methQueueGet(name)
        except s_exc.NoSuchName:
            return await self._methQueueAdd(name)

    async def _methQueueDel(self, name):
        '''
        Delete a given named Queue.

        Args:
            name (str): The name of the queue to delete.

        Returns:
            None: Returns None.
        '''
        todo = s_common.todo('delCoreQueue', name)
        gatekeys = ((self.runt.user.iden, ('queue', 'del',), f'queue:{name}'), )
        await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueList(self):
        '''
        Get a list of the Queues in the Cortex.

        Returns:
            list: A list of queue definitions the current user is allowed to interact with.
        '''
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
    A StormLib API instance of a named channel in the cortex multiqueue.
    '''

    def __init__(self, runt, name, info):

        StormType.__init__(self)
        self.runt = runt
        self.name = name
        self.info = info

        self.gateiden = f'queue:{name}'

        self.locls.update(self.getObjLocals())

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
        todo = s_common.todo('coreQueueCull', self.name, offs)
        gatekeys = self._getGateKeys('get')
        await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueSize(self):
        todo = s_common.todo('coreQueueSize', self.name)
        gatekeys = self._getGateKeys('get')
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueGets(self, offs=0, wait=True, cull=False, size=None):
        wait = await toint(wait)
        offs = await toint(offs)

        if size is not None:
            size = await toint(size)

        todo = s_common.todo('coreQueueGets', self.name, offs, cull=cull, wait=wait, size=size)
        gatekeys = self._getGateKeys('get')

        async for item in self.runt.dyniter('cortex', todo, gatekeys=gatekeys):
            yield item

    async def _methQueuePuts(self, items):
        items = await toprim(items)
        todo = s_common.todo('coreQueuePuts', self.name, items)
        gatekeys = self._getGateKeys('put')
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueGet(self, offs=0, cull=True, wait=True):

        offs = await toint(offs)
        wait = await toint(wait)

        todo = s_common.todo('coreQueueGet', self.name, offs, cull=cull, wait=wait)
        gatekeys = self._getGateKeys('get')

        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueuePop(self, offs=None):

        offs = await toint(offs, noneok=True)
        gatekeys = self._getGateKeys('get')

        # emulate the old behavior on no argument
        if offs is None:
            todo = s_common.todo('coreQueueGets', self.name, 0, cull=True, wait=False)
            async for item in self.runt.dyniter('cortex', todo, gatekeys=gatekeys):
                await self._methQueueCull(item[0])
                return item
            return

        todo = s_common.todo('coreQueuePop', self.name, offs)
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueuePut(self, item):
        return await self._methQueuePuts((item,))

    def _getGateKeys(self, perm):
        return ((self.runt.user.iden, ('queue', perm), self.gateiden),)

@registry.registerLib
class LibTelepath(Lib):
    '''
    A Storm Library for making Telepath connections to remote services.
    '''
    _storm_lib_path = ('telepath',)

    def getObjLocals(self):
        return {
            'open': self._methTeleOpen,
        }

    async def _methTeleOpen(self, url):
        '''
        Open and return a telepath RPC proxy.

        Args:
            url (str): The Telepath URL to connect to.

        Returns:
            Proxy: A Storm Proxy representing a Telepath Proxy.
        '''
        url = await tostr(url)
        scheme = url.split('://')[0]
        self.runt.confirm(('lib', 'telepath', 'open', scheme))
        return Proxy(await self.runt.getTeleProxy(url))

# @registry.registerType
class Proxy(StormType):

    def __init__(self, proxy, path=None):
        StormType.__init__(self, path=path)
        self.proxy = proxy

    async def deref(self, name):

        if name[0] == '_':
            mesg = f'No proxy method named {name}'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        meth = getattr(self.proxy, name, None)

        if isinstance(meth, s_telepath.GenrMethod):
            return ProxyGenrMethod(meth)

        if isinstance(meth, s_telepath.Method):
            return ProxyMethod(meth)

# @registry.registerType
class ProxyMethod(StormType):

    def __init__(self, meth, path=None):
        StormType.__init__(self, path=path)
        self.meth = meth

    async def __call__(self, *args, **kwargs):
        args = await toprim(args)
        kwargs = await toprim(kwargs)
        # TODO: storm types fromprim()
        return await self.meth(*args, **kwargs)

# @registry.registerType
class ProxyGenrMethod(StormType):

    def __init__(self, meth, path=None):
        StormType.__init__(self, path=path)
        self.meth = meth

    async def __call__(self, *args, **kwargs):
        args = await toprim(args)
        kwargs = await toprim(kwargs)
        async for prim in self.meth(*args, **kwargs):
            # TODO: storm types fromprim()
            yield prim

@registry.registerLib
class LibBase64(Lib):
    '''
    A Storm Library for encoding and decoding base64 data.
    '''
    _storm_lib_path = ('base64',)

    def getObjLocals(self):
        return {
            'encode': self._encode,
            'decode': self._decode
        }

    async def _encode(self, valu, urlsafe=True):
        '''
        Encode a bytes object to a base64 encoded string.

        Args:
            valu (bytes): The object to encode.

            urlsafe (bool): Perform the encoding in a urlsafe manner if true.

        Returns:
            str: A base64 encoded string.
        '''
        try:
            if urlsafe:
                return base64.urlsafe_b64encode(valu).decode('ascii')
            return base64.b64encode(valu).decode('ascii')
        except TypeError as e:
            mesg = f'Error during base64 encoding - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu, urlsafe=urlsafe) from None

    async def _decode(self, valu, urlsafe=True):
        '''
        Decode a string into a bytes object.

        Args:
            valu (str): The string to decode.

            urlsafe (bool): Perform the decoding in a urlsafe manner if true.

        Returns:
            bytes: A bytes object for the decoded data.
        '''
        try:
            if urlsafe:
                return base64.urlsafe_b64decode(valu)
            return base64.b64decode(valu)
        except binascii.Error as e:
            mesg = f'Error during base64 decoding - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu, urlsafe=urlsafe) from None

class Prim(StormType):
    '''
    The base type for all STORM primitive values.
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

    def value(self):
        return self.valu

    async def iter(self):
        return tuple(await s_coro.ornot(self.value))

    async def bool(self):
        return bool(await s_coro.ornot(self.value))

@registry.registerType
class Str(Prim):

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'split': self._methStrSplit,
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
        }

    def __int__(self):
        return int(self.value(), 0)

    def __str__(self):
        return self.value()

    def __len__(self):
        return len(self.valu)

    async def _methEncode(self, encoding='utf8'):
        '''
        Encoding a text values to bytes.

        Args:
            encoding (str): Encoding to use. Defaults to utf8.
        '''
        try:
            return self.valu.encode(encoding)
        except UnicodeEncodeError as e:
            raise s_exc.StormRuntimeError(mesg=str(e), valu=self.valu) from None

    async def _methStrSplit(self, text):
        '''
        Split the string into multiple parts based on a separator.

        Example:

            ($foo, $bar) = $baz.split(":")

        '''
        return self.valu.split(text)

    async def _methStrEndswith(self, text):
        return self.valu.endswith(text)

    async def _methStrStartswith(self, text):
        return self.valu.startswith(text)

    async def _methStrRjust(self, size):
        return self.valu.rjust(await toint(size))

    async def _methStrLjust(self, size):
        return self.valu.ljust(await toint(size))

    async def _methStrReplace(self, oldv, newv, maxv=None):
        '''
        Replace occurrences of a string with a new string,
        optionally restricting the number of replacements.

        Example:
            Replace instances of the string "bar" with the string "baz"::

                $foo.replace('bar', 'baz')
        '''
        if maxv is None:
            return self.valu.replace(oldv, newv)
        else:
            return self.valu.replace(oldv, newv, int(maxv))

    async def _methStrStrip(self, chars=None):
        '''
        Remove leading and trailing characters from a string.

        Args:
            chars (str): A list of characters to remove. If not specified, whitespace is stripped.

        Examples:
            Removing whitespace and specific characters::

                $strippedFoo = $foo.strip()
                $strippedBar = $bar.strip(asdf)

        '''
        return self.valu.strip(chars)

    async def _methStrLstrip(self, chars=None):
        '''
        Remove leading characters from a string.

        Args:
            chars (str): A list of characters to remove. If not specified, whitespace is stripped.

        Examples:
            Removing whitespace and specific characters::

                $strippedFoo = $foo.lstrip()
                $strippedBar = $bar.lstrip(w)

        '''
        return self.valu.lstrip(chars)

    async def _methStrRstrip(self, chars=None):
        '''
        Remove trailing characters from a string.

        Args:
            chars (str): A list of characters to remove. If not specified, whitespace is stripped.

        Examples:
            Removing whitespace and specific characters::

                $strippedFoo = $foo.rstrip()
                $strippedBar = $bar.rstrip(asdf)

        '''
        return self.valu.rstrip(chars)

    async def _methStrLower(self):
        '''
        Get a lowercased the of the string.

        Examples:
            Printing a lowercased string::

                $foo="Duck"
                $lib.print($foo.lower())

        '''
        return self.valu.lower()

@registry.registerType
class Bytes(Prim):

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
        }

    def __len__(self):
        return len(self.valu)

    def __str__(self):
        return self.valu.decode()

    async def _methDecode(self, encoding='utf8'):
        '''
        Decode a bytes to a string.

        Args:
            encoding (str): The encoding to use when decoding the bytes.
        '''
        try:
            return self.valu.decode(encoding)
        except UnicodeDecodeError as e:
            raise s_exc.StormRuntimeError(mesg=str(e), valu=self.valu) from None

    async def _methBunzip(self):
        '''
        Decompress the bytes using bzip2 and return them.

        Example:

            $foo = $mybytez.bunzip()
        '''
        return bz2.decompress(self.valu)

    async def _methBzip(self):
        '''
        Compress the bytes using bzip2 and return them.

        Example:

            $foo = $mybytez.bzip()
        '''
        return bz2.compress(self.valu)

    async def _methGunzip(self):
        '''
        Decompress the bytes using gzip and return them.

        Example:

            $foo = $mybytez.gunzip()
        '''
        return gzip.decompress(self.valu)

    async def _methGzip(self):
        '''
        Compress the bytes using gzip and return them.

        Example:

            $foo = $mybytez.gzip()
        '''
        return gzip.compress(self.valu)

    async def _methJsonLoad(self):
        '''
        Load JSON data from bytes.

        Example:

            $foo = $mybytez.json()
        '''
        return json.loads(self.valu)

@registry.registerType
class Dict(Prim):

    def __iter__(self):
        return self.valu.items()

    async def __aiter__(self):
        for item in self.valu.items():
            yield item

    def __len__(self):
        return len(self.valu)

    async def iter(self):
        return tuple(item for item in self.valu.items())

    async def setitem(self, name, valu):

        if valu is undef:
            self.valu.pop(name, None)
            return

        self.valu[name] = valu

    async def deref(self, name):
        return self.valu.get(name)

    async def value(self):
        return {await toprim(k): await toprim(v) for (k, v) in self.valu.items()}

@registry.registerType
class CmdOpts(Dict):
    '''
    A dictionary like object that holds a reference to a command options namespace.
    ( This allows late-evaluation of command arguments rather than forcing capture )
    '''

    def __iter__(self):
        valu = vars(self.valu.opts)
        return valu.items()

    async def __aiter__(self):
        valu = vars(self.valu.opts)
        for item in valu.items():
            yield item

    def __len__(self):
        valu = vars(self.valu.opts)
        return len(valu)

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

@registry.registerType
class Set(Prim):

    def __init__(self, valu, path=None):
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

    def __iter__(self):
        for item in self.valu:
            yield item

    async def __aiter__(self):
        for item in self.valu:
            yield item

    def __len__(self):
        return len(self.valu)

    async def _methSetSize(self):
        return len(self)

    async def _methSetHas(self, item):
        return item in self.valu

    async def _methSetAdd(self, *items):
        [self.valu.add(i) for i in items]

    async def _methSetAdds(self, *items):
        for item in items:
            [self.valu.add(i) for i in item]

    async def _methSetRem(self, *items):
        [self.valu.discard(i) for i in items]

    async def _methSetRems(self, *items):
        for item in items:
            [self.valu.discard(i) for i in item]

    async def _methSetList(self):
        return list(self.valu)

@registry.registerType
class List(Prim):

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'has': self._methListHas,
            'pop': self._methListPop,
            'size': self._methListSize,
            'index': self._methListIndex,
            'length': self._methListLength,
            'append': self._methListAppend,
        }

    def __iter__(self):
        for item in self.valu:
            yield item

    async def setitem(self, name, valu):

        indx = await toint(name)

        if valu is undef:
            try:
                self.valu.pop(indx)
            except IndexError:
                pass
            return

        self.valu[indx] = valu

    async def _derefGet(self, name):
        return await self._methListIndex(name)

    async def __aiter__(self):
        for item in self:
            yield item

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
        '''
        Pop and return the last entry in the list.
        '''
        try:
            return self.valu.pop()
        except IndexError:
            mesg = 'The list is empty.  Nothing to pop.'
            raise s_exc.StormRuntimeError(mesg=mesg)

    async def _methListAppend(self, valu):
        '''
        Append a value to the list.
        '''
        self.valu.append(valu)

    async def _methListIndex(self, valu):
        '''
        Return a single field from the list by index.
        '''
        indx = await toint(valu)
        try:
            return self.valu[indx]
        except IndexError as e:
            raise s_exc.StormRuntimeError(mesg=str(e), valurepr=repr(self.valu),
                                          len=len(self.valu), indx=indx) from None

    async def _methListLength(self):
        '''
        Return the length of the list.
        '''
        s_common.deprecated('StormType List.length()')
        return len(self)

    async def _methListSize(self):
        '''
        Return the length of the list.
        '''
        return len(self)

    async def value(self):
        return tuple([await toprim(v) for v in self.valu])

@registry.registerType
class Bool(Prim):

    def __str__(self):
        return str(self.value()).lower()

    def __int__(self):
        return int(self.value())

@registry.registerLib
class LibUser(Lib):
    '''
    A Storm Library for interacting with data about the current user.
    '''
    _storm_lib_path = ('user', )

    def getObjLocals(self):
        return {
            'name': self._libUserName,
            'allowed': self._libUserAllowed,
        }

    # Todo: Plumb vars and profile access via a @property, implement our own __init__
    # which makes the underlying prims to be accessed by the runtime
    def addLibFuncs(self):
        super().addLibFuncs()
        self.locls.update({
            'vars': StormHiveDict(self.runt, self.runt.user.vars),
            'profile': StormHiveDict(self.runt, self.runt.user.profile),
        })

    async def _libUserName(self):
        '''
        Get the name of the current runtime user.

        Returns:
            str: The name of the current user.
        '''
        return self.runt.user.name

    async def _libUserAllowed(self, permname, gateiden=None):
        '''
        Return True/False if the current user has the given permission.
        '''
        permname = await toprim(permname)
        gateiden = await tostr(gateiden, noneok=True)

        perm = tuple(permname.split('.'))
        todo = s_common.todo('isUserAllowed', self.runt.user.iden, perm, gateiden=gateiden)
        return bool(await self.runt.dyncall('cortex', todo))

@registry.registerLib
class LibGlobals(Lib):
    '''
    A Storm Library for interacting with global variables which are persistent across the Cortex.
    '''
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
        '''
        Get a Cortex global variables.

        Args:
            name (str): Name of the variable.

            default: Default value to return if the variable is not set.

        Returns:
            The variable value.
        '''
        self._reqStr(name)

        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('globals', 'get', name), None),)
        todo = s_common.todo('getStormVar', name, default=default)
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methPop(self, name, default=None):
        '''
        Delete a variable value from the Cortex.

        Args:
            name (str): Name of the variable.

            default: Default value to return if the variable is not set.

        Returns:
            The variable value.
        '''
        self._reqStr(name)
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('globals', 'pop', name), None),)
        todo = s_common.todo('popStormVar', name, default=default)
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methSet(self, name, valu):
        '''
        Set a variable value in the Cortex.

        Args:
            name (str): Name of the variable.

            valu: The value to set.

        Returns:
            The variable value.
        '''
        self._reqStr(name)
        valu = await toprim(valu)
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('globals', 'set', name), None),)
        todo = s_common.todo('setStormVar', name, valu)
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methList(self):
        '''
        Get a list of variable names and values.

        Returns:
            list: A list of variable names and values that the user can access.
        '''
        ret = []
        user = self.runt.user

        todo = ('itemsStormVar', (), {})

        async for key, valu in self.runt.dyniter('cortex', todo):
            if allowed(('globals', 'get', key)):
                ret.append((key, valu))
        return ret

@registry.registerType
class StormHiveDict(Prim):

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
            mesg = 'The name of a persistent variable must be a string.'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name)

        return await self.info.set(name, valu)

    def _list(self):
        return list(self.info.items())

    def __iter__(self):
        return list(self.info.items())

    def value(self):
        return self.info.pack()

@registry.registerLib
class LibVars(Lib):
    '''
    A Storm Library for interacting with runtime variables.
    '''
    _storm_lib_path = ('vars',)

    def getObjLocals(self):
        return {
            'get': self._libVarsGet,
            'set': self._libVarsSet,
            'del': self._libVarsDel,
            'list': self._libVarsList,
        }

    async def _libVarsGet(self, name, defv=None):
        '''
        Get the value of a variable from the current Runtime.

        Args:
            name (str): Name of the variable to get.

            defv: The default value returned if the variable is not set in the runtime.

        Returns:
            The value of the variable.
        '''
        return self.runt.getVar(name, defv=defv)

    async def _libVarsSet(self, name, valu):
        '''
        Set the value of a variable in the current Runtime.

        Args:
            name (str): Name of the variable to set.

            valu: The value to set the variable too.

        Returns:
            None: Returns None.
        '''
        self.runt.setVar(name, valu)

    async def _libVarsDel(self, name):
        '''
        Unset a variable in the current Runtime.

        Args:
            name (str): The variable name to remove.

        Returns:
            None: Returns None
        '''
        self.runt.vars.pop(name, None)

    async def _libVarsList(self):
        '''
        Get a list of variables from the current Runtime.

        Returns:
            list: A list of variable names and their values for the current Runtime.
        '''
        return list(self.runt.vars.items())

@registry.registerType
class Query(Prim):
    '''
    A storm primitive representing an embedded query.
    '''
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
        async for node, path in self._getRuntGenr():
            yield node

    async def __aiter__(self):
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

@registry.registerType
class NodeProps(Prim):

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self.get,
            'list': self.list,
        }

    async def _derefGet(self, name):
        return self.valu.get(name)

    async def setitem(self, name, valu):
        '''
        Set a property on a Node.

        Args:
            prop (str): The name of the property to set.

            valu: The value being set.

        Raises:
            s_exc:NoSuchProp: If the property being set is not valid for the node.
            s_exc.BadTypeValu: If the value of the proprerty fails to normalize.
        '''
        name = await tostr(name)
        valu = await toprim(valu)
        return await self.valu.set(name, valu)

    def __iter__(self):
        # Make copies of property values since array types are mutable
        items = tuple((key, copy.deepcopy(valu)) for key, valu in self.valu.props.items())
        for item in items:
            yield item

    @stormfunc(readonly=True)
    async def get(self, name, defv=None):
        return self.valu.get(name)

    @stormfunc(readonly=True)
    async def list(self):
        return list(self.valu.props.items())

    @stormfunc(readonly=True)
    def value(self):
        return dict(self.valu.props)

@registry.registerType
class NodeData(Prim):

    def __init__(self, node, path=None):

        Prim.__init__(self, node, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._getNodeData,
            'set': self._setNodeData,
            'pop': self._popNodeData,
            'list': self._listNodeData,
            'load': self._loadNodeData,
        }

    @stormfunc(readonly=True)
    async def _getNodeData(self, name):
        confirm(('node', 'data', 'get', name))
        return await self.valu.getData(name)

    async def _setNodeData(self, name, valu):
        confirm(('node', 'data', 'set', name))
        valu = await toprim(valu)
        s_common.reqjsonsafe(valu)
        return await self.valu.setData(name, valu)

    async def _popNodeData(self, name):
        confirm(('node', 'data', 'pop', name))
        return await self.valu.popData(name)

    @stormfunc(readonly=True)
    async def _listNodeData(self):
        confirm(('node', 'data', 'list'))
        return [x async for x in self.valu.iterData()]

    @stormfunc(readonly=True)
    async def _loadNodeData(self, name):
        confirm(('node', 'data', 'get', name))
        valu = await self.valu.getData(name)
        # set the data value into the nodedata dict so it gets sent
        self.valu.nodedata[name] = valu

@registry.registerType
class Node(Prim):
    '''
    Implements the STORM api for a node instance.
    '''
    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)

        self.ctors['data'] = self._ctorNodeData
        self.ctors['props'] = self._ctorNodeProps

        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'form': self._methNodeForm,
            'iden': self._methNodeIden,
            'ndef': self._methNodeNdef,
            'pack': self._methNodePack,
            'repr': self._methNodeRepr,
            'tags': self._methNodeTags,
            'edges': self._methNodeEdges,
            'value': self._methNodeValue,
            'globtags': self._methNodeGlobTags,
            'isform': self._methNodeIsForm,
            'getByLayer': self.getByLayer,
            'getStorNodes': self.getStorNodes,
        }

    async def getStorNodes(self):
        '''
        Return a list of "storage nodes" which were fused from the layers to make this node.
        '''
        return await self.valu.getStorNodes()

    def getByLayer(self):
        '''
        Return a dict you can use to lookup which props/tags came from which layers.
        '''
        return self.valu.getByLayer()

    def _ctorNodeData(self, path=None):
        return NodeData(self.valu, path=path)

    def _ctorNodeProps(self, path=None):
        return NodeProps(self.valu, path=path)

    @stormfunc(readonly=True)
    async def _methNodePack(self, dorepr=False):
        '''
        Return the serializable/packed version of the Node.

        Args:
            dorepr (bool): Include repr information for human readable versions of properties.

        Returns:
            (tuple): An (ndef, info) node tuple.
        '''
        return self.valu.pack(dorepr=dorepr)

    @stormfunc(readonly=True)
    async def _methNodeEdges(self, verb=None):
        '''
        Yields the (verb, iden) tuples for this nodes edges.
        '''
        verb = await toprim(verb)
        async for edge in self.valu.iterEdgesN1(verb=verb):
            yield edge

    @stormfunc(readonly=True)
    async def _methNodeIsForm(self, name):
        return self.valu.form.name == name

    @stormfunc(readonly=True)
    async def _methNodeTags(self, glob=None):
        tags = list(self.valu.tags.keys())
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
        '''
        Get the repr for the primary property or secondary propert of a Node.

        Args:
            name (str): Optional name of the secondary property to get the repr for.

            defv (str): Optional default value to return if the secondary property does not exist.

        Returns:
            String repr for the property.

        Raises:
            s_exc.StormRuntimeError: If the secondary property does not exist for the Node form.
        '''
        return self.valu.repr(name=name, defv=defv)

    @stormfunc(readonly=True)
    async def _methNodeIden(self):
        '''
        Get the iden of the Node.

        Returns:
            String value for the Node's iden.
        '''
        return self.valu.iden()

@registry.registerType
class PathMeta(Prim):
    '''
    Put the storm deref/setitem/iter convention on top of path variables.
    '''

    def __init__(self, path):
        Prim.__init__(self, None, path=path)

    async def deref(self, name):
        return self.path.metadata.get(name)

    async def setitem(self, name, valu):
        if valu is undef:
            self.path.metadata.pop(name, None)
            return
        self.path.meta(name, valu)

    async def __aiter__(self):
        # prevent "edit while iter" issues
        for item in list(self.path.metadata.items()):
            yield item

@registry.registerType
class PathVars(Prim):
    '''
    Put the storm deref/setitem/iter convention on top of path variables.
    '''

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
            self.path.popVar(name)
            return
        self.path.setVar(name, valu)

    def __iter__(self):
        # prevent "edit while iter" issues
        for item in list(self.path.vars.items()):
            yield item

    async def __aiter__(self):
        # prevent "edit while iter" issues
        for item in list(self.path.vars.items()):
            yield item

@registry.registerType
class Path(Prim):

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update(self.getObjLocals())
        self.locls.update({
            'vars': PathVars(path),
            'meta': PathMeta(path),
        })

    # Todo: Plumb vars access via a @property
    def getObjLocals(self):
        return {
            'idens': self._methPathIdens,
            'trace': self._methPathTrace,
            'listvars': self._methPathListVars,
        }

    async def _methPathIdens(self):
        return [n.iden() for n in self.valu.nodes]

    async def _methPathTrace(self):
        trace = self.valu.trace()
        return Trace(trace)

    async def _methPathListVars(self):
        '''
        List variables available in the path of a storm query.
        '''
        return list(self.path.vars.items())

@registry.registerType
class Trace(Prim):
    '''
    Storm API wrapper for the Path Trace object.
    '''
    def __init__(self, trace, path=None):
        Prim.__init__(self, trace, path=path)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'idens': self._methTraceIdens,
        }

    async def _methTraceIdens(self):
        return [n.iden() for n in self.valu.nodes]

@registry.registerType
class Text(Prim):
    '''
    A mutable text type for simple text construction.
    '''
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
        text = kwarg_format(text, **kwargs)
        self.valu += text

    async def _methTextStr(self):
        return self.valu

@registry.registerLib
class LibStats(Lib):
    '''
    A Storm Library for statistics related functionality.
    '''
    _storm_lib_path = ('stats',)

    def getObjLocals(self):
        return {
            'tally': self.tally,
        }

    async def tally(self):
        '''
        Get a Tally object.

        Returns:
            Tally: A Storm Tally object.
        '''
        return StatTally(path=self.path)

@registry.registerType
class StatTally(Prim):
    '''
    A tally object.

    $tally = $lib.stats.tally()

    $tally.inc(foo)

    for $name, $total in $tally {
    }

    '''
    def __init__(self, path=None):
        Prim.__init__(self, {}, path=path)
        self.counters = collections.defaultdict(int)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'inc': self.inc,
            'get': self.get,
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

@registry.registerLib
class LibLayer(Lib):
    '''
    A Storm Library for interacting with Layers in the Cortex.
    '''
    _storm_lib_path = ('layer',)

    def getObjLocals(self):
        return {
            'add': self._libLayerAdd,
            'del': self._libLayerDel,
            'get': self._libLayerGet,
            'list': self._libLayerList,
        }

    async def _libLayerAdd(self, ldef=None):
        '''
        Add a layer to the Cortex.

        Args:
            ldef (dict): A Layer definition.

        Returns:
            Layer: A Storm Layer object.
        '''
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
        '''
        Delete a layer from the Cortex.

        Args:
            iden (str): The iden of the layer to delete.

        Returns:
            None: Returns None.
        '''
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
        '''
        Get a Layer from the Cortex.

        Args:
            iden (str): The iden of the layer to get. If not set, this defaults to the default layer of the Cortex.

        Returns:
            Layer: A Storm Layer object.
        '''
        todo = s_common.todo('getLayerDef', iden)
        ldef = await self.runt.dyncall('cortex', todo)
        if ldef is None:
            mesg = f'No layer with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        return Layer(self.runt, ldef, path=self.path)

    async def _libLayerList(self):
        '''
        List the layers in a Cortex:

        Returns:
            list: A list of Storm Layer objects.
        '''
        todo = s_common.todo('getLayerDefs')
        defs = await self.runt.dyncall('cortex', todo)
        return [Layer(self.runt, ldef, path=self.path) for ldef in defs]

@registry.registerType
class Layer(Prim):
    '''
    Implements the STORM api for a layer instance.
    '''
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

        self.locls.update({
            'iden': ldef.get('iden'),
        })
        self.locls.update(self.getObjLocals())

    # Todo: Plumb iden access via a @property
    def getObjLocals(self):
        return {
            'set': self._methLayerSet,
            'get': self._methLayerGet,
            'pack': self._methLayerPack,
            'repr': self._methLayerRepr,
            'edits': self._methLayerEdits,
            'addPush': self._addPush,
            'delPush': self._delPush,
            'addPull': self._addPull,
            'delPull': self._delPull,
            'getTagCount': self._methGetTagCount,
            'getPropCount': self._methGetPropCount,
            'getFormCounts': self._methGetFormcount,
            'getStorNodes': self.getStorNodes,
        }

    async def _addPull(self, url, offs=0):
        '''
        Configure the layer to pull edits from a remote layer/feed.

        Args:
            url (str): The telepath URL to a layer/feed.
            offs (int): The (optional) offset to begin from.

        Perms:
            - admin privs are required on the layer.
            - lib.telepath.open.<scheme>
        '''
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

    async def _delPull(self, iden):
        '''
        Remove a pull config from the layer.
        Args:
            iden (str): The GUID of the push config to remove.

        Perms:
            - admin privs are required on the layer.
        '''
        iden = await tostr(iden)

        layriden = self.valu.get('iden')
        if not self.runt.isAdmin(gateiden=layriden):
            mesg = '$layr.delPull() requires admin privs on the top layer.'
            raise s_exc.AuthDeny(mesg=mesg)

        todo = s_common.todo('delLayrPull', layriden, iden)
        await self.runt.dyncall('cortex', todo)

    async def _addPush(self, url, offs=0):
        '''
        Configure the layer to push edits to a remote layer/feed.

        Args:
            url (str): A telepath URL of the target layer/feed.
            offs (int): The local layer offset to begin pushing from (default: 0).

        Perms:
            - admin privs are required on the layer.
            - lib.telepath.open.<scheme>
        '''
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

    async def _delPush(self, iden):
        '''
        Remove a push config from the layer.
        Args:
            iden (str): The GUID of the push config to remove.

        Perms:
            - admin privs are required on the layer.
        '''
        iden = await tostr(iden)
        layriden = self.valu.get('iden')

        if not self.runt.isAdmin(gateiden=layriden):
            mesg = '$layer.delPush() requires admin privs on the layer.'
            raise s_exc.AuthDeny(mesg=mesg)

        todo = s_common.todo('delLayrPush', layriden, iden)
        await self.runt.dyncall('cortex', todo)

    @stormfunc(readonly=True)
    async def _methGetFormcount(self):
        '''
        Get the formcounts for the Layer.

        Example:
            Get the formcounts for the current :ayer::

                $counts = $lib.layer.get().getFormCounts()

        Returns:
            Dictionary containing form names and the count of the nodes in the Layer.
        '''
        layriden = self.valu.get('iden')
        gatekeys = ((self.runt.user.iden, ('layer', 'read'), layriden),)
        todo = s_common.todo('getFormCounts')
        return await self.runt.dyncall(layriden, todo, gatekeys=gatekeys)

    async def _methGetTagCount(self, tagname, formname=None):
        '''
        Return the number of tag rows in the layer for the given tag name and optional form name.

        Example:
            $count = $lib.layer.get().getTagCount(foo.bar, formname=inet:ipv4)
        '''
        tagname = await tostr(tagname)
        formname = await tostr(formname, noneok=True)
        layriden = self.valu.get('iden')
        gatekeys = ((self.runt.user.iden, ('layer', 'read'), layriden),)
        todo = s_common.todo('getTagCount', tagname, formname=formname)
        return await self.runt.dyncall(layriden, todo, gatekeys=gatekeys)

    async def _methGetPropCount(self, propname, maxsize=None):
        '''
        Return the number of property rows in the layer for the given full form/property name.

        Example:
            $count = $lib.layer.get().getPropCount(inet:ipv4:asn)
        '''
        propname = await tostr(propname)
        maxsize = await toint(maxsize, noneok=True)

        prop = self.runt.snap.core.model.prop(propname)
        if prop is None:
            mesg = f'No property named {propname}'
            raise s_exc.NoSuchProp(mesg)

        if prop.isform:
            todo = s_common.todo('getPropCount', prop.name, None, maxsize=maxsize)
        else:
            todo = s_common.todo('getPropCount', prop.form.name, prop.name, maxsize=maxsize)

        layriden = self.valu.get('iden')
        gatekeys = ((self.runt.user.iden, ('layer', 'read'), layriden),)
        return await self.runt.dyncall(layriden, todo, gatekeys=gatekeys)

    async def _methLayerEdits(self, offs=0, wait=True, size=None):
        '''
        Yield (offs, nodeedits) tuples from the given offset.
        If wait=True, also consume them in real-time once caught up.
        '''
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

    async def getStorNodes(self):
        '''
        Yield (buid, sode) tuples represeting the data stored in this layer.

        NOTE: "storage nodes" (or "sodes") represent *only* the data stored in
              the layer and may not represent whole nodes.
        '''
        layriden = self.valu.get('iden')
        self.runt.confirm(('layer', 'read'), gateiden=layriden)

        todo = s_common.todo('getStorNodes')

        async for item in self.runt.dyniter(layriden, todo):
            yield item

    async def _methLayerGet(self, name, defv=None):
        return self.valu.get(name, defv)

    async def _methLayerSet(self, name, valu):

        name = await tostr(name)

        if name == 'name':
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
        return self.valu

    async def _methLayerRepr(self):
        iden = self.valu.get('iden')
        name = self.valu.get('name', 'unnamed')
        creator = self.valu.get('creator')
        readonly = self.valu.get('readonly')
        return f'Layer: {iden} (name: {name}) readonly: {readonly} creator: {creator}'

@registry.registerLib
class LibView(Lib):
    '''
    A Storm Library for interacting with Views in the Cortex.
    '''
    _storm_lib_path = ('view',)

    def getObjLocals(self):
        return {
            'add': self._methViewAdd,
            'del': self._methViewDel,
            'get': self._methViewGet,
            'list': self._methViewList,
        }

    async def _methViewAdd(self, layers, name=None):
        '''
        Add a View to the Cortex.

        Args:
            layers (list): A list of idens which make up the view.

            name (str): The name of the view.

        Returns:
            View: A Storm View object.
        '''
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
        '''
        Delete a View from the Cortex.

        Args:
            iden (str): The iden of the view to delete.

        Returns:
            None: Returns None.
        '''
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('view', 'del'), iden),)
        todo = ('delView', (iden,), {})
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    @stormfunc(readonly=True)
    async def _methViewGet(self, iden=None):
        '''
        Get a View from the Cortex.

        Args:
            iden (str): The iden of the View to get. If not specified, returns the current View.

        Returns:
            View: A Storm View object.
        '''
        if iden is None:
            iden = self.runt.snap.view.iden
        todo = s_common.todo('getViewDef', iden)
        vdef = await self.runt.dyncall('cortex', todo)
        if vdef is None:
            raise s_exc.NoSuchView(mesg=iden)

        return View(self.runt, vdef, path=self.path)

    @stormfunc(readonly=True)
    async def _methViewList(self):
        '''
        List the Views in the Cortex.

        Returns:
            list: A list of Storm View objects.
        '''
        todo = s_common.todo('getViewDefs')
        defs = await self.runt.dyncall('cortex', todo)
        return [View(self.runt, vdef, path=self.path) for vdef in defs]

@registry.registerType
class View(Prim):
    '''
    Implements the STORM api for a view instance.
    '''
    def __init__(self, runt, vdef, path=None):
        Prim.__init__(self, vdef, path=path)
        self.runt = runt

        self.locls.update({
            'iden': vdef.get('iden'),
            'layers': [Layer(runt, ldef, path=path) for ldef in vdef.get('layers')],
            'triggers': [Trigger(runt, tdef) for tdef in vdef.get('triggers')],
        })
        self.locls.update(self.getObjLocals())

    # Todo plumb in iden/layers/triggers access via a property
    def getObjLocals(self):
        return {
            'set': self._methViewSet,
            'get': self._methViewGet,
            'fork': self._methViewFork,
            'pack': self._methViewPack,
            'repr': self._methViewRepr,
            'merge': self._methViewMerge,
            'getEdges': self._methGetEdges,
            'addNodeEdits': self._methAddNodeEdits,
            'getEdgeVerbs': self._methGetEdgeVerbs,
            'getFormCounts': self._methGetFormcount,
        }

    async def _methAddNodeEdits(self, edits):

        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')
        layriden = self.valu.get('layers')[0].get('iden')

        meta = {'user': useriden}
        todo = s_common.todo('addNodeEdits', edits, meta)

        # ensure the user may make *any* node edits
        gatekeys = ((useriden, ('node',), layriden),)
        return await self.runt.dyncall(viewiden, todo, gatekeys=gatekeys)

    @stormfunc(readonly=True)
    async def _methGetFormcount(self):
        '''
        Get the formcounts for the View.

        Example:
            Get the formcounts for the current View::

                $counts = $lib.view.get().getFormCounts()

        Returns:
            Dictionary containing form names and the count of the nodes in the View's Layers.
        '''
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
        return self.valu

    async def _methViewFork(self, name=None):
        '''
        Fork a view in the cortex.
        '''
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

    async def _methViewMerge(self):
        '''
        Merge a forked view back into its parent.
        '''
        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')
        todo = s_common.todo('merge', useriden=useriden)
        return await self.runt.dyncall(viewiden, todo)

@registry.registerLib
class LibTrigger(Lib):
    '''
    A Storm Library for interacting with Triggers in the Cortex.
    '''
    _storm_lib_path = ('trigger',)

    def getObjLocals(self):
        return {
            'add': self._methTriggerAdd,
            'del': self._methTriggerDel,
            'list': self._methTriggerList,
            'get': self._methTriggerGet,
            'enable': self._methTriggerEnable,
            'disable': self._methTriggerDisable,
            'mod': self._methTriggerMod
        }

    async def _matchIdens(self, prefix):
        '''
        Returns the iden that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        user = self.runt.user

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
        '''
        Add a Trigger to the Cortex.

        Args:
            tdef (dict): A Trigger definition.

        Returns:
            Trigger: A Storm Trigger object.
        '''
        tdef = await toprim(tdef)

        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden

        tdef['user'] = useriden
        tdef['view'] = viewiden

        query = tdef.pop('query', None)
        if query is not None:
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
        '''
        Delete a Trigger from the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a trigger to delete. Only a single matching prefix
            will be deleted.

        Returns:
            str: The iden of the deleted trigger which matched the prefix.
        '''
        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden
        trig = await self._matchIdens(prefix)
        iden = trig.iden

        todo = s_common.todo('delTrigger', iden)
        gatekeys = ((useriden, ('trigger', 'del'), iden),)
        await self.dyncall(viewiden, todo, gatekeys=gatekeys)

        return iden

    async def _methTriggerMod(self, prefix, query):
        '''
        Modify an existing Trigger in the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a trigger to modify.
            Only a single matching prefix will be modified.

            query: The new Storm Query to set as the trigger query.

        Returns:
            str: The iden of the modified Trigger.
        '''
        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden

        trig = await self._matchIdens(prefix)
        iden = trig.iden
        gatekeys = ((useriden, ('trigger', 'set'), iden),)
        todo = s_common.todo('setTriggerInfo', iden, 'storm', query)
        await self.dyncall(viewiden, todo, gatekeys=gatekeys)

        return iden

    async def _methTriggerList(self):
        '''
        Get a list of Triggers in the Cortex.

        Returns:
            list: A List of trigger objects the user is allowed to access.
        '''
        user = self.runt.user
        view = self.runt.snap.view
        triggers = []

        for iden, trig in await view.listTriggers():
            if not allowed(('trigger', 'get'), gateiden=iden):
                continue
            triggers.append(Trigger(self.runt, trig.pack()))

        return triggers

    async def _methTriggerGet(self, iden):
        '''
        Get a Trigger in the Cortex.

        Args:
            iden (str): The iden of the Trigger to get.

        Returns:
            Trigger: A Storm Trigger object.
        '''
        trigger = await self.runt.snap.view.getTrigger(iden)
        if trigger is None:
            return None

        self.runt.confirm(('trigger', 'get'), gateiden=iden)

        return Trigger(self.runt, trigger.pack())

    async def _methTriggerEnable(self, prefix):
        '''
        Enable a Trigger in the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a trigger to modify.
            Only a single matching prefix will be modified.

        Returns:
            str: The iden of the trigger that was enabled.
        '''
        return await self._triggerendisable(prefix, True)

    async def _methTriggerDisable(self, prefix):
        '''
        Disable a Trigger in the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a trigger to modify.
            Only a single matching prefix will be modified.

        Returns:
            str: The iden of the trigger that was disabled.

        '''
        return await self._triggerendisable(prefix, False)

    async def _triggerendisable(self, prefix, state):
        trig = await self._matchIdens(prefix)
        iden = trig.iden

        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden
        gatekeys = ((useriden, ('trigger', 'set'), iden),)
        todo = s_common.todo('enableTrigger', iden)
        todo = s_common.todo('setTriggerInfo', iden, 'enabled', state)
        await self.dyncall(viewiden, todo, gatekeys=gatekeys)

        return iden

@registry.registerType
class Trigger(Prim):

    def __init__(self, runt, tdef):

        Prim.__init__(self, tdef)
        self.runt = runt

        self.locls.update({
            'iden': tdef['iden'],
        })
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'set': self.set,
        }

    async def deref(self, name):
        valu = self.valu.get(name, s_common.novalu)
        if valu is not s_common.novalu:
            return valu

        return self.locls.get(name)

    async def set(self, name, valu):
        trigiden = self.valu.get('iden')
        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden

        gatekeys = ((useriden, ('trigger', 'set'), viewiden),)
        todo = ('setTriggerInfo', (trigiden, name, valu), {})
        await self.runt.dyncall(viewiden, todo, gatekeys=gatekeys)

        self.valu[name] = valu

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
    _storm_lib_path = ('auth',)

    def getObjLocals(self):
        return {
            'ruleFromText': ruleFromText,
        }

@registry.registerLib
class LibUsers(Lib):
    '''
    A Storm Library for interacting with Auth Users in the Cortex.
    '''
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
        '''
        Get a list of Users in the Cortex.

        Returns:
            list: A list of Storm User objects.
        '''
        return [User(self.runt, udef['iden']) for udef in await self.runt.snap.core.getUserDefs()]

    async def _methUsersGet(self, iden):
        '''
        Get a specific User by iden.

        Args:
            iden (str): The iden of the user to retrieve.

        Returns:
            User: A Storm User object; or None if the user does not exist.
        '''
        udef = await self.runt.snap.core.getUserDef(iden)
        if udef is not None:
            return User(self.runt, udef['iden'])

    async def _methUsersByName(self, name):
        '''
        Get a specific user by name.

        Args:
            name (str): The name of the user to retrieve.

        Returns:
            User: A Storm User object; or None if the user does not exist.
        '''
        udef = await self.runt.snap.core.getUserDefByName(name)
        if udef is not None:
            return User(self.runt, udef['iden'])

    async def _methUsersAdd(self, name, passwd=None, email=None):
        '''
        Add a User to the Cortex.

        Args:
            name (str): The name of the user.

            passwd (str): The users password. This is optional.

            email (str): The user's email address. This is optional.

        Returns:
            User: A Storm User object for the new user.
        '''
        self.runt.confirm(('auth', 'user', 'add'))
        udef = await self.runt.snap.core.addUser(name, passwd=passwd, email=email)
        return User(self.runt, udef['iden'])

    async def _methUsersDel(self, iden):
        '''
        Delete a User from the Cortex.

        Args:
            iden (str): The iden of the user to delete.

        Returns:
            None: Returns None.
        '''
        self.runt.confirm(('auth', 'user', 'del'))
        await self.runt.snap.core.delUser(iden)

@registry.registerLib
class LibRoles(Lib):
    '''
    A Storm Library for interacting with Auth Roles in the Cortex.
    '''
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
        '''
        Get a list of Roles in the Cortex.

        Returns:
            list: A list of Storm Role objects.
        '''
        return [Role(self.runt, rdef['iden']) for rdef in await self.runt.snap.core.getRoleDefs()]

    async def _methRolesGet(self, iden):
        '''
        Get a specific Role by iden.

        Args:
            iden (str): The iden of the role to retrieve.

        Returns:
            Role: A Storm Role object; or None if the role does not exist.
        '''
        rdef = await self.runt.snap.core.getRoleDef(iden)
        if rdef is not None:
            return Role(self.runt, rdef['iden'])

    async def _methRolesByName(self, name):
        '''
        Get a specific Role by name.

        Args:
            name (str): The name of the role to retrieve.

        Returns:
            Role: A Storm Role object; or None if the role does not exist.
        '''
        rdef = await self.runt.snap.core.getRoleDefByName(name)
        if rdef is not None:
            return Role(self.runt, rdef['iden'])

    async def _methRolesAdd(self, name):
        '''
        Add a Role to the Cortex.

        Args:
            name (str): The name of the role.

        Returns:
            Role: A Storm Role object for the new user.
        '''
        self.runt.confirm(('auth', 'role', 'add'))
        rdef = await self.runt.snap.core.addRole(name)
        return Role(self.runt, rdef['iden'])

    async def _methRolesDel(self, iden):
        '''
        Delete a Role from the Cortex.

        Args:
            iden (str): The iden of the role to delete.

        Returns:
            None: Returns None.
        '''
        self.runt.confirm(('auth', 'role', 'del'))
        await self.runt.snap.core.delRole(iden)

@registry.registerLib
class LibGates(Lib):
    '''
    A Storm Library for interacting with Auth Gates in the Cortex.
    '''
    _storm_lib_path = ('auth', 'gates')

    def getObjLocals(self):
        return {
            'get': self._methGatesGet,
            'list': self._methGatesList,
        }

    async def _methGatesList(self):
        '''
        Get a list of Gates in the Cortex.

        Returns:
            list: A list of Storm Gate objects.
        '''
        todo = s_common.todo('getAuthGates')
        gates = await self.runt.coreDynCall(todo)
        return [Gate(self.runt, g) for g in gates]

    async def _methGatesGet(self, iden):
        '''
        Get a specific Gate by iden.

        Args:
            iden (str): The iden of the role to retrieve.

        Returns:
            Role: A Storm Gate object; or None if the role does not exist.
        '''
        iden = await toprim(iden)
        todo = s_common.todo('getAuthGate', iden)
        gate = await self.runt.coreDynCall(todo)
        if gate:
            return Gate(self.runt, gate)

@registry.registerType
class Gate(Prim):

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt

        # Todo: Plumb iden/role/users access via a @property and implement getObjLocals
        self.locls.update({
            'iden': valu.get('iden'),
            'users': valu.get('users'),
            'roles': valu.get('roles'),
        })

@registry.registerType
class User(Prim):

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt

        self.locls.update(self.getObjLocals())

    # Todo: Plumb iden access via a @property
    def getObjLocals(self):
        return {
            'iden': self._iden,
            'get': self._methUserGet,
            'roles': self._methUserRoles,
            'allowed': self._methUserAllowed,
            'grant': self._methUserGrant,
            'revoke': self._methUserRevoke,
            'addRule': self._methUserAddRule,
            'delRule': self._methUserDelRule,
            'setRules': self._methUserSetRules,
            'setAdmin': self._methUserSetAdmin,
            'setEmail': self._methUserSetEmail,
            'setLocked': self._methUserSetLocked,
            'setPasswd': self._methUserSetPasswd,
        }

    @property
    def _iden(self):
        '''
        Constant representing the user iden.

        Returns:
            str: The user iden.
        '''
        return self.valu

    async def _derefGet(self, name):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return udef.get(name, s_common.novalu)

    async def _methUserGet(self, name):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return udef.get(name)

    async def _methUserRoles(self):
        udef = await self.runt.snap.core.getUserDef(self.valu)
        return [Role(self.runt, rdef['iden']) for rdef in udef.get('roles')]

    async def _methUserAllowed(self, permname, gateiden=None):
        perm = tuple(permname.split('.'))
        return await self.runt.snap.core.isUserAllowed(self.valu, perm, gateiden=gateiden)

    async def _methUserGrant(self, iden):
        self.runt.confirm(('auth', 'user', 'grant'))
        await self.runt.snap.core.addUserRole(self.valu, iden)

    async def _methUserRevoke(self, iden):
        self.runt.confirm(('auth', 'user', 'revoke'))
        await self.runt.snap.core.delUserRole(self.valu, iden)

    async def _methUserSetRules(self, rules, gateiden=None):
        self.runt.confirm(('auth', 'user', 'set', 'rules'))
        await self.runt.snap.core.setUserRules(self.valu, rules, gateiden=gateiden)

    async def _methUserAddRule(self, rule, gateiden=None):
        self.runt.confirm(('auth', 'user', 'set', 'rules'))
        await self.runt.snap.core.addUserRule(self.valu, rule, gateiden=gateiden)

    async def _methUserDelRule(self, rule, gateiden=None):
        self.runt.confirm(('auth', 'user', 'set', 'rules'))
        await self.runt.snap.core.delUserRule(self.valu, rule, gateiden=gateiden)

    async def _methUserSetEmail(self, email):

        if self.runt.user.iden == self.valu:
            await self.runt.snap.core.setUserEmail(self.valu, email)
            return

        self.runt.confirm(('auth', 'user', 'set', 'email'))
        await self.runt.snap.core.setUserEmail(self.valu, email)

    async def _methUserSetAdmin(self, admin, gateiden=None):

        self.runt.confirm(('auth', 'user', 'set', 'admin'))
        admin = await tobool(admin)

        await self.runt.snap.core.setUserAdmin(self.valu, admin, gateiden=gateiden)

    async def _methUserSetPasswd(self, passwd):

        if self.runt.user.iden == self.valu:
            return await self.runt.snap.core.setUserPasswd(self.valu, passwd)

        self.runt.confirm(('auth', 'user', 'set', 'passwd'))
        return await self.runt.snap.core.setUserPasswd(self.valu, passwd)

    async def _methUserSetLocked(self, locked):
        self.runt.confirm(('auth', 'user', 'set', 'locked'))
        return await self.runt.snap.core.setUserLocked(self.valu, await tobool(locked))

    async def value(self):
        return await self.runt.snap.core.getUserDef(self.valu)

@registry.registerType
class Role(Prim):

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt
        self.locls.update({
            'iden': valu,
        })
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._methRoleGet,
            'addRule': self._methRoleAddRule,
            'delRule': self._methRoleDelRule,
            'setRules': self._methRoleSetRules,
        }

    async def _derefGet(self, name):
        rdef = await self.runt.snap.core.getRoleDef(self.valu)
        return rdef.get(name, s_common.novalu)

    async def _methRoleGet(self, name):
        rdef = await self.runt.snap.core.getRoleDef(self.valu)
        return rdef.get(name)

    async def _methRoleSetRules(self, rules, gateiden=None):
        self.runt.confirm(('auth', 'role', 'set', 'rules'))
        await self.runt.snap.core.setRoleRules(self.valu, rules, gateiden=gateiden)

    async def _methRoleAddRule(self, rule, gateiden=None):
        self.runt.confirm(('auth', 'role', 'set', 'rules'))
        await self.runt.snap.core.addRoleRule(self.valu, rule, gateiden=gateiden)

    async def _methRoleDelRule(self, rule, gateiden=None):
        self.runt.confirm(('auth', 'role', 'set', 'rules'))
        await self.runt.snap.core.delRoleRule(self.valu, rule, gateiden=gateiden)

    async def value(self):
        return await self.runt.snap.core.getRoleDef(self.valu)

@registry.registerLib
class LibCron(Lib):
    '''
    A Storm Library for interacting with Cron Jobs in the Cortex.
    '''
    _storm_lib_path = ('cron',)

    def getObjLocals(self):
        return {
            'at': self._methCronAt,
            'add': self._methCronAdd,
            'del': self._methCronDel,
            'get': self._methCronGet,
            'mod': self._methCronMod,
            'list': self._methCronList,
            'enable': self._methCronEnable,
            'disable': self._methCronDisable,
        }

    async def _matchIdens(self, prefix, perm):
        '''
        Returns the cron that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        user = self.runt.user

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
        '''
        Add a recurring cron job to the Cortex.

        Args:
            **kwargs: Key-value parameters used to add the cron job.

        Returns:
            CronJob: A Storm CronJob object.
        '''
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

        todo = s_common.todo('addCronJob', cdef)
        gatekeys = ((self.runt.user.iden, ('cron', 'add'), None),)
        cdef = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return CronJob(self.runt, cdef, path=self.path)

    async def _methCronAt(self, **kwargs):
        '''
        Add a non-recurring  cron job to the Cortex.

        Args:
            **kwargs: Key-value parameters used to add the cron job.

        Returns:
            CronJob: A Storm CronJob object.
        '''
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

        todo = s_common.todo('addCronJob', cdef)
        gatekeys = ((self.runt.user.iden, ('cron', 'add'), None),)
        cdef = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return CronJob(self.runt, cdef, path=self.path)

    async def _methCronDel(self, prefix):
        '''
        Delete a CronJob from the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a cron job to delete.
            Only a single matching prefix will be deleted.

        Returns:
            None: Returns None
        '''
        cron = await self._matchIdens(prefix, ('cron', 'del'))
        iden = cron['iden']

        todo = s_common.todo('delCronJob', iden)
        gatekeys = ((self.runt.user.iden, ('cron', 'del'), iden),)
        return await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methCronMod(self, prefix, query):
        '''
        Modify the Storm query for a CronJob in the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a cron job to modify.
            Only a single matching prefix will be modified.

            query (str): The new Storm query for the cron job.

        Returns:
            None: Returns None.
        '''
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = s_common.todo('updateCronJob', iden, query)
        gatekeys = ((self.runt.user.iden, ('cron', 'set'), iden),)
        await self.dyncall('cortex', todo, gatekeys=gatekeys)
        return iden

    async def _methCronList(self):
        '''
        List CronJobs in the Cortex.

        Returns:
            list: A list of CronJob Storm objects.
        '''
        todo = s_common.todo('listCronJobs')
        gatekeys = ((self.runt.user.iden, ('cron', 'get'), None),)
        defs = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return [CronJob(self.runt, cdef, path=self.path) for cdef in defs]

    async def _methCronGet(self, prefix):
        '''
        Get a CronJob in the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a cron job to get.
            Only a single matching prefix will be retrieved.

        Returns:
            CronJob: A Storm CronJob object.
        '''
        cdef = await self._matchIdens(prefix, ('cron', 'get'))

        return CronJob(self.runt, cdef, path=self.path)

    async def _methCronEnable(self, prefix):
        '''
        Enable a CronJob in the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a cron job to enable.
            Only a single matching prefix will be enabled.

        Returns:
            str: The iden of the CronJob which was enabled.
        '''
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = ('enableCronJob', (iden,), {})
        await self.runt.dyncall('cortex', todo)

        return iden

    async def _methCronDisable(self, prefix):
        '''
        Disable a CronJob in the Cortex.

        Args:
            prefix (str): A prefix to match in order to identify a cron job to disable.
            Only a single matching prefix will be enabled.

        Returns:
            str: The iden of the CronJob which was disabled.
        '''
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = ('disableCronJob', (iden,), {})
        await self.runt.dyncall('cortex', todo)

        return iden

@registry.registerType
class CronJob(Prim):
    '''
    Implements the STORM api for a cronjob instance.
    '''
    def __init__(self, runt, cdef, path=None):
        Prim.__init__(self, cdef, path=path)
        self.runt = runt
        self.locls.update({
            'iden': cdef.get('iden'),
        })
        self.locls.update(self.getObjLocals())

    # Todo: Plumb iden access via a @property
    def getObjLocals(self):
        return {
            'pack': self._methCronJobPack,
            'set': self._methCronJobSet,
            'pprint': self._methCronJobPprint,
        }

    async def _methCronJobSet(self, name, valu):
        '''
        Set an editable field in the cron job definition.

        Example:
            $lib.cron.get($iden).set(name, "foo bar cron job")
        '''
        name = await tostr(name)
        valu = await toprim(valu)
        iden = self.valu.get('iden')

        gatekeys = ((self.runt.user.iden, ('cron', 'set', name), iden),)
        todo = s_common.todo('editCronJob', iden, name, valu)
        self.valu = await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)
        return self

    async def _methCronJobPack(self):
        return self.valu

    @staticmethod
    def _formatTimestamp(ts):
        # N.B. normally better to use fromtimestamp with UTC timezone,
        # but we don't want timezone to print out
        return datetime.datetime.utcfromtimestamp(ts).isoformat(timespec='minutes')

    async def _methCronJobPprint(self):

        user = self.valu.get('username')
        laststart = self.valu.get('laststarttime')
        lastend = self.valu.get('lastfinishtime')
        result = self.valu.get('lastresult')
        iden = self.valu.get('iden')

        job = {
            'iden': iden,
            'idenshort': iden[:8] + '..',
            'user': user or '<None>',
            'query': self.valu.get('query') or '<missing>',
            'isrecur': 'Y' if self.valu.get('recur') else 'N',
            'isrunning': 'Y' if self.valu.get('isrunning') else 'N',
            'enabled': 'Y' if self.valu.get('enabled', True) else 'N',
            'startcount': self.valu.get('startcount') or 0,
            'laststart': 'Never' if laststart is None else self._formatTimestamp(laststart),
            'lastend': 'Never' if lastend is None else self._formatTimestamp(lastend),
            'lastresult': self.valu.get('lastresult') or '<None>',
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

    if isinstance(valu, StormType):
        return valu

    if basetypes:
        mesg = 'Unable to convert python primitive to StormType.'
        raise s_exc.NoSuchType(mesg=mesg, python_type=valu.__class__.__name__)

    return valu

async def tostr(valu, noneok=False):

    if noneok and valu is None:
        return None

    try:
        return str(valu)
    except Exception as e:
        mesg = f'Failed to make a string from {valu!r}.'
        raise s_exc.BadCast(mesg=mesg) from e

async def toiter(valu, noneok=False):
    '''
    Make a python primative or storm type into an iterable.
    '''

    if noneok and valu is None:
        return ()

    if isinstance(valu, Prim):
        return await valu.iter()

    return tuple(valu)

async def tobool(valu, noneok=False):

    if noneok and valu is None:
        return None

    if isinstance(valu, Prim):
        return await valu.bool()

    try:
        return bool(valu)
    except Exception as e:
        mesg = f'Failed to make a boolean from {valu!r}.'
        raise s_exc.BadCast(mesg=mesg)

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
