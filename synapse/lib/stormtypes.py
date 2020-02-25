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

import synapse.lib.ast as s_ast
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

        return int(x, 0)

    return int(x)

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
            return ctor(path=self.path)

        raise s_exc.NoSuchName(name=name, styp=self.__class__.__name__)

class Lib(StormType):

    def __init__(self, runt, name=()):
        StormType.__init__(self)
        self.runt = runt
        self.name = name

        self.addLibFuncs()

    def addLibFuncs(self):
        pass

    async def deref(self, name):
        try:
            return await StormType.deref(self, name)
        except s_exc.NoSuchName:
            pass

        path = self.name + (name,)

        slib = await self.runt.snap.getStormLib(path)
        if slib is None:
            raise s_exc.NoSuchName(name=name)

        ctor = slib[2].get('ctor', Lib)
        return ctor(self.runt, name=path)

class LibPkg(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._libPkgAdd,
            'del': self._libPkgDel,
            'list': self._libPkgList,
        })

    async def _libPkgAdd(self, pkgdef):
        self.runt.reqAllowed(('storm', 'pkg', 'add'))
        await self.runt.snap.addStormPkg(pkgdef)

    async def _libPkgDel(self, name):
        self.runt.reqAllowed(('storm', 'pkg', 'del'))
        return await self.runt.snap.delStormPkg(name)

    async def _libPkgList(self):
        return await self.runt.snap.getStormPkgs()

class LibDmon(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._libDmonAdd,
            'del': self._libDmonDel,
            'list': self._libDmonList,
        })

    async def _libDmonDel(self, iden):

        dmon = await self.runt.snap.getStormDmon(iden)
        if dmon is None:
            mesg = f'No storm dmon with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        if dmon.ddef.get('user') != self.runt.user.iden:
            self.runt.reqAllowed(('storm', 'dmon', 'del', iden))

        await self.runt.snap.delStormDmon(iden)

    async def _libDmonList(self):
        dmons = await self.runt.snap.getStormDmons()
        return [d.pack() for d in dmons]

    async def _libDmonAdd(self, quer, name='noname'):
        '''
        Add a storm dmon (persistent background task) to the cortex.

        $lib.dmon.add(${ myquery })
        '''
        self.runt.reqAllowed(('storm', 'dmon', 'add'))

        # closure style capture of runtime
        runtvars = {k: v for (k, v) in self.runt.vars.items() if s_msgpack.isok(v)}

        opts = {'vars': runtvars,
                'view': self.runt.snap.view.iden,  # Capture the current view iden.
                }

        ddef = {
            'name': name,
            'user': self.runt.user.iden,
            'storm': str(quer),
            'stormopts': opts,
        }

        dmon = await self.runt.snap.addStormDmon(ddef)

        return dmon.pack()

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

        self.runt.reqAllowed(('storm', 'service', 'add'))
        sdef = {
            'name': name,
            'url': url,
        }
        ssvc = await self.runt.snap.addStormSvc(sdef)
        return ssvc.sdef

    async def _libSvcDel(self, iden):
        self.runt.reqAllowed(('storm', 'service', 'del'))
        return await self.runt.snap.delStormSvc(iden)

    async def _libSvcGet(self, name):
        self.runt.reqAllowed(('storm', 'service', 'get', name))
        ssvc = self.runt.snap.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg)
        return ssvc

    async def _libSvcList(self):
        self.runt.reqAllowed(('storm', 'service', 'list'))
        retn = []

        for ssvc in self.runt.snap.getStormSvcs():
            sdef = dict(ssvc.sdef)
            sdef['ready'] = ssvc.ready.is_set()
            retn.append(sdef)

        return retn

    async def _libSvcWait(self, name):
        self.runt.reqAllowed(('storm', 'service', 'get'))
        ssvc = self.runt.snap.getStormSvc(name)
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
            'text': self._text,
            'print': self._print,
            'sorted': self._sorted,
            'import': self._libBaseImport,
        })

    async def _libBaseImport(self, name):

        mdef = self.runt.getStormMod(name)
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
        return len(item)

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

    async def _print(self, mesg, **kwargs):
        if not isinstance(mesg, str):
            mesg = repr(mesg)
        elif kwargs:
            mesg = kwarg_format(mesg, **kwargs)
        await self.runt.printf(mesg)

    async def _dict(self, **kwargs):
        return kwargs
        # TODO: return Dict(kwargs)

    async def _fire(self, name, **info):
        await self.runt.snap.fire('storm:fire', type=name, data=info)

