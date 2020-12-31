'''
The Layer 2.0 archtecture introduces several optimized node/message serialization formats
used by the layers to optimize returning primitives and facilitate efficient node construction:

.. note::

    This interface is subject to change between minor revisions.

Storage Types (<stortype>)

    In Layers 2.0, each node property from the model has an associated "storage type".  Each
    storage type determines how the data is indexed and represented within the Layer.  This
    formalizes the separation of "data model" from "storage model".  Each data model type has
    a "stortype" property which coresponds to one of the STOR_TYPE_XXX values.  The knowledge
    of the mapping of data model types to storage types is the responsibility of the data model,
    making the Layer implementation fully decoupled from the data model.

Node Edits / Edits

    A node edit consists of a (<buid>, <form>, [edits]) tuple.  An edit is Tuple of (<type>, <info>, List[NodeEdits])
    where the first element is an int that matches to an EDIT_* constant below, the info is a tuple that varies
    depending on the first element, and the third element is a list of dependent NodeEdits that will only be applied
    if the edit actually makes a change.

Storage Node (<sode>)

    A storage node is a layer/storage optimized node representation which is similar to a "packed node".
    A storage node *may* be partial ( as it is produced by a given layer ) and are joined by the view/snap
    into "full" storage nodes which are used to construct Node() instances.

    Sode format::

        (<buid>, {

            'ndef': (<formname>, <formvalu>),

            'props': {
                <propname>: <propvalu>,
            }

            'tags': {
                <tagname>: <tagvalu>,
            }

            'tagprops: {
                <tagname>: {
                    <propname>: <propvalu>,
                },
            }

            # changes that were *just* made.
            'edits': [
                <edit>
            ]

        }),

'''
import os
import math
import shutil
import struct
import asyncio
import logging
import ipaddress
import contextlib
import collections

import regex
import xxhash

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.gis as s_gis
import synapse.lib.cell as s_cell
import synapse.lib.cache as s_cache
import synapse.lib.nexus as s_nexus
import synapse.lib.queue as s_queue
import synapse.lib.urlhelp as s_urlhelp

import synapse.lib.config as s_config
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn

from synapse.lib.msgpack import deepcopy

logger = logging.getLogger(__name__)

import synapse.lib.msgpack as s_msgpack

reqValidLdef = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'lockmemory': {'type': 'boolean'},
        'logedits': {'type': 'boolean', 'default': True},
        'name': {'type': 'string'},
    },
    'additionalProperties': True,
    'required': ['iden', 'creator', 'lockmemory'],
})

class LayerApi(s_cell.CellApi):

    async def __anit__(self, core, link, user, layr):

        await s_cell.CellApi.__anit__(self, core, link, user)

        self.layr = layr
        self.liftperm = ('layer', 'lift', self.layr.iden)
        self.writeperm = ('layer', 'write', self.layr.iden)

    async def iterLayerNodeEdits(self):
        '''
        Scan the full layer and yield artificial nodeedit sets.
        '''

        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.iterLayerNodeEdits():
            yield item

    async def storNodeEdits(self, nodeedits, meta=None):

        await self._reqUserAllowed(self.writeperm)

        if meta is None:
            meta = {'time': s_common.now(),
                    'user': self.user.iden
                    }

        return await self.layr.storNodeEdits(nodeedits, meta)

    async def storNodeEditsNoLift(self, nodeedits, meta=None):

        await self._reqUserAllowed(self.writeperm)

        if meta is None:
            meta = {'time': s_common.now(),
                    'user': self.user.iden
                    }

        await self.layr.storNodeEditsNoLift(nodeedits, meta)

    async def syncNodeEdits(self, offs, wait=True):
        '''
        Yield (offs, nodeedits) tuples from the nodeedit log starting from the given offset.

        Once caught up with storage, yield them in realtime.
        '''
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.syncNodeEdits(offs, wait=wait):
            yield item

    async def splices(self, offs=None, size=None):
        '''
        Yield (offs, splice) tuples from the nodeedit log starting from the given offset.

        Nodeedits will be flattened into splices before being yielded.
        '''
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.splices(offs=offs, size=size):
            yield item

    async def getEditIndx(self):
        '''
        Returns what will be the *next* nodeedit log index.
        '''
        await self._reqUserAllowed(self.liftperm)
        return await self.layr.getEditIndx()

    async def getIden(self):
        await self._reqUserAllowed(self.liftperm)
        return self.layr.iden

BUID_CACHE_SIZE = 10000

STOR_TYPE_UTF8 = 1

STOR_TYPE_U8 = 2
STOR_TYPE_U16 = 3
STOR_TYPE_U32 = 4
STOR_TYPE_U64 = 5

STOR_TYPE_I8 = 6
STOR_TYPE_I16 = 7
STOR_TYPE_I32 = 8
STOR_TYPE_I64 = 9

STOR_TYPE_GUID = 10
STOR_TYPE_TIME = 11
STOR_TYPE_IVAL = 12
STOR_TYPE_MSGP = 13
STOR_TYPE_LATLONG = 14

STOR_TYPE_LOC = 15
STOR_TYPE_TAG = 16
STOR_TYPE_FQDN = 17
STOR_TYPE_IPV6 = 18

STOR_TYPE_U128 = 19
STOR_TYPE_I128 = 20

STOR_TYPE_MINTIME = 21

STOR_TYPE_FLOAT64 = 22
STOR_TYPE_HUGENUM = 23

# STOR_TYPE_TOMB      = ??
# STOR_TYPE_FIXED     = ??

STOR_FLAG_ARRAY = 0x8000

# Edit types (etyp)

EDIT_NODE_ADD = 0     # (<etyp>, (<valu>, <type>), ())
EDIT_NODE_DEL = 1     # (<etyp>, (<oldv>, <type>), ())
EDIT_PROP_SET = 2     # (<etyp>, (<prop>, <valu>, <oldv>, <type>), ())
EDIT_PROP_DEL = 3     # (<etyp>, (<prop>, <oldv>, <type>), ())
EDIT_TAG_SET = 4      # (<etyp>, (<tag>, <valu>, <oldv>), ())
EDIT_TAG_DEL = 5      # (<etyp>, (<tag>, <oldv>), ())
EDIT_TAGPROP_SET = 6  # (<etyp>, (<tag>, <prop>, <valu>, <oldv>, <type>), ())
EDIT_TAGPROP_DEL = 7  # (<etyp>, (<tag>, <prop>, <oldv>, <type>), ())
EDIT_NODEDATA_SET = 8 # (<etyp>, (<name>, <valu>, <oldv>), ())
EDIT_NODEDATA_DEL = 9 # (<etyp>, (<name>, <oldv>), ())
EDIT_EDGE_ADD = 10    # (<etyp>, (<verb>, <destnodeiden>), ())
EDIT_EDGE_DEL = 11    # (<etyp>, (<verb>, <destnodeiden>), ())

EDIT_PROGRESS = 100   # (used by syncIndexEvents) (<etyp>, (), ())

class IndxBy:
    '''
    IndxBy sub-classes encapsulate access methods and encoding details for
    various types of properties within the layer to be lifted/compared by
    storage types.
    '''
    def __init__(self, layr, abrv, db):
        self.db = db
        self.abrv = abrv
        self.layr = layr
        self.abrvlen = len(abrv)  # Dividing line between the abbreviations and the data-specific index

    def getNodeValu(self, buid):
        raise s_exc.NoSuchImpl(name='getNodeValu')

    def buidsByDups(self, indx):
        for _, buid in self.layr.layrslab.scanByDups(self.abrv + indx, db=self.db):
            yield buid

    def buidsByPref(self, indx=b''):
        for _, buid in self.layr.layrslab.scanByPref(self.abrv + indx, db=self.db):
            yield buid

    def keyBuidsByRange(self, minindx, maxindx):
        yield from self.layr.layrslab.scanByRange(self.abrv + minindx, self.abrv + maxindx, db=self.db)

    def buidsByRange(self, minindx, maxindx):
        yield from (x[1] for x in self.keyBuidsByRange(minindx, maxindx))

    def keyBuidsByRangeBack(self, minindx, maxindx):
        '''
        Yields backwards from maxindx to minindx
        '''
        yield from self.layr.layrslab.scanByRangeBack(self.abrv + maxindx, lmin=self.abrv + minindx, db=self.db)

    def buidsByRangeBack(self, minindx, maxindx):
        yield from (x[1] for x in self.keyBuidsByRangeBack(minindx, maxindx))

    def scanByDups(self, indx):
        for item in self.layr.layrslab.scanByDups(self.abrv + indx, db=self.db):
            yield item

    def scanByPref(self, indx=b''):
        for item in self.layr.layrslab.scanByPref(self.abrv + indx, db=self.db):
            yield item

    def scanByRange(self, minindx, maxindx):
        for item in self.layr.layrslab.scanByRange(self.abrv + minindx, self.abrv + maxindx, db=self.db):
            yield item

class IndxByForm(IndxBy):

    def __init__(self, layr, form):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.getPropAbrv(form, None)
        IndxBy.__init__(self, layr, abrv, layr.byprop)

        self.form = form

    def getNodeValu(self, buid):
        sode = self.layr._getStorNode(buid)
        valt = sode.get('valu')
        if valt is not None:
            return valt[0]

