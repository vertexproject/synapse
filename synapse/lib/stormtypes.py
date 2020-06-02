import bz2
import gzip
import json
import time
import base64
import asyncio
import logging
import binascii
import datetime
import calendar
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.ast as s_ast
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.msgpack as s_msgpack
import synapse.lib.provenance as s_provenance

logger = logging.getLogger(__name__)

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

def intOrNoneify(x):
    if x is None:
        return None
    return intify(x)

def kwarg_format(text, **kwargs):
    '''
    Replaces instances curly-braced argument names in text with their values
    '''
    for name, valu in kwargs.items():
        temp = '{%s}' % (name,)
        text = text.replace(temp, str(valu))

    return text

class StormType:
    '''
    The base type for storm runtime value objects.
    '''
    def __init__(self, path=None):
        self.path = path
        self.ctors = {}
        self.locls = {}

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
        pass

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
        return await self.runt.snap.core.dyncall(iden, todo, gatekeys=gatekeys)

    async def dyniter(self, iden, todo, gatekeys=()):
        async for item in self.runt.snap.core.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

class LibPkg(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._libPkgAdd,
            'del': self._libPkgDel,
            'list': self._libPkgList,
        })

    async def _libPkgAdd(self, pkgdef):
        self.runt.user.confirm(('pkgs', 'add'), None)
        await self.runt.snap.core.addStormPkg(pkgdef)

    async def _libPkgDel(self, name):
        self.runt.user.confirm(('pkgs', 'del'), None)
        await self.runt.snap.core.delStormPkg(name)

    async def _libPkgList(self):
        return await self.runt.snap.core.getStormPkgs()

class LibDmon(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._libDmonAdd,
            'del': self._libDmonDel,
            'log': self._libDmonLog,
            'list': self._libDmonList,
        })

    async def _libDmonDel(self, iden):

        dmon = await self.runt.snap.core.getStormDmon(iden)
        if dmon is None:
            mesg = f'No storm dmon with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        if dmon.get('user') != self.runt.user.iden:
            self.runt.user.confirm(('dmon', 'del', iden))

        await self.runt.snap.core.delStormDmon(iden)

    async def _libDmonList(self):
        return await self.runt.snap.core.getStormDmons()

    async def _libDmonLog(self, iden):
        self.runt.user.confirm(('dmon', 'log'))
        return await self.runt.snap.core.getStormDmonLog(iden)

    async def _libDmonAdd(self, quer, name='noname'):
        '''
        Add a storm dmon (persistent background task) to the cortex.

        $lib.dmon.add(${ myquery })
        '''
        self.runt.user.confirm(('dmon', 'add'))

        # closure style capture of runtime
        runtvars = {k: v for (k, v) in self.runt.vars.items() if s_msgpack.isok(v)}

        opts = {'vars': runtvars,
                'view': self.runt.snap.view.iden,  # Capture the current view iden.
                }

        ddef = {
            'name': name,
            'user': self.runt.user.iden,
            'storm': str(quer),
            'enabled': True,
            'stormopts': opts,
        }

        dmoniden = await self.runt.snap.core.addStormDmon(ddef)
        return dmoniden

class LibService(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._libSvcAdd,
            'del': self._libSvcDel,
            'get': self._libSvcGet,
            'list': self._libSvcList,
            'wait': self._libSvcWait,
        })

    async def _libSvcAdd(self, name, url):

        self.runt.user.confirm(('service', 'add'))
        sdef = {
            'name': name,
            'url': url,
        }
        return await self.runt.snap.core.addStormSvc(sdef)

    async def _libSvcDel(self, iden):
        self.runt.user.confirm(('service', 'del'))
        return await self.runt.snap.core.delStormSvc(iden)

    async def _libSvcGet(self, name):
        self.runt.user.confirm(('service', 'get', name))
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg)
        return ssvc

    async def _libSvcList(self):
        self.runt.user.confirm(('service', 'list'))
        retn = []

        for ssvc in self.runt.snap.core.getStormSvcs():
            sdef = dict(ssvc.sdef)
            sdef['ready'] = ssvc.ready.is_set()
            retn.append(sdef)

        return retn

    async def _libSvcWait(self, name):
        self.runt.user.confirm(('service', 'get'))
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        await ssvc.ready.wait()