class LibStr(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'concat': self.concat,
            'format': self.format,
        })

    async def concat(self, *args):
        strs = [str(a) for a in args]
        return ''.join(strs)

    async def format(self, text, **kwargs):

        text = kwarg_format(text, **kwargs)

        return text

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

        axon = await self.runt.snap.getCoreAxon()
        size, sha2 = await axon.put(byts)

        return (size, s_common.ehex(sha2))

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
        timetype = self.runt.snap.model.type('time')
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
        row = [toprim(a) for a in args]
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
        self.runt.reqLayerAllowed(('feed:data', *name.split('.')))
        with s_provenance.claim('feed:data', name=name):
            return self.runt.snap.addFeedNodes(name, data)

    async def _libList(self):
        return await self.runt.snap.getFeedFuncs()

    async def _libIngest(self, name, data, seqn=None):
        '''
        Add nodes to the graph with a given ingest type.

        Args:
            name (str): Name of the ingest function to send data too.
            data: Data to feed to the ingest function.
            seqn: A tuple of (guid, offset) values used for tracking ingest data.

        Notes:
            This is using the Runtimes's Snap to call addFeedData(), after setting
            the snap.strict mode to False. This will cause node creation and property
            setting to produce warning messages, instead of causing the Storm Runtime
            to be torn down.

        Returns:
            None or the sequence offset value.
        '''

        self.runt.reqLayerAllowed(('feed:data', *name.split('.')))
        with s_provenance.claim('feed:data', name=name):
            strict = self.runt.snap.strict
            self.runt.snap.strict = False
            retn = await self.runt.snap.addFeedData(name, data, seqn)
            self.runt.snap.strict = strict
        return retn

class LibQueue(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._methQueueAdd,
            'del': self._methQueueDel,
            'get': self._methQueueGet,
            'list': self._methQueueList,
        })

    async def _methQueueAdd(self, name):
        self.runt.reqAllowed(('storm', 'queue', 'add'))
        info = await self.runt.snap.addCoreQueue(name, {})
        return Queue(self.runt, name, info)

    async def _methQueueGet(self, name):

        info = await self.runt.snap.getCoreQueue(name)
        if info is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        return Queue(self.runt, name, info)

    async def _methQueueDel(self, name):

        if not await self.runt.snap.hasCoreQueue(name):
            mesg = f'No queue named {name} exists.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        info = await self.runt.snap.getCoreQueue(name)

        if (info.get('user') == self.runt.user.iden or
            self.runt.reqAllowed(('storm', 'queue', 'del', name))):
            await self.runt.snap.delCoreQueue(name)

    async def _methQueueList(self):
        self.runt.reqAllowed(('storm', 'lib', 'queue', 'list'))
        return await self.runt.snap.getCoreQueues()