class IndxByProp(IndxBy):

    def __init__(self, layr, form, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.getPropAbrv(form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.byprop)

        self.form = form
        self.prop = prop

    def getNodeValu(self, buid):
        sode = self.layr._getStorNode(buid)
        valt = sode['props'].get(self.prop)
        if valt is not None:
            return valt[0]

class IndxByPropArray(IndxBy):

    def __init__(self, layr, form, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.getPropAbrv(form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.byarray)

        self.form = form
        self.prop = prop

    def getNodeValu(self, buid):
        sode = self.layr._getStorNode(buid)
        valt = sode['props'].get(self.prop)
        if valt is not None:
            return valt[0]

class IndxByTag(IndxBy):

    def __init__(self, layr, form, tag):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.tagabrv.bytsToAbrv(tag.encode())
        if form is not None:
            abrv += layr.getPropAbrv(form, None)

        IndxBy.__init__(self, layr, abrv, layr.bytag)

        self.abrvlen = 16

        self.form = form
        self.tag = tag

    def getNodeValuForm(self, buid):
        sode = self.layr._getStorNode(buid)
        valt = sode['tags'].get(self.tag)
        if valt is not None:
            return valt, sode['form']

class IndxByTagProp(IndxBy):

    def __init__(self, layr, form, tag, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.getTagPropAbrv(form, tag, prop)
        IndxBy.__init__(self, layr, abrv, layr.bytagprop)

        self.form = form
        self.prop = prop
        self.tag = tag
        self.skey = (tag, prop)

    def getNodeValu(self, buid):
        sode = self.layr._getStorNode(buid)
        valt = sode['tagprops'].get(self.skey)
        if valt is not None:
            return valt[0]

class StorType:

    def __init__(self, layr, stortype):
        self.layr = layr
        self.stortype = stortype

        self.lifters = {}

    async def indxBy(self, liftby, cmpr, valu):
        func = self.lifters.get(cmpr)
        if func is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr)

        async for item in func(liftby, valu):
            yield item

    async def indxByForm(self, form, cmpr, valu):
        try:
            indxby = IndxByForm(self.layr, form)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu):
            yield item

    async def indxByProp(self, form, prop, cmpr, valu):
        try:
            indxby = IndxByProp(self.layr, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu):
            yield item

    async def indxByPropArray(self, form, prop, cmpr, valu):
        try:
            indxby = IndxByPropArray(self.layr, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu):
            yield item

    async def indxByTagProp(self, form, tag, prop, cmpr, valu):
        try:
            indxby = IndxByTagProp(self.layr, form, tag, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu):
            yield item

    def indx(self, valu):  # pragma: no cover
        raise NotImplementedError

    def decodeIndx(self, valu):  # pragma: no cover
        return s_common.novalu

    async def _liftRegx(self, liftby, valu):

        regx = regex.compile(valu)
        lastbuid = None

        for buid in liftby.buidsByPref():
            if buid == lastbuid:
                continue

            await asyncio.sleep(0)

            lastbuid = buid
            storvalu = liftby.getNodeValu(buid)

            def regexin(regx, storvalu):
                if isinstance(storvalu, str):
                    if regx.search(storvalu) is not None:
                        return True

                elif isinstance(storvalu, (tuple, list)):
                    return any(regexin(regx, sv) for sv in storvalu)

                return False

            if regexin(regx, storvalu):
                yield buid

class StorTypeUtf8(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_UTF8)

        self.lifters.update({
            '=': self._liftUtf8Eq,
            '~=': self._liftRegx,
            '^=': self._liftUtf8Prefix,
            'range=': self._liftUtf8Range,
        })

    async def _liftUtf8Eq(self, liftby, valu):
        indx = self._getIndxByts(valu)
        for item in liftby.buidsByDups(indx):
            yield item

    async def _liftUtf8Range(self, liftby, valu):
        minindx = self._getIndxByts(valu[0])
        maxindx = self._getIndxByts(valu[1])
        for item in liftby.buidsByRange(minindx, maxindx):
            yield item

    async def _liftUtf8Prefix(self, liftby, valu):
        indx = self._getIndxByts(valu)
        for item in liftby.buidsByPref(indx):
            yield item

    def _getIndxByts(self, valu):

        indx = valu.encode('utf8', 'surrogatepass')
        # cut down an index value to 256 bytes...
        if len(indx) <= 256:
            return indx

        base = indx[:248]
        sufx = xxhash.xxh64(indx).digest()
        return base + sufx

    def indx(self, valu):
        return (self._getIndxByts(valu), )

    def decodeIndx(self, bytz):
        if len(bytz) >= 256:
            return s_common.novalu
        return bytz.decode('utf8', 'surrogatepass')

class StorTypeHier(StorType):

    def __init__(self, layr, stortype, sepr='.'):
        StorType.__init__(self, layr, stortype)
        self.sepr = sepr

        self.lifters.update({
            '=': self._liftHierEq,
            '^=': self._liftHierPref,
        })

    def indx(self, valu):
        return (
            self.getHierIndx(valu),
        )

    def getHierIndx(self, valu):
        # encode the index values with a trailing sepr to allow ^=foo.bar to be boundary aware
        return (valu + self.sepr).encode()

    def decodeIndx(self, bytz):
        return bytz.decode()[:-len(self.sepr)]

    async def _liftHierEq(self, liftby, valu):
        indx = self.getHierIndx(valu)
        for item in liftby.buidsByDups(indx):
            yield item

    async def _liftHierPref(self, liftby, valu):
        indx = self.getHierIndx(valu)
        for item in liftby.buidsByPref(indx):
            yield item

class StorTypeLoc(StorTypeHier):
    def __init__(self, layr):
        StorTypeHier.__init__(self, layr, STOR_TYPE_LOC)

class StorTypeTag(StorTypeHier):

    def __init__(self, layr):
        StorTypeHier.__init__(self, layr, STOR_TYPE_TAG)

    @staticmethod
    def getTagFilt(cmpr, valu):

        if cmpr == '=':
            def filt1(x):
                return x == valu
            return filt1

        if cmpr == '@=':

            def filt2(item):

                if item is None:
                    return False

                if item == (None, None):
                    return False

                if item[0] >= valu[1]:
                    return False

                if item[1] <= valu[0]:
                    return False

                return True

            return filt2

class StorTypeFqdn(StorTypeUtf8):

    def indx(self, norm):
        return (
            self._getIndxByts(norm[::-1]),
        )

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_UTF8)
        self.lifters.update({
            '=': self._liftFqdnEq,
            '~=': self._liftRegx,
        })

    async def _liftFqdnEq(self, liftby, valu):

        if valu[0] == '*':
            indx = self._getIndxByts(valu[1:][::-1])
            for item in liftby.buidsByPref(indx):
                yield item
            return

        async for item in StorTypeUtf8._liftUtf8Eq(self, liftby, valu[::-1]):
            yield item

class StorTypeIpv6(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IPV6)

        self.lifters.update({
            '=': self._liftIPv6Eq,
            'range=': self._liftIPv6Range,
        })

    def getIPv6Indx(self, valu):
        return ipaddress.IPv6Address(valu).packed

    def indx(self, valu):
        return (
            self.getIPv6Indx(valu),
        )

    def decodeIndx(self, bytz):
        return str(ipaddress.IPv6Address(bytz))

    async def _liftIPv6Eq(self, liftby, valu):
        indx = self.getIPv6Indx(valu)
        for item in liftby.buidsByDups(indx):
            yield item

    async def _liftIPv6Range(self, liftby, valu):
        minindx = self.getIPv6Indx(valu[0])
        maxindx = self.getIPv6Indx(valu[1])
        for item in liftby.buidsByRange(minindx, maxindx):
            yield item

class StorTypeInt(StorType):

    def __init__(self, layr, stortype, size, signed):

        StorType.__init__(self, layr, stortype)

        self.size = size
        self.signed = signed

        self.offset = 0
        if signed:
            self.offset = 2 ** ((self.size * 8) - 1) - 1

        self.maxval = 2 ** (self.size * 8) - 1

        self.lifters.update({
            '=': self._liftIntEq,
            '<': self._liftIntLt,
            '>': self._liftIntGt,
            '<=': self._liftIntLe,
            '>=': self._liftIntGe,
            'range=': self._liftIntRange,
        })

        self.zerobyts = b'\x00' * self.size
        self.fullbyts = b'\xff' * self.size

    def getIntIndx(self, valu):
        return (valu + self.offset).to_bytes(self.size, 'big')

    def indx(self, valu):
        return (self.getIntIndx(valu),)

    def decodeIndx(self, bytz):
        return int.from_bytes(bytz, 'big') - self.offset

    async def _liftIntEq(self, liftby, valu):
        indx = valu + self.offset
        if indx < 0 or indx > self.maxval:
            return

        pkey = indx.to_bytes(self.size, 'big')
        for item in liftby.buidsByDups(pkey):
            yield item

    async def _liftIntGt(self, liftby, valu):
        async for item in self._liftIntGe(liftby, valu + 1):
            yield item

    async def _liftIntGe(self, liftby, valu):
        minv = valu + self.offset
        if minv > self.maxval:
            return

        minv = max(minv, 0)

        pkeymin = minv.to_bytes(self.size, 'big')
        pkeymax = self.fullbyts
        for item in liftby.buidsByRange(pkeymin, pkeymax):
            yield item

    async def _liftIntLt(self, liftby, valu):
        async for item in self._liftIntLe(liftby, valu - 1):
            yield item

    async def _liftIntLe(self, liftby, valu):
        maxv = valu + self.offset
        if maxv < 0:
            return

        maxv = min(maxv, self.maxval)

        pkeymin = self.zerobyts
        pkeymax = maxv.to_bytes(self.size, 'big')
        for item in liftby.buidsByRange(pkeymin, pkeymax):
            yield item

    async def _liftIntRange(self, liftby, valu):
        minv = valu[0] + self.offset
        maxv = valu[1] + self.offset
        if minv > self.maxval or maxv < 0:
            return

        minv = max(minv, 0)
        maxv = min(maxv, self.maxval)

        pkeymin = minv.to_bytes(self.size, 'big')
        pkeymax = maxv.to_bytes(self.size, 'big')
        for item in liftby.buidsByRange(pkeymin, pkeymax):
            yield item

class StorTypeHugeNum(StorType):

    def __init__(self, layr, stortype):
        StorType.__init__(self, layr, STOR_TYPE_HUGENUM)
        self.lifters.update({
            '=': self._liftHugeEq,
            '<': self._liftHugeLt,
            '>': self._liftHugeGt,
            '<=': self._liftHugeLe,
            '>=': self._liftHugeGe,
            'range=': self._liftHugeRange,
        })

        self.one = s_common.hugenum(1)
        self.offset = s_common.hugenum(0x7fffffffffffffffffffffffffffffff)

        self.zerobyts = b'\x00' * 16
        self.fullbyts = b'\xff' * 16

    def getHugeIndx(self, norm):
        scaled = s_common.hugenum(norm).scaleb(15)
        byts = int(scaled + self.offset).to_bytes(16, byteorder='big')
        return byts

    def indx(self, norm):
        return (self.getHugeIndx(norm),)

    def decodeIndx(self, bytz):
        return float(((int.from_bytes(bytz, 'big')) - self.offset) / 10 ** 15)

    async def _liftHugeEq(self, liftby, valu):
        byts = self.getHugeIndx(valu)
        for item in liftby.buidsByDups(byts):
            yield item

    async def _liftHugeGt(self, liftby, valu):
        valu = s_common.hugenum(valu)
        async for item in self._liftHugeGe(liftby, valu + self.one):
            yield item

    async def _liftHugeLt(self, liftby, valu):
        valu = s_common.hugenum(valu)
        async for item in self._liftHugeLe(liftby, valu - self.one):
            yield item

    async def _liftHugeGe(self, liftby, valu):
        pkeymin = self.getHugeIndx(valu)
        pkeymax = self.fullbyts
        for item in liftby.buidsByRange(pkeymin, pkeymax):
            yield item

    async def _liftHugeLe(self, liftby, valu):
        pkeymin = self.zerobyts
        pkeymax = self.getHugeIndx(valu)
        for item in liftby.buidsByRange(pkeymin, pkeymax):
            yield item

    async def _liftHugeRange(self, liftby, valu):
        pkeymin = self.getHugeIndx(valu[0])
        pkeymax = self.getHugeIndx(valu[1])
        for item in liftby.buidsByRange(pkeymin, pkeymax):
            yield item