class LibBase(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'len': self._len,
            'min': self._min,
            'max': self._max,
            'set': self._set,
            'dict': self._dict,
            'guid': self._guid,
            'fire': self._fire,
            'list': self._list,
            'null': None,
            'true': True,
            'false': False,
            'text': self._text,
            'cast': self._cast,
            'warn': self._warn,
            'print': self._print,
            'sorted': self._sorted,
            'import': self._libBaseImport,
        })

    async def _libBaseImport(self, name):

        mdef = await self.runt.snap.core.getStormMod(name)
        if mdef is None:
            mesg = f'No storm module named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        text = mdef.get('storm')

        query = await self.runt.getStormQuery(text)
        runt = await self.runt.getScopeRuntime(query, impd=True)

        # execute the query in a module scope
        async for item in query.run(runt, s_ast.agen()):
            pass  # pragma: no cover

        modlib = Lib(self.runt)
        modlib.locls.update(runt.vars)
        modlib.locls['__module__'] = mdef
        return modlib

    async def _cast(self, name, valu):

        name = await toprim(name)
        valu = await toprim(valu)

        typeitem = self.runt.snap.core.model.type(name)
        if typeitem is None:
            mesg = f'No type found for name {name}.'
            raise s_exc.NoSuchType(mesg=mesg)

        #TODO an eventual mapping between model types and storm prims

        norm, info = typeitem.norm(valu)
        return fromprim(norm, basetypes=False)

    async def _sorted(self, valu):
        for item in sorted(valu):
            yield item

    async def _set(self, *vals):
        return Set(set(vals))

    async def _list(self, *vals):
        return List(list(vals))

    async def _text(self, *args):
        valu = ''.join(args)
        return Text(valu)

    async def _guid(self, *args):
        if args:
            return s_common.guid(args)
        return s_common.guid()

    async def _len(self, item):
        try:
            return len(item)
        except TypeError:
            name = f'{item.__class__.__module__}.{item.__class__.__name__}'
            raise s_exc.StormRuntimeError(mesg=f'Object {name} does not have a length.', name=name) from None
        except Exception as e:  # pragma: no cover
            name = f'{item.__class__.__module__}.{item.__class__.__name__}'
            raise s_exc.StormRuntimeError(mesg=f'Unknown error during len(): {repr(e)}', name=name)

    async def _min(self, *args):
        # allow passing in a list of ints
        vals = []
        for arg in args:
            if isinstance(arg, (list, tuple)):
                vals.extend(arg)
                continue
            vals.append(arg)

        ints = [intify(x) for x in vals]
        return min(*ints)

    async def _max(self, *args):

        # allow passing in a list of ints
        vals = []
        for arg in args:
            if isinstance(arg, (list, tuple)):
                vals.extend(arg)
                continue
            vals.append(arg)

        ints = [intify(x) for x in vals]
        return max(*ints)

    @staticmethod
    def _get_mesg(mesg, **kwargs):
        if not isinstance(mesg, str):
            mesg = repr(mesg)
        elif kwargs:
            mesg = kwarg_format(mesg, **kwargs)
        return mesg

    async def _print(self, mesg, **kwargs):
        mesg = self._get_mesg(mesg, **kwargs)
        await self.runt.printf(mesg)

    async def _warn(self, mesg, **kwargs):
        mesg = self._get_mesg(mesg, **kwargs)
        await self.runt.warn(mesg, log=False)

    async def _dict(self, **kwargs):
        return Dict(kwargs)

    async def _fire(self, name, **info):
        info = await toprim(info)
        s_common.reqjsonsafe(info)
        await self.runt.snap.fire('storm:fire', type=name, data=info)

class LibStr(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'join': self.join,
            'concat': self.concat,
            'format': self.format,
        })

    async def concat(self, *args):
        strs = [str(a) for a in args]
        return ''.join(strs)

    async def format(self, text, **kwargs):

        text = kwarg_format(text, **kwargs)

        return text

    async def join(self, sepr, items):
        '''
        Join items into a string using a separator.

        Example:

            $foo = $lib.str.join('.', ('rep', 'vtx', 'tag'))
        '''
        strs = [str(item) for item in items]
        return sepr.join(items)

class LibBytes(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'put': self._libBytesPut,
        })

    async def _libBytesPut(self, byts):
        '''
        Save the given bytes variable to the axon.

        Returns:
            ($size, $sha256)

        Example:
            ($size, $sha2) = $lib.bytes.put($bytes)
        '''
        if not isinstance(byts, bytes):
            mesg = '$lib.bytes.put() requires a bytes argument'
            raise s_exc.BadArg(mesg=mesg)

        await self.runt.snap.core.getAxon()
        todo = s_common.todo('put', byts)
        size, sha2 = await self.dyncall('axon', todo)

        return (size, s_common.ehex(sha2))

class LibLift(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'byNodeData': self.byNodeData,
        })

    async def byNodeData(self, name):
        async for node in self.runt.snap.nodesByDataName(name):
            yield node

