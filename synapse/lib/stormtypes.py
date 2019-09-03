import bz2
import gzip
import json
import asyncio
import datetime

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.cache as s_cache
import synapse.lib.scope as s_scope
import synapse.lib.msgpack as s_msgpack

def intify(x):
    if isinstance(x, str):
        return int(x, 0)
    return int(x)

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

    async def deref(self, name):

        locl = self.locls.get(name, s_common.novalu)
        if locl is not s_common.novalu:
            return locl

        ctor = self.ctors.get(name)
        if ctor is not None:
            return ctor(path=self.path)

        raise s_exc.NoSuchName(name=name)

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

#class LibTask(Lib):
    #def addLibFuncs(self):
        #self.locls.update({
            #'addStormDmon': self._libTaskDmon,
        #})

class LibDmon(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'add': self._libDmonAdd,
            #'exit': self._libDmonExit,
        })

    async def _libDmonAdd(self, quer, once=True):

        self.runt.allowed('storm', 'lib', 'dmon', 'add')

        # closure style capture of runtime
        runtvars = {k: v for (k, v) in self.runt.vars.items() if s_msgpack.isok(v)}

        opts = {'vars': runtvars}

        ddef = {
            'once': once,
            'user': self.runt.user.iden,

            'storm': str(quer),
            'stormopts': opts,
        }

        return await self.runt.snap.core.addStormDmon(ddef)

    async def _libDmonExit(self):
        iden = s_scope.get('storm:dmon')
        print('DMON EXIT: %r' % (scope,))

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
            'text': self._text,
            'print': self._print,
            'service': self._methLibService,
        })

    async def _methLibService(self, name):
        '''
        $lib.service(woot).doWootThing(:prop)
        '''
        return self.runt.snap.core.getStormSvc(name)

    async def _set(self, *vals):
        return Set(set(vals))

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

class LibTime(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'fromunix': self.fromunix,
            'parse': self.parse,
            'sleep': self.sleep,
            'ticker': self.ticker,
        })

    # TODO from other iso formats!

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
        await asyncio.sleep(float(valu))

    async def ticker(self, tick, count=None):

        if count is not None:
            count = intify(count)

        tick = float(tick)

        offs = 0
        while True:
            await asyncio.sleep(tick)
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

class LibTelepath(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'open': self._methTeleOpen,
        })

    async def _methTeleOpen(self, url, **opts):
        '''
        Open and return a telepath RPC proxy.
        '''
        scheme = url.split('://')[0]
        self.runt.allowed(('storm', 'lib', 'telepath', 'open', scheme))
        return Proxy(await self.runt.getTeleProxy(url))

class Proxy(StormType):

    def __init__(self, proxy, path=None):
        StormType.__init__(self, path=path)
        self.proxy = proxy

    async def deref(self, name):

        if name[0] == '_':
            mesg = f'No proxy method named {name}'
            raise s_exc.NoSuchName(mesg=mesg)

        return getattr(self.proxy, name, None)

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
        })

    async def _methStrSplit(self, text):
        '''
        Split the string into multiple parts based on a separator.

        Example:

            ($foo, $bar) = $baz.split(":")

        '''
        return self.valu.split(text)

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

    async def deref(self, name):
        return self.valu.get(name)

class Set(Prim):

    def __init__(self, valu, path=None):
        Prim.__init__(self, set(valu), path=path)
        self.locls.update({
            'add': self._methSetAdd,
            'adds': self._methSetAdds,
            'rem': self._methSetRem,
            'rems': self._methSetRems,
            'list': self._methSetList,
        })

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
            'index': self._methListIndex,
            'length': self._methListLength,
            'append': self._methListAppend,
        })

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
        return len(self.valu)

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

    def _reqAllowed(self, perm, name):
        self.runt.allowed(perm, name)

    def _reqStr(self, name):
        if not isinstance(name, str):
            mesg = 'The name of a persistent variable must be a string.'
            raise s_exc.StormRuntimeError(mesg=mesg, name=name)

    async def _methGet(self, name, default=None):
        self._reqStr(name)
        self._reqAllowed('storm:globals:get', name)
        return self._stormvars.get(name, default=default)

    async def _methPop(self, name, default=None):
        self._reqStr(name)
        self._reqAllowed('storm:globals:pop', name)
        return await self._stormvars.pop(name, default=default)

    async def _methSet(self, name, valu):
        self._reqStr(name)
        self._reqAllowed('storm:globals:set', name)
        await self._stormvars.set(name, valu)

    async def _methList(self):
        ret = []
        for key, valu in list(self._stormvars.items()):
            try:
                self._reqAllowed('storm:globals:get', key)
            except s_exc.AuthDeny as e:
                continue
            else:
                ret.append((key, valu))
        return ret

class Query(StormType):
    '''
    A storm primitive representing an embedded query.
    '''
    def __init__(self, text, opts, path=None):

        StormType.__init__(self, path=path)

        self.text = text
        self.opts = opts

        self.locls.update({
        })

    def __str__(self):
        return self.text

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

    async def _methNodeIsForm(self, name):
        return node.form.name == name

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

    async def _methNodeRepr(self, name=None):
        return self.valu.repr(name=name)

    async def _methNodeIden(self):
        return self.valu.iden()

class Path(Prim):

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update({
            'idens': self._methPathIdens,
            'trace': self._methPathTrace,
        })

    async def _methPathIdens(self):
        return [n.iden() for n in self.valu.nodes]

    async def _methPathTrace(self):
        trace = self.valu.trace()
        return Trace(trace)

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

# These will go away once we have value objects in storm runtime
def toprim(valu, path=None):

    if isinstance(valu, (str, tuple, list, dict, int)):
        return valu

    if isinstance(valu, Prim):
        return valu.value()

    if isinstance(valu, s_node.Node):
        return valu.ndef[1]

    raise s_exc.NoSuchType(name=valu.__class__.__name__)

def fromprim(valu, path=None):

    if isinstance(valu, str):
        return Str(valu, path=path)

    # TODO: make s_node.Node a storm type itself?
    if isinstance(valu, s_node.Node):
        return Node(valu, path=path)

    if isinstance(valu, s_node.Path):
        return Path(valu, path=path)

    if isinstance(valu, StormType):
        return valu

    if isinstance(valu, (tuple, list)):
        return List(valu, path=path)

    if isinstance(valu, dict):
        return Dict(valu, path=path)

    if isinstance(valu, bytes):
        return Bytes(valu, path=path)

    raise s_exc.NoSuchType(name=valu.__class__.__name__)
