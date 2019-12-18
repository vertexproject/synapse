import bz2
import gzip
import json
import base64
import asyncio
import logging
import binascii
import datetime
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

        slib = self.runt.snap.core.getStormLib(path)
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
        await self.runt.snap.core.addStormPkg(pkgdef)

    async def _libPkgDel(self, name):
        self.runt.reqAllowed(('storm', 'pkg', 'del'))
        return await self.runt.snap.core.delStormPkg(name)

    async def _libPkgList(self):
        return await self.runt.snap.core.getStormPkgs()

class LibDmon(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._libDmonAdd,
            'del': self._libDmonDel,
            'list': self._libDmonList,
        })

    async def _libDmonDel(self, iden):

        dmon = await self.runt.snap.core.getStormDmon(iden)
        if dmon is None:
            mesg = f'No storm dmon with iden: {iden}'
            raise s_exc.NoSuchIden(mesg=mesg)

        if dmon.ddef.get('user') != self.runt.user.iden:
            self.runt.reqAllowed(('storm', 'dmon', 'del', iden))

        await self.runt.snap.core.delStormDmon(iden)

    async def _libDmonList(self):
        dmons = await self.runt.snap.core.getStormDmons()
        return [d.pack() for d in dmons]

    async def _libDmonAdd(self, quer, name='noname'):
        '''
        Add a storm dmon (persistent background task) to the cortex.

        $lib.dmon.add(${ myquery })
        '''
        self.runt.reqAllowed(('storm', 'dmon', 'add'))

        # closure style capture of runtime
        runtvars = {k: v for (k, v) in self.runt.vars.items() if s_msgpack.isok(v)}

        opts = {'vars': runtvars}

        ddef = {
            'name': name,
            'user': self.runt.user.iden,
            'storm': str(quer),
            'stormopts': opts,
        }

        dmon = await self.runt.snap.core.addStormDmon(ddef)

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
        ssvc = await self.runt.snap.core.addStormSvc(sdef)
        return ssvc.sdef

    async def _libSvcDel(self, iden):
        self.runt.reqAllowed(('storm', 'service', 'del'))
        return await self.runt.snap.core.delStormSvc(iden)

    async def _libSvcGet(self, name):
        self.runt.reqAllowed(('storm', 'service', 'get', name))
        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg)
        return ssvc

    async def _libSvcList(self):
        self.runt.reqAllowed(('storm', 'service', 'list'))
        retn = []

        for ssvc in self.runt.snap.core.getStormSvcs():
            sdef = dict(ssvc.sdef)
            sdef['ready'] = ssvc.ready.is_set()
            retn.append(sdef)

        return retn

    async def _libSvcWait(self, name):
        self.runt.reqAllowed(('storm', 'service', 'get'))
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

        await self.runt.snap.core.axready.wait()
        size, sha2 = await self.runt.snap.core.axon.put(byts)
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

    async def ticker(self, tick, count=None):

        if count is not None:
            count = intify(count)

        tick = float(tick)

        offs = 0
        while True:

            await self.runt.snap.waitfini(timeout=tick)
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
        return await self.runt.snap.core.getFeedFuncs()

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

        info = self.runt.snap.core.multiqueue.queues.get(name)
        if info is not None:
            mesg = f'A queue named {name} already exists.'
            raise s_exc.DupName(mesg=mesg)

        info = {'user': self.runt.user.iden, 'time': s_common.now()}
        self.runt.snap.core.multiqueue.add(name, info)

        return Queue(self.runt, name, info)

    async def _methQueueGet(self, name):

        info = self.runt.snap.core.multiqueue.queues.get(name)
        if info is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        return Queue(self.runt, name, info)

    async def _methQueueDel(self, name, allow=()):

        info = self.runt.snap.core.multiqueue.queues.get(name)
        if info is None:
            mesg = f'No queue named {name} exists.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        if info.get('user') != self.runt.user.iden:
            self.runt.reqAllowed(('storm', 'queue', 'del', name))

        await self.runt.snap.core.multiqueue.rem(name)

    async def _methQueueList(self):
        self.runt.reqAllowed(('storm', 'lib', 'queue', 'list'))
        return self.runt.snap.core.multiqueue.list()

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
        await self.reqAllowed(('storm', 'queue', self.name, 'get'))

        offs = intify(offs)

        await self.runt.snap.core.multiqueue.cull(self.name, offs)

    async def _methQueueGets(self, offs=0, wait=True, cull=True, size=None):

        await self.reqAllowed(('storm', 'queue', self.name, 'get'))

        wait = intify(wait)
        cull = intify(cull)
        offs = intify(offs)

        if size is not None:
            size = intify(size)

        mque = self.runt.snap.core.multiqueue

        async for item in mque.gets(self.name, offs, cull=cull, wait=wait, size=size):
            yield item

    async def _methQueuePuts(self, items, wait=False):
        await self.reqAllowed(('storm', 'queue', self.name, 'put'))
        return self.runt.snap.core.multiqueue.puts(self.name, items)

    async def reqAllowed(self, perm):
        if self.info.get('user') == self.runt.user.iden:
            return
        self.runt.reqAllowed(perm)

    async def _methQueueGet(self, offs=0, wait=True, cull=True):

        await self.reqAllowed(('storm', 'queue', self.name, 'get'))

        offs = intify(offs)
        wait = intify(wait)
        cull = intify(cull)

        mque = self.runt.snap.core.multiqueue

        async for item in mque.gets(self.name, offs, cull=cull, wait=wait):
            return item

    async def _methQueuePut(self, item):
        await self.reqAllowed(('storm', 'queue', self.name, 'put'))
        return self.runt.snap.core.multiqueue.put(self.name, item)

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
        })

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
            'bunzip': self._methBunzip,
            'gunzip': self._methGunzip,
            'bzip': self._methBzip,
            'gzip': self._methGzip,
            'json': self._methJsonLoad,
        })

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
        self.locls.update({
            'name': self._libUserName,
            'vars': hivedict,
        })

    async def _libUserName(self, path=None):
        return self.runt.user.name

class LibGlobals(Lib):
    '''
    Global persistent Storm variables
    '''
    def __init__(self, runt, name):
        self._stormvars = runt.snap.core.stormvars
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
        ret = self.runt.getVar(name, defv=s_common.novalu)
        if ret is s_common.novalu:
            mesg = f'No var with name: {name}'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name)

        return ret

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
            'ndef': self._methNodeNdef,
            'tags': self._methNodeTags,
            'repr': self._methNodeRepr,
            'iden': self._methNodeIden,
            'value': self._methNodeValue,
            'globtags': self._methNodeGlobTags,

            'isform': self._methNodeIsForm,
        })

        def ctordata(path=None):
            return NodeData(node, path=path)

        self.ctors['data'] = ctordata

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