class LibTime(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'now': s_common.now,
            'fromunix': self.fromunix,
            'parse': self.parse,
            'format': self.format,
            'sleep': self.sleep,
            'ticker': self.ticker,
        })

    # TODO from other iso formats!

    async def format(self, valu, format):
        '''
        Format a Synapse timestamp into a string value using strftime.
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

    async def parse(self, valu, format):
        '''
        Parse a timestamp string using datetimte.strptime formatting.
        '''
        try:
            dt = datetime.datetime.strptime(valu, format)
        except ValueError as e:
            mesg = f'Error during time parsing - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, valu=valu,
                                          format=format) from None
        return int((dt - s_time.EPOCH).total_seconds() * 1000)

    async def sleep(self, valu):
        '''
        Sleep/yield execution of the storm query.
        '''
        await self.runt.snap.waitfini(timeout=float(valu))
        await self.runt.snap.clearCache()

    async def ticker(self, tick, count=None):

        if count is not None:
            count = intify(count)

        tick = float(tick)

        offs = 0
        while True:

            await self.runt.snap.waitfini(timeout=tick)
            await self.runt.snap.clearCache()
            yield offs

            offs += 1
            if count is not None and offs == count:
                break

    async def fromunix(self, secs):
        '''
        Normalize a timestamp from a unix epoch time.

        Example:

            <query> [ :time = $lib.time.fromunix($epoch) ]


        '''
        secs = float(secs)
        return int(secs * 1000)

class LibCsv(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'emit': self._libCsvEmit,
        })

    async def _libCsvEmit(self, *args, table=None):
        '''
        Emit a csv:row event for the given args.
        '''
        row = [await toprim(a) for a in args]
        await self.runt.snap.fire('csv:row', row=row, table=table)

class LibFeed(Lib):
    def addLibFuncs(self):
        self.locls.update({
            'genr': self._libGenr,
            'list': self._libList,
            'ingest': self._libIngest,
        })

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
        self.runt.layerConfirm(('feed:data', *name.split('.')))
        with s_provenance.claim('feed:data', name=name):
            return self.runt.snap.addFeedNodes(name, data)

    async def _libList(self):
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

        self.runt.layerConfirm(('feed:data', *name.split('.')))
        with s_provenance.claim('feed:data', name=name):
            strict = self.runt.snap.strict
            self.runt.snap.strict = False
            await self.runt.snap.addFeedData(name, data)
            self.runt.snap.strict = strict

class LibQueue(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._methQueueAdd,
            'del': self._methQueueDel,
            'get': self._methQueueGet,
            'list': self._methQueueList,
        })

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

    async def _methQueueDel(self, name):
        todo = s_common.todo('delCoreQueue', name)
        gatekeys = ((self.runt.user.iden, ('queue', 'del',), f'queue:{name}'), )
        await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueList(self):
        retn = []

        todo = s_common.todo('listCoreQueues')
        qlist = await self.dyncall('cortex', todo)

        for queue in qlist:
            if not self.runt.user.allowed(('queue', 'get'), f"queue:{queue['name']}"):
                continue

            retn.append(queue)

        return retn

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

        self.locls.update({
            'get': self._methQueueGet,
            'pop': self._methQueuePop,
            'put': self._methQueuePut,
            'puts': self._methQueuePuts,
            'gets': self._methQueueGets,
            'cull': self._methQueueCull,
            'size': self._methQueueSize,
        })

    async def _methQueueCull(self, offs):
        offs = intify(offs)
        todo = s_common.todo('coreQueueCull', self.name, offs)
        gatekeys = self._getGateKeys('get')
        await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueSize(self):
        todo = s_common.todo('coreQueueSize', self.name)
        gatekeys = self._getGateKeys('get')
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueGets(self, offs=0, wait=True, cull=False, size=None):
        wait = intify(wait)
        offs = intify(offs)

        if size is not None:
            size = intify(size)

        todo = s_common.todo('coreQueueGets', self.name, offs, wait=wait, size=size)
        gatekeys = self._getGateKeys('get')

        async for item in self.runt.dyniter('cortex', todo, gatekeys=gatekeys):
            yield item

    async def _methQueuePuts(self, items, wait=False):
        todo = s_common.todo('coreQueuePuts', self.name, items)
        gatekeys = self._getGateKeys('put')
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueueGet(self, offs=0, cull=True, wait=True):

        offs = intify(offs)
        wait = intify(wait)

        todo = s_common.todo('coreQueueGet', self.name, offs, cull=cull, wait=wait)
        gatekeys = self._getGateKeys('get')

        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methQueuePop(self, offs=0, cull=True, wait=True):

        offs = intify(offs)
        wait = intify(wait)

        todo = s_common.todo('coreQueueGet', self.name, offs, cull=cull, wait=wait)
        gatekeys = self._getGateKeys('get')

        valu = await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)
        if valu is not None:
            await self._methQueueCull(valu[0])

        return valu

    async def _methQueuePut(self, item):
        return await self._methQueuePuts((item,))

    def _getGateKeys(self, perm):
        return ((self.runt.user.iden, ('queue', perm), self.gateiden),)

class LibTelepath(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'open': self._methTeleOpen,
        })

    async def _methTeleOpen(self, url):
        '''
        Open and return a telepath RPC proxy.
        '''
        scheme = url.split('://')[0]
        self.runt.user.confirm(('lib', 'telepath', 'open', scheme))
        return Proxy(await self.runt.getTeleProxy(url))

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

class ProxyMethod(StormType):

    def __init__(self, meth, path=None):
        StormType.__init__(self, path=path)
        self.meth = meth

    async def __call__(self, *args, **kwargs):
        args = await toprim(args)
        kwargs = await toprim(kwargs)
        # TODO: storm types fromprim()
        return await self.meth(*args, **kwargs)

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

class LibBase64(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'encode': self._encode,
            'decode': self._decode
        })

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

class Prim(StormType):
    '''
    The base type for all STORM primitive values.
    '''
    def __init__(self, valu, path=None):
        StormType.__init__(self, path=path)
        self.valu = valu

    def __bool__(self):
        return bool(self.valu)

    def __len__(self):
        name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        raise s_exc.StormRuntimeError(mesg=f'Object {name} does not have a length.', name=name)

    def value(self):
        return self.valu

class Str(Prim):

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update({
            'split': self._methStrSplit,
            'endswith': self._methStrEndswith,
            'startswith': self._methStrStartswith,
            'ljust': self._methStrLjust,
            'rjust': self._methStrRjust,
            'encode': self._methEncode,
            'replace': self._methStrReplace,
        })

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
        return self.valu.rjust(intify(size))

    async def _methStrLjust(self, size):
        return self.valu.ljust(intify(size))

    async def _methStrReplace(self, oldv, newv, maxv=None):
        '''
        Replace occurrences of a string with a new string,
        optionally restricting the number of replacements.

        Example:

            $foo.replace('bar', 'baz')
        '''
        if maxv is None:
            return self.valu.replace(oldv, newv)
        else:
            return self.valu.replace(oldv, newv, int(maxv))

class Bytes(Prim):

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update({
            'decode': self._methDecode,
            'bunzip': self._methBunzip,
            'gunzip': self._methGunzip,
            'bzip': self._methBzip,
            'gzip': self._methGzip,
            'json': self._methJsonLoad,
        })

    def __len__(self):
        return len(self.valu)

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

class Dict(Prim):

    def __iter__(self):
        return self.valu.items()

    async def __aiter__(self):
        for item in self.valu.items():
            yield item

    def __len__(self):
        return len(self.valu)

    async def setitem(self, name, valu):
        self.valu[name] = valu

    async def deref(self, name):
        return self.valu.get(name)

    async def value(self):
        return {await toprim(k): await toprim(v) for (k, v) in self.valu.items()}

class Set(Prim):

    def __init__(self, valu, path=None):
        Prim.__init__(self, set(valu), path=path)
        self.locls.update({
            'add': self._methSetAdd,
            'has': self._methSetHas,
            'rem': self._methSetRem,
            'adds': self._methSetAdds,
            'rems': self._methSetRems,
            'list': self._methSetList,
            'size': self._methSetSize,
        })

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

class List(Prim):

    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update({
            'has': self._methListHas,
            'size': self._methListSize,
            'index': self._methListIndex,
            'length': self._methListLength,
            'append': self._methListAppend,
        })

    def __iter__(self):
        for item in self.valu:
            yield item

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

    async def _methListAppend(self, valu):
        self.valu.append(valu)

    async def _methListIndex(self, valu):
        '''
        Return a single field from the list by index.
        '''
        indx = intify(valu)
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

class Bool(Prim):
    pass

class LibUser(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'name': self._libUserName,
            'vars': StormHiveDict(self.runt, self.runt.user.vars),
            'profile': StormHiveDict(self.runt, self.runt.user.profile),
        })

    async def _libUserName(self, path=None):
        return self.runt.user.name

class LibGlobals(Lib):
    '''
    Global persistent Storm variables
    '''
    def __init__(self, runt, name):
        Lib.__init__(self, runt, name)

    def addLibFuncs(self):
        self.locls.update({
            'get': self._methGet,
            'pop': self._methPop,
            'set': self._methSet,
            'list': self._methList,
        })

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
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('globals', 'set', name), None),)
        todo = s_common.todo('setStormVar', name, valu)
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methList(self):
        ret = []
        user = self.runt.user

        todo = ('itemsStormVar', (), {})

        async for key, valu in self.runt.dyniter('cortex', todo):
            if user.allowed(('globals', 'get', key)):
                ret.append((key, valu))
        return ret

class StormHiveDict(Prim):

    def __init__(self, runt, info):
        Prim.__init__(self, None)
        self.runt = runt
        self.info = info
        self.locls.update({
            'get': self.info.get,
            'pop': self.info.pop,
            'set': self.info.set,
            'list': self.list,
        })

    async def set(self, name, valu):

        if not isinstance(name, str):
            mesg = 'The name of a persistent variable must be a string.'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name)

        return await self.info.set(name, valu)

    def list(self):
        return list(self.info.items())

    def __iter__(self):
        return list(self.info.items())

    def value(self):
        return self.info.pack()

class LibVars(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'get': self._libVarsGet,
            'set': self._libVarsSet,
            'del': self._libVarsDel,
            'list': self._libVarsList,
        })

    async def _libVarsGet(self, name, defv=None):
        '''
        Resolve a variable in a storm query
        '''
        return self.runt.getVar(name, defv=defv)

    async def _libVarsSet(self, name, valu):
        '''
        Set a variable in a storm query
        '''
        self.runt.setVar(name, valu)

    async def _libVarsDel(self, name):
        '''
        Unset a variable in a storm query.
        '''
        self.runt.vars.pop(name, None)

    async def _libVarsList(self):
        '''
        List variables available in a storm query.
        '''
        return list(self.runt.vars.items())

class Query(Prim):
    '''
    A storm primitive representing an embedded query.
    '''
    def __init__(self, text, varz, runt, path=None):

        Prim.__init__(self, text, path=path)

        self.text = text
        self.varz = varz
        self.runt = runt

        self.locls.update({
            'exec': self._methQueryExec,
        })

    def __str__(self):
        return self.text

    async def _getRuntGenr(self):
        opts = {'vars': self.varz}
        query = await self.runt.getStormQuery(self.text)
        with self.runt.snap.getStormRuntime(opts=opts) as runt:
            async for item in query.run(runt, s_ast.agen()):
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
        except s_ast.StormReturn as e:
            return e.item
        except asyncio.CancelledError:  # pragma: no cover
            raise

class NodeProps(Prim):

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update({
            'get': self.get,
            'list': self.list,
            # TODO implement set()
        })

    async def _derefGet(self, name):
        return self.valu.get(name)

    async def get(self, name, defv=None):
        return self.valu.get(name)

    async def list(self):
        return list(self.valu.props.items())

    def value(self):
        return dict(self.valu.props)

class NodeData(Prim):

    def __init__(self, node, path=None):

        Prim.__init__(self, node, path=path)

        self.locls.update({
            'get': self._getNodeData,
            'set': self._setNodeData,
            'pop': self._popNodeData,
            'list': self._listNodeData,
            'load': self._loadNodeData,
        })

    def _reqAllowed(self, perm):
        if not self.valu.snap.user.allowed(perm):
            pstr = '.'.join(perm)
            mesg = f'User is not allowed permission: {pstr}'
            raise s_exc.AuthDeny(perm=perm, mesg=mesg)

    async def _getNodeData(self, name):
        self._reqAllowed(('node', 'data', 'get', name))
        return await self.valu.getData(name)

    async def _setNodeData(self, name, valu):
        self._reqAllowed(('node', 'data', 'set', name))
        valu = await toprim(valu)
        s_common.reqjsonsafe(valu)
        return await self.valu.setData(name, valu)

    async def _popNodeData(self, name):
        self._reqAllowed(('node', 'data', 'pop', name))
        return await self.valu.popData(name)

    async def _listNodeData(self):
        self._reqAllowed(('node', 'data', 'list'))
        return [x async for x in self.valu.iterData()]

    async def _loadNodeData(self, name):
        self._reqAllowed(('node', 'data', 'get', name))
        valu = await self.valu.getData(name)
        # set the data value into the nodedata dict so it gets sent
        self.valu.nodedata[name] = valu

class Node(Prim):
    '''
    Implements the STORM api for a node instance.
    '''
    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update({
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
        })

        self.ctors['data'] = self._ctorNodeData
        self.ctors['props'] = self._ctorNodeProps

    def _ctorNodeData(self, path=None):
        return NodeData(self.valu, path=path)

    def _ctorNodeProps(self, path=None):
        return NodeProps(self.valu, path=path)

    async def _methNodePack(self, dorepr=False):
        '''
        Return the serializable/packed version of the Node.

        Args:
            dorepr (bool): Include repr information for human readable versions of properties.

        Returns:
            (tuple): An (ndef, info) node tuple.
        '''
        return self.valu.pack(dorepr=dorepr)

    async def _methNodeEdges(self, verb=None):
        '''
        Yields the (verb, iden) tuples for this nodes edges.
        '''
        verb = await toprim(verb)
        async for edge in self.valu.iterEdgesN1(verb=verb):
            yield edge

    async def _methNodeIsForm(self, name):
        return self.valu.form.name == name

    async def _methNodeTags(self, glob=None):
        tags = list(self.valu.tags.keys())
        if glob is not None:
            regx = s_cache.getTagGlobRegx(glob)
            tags = [t for t in tags if regx.fullmatch(t)]
        return tags

    async def _methNodeGlobTags(self, glob):
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

    async def _methNodeValue(self):
        return self.valu.ndef[1]

    async def _methNodeForm(self):
        return self.valu.ndef[0]

    async def _methNodeNdef(self):
        return self.valu.ndef

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

    async def _methNodeIden(self):
        return self.valu.iden()

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
        self.path.setVar(name, valu)

    def __iter__(self):
        # prevent "edit while iter" issues
        for item in list(self.path.vars.items()):
            yield item

    async def __aiter__(self):
        # prevent "edit while iter" issues
        for item in list(self.path.vars.items()):
            yield item

class Path(Prim):

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update({
            'idens': self._methPathIdens,
            'trace': self._methPathTrace,
            'listvars': self._methPathListVars,
            'vars': PathVars(path),
        })

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

class Trace(Prim):
    '''
    Storm API wrapper for the Path Trace object.
    '''
    def __init__(self, trace, path=None):
        Prim.__init__(self, trace, path=path)
        self.locls.update({
            'idens': self._methTraceIdens,
        })

    async def _methTraceIdens(self):
        return [n.iden() for n in self.valu.nodes]

class Text(Prim):
    '''
    A mutable text type for simple text construction.
    '''
    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update({
            'add': self._methTextAdd,
            'str': self._methTextStr,
        })

    def __len__(self):
        return len(self.valu)

    async def _methTextAdd(self, text, **kwargs):
        text = kwarg_format(text, **kwargs)
        self.valu += text

    async def _methTextStr(self):
        return self.valu

class LibStats(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'tally': self.tally,
        })

    async def tally(self):
        return StatTally(path=self.path)

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

        self.locls.update({
            'inc': self.inc,
            'get': self.get,
        })

        self.counters = collections.defaultdict(int)

    async def __aiter__(self):
        for name, valu in self.counters.items():
            yield name, valu

    def __len__(self):
        return len(self.counters)

    async def inc(self, name, valu=1):
        valu = intify(valu)
        self.counters[name] += valu

    async def get(self, name):
        return self.counters.get(name, 0)

    def value(self):
        return dict(self.counters)

class LibLayer(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._libLayerAdd,
            'del': self._libLayerDel,
            'get': self._libLayerGet,
            'list': self._libLayerList,
        })

    async def _libLayerAdd(self, ldef=None):
        '''
        Add a layer to the cortex.
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
        if ldef is None:
            mesg = f'Failed to add layer.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        return Layer(self.runt, ldef, path=self.path)

    async def _libLayerDel(self, iden):
        '''
        Delete a layer from the cortex.
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
        Get a layer from the cortex.
        '''
        todo = s_common.todo('getLayerDef', iden)
        ldef = await self.runt.dyncall('cortex', todo)
        if ldef is None:
            mesg = f'No layer with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        return Layer(self.runt, ldef, path=self.path)

    async def _libLayerList(self):
        '''
        List the layers in a cortex.
        '''
        todo = s_common.todo('getLayerDefs')
        defs = await self.runt.dyncall('cortex', todo)
        return [Layer(self.runt, ldef, path=self.path) for ldef in defs]

