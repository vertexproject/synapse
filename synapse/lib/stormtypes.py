import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.node as s_node
import synapse.lib.cache as s_cache

def intify(x):
    if isinstance(x, str):
        return int(x, 0)
    return int(x)

class StormType:
    '''
    The base type for storm runtime value objects.
    '''
    def __init__(self, path=None):
        self.path = path
        self.ctors = {}
        self.locls = {}

    def deref(self, name):

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

    def deref(self, name):
        try:
            return StormType.deref(self, name)
        except s_exc.NoSuchName as e:
            pass

        path = self.name + (name,)

        slib = self.runt.snap.core.getStormLib(path)
        if slib is None:
            raise s_exc.NoSuchName(name=name)

        ctor = slib[2].get('ctor', Lib)
        return ctor(self.runt, name=path)

class LibBase(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'len': self._len,
            'min': self._min,
            'max': self._max,
            'dict': self._dict,
            'print': self._print,
        })

    async def _len(self, item):
        return len(item)

    async def _min(self, *vals):
        ints = [intify(x) for x in vals]
        return min(*ints)

    async def _max(self, *vals):
        ints = [intify(x) for x in vals]
        return max(*ints)

    async def _print(self, mesg):
        if not isinstance(mesg, str):
            mesg = repr(mesg)
        await self.runt.printf(mesg)

    async def _dict(self, **kwargs):
        return kwargs

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

        for name, valu in kwargs.items():
            temp = '{%s}' % (name,)
            text = text.replace(temp, str(valu))

        return text

class LibTime(Lib):

    def addLibFuncs(self):
        self.locls.update({
            'fromunix': self.fromunix,
        })

    #TODO from other iso formats!

    async def fromunix(self, secs):
        '''
        Normalize a timestamp from a unix epoch time.

        Example:

            <query> [ :time = $lib.time.fromunix($epoch) ]

        '''
        secs = float(secs)
        return int(secs * 1000)

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

class Dict(Prim):

    def deref(self, name):
        return self.valu.get(name)

class Node(Prim):
    '''
    Implements the STORM api for a node instance.
    '''

    def __init__(self, node, path=None):
        Prim.__init__(self, node, path=path)
        self.locls.update({
            'value': self._methNodeValue,
            'form': self._methNodeForm,
            'tags': self._methNodeTags,
        })

    async def _methNodeTags(self, glob=None):
        tags = list(self.valu.tags.keys())
        if glob is not None:
            regx = s_cache.getTagGlobRegx(glob)
            tags = [t for t in tags if regx.fullmatch(t)]
        return tags

    async def _methNodeValue(self):
        return self.valu.ndef[1]

    async def _methNodeForm(self):
        return self.valu.ndef[0]

def fromprim(valu, path=None):

    if isinstance(valu, str):
        return Str(valu, path=path)

    # TODO: make s_node.Node a storm type itself?
    if isinstance(valu, s_node.Node):
        return Node(valu, path=path)

    if isinstance(valu, StormType):
        return valu

    #if isinstance(valu, (tuple, list)):
        #return List(valu, path=path)

    if isinstance(valu, dict):
        return Dict(valu, path=path)

    raise s_exc.NoSuchType(name=valu.__class__.__name__)