class Queue(StormType):
    '''
    A StormLib API instance of a named channel in the cortex multiqueue.
    '''

    def __init__(self, runt, name, info):

        StormType.__init__(self)
        self.runt = runt
        self.name = name
        self.info = info

        self.locls.update({
            'get': self._methQueueGet,
            'put': self._methQueuePut,
            'puts': self._methQueuePuts,
            'gets': self._methQueueGets,
            'cull': self._methQueueCull,
        })

    async def _methQueueCull(self, offs):
        self.reqAllowed(('storm', 'queue', self.name, 'get'))

        offs = intify(offs)
        await self.runt.snap.cullCoreQueue(self.name, offs)

    async def _methQueueGets(self, offs=0, wait=True, cull=True, size=None):

        self.reqAllowed(('storm', 'queue', self.name, 'get'))

        wait = intify(wait)
        cull = intify(cull)
        offs = intify(offs)

        if size is not None:
            size = intify(size)

        async for item in self.runt.snap.getsCoreQueue(self.name, offs, cull=cull, wait=wait, size=size):
            yield item

    async def _methQueuePuts(self, items, wait=False):
        self.reqAllowed(('storm', 'queue', self.name, 'put'))
        return await self.runt.snap.putsCoreQueue(self.name, items)

    def reqAllowed(self, perm):
        if self.info.get('user') == self.runt.user.iden:
            return
        self.runt.reqAllowed(perm)

    async def _methQueueGet(self, offs=0, wait=True, cull=True):

        self.reqAllowed(('storm', 'queue', self.name, 'get'))

        offs = intify(offs)
        wait = intify(wait)
        cull = intify(cull)

        async for item in self.runt.snap.getsCoreQueue(self.name, offs, cull=cull, wait=wait):
            return item

    async def _methQueuePut(self, item):
        self.reqAllowed(('storm', 'queue', self.name, 'put'))
        return await self.runt.snap.putCoreQueue(self.name, item)

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
        self.runt.reqAllowed(('storm', 'lib', 'telepath', 'open', scheme))
        return Proxy(await self.runt.getTeleProxy(url))

class Proxy(StormType):

    def __init__(self, proxy, path=None):
        StormType.__init__(self, path=path)
        self.proxy = proxy

    async def deref(self, name):

        if name[0] == '_':
            mesg = f'No proxy method named {name}'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        return getattr(self.proxy, name, None)

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
        })

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

    async def setitem(self, name, valu):
        self.valu[name] = valu

    async def deref(self, name):
        return self.valu.get(name)

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

    def __len__(self):
        return len(self.valu)

    def __iter__(self):
        for item in self.valu:
            yield item

    async def __aiter__(self):
        for item in self.valu:
            yield item

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
            'size': self._methListSize,
            'index': self._methListIndex,
            'length': self._methListLength,
            'append': self._methListAppend,
        })

    def __len__(self):
        return len(self.valu)

    def __iter__(self):
        for item in self.valu:
            yield item

    async def __aiter__(self):
        for item in self:
            yield item

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
        # TODO - Remove this v0.3.0
        return len(self)

    async def _methListSize(self):
        '''
        Return the length of the list.
        '''
        return len(self)

class StormHiveDict(Prim):
    # A Storm API for a HiveDict
    def __init__(self, valu, path=None):
        Prim.__init__(self, valu, path=path)
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
        return self.valu.get(name, default=default)

    async def _methPop(self, name, default=None):
        self._reqStr(name)
        return await self.valu.pop(name, default=default)

    async def _methSet(self, name, valu):
        self._reqStr(name)
        await self.valu.set(name, valu)

    async def _methList(self):
        return list(self.valu.items())

class LibUser(Lib):
    def addLibFuncs(self):
        hivedict = StormHiveDict(self.runt.user.pvars)
        profdict = StormHiveDict(self.runt.user.profile)
        self.locls.update({
            'name': self._libUserName,
            'vars': hivedict,
            'profile': profdict,
        })

    async def _libUserName(self, path=None):
        return self.runt.user.name