class Layer(Prim):
    '''
    Implements the STORM api for a layer instance.
    '''
    def __init__(self, runt, ldef, path=None):
        Prim.__init__(self, ldef, path=path)
        self.runt = runt
        self.locls.update({
            'iden': ldef.get('iden'),
            'set': self._methLayerSet,
            'get': self._methLayerGet,
            'pack': self._methLayerPack,
            'repr': self._methLayerRepr,
        })

    async def _methLayerGet(self, name, defv=None):
        return self.valu.get(name, defv)

    async def _methLayerSet(self, name, valu):
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

class LibView(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._methViewAdd,
            'del': self._methViewDel,
            'get': self._methViewGet,
            'list': self._methViewList,
        })

    async def _methViewAdd(self, layers, name=None):
        '''
        Add a view to the cortex.
        '''
        self.runt.confirm(('view', 'add'))

        vdef = {
            'creator': self.runt.user.iden,
            'layers': layers
        }

        if name is not None:
            vdef['name'] = name

        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('view', 'add'), None),)
        todo = ('addView', (vdef,), {})
        vdef = await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)
        return View(self.runt, vdef, path=self.path)

    async def _methViewDel(self, iden):
        useriden = self.runt.user.iden
        gatekeys = ((useriden, ('view', 'del'), iden),)
        todo = ('delView', (iden,), {})
        return await self.runt.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methViewGet(self, iden=None):
        '''
        Retrieve a view from the cortex.
        '''
        todo = s_common.todo('getViewDef', iden)
        vdef = await self.runt.dyncall('cortex', todo)
        if vdef is None:
            raise s_exc.NoSuchView(mesg=iden)

        return View(self.runt, vdef, path=self.path)

    async def _methViewList(self):
        '''
        List the views in the cortex.
        '''
        todo = s_common.todo('getViewDefs')
        defs = await self.runt.dyncall('cortex', todo)
        return [View(self.runt, vdef, path=self.path) for vdef in defs]

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
            'set': self._methViewSet,
            'get': self._methViewGet,
            'fork': self._methViewFork,
            'pack': self._methViewPack,
            'repr': self._methViewRepr,
            'merge': self._methViewMerge,
            'getEdges': self._methGetEdges,
            'getEdgeVerbs': self._methGetEdgeVerbs,
        })

    async def _methGetEdges(self, verb=None):
        verb = await toprim(verb)
        todo = s_common.todo('getEdges', verb=verb)
        async for edge in self.viewDynIter(todo, ('view', 'read')):
            yield edge

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

    async def _methViewGet(self, name, defv=None):
        return self.valu.get(name, defv)

    async def _methViewSet(self, name, valu):
        todo = s_common.todo('setViewInfo', name, valu)
        valu = await self.viewDynCall(todo, ('view', 'set', name))
        self.valu[name] = valu

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

    async def _methViewPack(self):
        return self.valu

    async def _methViewFork(self, name=None):
        '''
        Fork a view in the cortex.
        '''
        useriden = self.runt.user.iden
        viewiden = self.valu.get('iden')

        gatekeys = ((useriden, ('view', 'add'), None),)

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