class StorTypeFloat(StorType):
    FloatPacker = struct.Struct('>d')
    fpack = FloatPacker.pack
    FloatPackPosMax = FloatPacker.pack(math.inf)
    FloatPackPosMin = FloatPacker.pack(0.0)
    FloatPackNegMin = FloatPacker.pack(-math.inf)
    FloatPackNegMax = FloatPacker.pack(-0.0)

    def __init__(self, layr, stortype, size=8):
        '''
        Size reserved for later use
        '''
        assert size == 8

        StorType.__init__(self, layr, stortype)

        self.lifters.update({
            '=': self._liftFloatEq,
            '<': self._liftFloatLt,
            '>': self._liftFloatGt,
            '<=': self._liftFloatLe,
            '>=': self._liftFloatGe,
            'range=': self._liftFloatRange,
        })

    def indx(self, valu):
        return (self.fpack(valu),)

    def decodeIndx(self, bytz):
        return self.FloatPacker.unpack(bytz)[0]

    async def _liftFloatEq(self, liftby, valu):
        for item in liftby.buidsByDups(self.fpack(valu)):
            yield item

    async def _liftFloatGeCommon(self, liftby, valu):
        if math.isnan(valu):
            raise s_exc.NotANumberCompared()

        valupack = self.fpack(valu)

        if math.copysign(1.0, valu) < 0.0:  # negative values and -0.0
            for item in liftby.keyBuidsByRangeBack(self.FloatPackNegMax, valupack):
                yield item
            valupack = self.FloatPackPosMin

        for item in liftby.keyBuidsByRange(valupack, self.FloatPackPosMax):
            yield item

    async def _liftFloatGe(self, liftby, valu):
        async for item in self._liftFloatGeCommon(liftby, valu):
            yield item[1]

    async def _liftFloatGt(self, liftby, valu):
        valupack = self.fpack(valu)
        async for item in self._liftFloatGeCommon(liftby, valu):
            if item[0] == valupack:
                continue
            yield item[1]

    async def _liftFloatLeCommon(self, liftby, valu):
        if math.isnan(valu):
            raise s_exc.NotANumberCompared()

        valupack = self.fpack(valu)

        if math.copysign(1.0, valu) > 0.0:
            for item in liftby.keyBuidsByRangeBack(self.FloatPackNegMax, self.FloatPackNegMin):
                yield item
            for item in liftby.keyBuidsByRange(self.FloatPackPosMin, valupack):
                yield item
        else:
            for item in liftby.keyBuidsByRangeBack(valupack, self.FloatPackNegMin):
                yield item

    async def _liftFloatLe(self, liftby, valu):
        async for item in self._liftFloatLeCommon(liftby, valu):
            yield item[1]

    async def _liftFloatLt(self, liftby, valu):
        valupack = self.fpack(valu)
        async for item in self._liftFloatLeCommon(liftby, valu):
            if item[0] == valupack:
                continue
            yield item[1]

    async def _liftFloatRange(self, liftby, valu):
        valumin, valumax = valu

        if math.isnan(valumin) or math.isnan(valumax):
            raise s_exc.NotANumberCompared()

        assert valumin <= valumax

        pkeymin, pkeymax = (self.fpack(v) for v in valu)

        if math.copysign(1.0, valumin) > 0.0:
            # Entire range is nonnegative
            for item in liftby.buidsByRange(pkeymin, pkeymax):
                yield item
            return

        if math.copysign(1.0, valumax) < 0.0:  # negative values and -0.0
            # Entire range is negative
            for item in liftby.buidsByRangeBack(pkeymax, pkeymin):
                yield item
            return

        # Yield all values between min and -0
        for item in liftby.buidsByRangeBack(self.FloatPackNegMax, pkeymin):
            yield item

        # Yield all values between 0 and max
        for item in liftby.buidsByRange(self.FloatPackPosMin, pkeymax):
            yield item

class StorTypeGuid(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_GUID)
        self.lifters.update({
            '=': self._liftGuidEq,
        })

    async def _liftGuidEq(self, liftby, valu):
        indx = s_common.uhex(valu)
        for item in liftby.buidsByDups(indx):
            yield item

    def indx(self, valu):
        return (s_common.uhex(valu),)

    def decodeIndx(self, bytz):
        return s_common.ehex(bytz)

class StorTypeTime(StorTypeInt):

    def __init__(self, layr):
        StorTypeInt.__init__(self, layr, STOR_TYPE_TIME, 8, True)
        self.lifters.update({
            '@=': self._liftAtIval,
        })

    async def _liftAtIval(self, liftby, valu):
        minindx = self.getIntIndx(valu[0])
        maxindx = self.getIntIndx(valu[1] - 1)
        for _, buid in liftby.scanByRange(minindx, maxindx):
            yield buid

class StorTypeIval(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IVAL)
        self.timetype = StorTypeTime(layr)
        self.lifters.update({
            '=': self._liftIvalEq,
            '@=': self._liftIvalAt,
        })

    async def _liftIvalEq(self, liftby, valu):
        indx = self.timetype.getIntIndx(valu[0]) + self.timetype.getIntIndx(valu[1])
        for item in liftby.buidsByDups(indx):
            yield item

    async def _liftIvalAt(self, liftby, valu):

        minindx = self.timetype.getIntIndx(valu[0])
        maxindx = self.timetype.getIntIndx(valu[1])

        for lkey, buid in liftby.scanByPref():

            tick = lkey[-16:-8]
            tock = lkey[-8:]

            # check for non-ovelap left and right
            if tick >= maxindx:
                continue

            if tock <= minindx:
                continue

            yield buid

    def indx(self, valu):
        return (self.timetype.getIntIndx(valu[0]) + self.timetype.getIntIndx(valu[1]),)

    def decodeIndx(self, bytz):
        return (self.timetype.decodeIndx(bytz[:8]), self.timetype.decodeIndx(bytz[8:]))

class StorTypeMsgp(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_MSGP)
        self.lifters.update({
            '=': self._liftMsgpEq,
            '~=': self._liftRegx,
        })

    async def _liftMsgpEq(self, liftby, valu):
        indx = s_common.buid(valu)
        for item in liftby.buidsByDups(indx):
            yield item

    def indx(self, valu):
        return (s_common.buid(valu),)

class StorTypeLatLon(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_LATLONG)

        self.scale = 10 ** 8
        self.latspace = 90 * 10 ** 8
        self.lonspace = 180 * 10 ** 8

        self.lifters.update({
            '=': self._liftLatLonEq,
            'near=': self._liftLatLonNear,
        })

    async def _liftLatLonEq(self, liftby, valu):
        indx = self._getLatLonIndx(valu)
        for item in liftby.buidsByDups(indx):
            yield item

    async def _liftLatLonNear(self, liftby, valu):

        (lat, lon), dist = valu

        # latscale = (lat * self.scale) + self.latspace
        # lonscale = (lon * self.scale) + self.lonspace

        latmin, latmax, lonmin, lonmax = s_gis.bbox(lat, lon, dist)

        lonminindx = (round(lonmin * self.scale) + self.lonspace).to_bytes(5, 'big')
        lonmaxindx = (round(lonmax * self.scale) + self.lonspace).to_bytes(5, 'big')

        latminindx = (round(latmin * self.scale) + self.latspace).to_bytes(5, 'big')
        latmaxindx = (round(latmax * self.scale) + self.latspace).to_bytes(5, 'big')

        # scan by lon range and down-select the results to matches.
        for lkey, buid in liftby.scanByRange(lonminindx, lonmaxindx):

            # lkey = <abrv> <lonindx> <latindx>

            # limit results to the bounding box before unpacking...
            latbyts = lkey[13:18]

            if latbyts > latmaxindx:
                continue

            if latbyts < latminindx:
                continue

            lonbyts = lkey[8:13]

            latvalu = (int.from_bytes(latbyts, 'big') - self.latspace) / self.scale
            lonvalu = (int.from_bytes(lonbyts, 'big') - self.lonspace) / self.scale

            if s_gis.haversine((lat, lon), (latvalu, lonvalu)) <= dist:
                yield buid

    def _getLatLonIndx(self, latlong):
        # yield index bytes in lon/lat order to allow cheap optimal indexing
        latindx = (round(latlong[0] * self.scale) + self.latspace).to_bytes(5, 'big')
        lonindx = (round(latlong[1] * self.scale) + self.lonspace).to_bytes(5, 'big')
        return lonindx + latindx

    def indx(self, valu):
        # yield index bytes in lon/lat order to allow cheap optimal indexing
        return (self._getLatLonIndx(valu),)

    def decodeIndx(self, bytz):
        lon = (int.from_bytes(bytz[:5], 'big') - self.lonspace) / self.scale
        lat = (int.from_bytes(bytz[5:], 'big') - self.latspace) / self.scale
        return (lat, lon)