class LibGlobals(Lib):
    '''
    Global persistent Storm variables
    '''
    def __init__(self, runt, name):
        self._stormvars = runt.snap.getStormVars()
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
        self.runt.reqAllowed(('storm:globals:get', name))
        return self._stormvars.get(name, default=default)

    async def _methPop(self, name, default=None):
        self._reqStr(name)
        self.runt.reqAllowed(('storm:globals:pop', name))
        return await self._stormvars.pop(name, default=default)

    async def _methSet(self, name, valu):
        self._reqStr(name)
        self.runt.reqAllowed(('storm:globals:set', name))
        await self._stormvars.set(name, valu)

    async def _methList(self):
        ret = []
        for key, valu in list(self._stormvars.items()):
            try:
                self.runt.reqAllowed(('storm:globals:get', key))
            except s_exc.AuthDeny:
                continue
            else:
                ret.append((key, valu))
        return ret

class LibVars(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'get': self._libVarsGet,
            'set': self._libVarsSet,
            'del': self._libVarsDel,
            'list': self._libVarsList,
        })

    async def _libVarsGet(self, name):
        '''
        Resolve a variable in a storm query
        '''
        return self.runt.getVar(name, defv=s_common.novalu)

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

class Query(StormType):
    '''
    A storm primitive representing an embedded query.
    '''
    def __init__(self, text, opts, runt, path=None):

        StormType.__init__(self, path=path)

        self.text = text
        self.opts = opts
        self.runt = runt

        self.locls.update({
            'exec': self._methQueryExec,
        })

    def __str__(self):
        return self.text

    async def _methQueryExec(self):
        query = await self.runt.getStormQuery(self.text)
        subrunt = await self.runt.getScopeRuntime(query)

        logger.info(f'Executing storm query via exec() {{{self.text}}} as [{self.runt.user.name}]')
        cancelled = False
        try:
            async for item in query.run(subrunt, genr=s_ast.agen()):
                pass  # pragma: no cover
        except s_ast.StormReturn as e:
            return e.item
        except asyncio.CancelledError:  # pragma: no cover
            cancelled = True
            raise
        finally:
            if not cancelled:
                await self.runt.propBackGlobals(subrunt)

class NodeData(Prim):

    def __init__(self, node, path=None):

        Prim.__init__(self, node, path=path)

        self.locls.update({
            'get': self._getNodeData,
            'set': self._setNodeData,
            'pop': self._popNodeData,
            'list': self._listNodeData,
        })

    def _reqAllowed(self, perm):
        if not self.valu.snap.user.allowed(perm):
            pstr = '.'.join(perm)
            mesg = f'User is not allowed permission: {pstr}'
            raise s_exc.AuthDeny(perm=perm, mesg=mesg)

    async def _getNodeData(self, name):
        self._reqAllowed(('storm', 'node', 'data', 'get', name))
        return await self.valu.getData(name)

    async def _setNodeData(self, name, valu):
        self._reqAllowed(('storm', 'node', 'data', 'set', name))
        return await self.valu.setData(name, valu)

    async def _popNodeData(self, name):
        self._reqAllowed(('storm', 'node', 'data', 'pop', name))
        return await self.valu.popData(name)

    async def _listNodeData(self):
        self._reqAllowed(('storm', 'node', 'data', 'list'))
        return [x async for x in self.valu.iterData()]

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
            'value': self._methNodeValue,
            'globtags': self._methNodeGlobTags,

            'isform': self._methNodeIsForm,
        })

        def ctordata(path=None):
            return NodeData(node, path=path)

        self.ctors['data'] = ctordata

    async def _methNodePack(self, dorepr=False):
        '''
        Return the serializable/packed version of the Node.

        Args:
            dorepr (bool): Include repr information for human readable versions of properties.

        Returns:
            (tuple): An (ndef, info) node tuple.
        '''
        return self.valu.pack(dorepr=dorepr)

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
        try:
            return self.valu.repr(name=name)

        except s_exc.NoPropValu:
            return defv

        except s_exc.NoSuchProp as e:
            form = e.get('form')
            prop = e.get('prop')
            mesg = f'Requested property [{prop}] does not exist for the form [{form}].'
            raise s_exc.StormRuntimeError(mesg=mesg, form=form, prop=prop) from None

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

    async def inc(self, name, valu=1):
        valu = intify(valu)
        self.counters[name] += valu

    async def get(self, name):
        return self.counters.get(name, 0)