class LibTrigger(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._methTriggerAdd,
            'del': self._methTriggerDel,
            'list': self._methTriggerList,
            'get': self._methTriggerGet,
            'enable': self._methTriggerEnable,
            'disable': self._methTriggerDisable,
            'mod': self._methTriggerMod
        })

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

                if not user.allowed(('trigger', 'get'), gateiden=iden):
                    continue

                match = trig

        if match is None:
            mesg = 'Provided iden does not match any valid authorized triggers.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

        return match

    async def _methTriggerAdd(self, tdef): # cond, form=None, tag=None, prop=None, storm=None, disabled=False):
        '''
        Add a trigger to the cortex.
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
        Delete a trigger from the cortex.
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
        Modify a trigger in the cortex.
        '''
        useriden = self.runt.user.iden
        viewiden = self.runt.snap.view.iden

        if not query.startswith('{'):
            mesg = 'Expected second argument to start with {'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix, query=query)

        # Remove the curly braces
        query = query[1:-1]

        trig = await self._matchIdens(prefix)
        iden = trig.iden
        gatekeys = ((useriden, ('trigger', 'set'), iden),)
        todo = s_common.todo('setTriggerInfo', iden, 'storm', query)
        await self.dyncall(viewiden, todo, gatekeys=gatekeys)

        return iden

    async def _methTriggerList(self):
        '''
        List triggers in the cortex.
        '''
        user = self.runt.user
        view = self.runt.snap.view
        triggers = []

        for iden, trig in await view.listTriggers():
            if not user.allowed(('trigger', 'get'), gateiden=iden):
                continue
            triggers.append(Trigger(self.runt, trig.pack()))

        return triggers

    async def _methTriggerGet(self, iden):
        trigger = await self.runt.snap.view.getTrigger(iden)
        if trigger is None:
            return None

        self.runt.user.confirm(('trigger', 'get'), gateiden=iden)

        return Trigger(self.runt, trigger.pack())

    async def _methTriggerEnable(self, prefix):
        '''
        Enable a trigger in the cortex.
        '''
        return await self._triggerendisable(prefix, True)

    async def _methTriggerDisable(self, prefix):
        '''
        Enable a trigger in the cortex.
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

class Trigger(Prim):

    def __init__(self, runt, tdef):

        Prim.__init__(self, tdef)
        self.runt = runt

        self.locls.update({
            'set': self.set,
            'iden': tdef['iden'],
        })

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

    allow = True
    if text.startswith('!'):
        text = text[1:]
        allow = False

    return (allow, tuple(text.split('.')))

class LibAuth(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'ruleFromText': ruleFromText,
        })

class LibUsers(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._methUsersAdd,
            'del': self._methUsersDel,
            'list': self._methUsersList,
            'get': self._methUsersGet,
            'byname': self._methUsersByName,
        })

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

    async def _methUsersAdd(self, name, passwd=None, email=None):
        self.runt.user.confirm(('auth', 'user', 'add'))
        udef = await self.runt.snap.core.addUser(name, passwd=passwd, email=email)
        return User(self.runt, udef['iden'])

    async def _methUsersDel(self, iden):
        self.runt.user.confirm(('auth', 'user', 'del'))
        await self.runt.snap.core.delUser(iden)

class LibRoles(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._methRolesAdd,
            'del': self._methRolesDel,
            'list': self._methRolesList,
            'get': self._methRolesGet,
            'byname': self._methRolesByName,
        })

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
        self.runt.user.confirm(('auth', 'role', 'add'))
        rdef = await self.runt.snap.core.addRole(name)
        return Role(self.runt, rdef['iden'])

    async def _methRolesDel(self, iden):
        self.runt.user.confirm(('auth', 'role', 'del'))
        await self.runt.snap.core.delRole(iden)

class LibGates(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'get': self._methGatesGet,
            'list': self._methGatesList,
        })

    async def _methGatesList(self):
        todo = s_common.todo('getAuthGates')
        gates = await self.runt.coreDynCall(todo)
        return [Gate(self.runt, g) for g in gates]

    async def _methGatesGet(self, iden):
        iden = await toprim(iden)
        todo = s_common.todo('getAuthGate', iden)
        gate = await self.runt.coreDynCall(todo)
        if gate is None:
            return None
        return Gate(self.runt, gate)

class Gate(Prim):

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt

        self.locls.update({
            'iden': valu.get('iden'),
            'users': valu.get('users'),
            'roles': valu.get('roles'),
        })

class User(Prim):

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt

        self.locls.update({
            'iden': valu,
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
        })

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
        self.runt.user.confirm(('auth', 'user', 'grant'))
        await self.runt.snap.core.addUserRole(self.valu, iden)

    async def _methUserRevoke(self, iden):
        self.runt.user.confirm(('auth', 'user', 'revoke'))
        await self.runt.snap.core.delUserRole(self.valu, iden)

    async def _methUserSetRules(self, rules, gateiden=None):
        self.runt.user.confirm(('auth', 'user', 'set', 'rules'))
        await self.runt.snap.core.setUserRules(self.valu, rules, gateiden=gateiden)

    async def _methUserAddRule(self, rule, gateiden=None):
        self.runt.user.confirm(('auth', 'user', 'set', 'rules'))
        await self.runt.snap.core.addUserRule(self.valu, rule, gateiden=gateiden)

    async def _methUserDelRule(self, rule, gateiden=None):
        self.runt.user.confirm(('auth', 'user', 'set', 'rules'))
        await self.runt.snap.core.delUserRule(self.valu, rule, gateiden=gateiden)

    async def _methUserSetEmail(self, email):

        if self.runt.user.iden == self.valu:
            await self.runt.snap.core.setUserEmail(self.valu, email)
            return

        self.runt.user.confirm(('auth', 'user', 'set', 'email'))
        await self.runt.snap.core.setUserEmail(self.valu, email)

    async def _methUserSetAdmin(self, admin, gateiden=None):

        self.runt.user.confirm(('auth', 'user', 'set', 'admin'))
        admin = bool(intify(admin))

        await self.runt.snap.core.setUserAdmin(self.valu, admin, gateiden=gateiden)

    async def _methUserSetPasswd(self, passwd):

        if self.runt.user.iden == self.valu:
            return await self.runt.snap.core.setUserPasswd(self.valu, passwd)

        self.runt.user.confirm(('auth', 'user', 'set', 'passwd'))
        return await self.runt.snap.core.setUserPasswd(self.valu, passwd)

    async def _methUserSetLocked(self, locked):
        self.runt.user.confirm(('auth', 'user', 'set', 'locked'))
        return await self.runt.snap.core.setUserLocked(self.valu, bool(intify(locked)))

    async def value(self):
        return await self.runt.snap.core.getUserDef(self.valu)

class Role(Prim):

    def __init__(self, runt, valu, path=None):

        Prim.__init__(self, valu, path=path)
        self.runt = runt

        self.locls.update({
            'iden': valu,
            'get': self._methRoleGet,
            'addRule': self._methRoleAddRule,
            'delRule': self._methRoleDelRule,
            'setRules': self._methRoleSetRules,
        })

    async def _derefGet(self, name):
        rdef = await self.runt.snap.core.getRoleDef(self.valu)
        return rdef.get(name, s_common.novalu)

    async def _methRoleGet(self, name):
        rdef = await self.runt.snap.core.getRoleDef(self.valu)
        return rdef.get(name)

    async def _methRoleSetRules(self, rules, gateiden=None):
        self.runt.user.confirm(('auth', 'role', 'set', 'rules'))
        await self.runt.snap.core.setRoleRules(self.valu, rules, gateiden=gateiden)

    async def _methRoleAddRule(self, rule, gateiden=None):
        self.runt.user.confirm(('auth', 'role', 'set', 'rules'))
        await self.runt.snap.core.addRoleRule(self.valu, rule, gateiden=gateiden)

    async def _methRoleDelRule(self, rule, gateiden=None):
        self.runt.user.confirm(('auth', 'role', 'set', 'rules'))
        await self.runt.snap.core.delRoleRule(self.valu, rule, gateiden=gateiden)

    async def value(self):
        return await self.runt.snap.core.getRoleDef(self.valu)

class LibCron(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'at': self._methCronAt,
            'add': self._methCronAdd,
            'del': self._methCronDel,
            'get': self._methCronGet,
            'mod': self._methCronMod,
            'list': self._methCronList,
            'enable': self._methCronEnable,
            'disable': self._methCronDisable,
        })

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

            if iden.startswith(prefix) and user.allowed(perm, gateiden=iden):
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

    def _parseIncval(self, incunit, incval):
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
        Add a cron job to the cortex.
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

        if not query.startswith('{'):
            mesg = 'Query parameter must start with {'
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
                incval = self._parseIncval(optname, optval)
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

        cdef = {'storm': query[1:-1],
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
        Add non-recurring cron jobs to the cortex.
        '''
        tslist = []
        now = time.time()

        query = kwargs.get('query', None)
        if query is None:
            mesg = 'Query parameter is required.'
            raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

        if not query.startswith('{'):
            mesg = 'Query parameter must start with {'
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

        if not tslist:
            mesg = 'At least one requirement must be provided'
            raise s_exc.StormRuntimeError(mesg=mesg, kwargs=kwargs)

        reqdicts = [_ts_to_reqdict(ts) for ts in tslist]

        cdef = {'storm': query[1:-1],
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
        Delete a cron job from the cortex.
        '''
        cron = await self._matchIdens(prefix, ('cron', 'del'))
        iden = cron['iden']

        todo = s_common.todo('delCronJob', iden)
        gatekeys = ((self.runt.user.iden, ('cron', 'del'), iden),)
        return await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methCronMod(self, prefix, query):
        '''
        Modify a cron job in the cortex.
        '''
        if not query.startswith('{'):
            mesg = 'Expected second argument to start with {'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix, query=query)

        # Remove the curly braces
        query = query[1:-1]

        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = s_common.todo('updateCronJob', iden, query)
        gatekeys = ((self.runt.user.iden, ('cron', 'set'), iden),)
        return await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _methCronList(self):
        '''
        List cron jobs in the cortex.
        '''
        todo = s_common.todo('listCronJobs')
        gatekeys = ((self.runt.user.iden, ('cron', 'get'), None),)
        defs = await self.dyncall('cortex', todo, gatekeys=gatekeys)

        return [CronJob(self.runt, cdef, path=self.path) for cdef in defs]

    async def _methCronGet(self, prefix):
        '''
        Retrieve a cron job from the cortex.
        '''
        cdef = await self._matchIdens(prefix, ('cron', 'get'))

        return CronJob(self.runt, cdef, path=self.path)

    async def _methCronEnable(self, prefix):
        '''
        Enable a cron job in the cortex.
        '''
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = ('enableCronJob', (iden,), {})
        await self.runt.dyncall('cortex', todo)

        return iden

    async def _methCronDisable(self, prefix):
        '''
        Disable a cron job in the cortex.
        '''
        cron = await self._matchIdens(prefix, ('cron', 'set'))
        iden = cron['iden']

        todo = ('disableCronJob', (iden,), {})
        await self.runt.dyncall('cortex', todo)

        return iden

class CronJob(Prim):
    '''
    Implements the STORM api for a cronjob instance.
    '''
    def __init__(self, runt, cdef, path=None):
        Prim.__init__(self, cdef, path=path)
        self.runt = runt
        self.locls.update({
            'iden': cdef.get('iden'),
            'pack': self._methCronJobPack,
            'pprint': self._methCronJobPprint,
        })

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

class LibModel(Lib):
    '''
    A collection of method around the data model
    '''
    def __init__(self, runt, name=()):
        Lib.__init__(self, runt, name)
        self.model = runt.model

    def addLibFuncs(self):
        self.locls.update({
            'type': self._methType,
            'prop': self._methProp,
            'form': self._methForm,
        })

    @s_cache.memoize(size=100)
    async def _methType(self, name):
        type_ = self.model.type(name)
        if type_ is not None:
            return ModelType(type_)

    @s_cache.memoize(size=100)
    async def _methProp(self, name):
        prop = self.model.prop(name)
        if prop is not None:
            return ModelProp(prop)

    @s_cache.memoize(size=100)
    async def _methForm(self, name):
        form = self.model.form(name)
        if form is not None:
            return ModelForm(form)

class ModelForm(Prim):

    def __init__(self, form, path=None):

        Prim.__init__(self, form, path=path)

        self.locls.update({
            'name': form.name,
            'prop': self._getFormProp,
        })

        self.ctors.update({
            'type': self._ctorFormType,
        })

    def _ctorFormType(self, path=None):
        return ModelType(self.valu.type, path=path)

    def _getFormProp(self, name):
        prop = self.valu.prop(name)
        if prop is not None:
            return ModelProp(prop)

class ModelProp(Prim):

    def __init__(self, prop, path=None):

        Prim.__init__(self, prop, path=path)

        self.locls.update({
            'name': prop.name,
            'full': prop.full,
        })

        self.ctors.update({
            'form': self._ctorPropForm,
            'type': self._ctorPropType,
        })

    def _ctorPropType(self, path=None):
        return ModelType(self.valu.type, path=path)

    def _ctorPropForm(self, path=None):
        return ModelForm(self.valu.form, path=path)

class ModelType(Prim):
    '''
    A Storm types wrapper around a lib.types.Type
    '''
    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
        self.locls.update({
            'name': valu.name,
            'repr': self._methRepr,
            'norm': self._methNorm,
        })

    async def _methRepr(self, valu):
        nval = self.valu.norm(valu)
        return self.valu.repr(nval[0])

    async def _methNorm(self, valu):
        return self.valu.norm(valu)

# These will go away once we have value objects in storm runtime
async def toprim(valu, path=None):

    if isinstance(valu, (str, int, bool, float, bytes)) or valu is None:
        return valu

    if isinstance(valu, (tuple, list)):
        return tuple([await toprim(v) for v in valu])

    if isinstance(valu, dict):
        return {await toprim(k): await toprim(v) for (k, v) in valu.items()}

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