class Layer(s_nexus.Pusher):
    '''
    The base class for a cortex layer.
    '''
    nodeeditctor = s_slabseqn.SlabSeqn

    def __repr__(self):
        return f'Layer ({self.__class__.__name__}): {self.iden}'

    async def __anit__(self, layrinfo, dirn, nexsroot=None, allow_upstream=True):

        self.nexsroot = nexsroot
        self.layrinfo = layrinfo
        self.allow_upstream = allow_upstream

        self.addoffs = None  # The nexus log index where I was created
        self.deloffs = None  # The nexus log index where I was deleted
        self.isdeleted = False

        self.iden = layrinfo.get('iden')
        await s_nexus.Pusher.__anit__(self, self.iden, nexsroot=nexsroot)

        self.dirn = dirn
        self.readonly = layrinfo.get('readonly')

        self.lockmemory = self.layrinfo.get('lockmemory')
        self.growsize = self.layrinfo.get('growsize')
        self.logedits = self.layrinfo.get('logedits')

        # slim hooks to avoid async/fire
        self.nodeAddHook = None
        self.nodeDelHook = None

        path = s_common.genpath(self.dirn, 'layer_v2.lmdb')

        self.fresh = not os.path.exists(path)

        self.dirty = {}

        await self._initLayerStorage()

        self.stortypes = [

            None,

            StorTypeUtf8(self),

            StorTypeInt(self, STOR_TYPE_U8, 1, False),
            StorTypeInt(self, STOR_TYPE_U16, 2, False),
            StorTypeInt(self, STOR_TYPE_U32, 4, False),
            StorTypeInt(self, STOR_TYPE_U64, 8, False),

            StorTypeInt(self, STOR_TYPE_I8, 1, True),
            StorTypeInt(self, STOR_TYPE_I16, 2, True),
            StorTypeInt(self, STOR_TYPE_I32, 4, True),
            StorTypeInt(self, STOR_TYPE_I64, 8, True),

            StorTypeGuid(self),
            StorTypeTime(self),
            StorTypeIval(self),
            StorTypeMsgp(self),
            StorTypeLatLon(self),

            StorTypeLoc(self),
            StorTypeTag(self),
            StorTypeFqdn(self),
            StorTypeIpv6(self),

            StorTypeInt(self, STOR_TYPE_U128, 16, False),
            StorTypeInt(self, STOR_TYPE_I128, 16, True),

            StorTypeTime(self), # STOR_TYPE_MINTIME

            StorTypeFloat(self, STOR_TYPE_FLOAT64, 8),
            StorTypeHugeNum(self, STOR_TYPE_HUGENUM),
        ]

        self.editors = [
            self._editNodeAdd,
            self._editNodeDel,
            self._editPropSet,
            self._editPropDel,
            self._editTagSet,
            self._editTagDel,
            self._editTagPropSet,
            self._editTagPropDel,
            self._editNodeDataSet,
            self._editNodeDataDel,
            self._editNodeEdgeAdd,
            self._editNodeEdgeDel,
        ]

        self.canrev = True
        self.ctorname = f'{self.__class__.__module__}.{self.__class__.__name__}'

        self.windows = []
        self.upstreamwaits = collections.defaultdict(lambda: collections.defaultdict(list))

        self.buidcache = s_cache.LruDict(BUID_CACHE_SIZE)

        uplayr = layrinfo.get('upstream')
        if uplayr is not None and allow_upstream:
            if isinstance(uplayr, (tuple, list)):
                for layr in uplayr:
                    await self.initUpstreamSync(layr)
            else:
                await self.initUpstreamSync(uplayr)

        self.onfini(self._onLayrFini)

    async def pack(self):
        ret = self.layrinfo.pack()
        ret['totalsize'] = await self.getLayerSize()
        return ret

    @s_nexus.Pusher.onPushAuto('layer:truncate')
    async def truncate(self):
        '''
        Nuke all the contents in the layer, leaving an empty layer
        '''
        self.dirty.clear()
        self.buidcache.clear()

        await self.layrslab.trash()
        await self.nodeeditslab.trash()
        await self.dataslab.trash()

        await self._initLayerStorage()

    async def clone(self, newdirn):
        '''
        Copy the contents of this layer to a new layer
        '''
        for root, dnames, fnames in os.walk(self.dirn, topdown=True):

            relpath = os.path.relpath(root, start=self.dirn)

            for name in list(dnames):

                relname = os.path.join(relpath, name)

                srcpath = s_common.genpath(root, name)
                dstpath = s_common.genpath(newdirn, relname)

                if srcpath in s_lmdbslab.Slab.allslabs:
                    slab = s_lmdbslab.Slab.allslabs[srcpath]
                    await slab.copyslab(dstpath)

                    dnames.remove(name)
                    continue

                s_common.gendir(dstpath)

            for name in fnames:

                srcpath = s_common.genpath(root, name)
                # skip unix sockets etc...
                if not os.path.isfile(srcpath):
                    continue

                dstpath = s_common.genpath(newdirn, relpath, name)
                shutil.copy(srcpath, dstpath)

    async def waitForHot(self):
        '''
        Wait for the layer's slab to be prefaulted and locked into memory if lockmemory is true, otherwise return.
        '''
        await self.layrslab.lockdoneevent.wait()

    async def _layrV2toV3(self):

        bybuid = self.layrslab.initdb('bybuid')
        sode = collections.defaultdict(dict)

        tostor = []
        lastbuid = None

        count = 0
        forms = await self.getFormCounts()
        minforms = sum(forms.values())

        logger.warning(f'Converting layer from v2 to v3 storage (>={minforms} nodes): {self.dirn}')

        for lkey, lval in self.layrslab.scanByFull(db=bybuid):

            flag = lkey[32]
            buid = lkey[:32]

            if lastbuid != buid:

                if lastbuid is not None:

                    count += 1
                    tostor.append((lastbuid, s_msgpack.en(sode)))

                    sode.clear()

                    if len(tostor) >= 10000:
                        logger.warning(f'...syncing 10k nodes @{count}')
                        self.layrslab.putmulti(tostor, db=self.bybuidv3)
                        tostor.clear()

                lastbuid = buid

            if flag == 0:
                form, valu, stortype = s_msgpack.un(lval)
                sode['form'] = form
                sode['valu'] = (valu, stortype)
                continue

            if flag == 1:
                name = lkey[33:].decode()
                sode['props'][name] = s_msgpack.un(lval)
                continue

            if flag == 2:
                name = lkey[33:].decode()
                sode['tags'][name] = s_msgpack.un(lval)
                continue

            if flag == 3:
                tag, prop = lkey[33:].decode().split(':')
                sode['tagprops'][(tag, prop)] = s_msgpack.un(lval)
                continue

            if flag == 9:
                sode['form'] = lval.decode()
                continue

            logger.warning('Invalid flag %d found for buid %s during migration', flag, buid) # pragma: no cover

        count += 1

        # Mop up the leftovers
        if lastbuid is not None:
            count += 1
            tostor.append((lastbuid, s_msgpack.en(sode)))
        if tostor:
            self.layrslab.putmulti(tostor, db=self.bybuidv3)

        logger.warning('...removing old bybuid index')
        self.layrslab.dropdb('bybuid')

        self.meta.set('version', 3)
        self.layrvers = 3

        logger.warning(f'...complete! ({count} nodes)')

    async def _initLayerStorage(self):

        slabopts = {
            'readonly': self.readonly,
            'max_dbs': 128,
            'map_async': True,
            'readahead': True,
            'lockmemory': self.lockmemory,
            'growsize': self.growsize,
        }

        path = s_common.genpath(self.dirn, 'layer_v2.lmdb')
        nodedatapath = s_common.genpath(self.dirn, 'nodedata.lmdb')

        self.layrslab = await s_lmdbslab.Slab.anit(path, **slabopts)
        self.dataslab = await s_lmdbslab.Slab.anit(nodedatapath, map_async=True,
                                                   readahead=False, readonly=self.readonly)

        metadb = self.layrslab.initdb('layer:meta')
        self.meta = s_lmdbslab.SlabDict(self.layrslab, db=metadb)
        if self.fresh:
            self.meta.set('version', 3)

        self.formcounts = await self.layrslab.getHotCount('count:forms')

        path = s_common.genpath(self.dirn, 'nodeedits.lmdb')
        self.nodeeditslab = await s_lmdbslab.Slab.anit(path, readonly=self.readonly)
        self.offsets = await self.layrslab.getHotCount('offsets')

        self.tagabrv = self.layrslab.getNameAbrv('tagabrv')
        self.propabrv = self.layrslab.getNameAbrv('propabrv')
        self.tagpropabrv = self.layrslab.getNameAbrv('tagpropabrv')

        self.onfini(self.layrslab)
        self.onfini(self.nodeeditslab)
        self.onfini(self.dataslab)

        self.bybuidv3 = self.layrslab.initdb('bybuidv3')

        self.byverb = self.layrslab.initdb('byverb', dupsort=True)
        self.edgesn1 = self.layrslab.initdb('edgesn1', dupsort=True)
        self.edgesn2 = self.layrslab.initdb('edgesn2', dupsort=True)

        self.bytag = self.layrslab.initdb('bytag', dupsort=True)
        self.byprop = self.layrslab.initdb('byprop', dupsort=True)
        self.byarray = self.layrslab.initdb('byarray', dupsort=True)
        self.bytagprop = self.layrslab.initdb('bytagprop', dupsort=True)

        self.countdb = self.layrslab.initdb('counters')
        self.nodedata = self.dataslab.initdb('nodedata')
        self.dataname = self.dataslab.initdb('dataname', dupsort=True)

        self.nodeeditlog = self.nodeeditctor(self.nodeeditslab, 'nodeedits')

        self.layrslab.on('commit', self._onLayrSlabCommit)

        self.layrvers = self.meta.get('version', 2)

        if self.layrvers < 3:
            await self._layrV2toV3()

    async def getSpawnInfo(self):
        info = await self.pack()
        info['dirn'] = self.dirn
        info['ctor'] = self.ctorname
        return info

    async def getLayerSize(self):
        '''
        Get the total storage size for the layer.
        '''
        totalsize = 0
        for fpath, _, fnames in os.walk(self.dirn):
            for fname in fnames:
                fp = s_common.genpath(fpath, fname)
                try:
                    stat = os.stat(fp)
                except OSError:  # pragma: no cover
                    pass
                else:
                    totalsize += stat.st_size
        return totalsize

    @s_nexus.Pusher.onPushAuto('layer:set')
    async def setLayerInfo(self, name, valu):
        '''
        Set a mutable layer property.
        '''
        if name not in ('name', 'logedits'):
            mesg = f'{name} is not a valid layer info key'
            raise s_exc.BadOptValu(mesg=mesg)

        if name == 'logedits':
            valu = bool(valu)
            self.logedits = valu

        # TODO when we can set more props, we may need to parse values.
        await self.layrinfo.set(name, valu)

        return valu

    async def stat(self):
        ret = {**self.layrslab.statinfo(),
               }
        if self.logedits:
            ret['nodeeditlog_indx'] = (self.nodeeditlog.index(), 0, 0)
        return ret

    async def _onLayrFini(self):
        [(await wind.fini()) for wind in self.windows]

    async def getFormCounts(self):
        return self.formcounts.pack()

    @s_cache.memoize()
    def getPropAbrv(self, form, prop):
        return self.propabrv.bytsToAbrv(s_msgpack.en((form, prop)))

    def setPropAbrv(self, form, prop):
        return self.propabrv.setBytsToAbrv(s_msgpack.en((form, prop)))

    @s_cache.memoize()
    def getTagPropAbrv(self, *args):
        return self.tagpropabrv.bytsToAbrv(s_msgpack.en(args))

    def setTagPropAbrv(self, *args):
        return self.tagpropabrv.setBytsToAbrv(s_msgpack.en(args))

    def getAbrvProp(self, abrv):
        byts = self.propabrv.abrvToByts(abrv)

        return s_msgpack.un(byts)

    async def getNodeValu(self, buid, prop=None):
        '''
        Retrieve either the form valu or a prop valu for the given node by buid.
        '''
        sode = self._getStorNode(buid)
        if prop is None:
            return sode.get('valu', (None, None))[0]
        return sode['props'].get(prop, (None, None))[0]

    async def getNodeTag(self, buid, tag):
        sode = self._getStorNode(buid)
        return sode['tags'].get(tag)

    async def getNodeForm(self, buid):
        sode = self._getStorNode(buid)
        return sode.get('form')

    def setSodeDirty(self, buid, sode, form):
        sode['form'] = form
        self.dirty[buid] = sode

    async def _onLayrSlabCommit(self, mesg):
        await self._saveDirtySodes()

    async def _saveDirtySodes(self):

        if not self.dirty:
            return

        # flush any dirty storage nodes before the commit
        kvlist = []

        for buid, sode in self.dirty.items():
            self.buidcache[buid] = sode
            kvlist.append((buid, s_msgpack.en(sode)))

        self.layrslab.putmulti(kvlist, db=self.bybuidv3)
        self.dirty.clear()

    async def getStorNode(self, buid):
        return deepcopy(self._getStorNode(buid))

    def _getStorNode(self, buid):
        '''
        Return the storage node for the given buid.

        NOTE: This API returns the *actual* storage node dict if it's
              dirty. You must make a deep copy if you plan to return it
              outside of the Layer.
        '''

        # check the dirty nodes first
        sode = self.dirty.get(buid)
        if sode is not None:
            return sode

        sode = self.buidcache.get(buid)
        if sode is not None:
            return sode

        sode = collections.defaultdict(dict)

        self.buidcache[buid] = sode

        byts = self.layrslab.get(buid, db=self.bybuidv3)
        if byts is not None:
            sode.update(s_msgpack.un(byts))

        return sode

    async def getTagCount(self, tagname, formname=None):
        '''
        Return the number of tag rows in the layer for the given tag/form.
        '''
        try:
            abrv = self.tagabrv.bytsToAbrv(tagname.encode())
            if formname is not None:
                abrv += self.getPropAbrv(formname, None)

        except s_exc.NoSuchAbrv:
            return 0

        return await self.layrslab.countByPref(abrv, db=self.bytag)

    async def getPropCount(self, formname, propname=None, maxsize=None):
        '''
        Return the number of property rows in the layer for the given form/prop.
        '''
        try:
            abrv = self.getPropAbrv(formname, propname)
        except s_exc.NoSuchAbrv:
            return 0

        return await self.layrslab.countByPref(abrv, db=self.byprop, maxsize=maxsize)

    async def liftByTag(self, tag, form=None):

        try:
            abrv = self.tagabrv.bytsToAbrv(tag.encode())
            if form is not None:
                abrv += self.getPropAbrv(form, None)

        except s_exc.NoSuchAbrv:
            return

        for _, buid in self.layrslab.scanByPref(abrv, db=self.bytag):
            yield buid, deepcopy(self._getStorNode(buid))

    async def liftByTagValu(self, tag, cmpr, valu, form=None):

        try:
            abrv = self.tagabrv.bytsToAbrv(tag.encode())
            if form is not None:
                abrv += self.getPropAbrv(form, None)

        except s_exc.NoSuchAbrv:
            return

        filt = StorTypeTag.getTagFilt(cmpr, valu)
        if filt is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr)

        for _, buid in self.layrslab.scanByPref(abrv, db=self.bytag):
            # filter based on the ival value before lifting the node...
            valu = await self.getNodeTag(buid, tag)
            if filt(valu):
                yield buid, deepcopy(self._getStorNode(buid))

    async def hasTagProp(self, name):
        async for _ in self.liftTagProp(name):
            return True

        return False

    async def liftTagProp(self, name):
        '''
        Note:
            This will lift *all* syn:tag nodes.
        '''
        async for _, tag in self.iterFormRows('syn:tag'):
            try:
                abrv = self.getTagPropAbrv(None, tag, name)

            except s_exc.NoSuchAbrv:
                continue

            for _, buid in self.layrslab.scanByPref(abrv, db=self.bytagprop):
                yield buid

    async def liftByTagProp(self, form, tag, prop):
        try:
            abrv = self.getTagPropAbrv(form, tag, prop)

        except s_exc.NoSuchAbrv:
            return

        for _, buid in self.layrslab.scanByPref(abrv, db=self.bytagprop):
            yield buid, deepcopy(self._getStorNode(buid))

    async def liftByTagPropValu(self, form, tag, prop, cmprvals):
        '''
        Note:  form may be None
        '''
        for cmpr, valu, kind in cmprvals:

            async for buid in self.stortypes[kind].indxByTagProp(form, tag, prop, cmpr, valu):
                yield buid, deepcopy(self._getStorNode(buid))

    async def liftByProp(self, form, prop):

        try:
            abrv = self.getPropAbrv(form, prop)

        except s_exc.NoSuchAbrv:
            return

        for _, buid in self.layrslab.scanByPref(abrv, db=self.byprop):
            yield buid, deepcopy(self._getStorNode(buid))

    # NOTE: form vs prop valu lifting is differentiated to allow merge sort
    async def liftByFormValu(self, form, cmprvals):
        for cmpr, valu, kind in cmprvals:
            async for buid in self.stortypes[kind].indxByForm(form, cmpr, valu):
                yield buid, deepcopy(self._getStorNode(buid))

    async def liftByPropValu(self, form, prop, cmprvals):
        for cmpr, valu, kind in cmprvals:
            if kind & 0x8000:
                kind = STOR_TYPE_MSGP
            async for buid in self.stortypes[kind].indxByProp(form, prop, cmpr, valu):
                yield buid, deepcopy(self._getStorNode(buid))

    async def liftByPropArray(self, form, prop, cmprvals):
        for cmpr, valu, kind in cmprvals:
            async for buid in self.stortypes[kind].indxByPropArray(form, prop, cmpr, valu):
                yield buid, deepcopy(self._getStorNode(buid))

    async def liftByDataName(self, name):
        try:
            abrv = self.getPropAbrv(name, None)

        except s_exc.NoSuchAbrv:
            return

        for abrv, buid in self.dataslab.scanByDups(abrv, db=self.dataname):

            sode = self._getStorNode(buid).copy()

            byts = self.dataslab.get(buid + abrv, db=self.nodedata)
            if byts is not None:
                item = s_msgpack.un(byts)
                sode['nodedata'][name] = item

            yield buid, deepcopy(sode)

    async def storNodeEdits(self, nodeedits, meta):

        results = await self._push('edits', nodeedits, meta)

        retn = []
        for buid, _, edits in results:
            sode = deepcopy(self._getStorNode(buid))
            retn.append((buid, sode, edits))

        return retn

    @s_nexus.Pusher.onPush('edits', passitem=True)
    async def _storNodeEdits(self, nodeedits, meta, nexsitem):
        '''
        Execute a series of node edit operations, returning the updated nodes.

        Args:
            nodeedits:  List[Tuple(buid, form, edits, subedits)]  List of requested changes per node

        Returns:
            List[Tuple[buid, form, edits]]  Same list, but with only the edits actually applied (plus the old value)
        '''
        edited = False

        # use/abuse python's dict ordering behavior
        results = {}

        nodeedits = collections.deque(nodeedits)
        while nodeedits:

            buid, form, edits = nodeedits.popleft()

            sode = self._getStorNode(buid)

            changes = []
            for edit in edits:

                delt = self.editors[edit[0]](buid, form, edit, sode, meta)
                if delt and edit[2]:
                    nodeedits.extend(edit[2])

                changes.extend(delt)

            flatedit = results.get(buid)
            if flatedit is None:
                results[buid] = flatedit = (buid, form, [])

            flatedit[2].extend(changes)

            if changes:
                edited = True

        flatedits = list(results.values())

        if edited:
            nexsindx = nexsitem[0] if nexsitem is not None else None
            await self.fire('layer:write', layer=self.iden, edits=flatedits, meta=meta, nexsindx=nexsindx)

            if self.logedits:
                offs = self.nodeeditlog.add((flatedits, meta), indx=nexsindx)
                [(await wind.put((offs, flatedits, meta))) for wind in tuple(self.windows)]

        await asyncio.sleep(0)

        return flatedits

    def mayDelBuid(self, buid, sode):

        if sode.get('valu'):
            return

        if sode.get('props'):
            return

        if sode.get('tags'):
            return

        if sode.get('tagprops'):
            return

        if self.dataslab.prefexists(buid, self.nodedata):
            return

        if self.layrslab.prefexists(buid, db=self.edgesn1):
            return

        # no more refs in this layer.  time to pop it...
        self.dirty.pop(buid, None)
        self.buidcache.pop(buid, None)
        self.layrslab.delete(buid, db=self.bybuidv3)

    async def storNodeEditsNoLift(self, nodeedits, meta):
        '''
        Execute a series of node edit operations.

        Does not return the updated nodes.
        '''
        await self._push('edits', nodeedits, meta)

    def _editNodeAdd(self, buid, form, edit, sode, meta):

        valt = edit[1]
        valu, stortype = valt
        if sode.get('valu') == valt:
            return ()

        sode['valu'] = valt
        self.setSodeDirty(buid, sode, form)

        abrv = self.setPropAbrv(form, None)

        if stortype & STOR_FLAG_ARRAY:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byarray)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byprop)

        self.formcounts.inc(form)
        if self.nodeAddHook is not None:
            self.nodeAddHook()

        retn = [
            (EDIT_NODE_ADD, (valu, stortype), ())
        ]

        tick = meta.get('time')
        if tick is None:
            tick = s_common.now()

        edit = (EDIT_PROP_SET, ('.created', tick, None, STOR_TYPE_MINTIME), ())
        retn.extend(self._editPropSet(buid, form, edit, sode, meta))

        return retn

    def _editNodeDel(self, buid, form, edit, sode, meta):

        valt = sode.pop('valu', None)
        if valt is None:
            # TODO tombstone
            self.mayDelBuid(buid, sode)
            return ()

        self.setSodeDirty(buid, sode, form)

        valu, stortype = valt

        abrv = self.setPropAbrv(form, None)

        if stortype & STOR_FLAG_ARRAY:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byarray)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)

        self.formcounts.inc(form, valu=-1)
        if self.nodeDelHook is not None:
            self.nodeDelHook()

        self._wipeNodeData(buid)
        # TODO edits to become async so we can sleep(0) on large deletes?
        self._delNodeEdges(buid)

        self.buidcache.pop(buid, None)

        self.mayDelBuid(buid, sode)

        return (
            (EDIT_NODE_DEL, (valu, stortype), ()),
        )

    def _editPropSet(self, buid, form, edit, sode, meta):

        prop, valu, oldv, stortype = edit[1]

        oldv, oldt = sode['props'].get(prop, (None, None))

        abrv = self.setPropAbrv(form, prop)
        univabrv = None

        if prop[0] == '.': # '.' to detect universal props (as quickly as possible)
            univabrv = self.setPropAbrv(None, prop)

        if oldv is not None:

            # merge intervals and min times
            if stortype == STOR_TYPE_IVAL:
                valu = (min(*oldv, *valu), max(*oldv, *valu))

            elif stortype == STOR_TYPE_MINTIME:
                valu = min(valu, oldv)

            if valu == oldv:
                return ()

            if oldt & STOR_FLAG_ARRAY:

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(abrv + oldi, buid, db=self.byarray)
                    if univabrv is not None:
                        self.layrslab.delete(univabrv + oldi, buid, db=self.byarray)

                for indx in self.getStorIndx(STOR_TYPE_MSGP, oldv):
                    self.layrslab.delete(abrv + indx, buid, db=self.byprop)
                    if univabrv is not None:
                        self.layrslab.delete(univabrv + indx, buid, db=self.byprop)

            else:

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(abrv + oldi, buid, db=self.byprop)
                    if univabrv is not None:
                        self.layrslab.delete(univabrv + oldi, buid, db=self.byprop)

        sode['props'][prop] = (valu, stortype)
        self.setSodeDirty(buid, sode, form)

        if stortype & STOR_FLAG_ARRAY:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byarray)
                if univabrv is not None:
                    self.layrslab.put(univabrv + indx, buid, db=self.byarray)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.put(univabrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.put(univabrv + indx, buid, db=self.byprop)

        return (
            (EDIT_PROP_SET, (prop, valu, oldv, stortype), ()),
        )

    def _editPropDel(self, buid, form, edit, sode, meta):

        prop, oldv, stortype = edit[1]

        abrv = self.setPropAbrv(form, prop)
        univabrv = None

        if prop[0] == '.': # '.' to detect universal props (as quickly as possible)
            univabrv = self.setPropAbrv(None, prop)

        valt = sode['props'].pop(prop, None)
        if valt is None:
            # FIXME tombstone
            self.mayDelBuid(buid, sode)
            return ()

        self.setSodeDirty(buid, sode, form)

        valu, stortype = valt

        if stortype & STOR_FLAG_ARRAY:

            realtype = stortype & 0x7fff

            for aval in valu:
                for indx in self.getStorIndx(realtype, aval):
                    self.layrslab.put(abrv + indx, buid, db=self.byarray)
                    if univabrv is not None:
                        self.layrslab.delete(univabrv + indx, buid, db=self.byarray)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.delete(univabrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.delete(univabrv + indx, buid, db=self.byprop)

        self.mayDelBuid(buid, sode)
        return (
            (EDIT_PROP_DEL, (prop, valu, stortype), ()),
        )

    def _editTagSet(self, buid, form, edit, sode, meta):

        if form is None: # pragma: no cover
            logger.warning(f'Invalid tag set edit, form is None: {edit}')
            return ()

        tag, valu, oldv = edit[1]

        tagabrv = self.tagabrv.setBytsToAbrv(tag.encode())
        formabrv = self.setPropAbrv(form, None)

        oldv = sode['tags'].get(tag)
        if oldv is not None:

            if oldv != (None, None) and valu != (None, None):

                valu = (min(oldv[0], valu[0]), max(oldv[1], valu[1]))

            if oldv == valu:
                return ()

        sode['tags'][tag] = valu
        self.setSodeDirty(buid, sode, form)

        self.layrslab.put(tagabrv + formabrv, buid, db=self.bytag)

        return (
            (EDIT_TAG_SET, (tag, valu, oldv), ()),
        )

    def _editTagDel(self, buid, form, edit, sode, meta):

        tag, oldv = edit[1]
        formabrv = self.setPropAbrv(form, None)

        oldv = sode['tags'].pop(tag, None)
        if oldv is None:
            # TODO tombstone
            self.mayDelBuid(buid, sode)
            return ()

        self.setSodeDirty(buid, sode, form)

        tagabrv = self.tagabrv.bytsToAbrv(tag.encode())

        self.layrslab.delete(tagabrv + formabrv, buid, db=self.bytag)

        self.mayDelBuid(buid, sode)
        return (
            (EDIT_TAG_DEL, (tag, oldv), ()),
        )

    def _editTagPropSet(self, buid, form, edit, sode, meta):

        if form is None: # pragma: no cover
            logger.warning(f'Invalid tagprop set edit, form is None: {edit}')
            return ()

        tag, prop, valu, oldv, stortype = edit[1]

        tpkey = (tag, prop)

        tp_abrv = self.setTagPropAbrv(None, tag, prop)
        ftp_abrv = self.setTagPropAbrv(form, tag, prop)

        oldv, oldt = sode['tagprops'].get(tpkey, (None, None))
        if oldv is not None:

            if valu == oldv and stortype == oldt:
                return ()

            for oldi in self.getStorIndx(oldt, oldv):
                self.layrslab.delete(tp_abrv + oldi, buid, db=self.bytagprop)
                self.layrslab.delete(ftp_abrv + oldi, buid, db=self.bytagprop)

        sode['tagprops'][tpkey] = (valu, stortype)
        self.setSodeDirty(buid, sode, form)

        kvpairs = []
        for indx in self.getStorIndx(stortype, valu):
            kvpairs.append((tp_abrv + indx, buid))
            kvpairs.append((ftp_abrv + indx, buid))

        self.layrslab.putmulti(kvpairs, db=self.bytagprop)

        return (
            (EDIT_TAGPROP_SET, (tag, prop, valu, oldv, stortype), ()),
        )

    def _editTagPropDel(self, buid, form, edit, sode, meta):

        tag, prop, valu, stortype = edit[1]

        tpkey = (tag, prop)

        oldv, oldt = sode['tagprops'].pop(tpkey, (None, None))
        if oldv is None:
            self.mayDelBuid(buid, sode)
            return ()

        self.setSodeDirty(buid, sode, form)

        tp_abrv = self.setTagPropAbrv(None, tag, prop)
        ftp_abrv = self.setTagPropAbrv(form, tag, prop)

        for oldi in self.getStorIndx(oldt, oldv):
            self.layrslab.delete(tp_abrv + oldi, buid, db=self.bytagprop)
            self.layrslab.delete(ftp_abrv + oldi, buid, db=self.bytagprop)

        self.mayDelBuid(buid, sode)
        return (
            (EDIT_TAGPROP_DEL, (tag, prop, oldv, oldt), ()),
        )

    def _editNodeDataSet(self, buid, form, edit, sode, meta):

        name, valu, oldv = edit[1]
        abrv = self.setPropAbrv(name, None)

        byts = s_msgpack.en(valu)
        oldb = self.dataslab.replace(buid + abrv, byts, db=self.nodedata)
        if oldb == byts:
            return ()

        # a bit of special case...
        if sode.get('form') is None:
            self.setSodeDirty(buid, sode, form)

        if oldb is not None:
            oldv = s_msgpack.un(oldb)

        self.dataslab.put(abrv, buid, db=self.dataname)

        return (
            (EDIT_NODEDATA_SET, (name, valu, oldv), ()),
        )

    def _editNodeDataDel(self, buid, form, edit, sode, meta):

        name, valu = edit[1]
        abrv = self.setPropAbrv(name, None)

        oldb = self.dataslab.pop(buid + abrv, db=self.nodedata)
        if oldb is None:
            self.mayDelBuid(buid, sode)
            return ()

        oldv = s_msgpack.un(oldb)
        self.dataslab.delete(abrv, buid, db=self.dataname)

        self.mayDelBuid(buid, sode)
        return (
            (EDIT_NODEDATA_DEL, (name, oldv), ()),
        )

    def _editNodeEdgeAdd(self, buid, form, edit, sode, meta):

        if form is None: # pragma: no cover
            logger.warning(f'Invalid node edge edit, form is None: {edit}')
            return ()

        verb, n2iden = edit[1]

        venc = verb.encode()
        n2buid = s_common.uhex(n2iden)

        n1key = buid + venc

        if self.layrslab.hasdup(n1key, n2buid, db=self.edgesn1):
            return ()

        # a bit of special case...
        if sode.get('form') is None:
            self.setSodeDirty(buid, sode, form)

        self.layrslab.put(venc, buid + n2buid, db=self.byverb)
        self.layrslab.put(n1key, n2buid, db=self.edgesn1)
        self.layrslab.put(n2buid + venc, buid, db=self.edgesn2)

        return (
            (EDIT_EDGE_ADD, (verb, n2iden), ()),
        )

    def _editNodeEdgeDel(self, buid, form, edit, sode, meta):

        verb, n2iden = edit[1]

        venc = verb.encode()
        n2buid = s_common.uhex(n2iden)

        if not self.layrslab.delete(buid + venc, n2buid, db=self.edgesn1):
            self.mayDelBuid(buid, sode)
            return ()

        self.layrslab.delete(venc, buid + n2buid, db=self.byverb)
        self.layrslab.delete(n2buid + venc, buid, db=self.edgesn2)

        self.mayDelBuid(buid, sode)
        return (
            (EDIT_EDGE_DEL, (verb, n2iden), ()),
        )

    async def getEdgeVerbs(self):

        for lkey in self.layrslab.scanKeys(db=self.byverb):
            yield lkey.decode()

    async def getEdges(self, verb=None):

        if verb is None:

            for lkey, lval in self.layrslab.scanByFull(db=self.byverb):
                yield (s_common.ehex(lval[:32]), lkey.decode(), s_common.ehex(lval[32:]))

            return

        for _, lval in self.layrslab.scanByDups(verb.encode(), db=self.byverb):
            yield (s_common.ehex(lval[:32]), verb, s_common.ehex(lval[32:]))

    def _delNodeEdges(self, buid):
        for lkey, n2buid in self.layrslab.scanByPref(buid, db=self.edgesn1):
            venc = lkey[32:]
            self.layrslab.delete(venc, buid + n2buid, db=self.byverb)
            self.layrslab.delete(lkey, n2buid, db=self.edgesn1)
            self.layrslab.delete(n2buid + venc, buid, db=self.edgesn2)

    def getStorIndx(self, stortype, valu):

        if stortype & 0x8000:

            realtype = stortype & 0x7fff

            retn = []
            [retn.extend(self.getStorIndx(realtype, aval)) for aval in valu]
            return retn

        return self.stortypes[stortype].indx(valu)

    async def iterNodeEdgesN1(self, buid, verb=None):

        pref = buid
        if verb is not None:
            pref += verb.encode()

        for lkey, n2buid in self.layrslab.scanByPref(pref, db=self.edgesn1):
            verb = lkey[32:].decode()
            yield verb, s_common.ehex(n2buid)

    async def iterNodeEdgesN2(self, buid, verb=None):
        pref = buid
        if verb is not None:
            pref += verb.encode()

        for lkey, n1buid in self.layrslab.scanByPref(pref, db=self.edgesn2):
            verb = lkey[32:].decode()
            yield verb, s_common.ehex(n1buid)

    async def iterFormRows(self, form, stortype=None, startvalu=None):
        try:
            indxby = IndxByForm(self, form)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterPropRows(self, form, prop, stortype=None, startvalu=None):
        try:
            indxby = IndxByProp(self, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterUnivRows(self, prop, stortype=None, startvalu=None):
        '''
        Args:
            startvalu (Any): The value to start at.  May only be not None if stortype is not None.
        '''
        try:
            indxby = IndxByProp(self, None, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterTagRows(self, tag, form=None, starttupl=None):
        '''
        Args:
            tag(str): the tag to match
            form(Optional[str]):  if present, only yields buids of nodes that match the form
            starttupl(Optional[Tuple[buid, form]]):  if present, (re)starts the stream of values there

        Returns:
            AsyncIterator[Tuple(buid, (valu, form))]

        Note:
            This yields (buid, (tagvalu, form)) instead of just buid, valu in order to allow resuming an interrupted
            call by feeding the last value retrieved into starttupl
        '''
        try:
            indxby = IndxByTag(self, form, tag)

        except s_exc.NoSuchAbrv:
            return

        abrv = indxby.abrv

        startkey = startvalu = None

        if starttupl:
            startbuid, startform = starttupl
            startvalu = startbuid

            if form:
                if startform != form:
                    return  # Caller specified a form but doesn't want to start on the same form?!
                startkey = None
            else:
                try:
                    startkey = self.getPropAbrv(startform, None)
                except s_exc.NoSuchAbrv:
                    return

        for _, buid in self.layrslab.scanByPref(abrv, startkey=startkey, startvalu=startvalu, db=indxby.db):

            item = indxby.getNodeValuForm(buid)

            await asyncio.sleep(0)
            if item is None:
                continue

            yield buid, item

    async def iterTagPropRows(self, tag, prop, form=None, stortype=None, startvalu=None):
        '''
        Yields (buid, valu) that match a tag:prop

        Args:
            form:  may be None

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        try:
            indxby = IndxByTagProp(self, form, tag, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def _iterRows(self, indxby, stortype=None, startvalu=None):
        '''
        Args:
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any): The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple[buid,valu]]
        '''
        assert stortype is not None or startvalu is None

        abrv = indxby.abrv
        abrvlen = indxby.abrvlen
        startbytz = None

        if stortype:
            stor = self.stortypes[stortype]
            if startvalu is not None:
                startbytz = stor.indx(startvalu)[0]

        for key, buid in self.layrslab.scanByPref(abrv, startkey=startbytz, db=indxby.db):

            if stortype is not None:
                # Extract the value directly out of the end of the key
                indx = key[abrvlen:]

                valu = stor.decodeIndx(indx)
                if valu is not s_common.novalu:
                    await asyncio.sleep(0)

                    yield buid, valu
                    continue

            valu = indxby.getNodeValu(buid)

            await asyncio.sleep(0)

            if valu is None:
                continue

            yield buid, valu

    async def getNodeData(self, buid, name):
        '''
        Return a single element of a buid's node data
        '''
        try:
            abrv = self.getPropAbrv(name, None)

        except s_exc.NoSuchAbrv:
            return False, None

        byts = self.dataslab.get(buid + abrv, db=self.nodedata)
        if byts is None:
            return False, None

        return True, s_msgpack.un(byts)

    async def iterNodeData(self, buid):
        '''
        Return a generator of all a buid's node data
        '''
        for lkey, byts in self.dataslab.scanByPref(buid, db=self.nodedata):
            abrv = lkey[32:]

            valu = s_msgpack.un(byts)
            prop = self.getAbrvProp(abrv)
            yield prop[0], valu

    async def iterLayerNodeEdits(self):
        '''
        Scan the full layer and yield artificial sets of nodeedits.
        '''
        await self._saveDirtySodes()

        for buid, byts in self.layrslab.scanByFull(db=self.bybuidv3):

            sode = s_msgpack.un(byts)

            form = sode.get('form')
            if form is None:
                iden = s_common.ehex(buid)
                logger.warning(f'NODE HAS NO FORM: {iden}')
                continue

            edits = []
            nodeedit = (buid, form, edits)

            # TODO tombstones
            valt = sode.get('valu')
            if valt is not None:
                edits.append((EDIT_NODE_ADD, valt, ()))

            for prop, (valu, stortype) in sode.get('props', {}).items():
                edits.append((EDIT_PROP_SET, (prop, valu, None, stortype), ()))

            for tag, tagv in sode.get('tags', {}).items():
                edits.append((EDIT_TAG_SET, (tag, tagv, None), ()))

            for (tag, prop), (valu, stortype) in sode.get('tagprops', {}).items():
                edits.append((EDIT_TAGPROP_SET, (tag, prop, valu, None, stortype), ()))

            async for prop, valu in self.iterNodeData(buid):
                edits.append((EDIT_NODEDATA_SET, (prop, valu, None), ()))

            async for verb, n2iden in self.iterNodeEdgesN1(buid):
                edits.append((EDIT_EDGE_ADD, (verb, n2iden), ()))

            yield nodeedit

    async def initUpstreamSync(self, url):
        self.schedCoro(self._initUpstreamSync(url))

    async def _initUpstreamSync(self, url):
        '''
        We're a downstream layer, receiving a stream of edits from an upstream layer telepath proxy at url
        '''

        while not self.isfini:

            try:

                async with await s_telepath.openurl(url) as proxy:

                    creator = self.layrinfo.get('creator')

                    iden = await proxy.getIden()
                    offs = self.offsets.get(iden)
                    logger.warning(f'upstream sync connected ({s_urlhelp.sanitizeUrl(url)} offset={offs})')

                    if offs == 0:
                        offs = await proxy.getEditIndx()
                        meta = {'time': s_common.now(),
                                'user': creator,
                                }

                        async for item in proxy.iterLayerNodeEdits():
                            await self.storNodeEditsNoLift([item], meta)

                        self.offsets.set(iden, offs)

                        waits = [v for k, v in self.upstreamwaits[iden].items() if k <= offs]
                        for wait in waits:
                            [e.set() for e in wait]

                    while not proxy.isfini:

                        offs = self.offsets.get(iden)

                        # pump them into a queue so we can consume them in chunks
                        q = asyncio.Queue(maxsize=1000)

                        async def consume(x):
                            try:
                                async for item in proxy.syncNodeEdits(x):
                                    await q.put(item)
                            finally:
                                await q.put(None)

                        proxy.schedCoro(consume(offs))

                        done = False
                        while not done:

                            # get the next item so we maybe block...
                            item = await q.get()
                            if item is None:
                                break

                            items = [item]

                            # check if there are more we can eat
                            for _ in range(q.qsize()):

                                nexi = await q.get()
                                if nexi is None:
                                    done = True
                                    break

                                items.append(nexi)

                            for nodeeditoffs, item in items:
                                await self.storNodeEditsNoLift(item, {'time': s_common.now(),
                                                                      'user': creator,
                                                                      })
                                self.offsets.set(iden, nodeeditoffs + 1)

                                waits = self.upstreamwaits[iden].pop(nodeeditoffs + 1, None)
                                if waits is not None:
                                    [e.set() for e in waits]

            except asyncio.CancelledError: # pragma: no cover
                return

            except Exception:
                logger.exception('error in initUpstreamSync loop')

            await self.waitfini(1)

    def _wipeNodeData(self, buid):
        '''
        Remove all node data for a buid
        '''
        for lkey, _ in self.dataslab.scanByPref(buid, db=self.nodedata):
            self.dataslab.delete(lkey, db=self.nodedata)

    async def getModelVers(self):
        return self.layrinfo.get('model:version', (-1, -1, -1))

    async def setModelVers(self, vers):
        await self.layrinfo.set('model:version', vers)

    async def getStorNodes(self):
        '''
        Yield (buid, sode) tuples for all the nodes with props/tags/tagprops stored in this layer.
        '''
        done = set()

        for buid, sode in list(self.dirty.items()):
            done.add(buid)
            yield buid, sode

        for buid, byts in self.layrslab.scanByFull(db=self.bybuidv3):

            if buid in done:
                continue

            yield buid, s_msgpack.un(byts)
            await asyncio.sleep(0)

    async def splices(self, offs=None, size=None):
        '''
        Yield (offs, splice) tuples from the nodeedit log starting from the given offset.

        Nodeedits will be flattened into splices before being yielded.
        '''
        if not self.logedits:
            return

        if offs is None:
            offs = (0, 0, 0)

        if size is not None:

            count = 0
            async for offset, nodeedits, meta in self.iterNodeEditLog(offs[0]):
                async for splice in self.makeSplices(offset, nodeedits, meta):

                    if splice[0] < offs:
                        continue

                    if count >= size:
                        return

                    yield splice
                    count = count + 1
        else:
            async for offset, nodeedits, meta in self.iterNodeEditLog(offs[0]):
                async for splice in self.makeSplices(offset, nodeedits, meta):

                    if splice[0] < offs:
                        continue

                    yield splice

    async def splicesBack(self, offs=None, size=None):

        if not self.logedits:
            return

        if offs is None:
            offs = (await self.getEditIndx(), 0, 0)

        if size is not None:

            count = 0
            async for offset, nodeedits, meta in self.iterNodeEditLogBack(offs[0]):
                async for splice in self.makeSplices(offset, nodeedits, meta, reverse=True):

                    if splice[0] > offs:
                        continue

                    if count >= size:
                        return

                    yield splice
                    count += 1
        else:
            async for offset, nodeedits, meta in self.iterNodeEditLogBack(offs[0]):
                async for splice in self.makeSplices(offset, nodeedits, meta, reverse=True):

                    if splice[0] > offs:
                        continue

                    yield splice

    async def iterNodeEditLog(self, offs=0):
        '''
        Iterate the node edit log and yield (offs, edits, meta) tuples.
        '''
        for offs, (edits, meta) in self.nodeeditlog.iter(offs):
            yield (offs, edits, meta)

    async def iterNodeEditLogBack(self, offs=0):
        '''
        Iterate the node edit log and yield (offs, edits, meta) tuples in reverse.
        '''
        for offs, (edits, meta) in self.nodeeditlog.iterBack(offs):
            yield (offs, edits, meta)

    async def syncNodeEdits2(self, offs, wait=True):
        '''
        Once caught up with storage, yield them in realtime.

        Returns:
            Tuple of offset(int), nodeedits, meta(dict)
        '''
        if not self.logedits:
            return

        for offi, (nodeedits, meta) in self.nodeeditlog.iter(offs):
            yield (offi, nodeedits, meta)

        if wait:
            async with self.getNodeEditWindow() as wind:
                async for item in wind:
                    yield item

    async def syncNodeEdits(self, offs, wait=True):
        '''
        Identical to syncNodeEdits2, but doesn't yield meta
        '''
        async for offi, nodeedits, _meta in self.syncNodeEdits2(offs, wait=wait):
            yield (offi, nodeedits)

    async def syncIndexEvents(self, offs, matchdef, wait=True):
        '''
        Yield (offs, (buid, form, ETYPE, VALS, META)) tuples from the nodeedit log starting from the given offset.
        Only edits that match the filter in matchdef will be yielded.

        ETYPE is an constant EDIT_* above.  VALS is a tuple whose format depends on ETYPE, outlined in the comment
        next to the constant.  META is a dict that may contain keys 'user' and 'time' to represent the iden of the user
        that initiated the change, and the time that it took place, respectively.

        Additionally, every 1000 entries, an entry (offs, (None, None, EDIT_PROGRESS, (), ())) message is emitted.

        Args:
            offs(int): starting nexus/editlog offset
            matchdef(Dict[str, Sequence[str]]):  a dict describing which events are yielded
            wait(bool):  whether to pend and stream value until this layer is fini'd

        The matchdef dict may contain the following keys:  forms, props, tags, tagprops.  The value must be a sequence
        of strings.  Each key/val combination is treated as an "or", so each key and value yields more events.
            forms: EDIT_NODE_ADD and EDIT_NODE_DEL events.  Matches events for nodes with forms in the value list.
            props: EDIT_PROP_SET and EDIT_PROP_DEL events.  Values must be in form:prop or .universal form
            tags:  EDIT_TAG_SET and EDIT_TAG_DEL events.  Values must be the raw tag with no #.
            tagprops: EDIT_TAGPROP_SET and EDIT_TAGPROP_DEL events.   Values must be just the prop or tag:prop.

        Note:
            Will not yield any values if this layer was not created with logedits enabled
        '''

        formm = set(matchdef.get('forms', ()))
        propm = set(matchdef.get('props', ()))
        tagm = set(matchdef.get('tags', ()))
        tagpropm = set(matchdef.get('tagprops', ()))
        count = 0

        async for curoff, editses in self.syncNodeEdits(offs, wait=wait):
            for buid, form, edit in editses:
                for etyp, vals, meta in edit:
                    if ((form in formm and etyp in (EDIT_NODE_ADD, EDIT_NODE_DEL))
                            or (etyp in (EDIT_PROP_SET, EDIT_PROP_DEL)
                                and (vals[0] in propm or f'{form}:{vals[0]}' in propm))
                            or (etyp in (EDIT_TAG_SET, EDIT_TAG_DEL) and vals[0] in tagm)
                            or (etyp in (EDIT_TAGPROP_SET, EDIT_TAGPROP_DEL)
                                and (vals[1] in tagpropm or f'{vals[0]}:{vals[1]}' in tagpropm))):

                        yield (curoff, (buid, form, etyp, vals, meta))

            await asyncio.sleep(0)

            count += 1
            if count % 1000 == 0:
                yield (curoff, (None, None, EDIT_PROGRESS, (), ()))

    async def makeSplices(self, offs, nodeedits, meta, reverse=False):
        '''
        Flatten a set of nodeedits into splices.
        '''
        if meta is None:
            meta = {}

        user = meta.get('user')
        time = meta.get('time')
        prov = meta.get('prov')

        if reverse:
            nodegenr = reversed(list(enumerate(nodeedits)))
        else:
            nodegenr = enumerate(nodeedits)

        for nodeoffs, (buid, form, edits) in nodegenr:

            formvalu = None

            if reverse:
                editgenr = reversed(list(enumerate(edits)))
            else:
                editgenr = enumerate(edits)

            for editoffs, (edit, info, _) in editgenr:

                if edit in (EDIT_NODEDATA_SET, EDIT_NODEDATA_DEL, EDIT_EDGE_ADD, EDIT_EDGE_DEL):
                    continue

                spliceoffs = (offs, nodeoffs, editoffs)

                props = {
                    'time': time,
                    'user': user,
                }

                if prov is not None:
                    props['prov'] = prov

                if edit == EDIT_NODE_ADD:
                    formvalu, stortype = info
                    props['ndef'] = (form, formvalu)

                    yield (spliceoffs, ('node:add', props))
                    continue

                if edit == EDIT_NODE_DEL:
                    formvalu, stortype = info
                    props['ndef'] = (form, formvalu)

                    yield (spliceoffs, ('node:del', props))
                    continue

                if formvalu is None:
                    formvalu = await self.getNodeValu(buid)

                props['ndef'] = (form, formvalu)

                if edit == EDIT_PROP_SET:
                    prop, valu, oldv, stortype = info
                    props['prop'] = prop
                    props['valu'] = valu
                    props['oldv'] = oldv

                    yield (spliceoffs, ('prop:set', props))
                    continue

                if edit == EDIT_PROP_DEL:
                    prop, valu, stortype = info
                    props['prop'] = prop
                    props['valu'] = valu

                    yield (spliceoffs, ('prop:del', props))
                    continue

                if edit == EDIT_TAG_SET:
                    tag, valu, oldv = info
                    props['tag'] = tag
                    props['valu'] = valu
                    props['oldv'] = oldv

                    yield (spliceoffs, ('tag:add', props))
                    continue

                if edit == EDIT_TAG_DEL:
                    tag, valu = info
                    props['tag'] = tag
                    props['valu'] = valu

                    yield (spliceoffs, ('tag:del', props))
                    continue

                if edit == EDIT_TAGPROP_SET:
                    tag, prop, valu, oldv, stortype = info
                    props['tag'] = tag
                    props['prop'] = prop
                    props['valu'] = valu
                    props['oldv'] = oldv

                    yield (spliceoffs, ('tag:prop:set', props))
                    continue

                if edit == EDIT_TAGPROP_DEL:
                    tag, prop, valu, stortype = info
                    props['tag'] = tag
                    props['prop'] = prop
                    props['valu'] = valu

                    yield (spliceoffs, ('tag:prop:del', props))

    @contextlib.asynccontextmanager
    async def getNodeEditWindow(self):
        if not self.logedits:
            raise s_exc.BadConfValu(mesg='Layer logging must be enabled for getting nodeedits')

        async with await s_queue.Window.anit(maxsize=10000) as wind:

            async def fini():
                self.windows.remove(wind)

            wind.onfini(fini)

            self.windows.append(wind)

            yield wind

    async def getEditIndx(self):
        '''
        Returns what will be the *next* (i.e. 1 past the last) nodeedit log index.
        '''
        if not self.logedits:
            return 0

        return self.nodeeditlog.index()

    async def getEditOffs(self):
        '''
        Return the offset of the last *recorded* log entry.  Returns -1 if nodeedit log is disabled or empty.
        '''
        if not self.logedits:
            return -1

        last = self.nodeeditlog.last()
        if last is not None:
            return last[0]

        return -1

    async def waitEditOffs(self, offs, timeout=None):
        '''
        Wait for the node edit log to write an entry at/past the given offset.
        '''
        if not self.logedits:
            mesg = 'Layer.waitEditOffs() does not work with logedits disabled.'
            raise s_exc.BadArg(mesg=mesg)

        return await self.nodeeditlog.waitForOffset(offs, timeout=timeout)

    async def waitUpstreamOffs(self, iden, offs):
        evnt = asyncio.Event()

        if self.offsets.get(iden) >= offs:
            evnt.set()
        else:
            self.upstreamwaits[iden][offs].append(evnt)

        return evnt

    async def delete(self):
        '''
        Delete the underlying storage
        '''
        self.isdeleted = True
        await self.fini()
        shutil.rmtree(self.dirn, ignore_errors=True)

def getFlatEdits(nodeedits):

    editsbynode = collections.defaultdict(list)

    # flatten out conditional node edits
    def addedits(buid, form, edits):
        nkey = (buid, form)
        for edittype, editinfo, condedits in edits:
            editsbynode[nkey].append((edittype, editinfo, ()))
            for condedit in condedits:
                addedits(*condedit)

    for buid, form, edits in nodeedits:
        addedits(buid, form, edits)

    return [(k[0], k[1], v) for (k, v) in editsbynode.items()]