class LibView(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._methViewAdd,
            'del': self._methViewDel,
            'fork': self._methViewFork,
            'get': self._methViewGet,
            'list': self._methViewList,
            'merge': self._methViewMerge,
        })

    async def _methViewAdd(self, layers):
        '''
        Add a view to the cortex.
        '''
        self.runt.reqAllowed(('view', 'add'))

        iden = s_common.guid()
        view = await self.runt.snap.addView(iden, layers)

        if view is None:
            mesg = f'Failed to add view.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=iden, layers=layers)

        return View(self.runt, view, path=self.path)

    async def _methViewDel(self, iden):
        '''
        Delete a view in the cortex.
        '''
        view = self.runt.snap.getView(iden)
        if view is None:
            mesg = f'No view with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        if view is self.runt.snap.core.view:
            mesg = f'Deleting the main view is not permitted.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=iden)

        if not view.info.get('owner') == self.runt.user.iden:
            self.runt.reqAllowed(('view', 'del'))

        await self.runt.snap.delView(iden=view.iden)

        return True

    async def _methViewFork(self, iden):
        '''
        Fork a view in the cortex.
        '''
        self.runt.reqAllowed(('view', 'add'))

        view = self.runt.snap.getView(iden)
        if view is None:
            mesg = f'No view with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        newview = await view.fork(owner=self.runt.user.iden)

        return View(self.runt, newview, path=self.path)

    async def _methViewGet(self, iden=None):
        '''
        Retrieve a view from the cortex.
        '''
        self.runt.reqAllowed(('view', 'read'))

        view = self.runt.snap.getView(iden)
        if view is None:
            mesg = f'No view with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        return View(self.runt, view, path=self.path)

    async def _methViewList(self):
        '''
        List the views in the cortex.
        '''
        self.runt.reqAllowed(('view', 'read'))

        views = self.runt.snap.listViews()

        return [View(self.runt, view, path=self.path) for view in views]

    async def _methViewMerge(self, iden):
        '''
        Merge a forked view back into its parent.

        When complete, the view is deleted.
        '''
        view = self.runt.snap.getView(iden)
        if view is None:
            mesg = f'No view with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        if not view.info.get('owner') == self.runt.user.iden:
            self.runt.reqAllowed(('view', 'del'))

        view.layers[0].readonly = True
        try:
            await view.mergeAllowed(self.runt.user)
            await view.merge()
        except asyncio.CancelledError:  # pragma: no cover
            raise

        except s_exc.AuthDeny as e:
            view.layers[0].readonly = False
            perm = e.get('perm')
            mesg = f'Insufficient permissions to perform merge: {e.get("mesg")}'
            raise s_exc.AuthDeny(mesg=mesg, perm=perm, iden=iden) from None

        except Exception as e:
            view.layers[0].readonly = False
            mesg = f'Error during merge - {str(e)}'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=iden) from None

class View(Prim):
    '''
    Implements the STORM api for a view instance.
    '''
    def __init__(self, runt, view, path=None):

        Prim.__init__(self, view, path=path)
        self.runt = runt

        self.locls.update({
            'iden': view.iden,
            'pack': self._methViewPack,
            'fork': self._methViewFork,
        })

    async def _methViewFork(self):

        self.runt.reqAllowed(('view', 'add'))

        view = await self.valu.fork(owner=self.runt.user.iden)

        return View(self.runt, view)

    async def _methViewPack(self):

        layrinfo = []
        for layr in self.valu.layers:
            layrinfo.append({
                'ctor': layr.ctorname,
                'iden': layr.iden,
                'readonly': layr.readonly,
            })

        return {
            'iden': self.valu.iden,
            'owner': self.valu.info.get('owner'),
            'layers': layrinfo,
        }

class LibTrigger(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._methTriggerAdd,
            'del': self._methTriggerDel,
            'mod': self._methTriggerMod,
            'list': self._methTriggerList,
            'enable': self._methTriggerEnable,
            'disable': self._methTriggerDisable,
        })

    async def _matchIdens(self, prefix, perm):
        '''
        Returns the iden that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        matches = []
        trigs = await self.runt.snap.listTriggers()

        for (iden, trig) in trigs:
            if iden.startswith(prefix) and await trig.allowed(self.runt.user, perm):
                matches.append(iden)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            mesg = 'Provided iden does not match any valid authorized triggers.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)
        else:
            mesg = 'Provided iden matches more than one trigger.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

    async def _methTriggerAdd(self, cond, form=None, tag=None, prop=None, query=None, disabled=False):
        '''
        Add a trigger to the cortex.
        '''
        self.runt.reqAllowed(('trigger', 'add'))

        if query is None:
            mesg = 'Missing query parameter'
            raise s_exc.StormRuntimeError(mesg=mesg, cond=cond, form=form, tag=tag,
                                          prop=prop, query=query, disabled=disabled)

        if cond.startswith('tag') and tag is None:
            mesg = 'Missing tag parameter'
            raise s_exc.StormRuntimeError(mesg=mesg, cond=cond, form=form, tag=tag,
                                          prop=prop, query=query, disabled=disabled)

        elif cond.startswith('node'):
            if form is None:
                mesg = 'Missing form parameter'
                raise s_exc.StormRuntimeError(mesg=mesg, cond=cond, form=form, tag=tag,
                                              prop=prop, query=query, disabled=disabled)
            if tag is not None:
                mesg = 'node:* does not support a tag'
                raise s_exc.StormRuntimeError(mesg=mesg, cond=cond, form=form, tag=tag,
                                              prop=prop, query=query, disabled=disabled)

        elif cond.startswith('prop'):
            if prop is None:
                mesg = 'Missing prop parameter'
                raise s_exc.StormRuntimeError(mesg=mesg, cond=cond, form=form, tag=tag,
                                              prop=prop, query=query, disabled=disabled)
            if tag is not None:
                mesg = 'prop:set does not support a tag'
                raise s_exc.StormRuntimeError(mesg=mesg, cond=cond, form=form, tag=tag,
                                              prop=prop, query=query, disabled=disabled)

        # Remove the curly braces
        query = query[1:-1]

        if tag is not None:
            tag = tag[1:]

        info = {'form': form, 'tag': tag, 'prop': prop}

        iden = await self.runt.snap.addTrigger(cond, query, info=info,
                                               disabled=disabled)
        return iden

    async def _methTriggerDel(self, prefix):
        '''
        Delete a trigger from the cortex.
        '''
        iden = await self._matchIdens(prefix, ('trigger', 'del'))

        await self.runt.snap.delTrigger(iden)

        return iden

    async def _methTriggerMod(self, prefix, query):
        '''
        Modify a trigger in the cortex.
        '''
        if not query.startswith('{'):
            mesg = 'Expected second argument to start with {'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix, query=query)

        # Remove the curly braces
        query = query[1:-1]

        iden = await self._matchIdens(prefix, ('trigger', 'set'))
        await self.runt.snap.updateTrigger(iden, query)

        return iden

    async def _methTriggerList(self):
        '''
        List triggers in the cortex.
        '''
        triglist = await self.runt.snap.listTriggers()

        triggers = []
        for iden, trigger in triglist:
            if not await trigger.allowed(self.runt.user, ('trigger', 'get')):
                continue

            trig = trigger.pack()
            user = self.runt.snap.getUserName(trig.get('useriden'))

            triggers.append({
                'iden': iden,
                'idenshort': iden[:8] + '..',
                'user': user or '<None>',
                'query': trig.get('storm') or '<missing>',
                'cond': trig.get('cond') or '<missing>',
                'enabled': 'Y' if trig.get('enabled', True) else 'N',
                'tag': '#' + (trig.get('tag') or '<missing>'),
                'form': trig.get('form') or '',
                'prop': trig.get('prop') or '<missing>',
            })

        return triggers

    async def _methTriggerEnable(self, prefix):
        '''
        Enable a trigger in the cortex.
        '''
        iden = await self._matchIdens(prefix, ('trigger', 'set'))
        await self.runt.snap.enableTrigger(iden)

        return iden

    async def _methTriggerDisable(self, prefix):
        '''
        Disable a trigger in the cortex.
        '''
        iden = await self._matchIdens(prefix, ('trigger', 'set'))
        await self.runt.snap.disableTrigger(iden)

        return iden

class LibCron(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'at': self._methCronAt,
            'add': self._methCronAdd,
            'del': self._methCronDel,
            'mod': self._methCronMod,
            'list': self._methCronList,
            'stat': self._methCronStat,
            'enable': self._methCronEnable,
            'disable': self._methCronDisable,
        })

    async def _matchIdens(self, prefix, perm):
        '''
        Returns the iden that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        matches = []
        crons = await self.runt.snap.listCronJobs()

        for (iden, cron) in crons:
            if iden.startswith(prefix) and await cron.allowed(self.runt.user, perm):
                matches.append(iden)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            mesg = 'Provided iden does not match any valid authorized cron job.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)
        else:
            mesg = 'Provided iden matches more than one cron job.'
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
        self.runt.reqAllowed(('cron', 'add'))

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

        # Remove the curly braces
        query = query[1:-1]

        iden = await self.runt.snap.addCronJob(query, reqdict, incunit, incval)
        return iden

    async def _methCronAt(self, **kwargs):
        '''
        Add non-recurring cron jobs to the cortex.
        '''
        self.runt.reqAllowed(('cron', 'add'))

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

        query = query[1:-1]

        iden = await self.runt.snap.addCronJob(query, reqdicts, None, None)
        return iden

    async def _methCronDel(self, prefix):
        '''
        Delete a cron job from the cortex.
        '''
        iden = await self._matchIdens(prefix, ('cron', 'del'))

        await self.runt.snap.delCronJob(iden)

        return iden

    async def _methCronMod(self, prefix, query):
        '''
        Modify a cron job in the cortex.
        '''
        if not query.startswith('{'):
            mesg = 'Expected second argument to start with {'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix, query=query)

        # Remove the curly braces
        query = query[1:-1]

        iden = await self._matchIdens(prefix, ('cron', 'set'))
        await self.runt.snap.updateCronJob(iden, query)

        return iden

    @staticmethod
    def _formatTimestamp(ts):
        # N.B. normally better to use fromtimestamp with UTC timezone,
        # but we don't want timezone to print out
        return datetime.datetime.utcfromtimestamp(ts).isoformat(timespec='minutes')

    async def _methCronList(self):
        '''
        List cron jobs in the cortex.
        '''
        cronlist = await self.runt.snap.listCronJobs()

        jobs = []
        for iden, cronjob in cronlist:
            if not await cronjob.allowed(self.runt.user, ('cron', 'get')):
                continue

            cron = cronjob.pack()
            user = self.runt.snap.getUserName(cron.get('useriden'))

            laststart = cron.get('laststarttime')
            lastend = cron.get('lastfinishtime')
            result = cron.get('lastresult')

            jobs.append({
                'iden': iden,
                'idenshort': iden[:8] + '..',
                'user': user or '<None>',
                'query': cron.get('query') or '<missing>',
                'isrecur': 'Y' if cron.get('recur') else 'N',
                'isrunning': 'Y' if cron.get('isrunning') else 'N',
                'enabled': 'Y' if cron.get('enabled', True) else 'N',
                'startcount': cron.get('startcount') or 0,
                'laststart': 'Never' if laststart is None else self._formatTimestamp(laststart),
                'lastend': 'Never' if lastend is None else self._formatTimestamp(lastend),
                'iserr': 'X' if result is not None and not result.startswith('finished successfully') else ' '
            })

        return jobs

    async def _methCronStat(self, prefix):
        '''
        Get information about a cron job.
        '''
        matches = []
        crons = await self.runt.snap.listCronJobs()

        for (iden, cron) in crons:
            if iden.startswith(prefix) and await cron.allowed(self.runt.user, ('cron', 'get')):
                matches.append(iden)

        if len(matches) == 0:
            mesg = 'Provided iden does not match any valid authorized cron job.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)
        elif len(matches) > 1:
            mesg = 'Provided iden matches more than one cron job.'
            raise s_exc.StormRuntimeError(mesg=mesg, iden=prefix)

        iden = matches[0]
        cronjob = [cron[1] for cron in crons if cron[0] == iden][0]
        cron = cronjob.pack()
        user = self.runt.snap.getUserName(cron.get('useriden'))

        laststart = cron.get('laststarttime')
        lastend = cron.get('lastfinishtime')

        job = {
            'iden': iden,
            'user': user or '<None>',
            'query': cron.get('query') or '<missing>',
            'isrecur': 'Y' if cron.get('recur') else 'N',
            'isrunning': 'Y' if cron.get('isrunning') else 'N',
            'enabled': 'Y' if cron.get('enabled', True) else 'N',
            'startcount': cron.get('startcount') or 0,
            'laststart': 'Never' if laststart is None else self._formatTimestamp(laststart),
            'lastend': 'Never' if lastend is None else self._formatTimestamp(lastend),
            'lastresult': cron.get('lastresult') or '<None>',
            'recs': []
        }

        for reqdict, incunit, incval in cron.get('recs', []):
            job['recs'].append({
                'reqdict': reqdict or '<None>',
                'incunit': incunit or '<None>',
                'incval': incval or '<None>'
            })

        return job

    async def _methCronEnable(self, prefix):
        '''
        Enable a cron job in the cortex.
        '''
        iden = await self._matchIdens(prefix, ('cron', 'set'))
        await self.runt.snap.enableCronJob(iden)

        return iden

    async def _methCronDisable(self, prefix):
        '''
        Disable a cron job in the cortex.
        '''
        iden = await self._matchIdens(prefix, ('cron', 'set'))
        await self.runt.snap.disableCronJob(iden)

        return iden

# These will go away once we have value objects in storm runtime
def toprim(valu, path=None):

    if isinstance(valu, (str, tuple, list, dict, int)) or valu is None:
        return valu

    if isinstance(valu, Prim):
        return valu.value()

    if isinstance(valu, s_node.Node):
        return valu.ndef[1]

    mesg = 'Unable to convert object to Storm primitive.'
    raise s_exc.NoSuchType(mesg=mesg, name=valu.__class__.__name__)

def fromprim(valu, path=None):

    if isinstance(valu, str):
        return Str(valu, path=path)

    # TODO: make s_node.Node a storm type itself?
    if isinstance(valu, s_node.Node):
        return Node(valu, path=path)

    if isinstance(valu, s_node.Path):
        return Path(valu, path=path)

    if isinstance(valu, (tuple, list)):
        # FIXME - List() has methods which are incompatible with a Python tuple.
        return List(valu, path=path)

    if isinstance(valu, dict):
        return Dict(valu, path=path)

    if isinstance(valu, bytes):
        return Bytes(valu, path=path)

    if isinstance(valu, StormType):
        return valu

    mesg = 'Unable to convert python primitive to StormType.'
    raise s_exc.NoSuchType(mesg=mesg, python_type=valu.__class__.__name__)
