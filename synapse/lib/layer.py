'''
The Layer 2.0 archtecture introduces several optimized node/message serialization formats
used by the layers to optimize returning primitives and facilitate efficient node construction.

Note:  this interface is subject to change between minor revisions.

Storage Types (<stortype>):

    In Layers 2.0, each node property from the model has an associated "storage type".  Each
    storage type determines how the data is indexed and represented within the Layer.  This
    formalizes the separation of "data model" from "storage model".  Each data model type has
    a "stortype" property which coresponds to one of the STOR_TYPE_XXX values.  The knowledge
    of the mapping of data model types to storage types is the responsibility of the data model,
    making the Layer implementation fully decoupled from the data model.

Node Edits / Edits:

    A node edit consists of a (<buid>, <form>, [edits]) tuple where edits is a list of (<type>, <info>)
    edits which corespond to the EDIT_XXX types.

Storage Node (<sode>):

    A storage node is a layer/storage optimized node representation which is similar to a "packed node".
    A storage node *may* be partial ( as it is produced by a given layer ) and are joined by the view/snap
    into "full" storage nodes which are used to construct Node() instances.

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
import itertools
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

import synapse.lib.config as s_config
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn

logger = logging.getLogger(__name__)

FAIR_ITERS = 10  # every this many rows, yield CPU to other tasks

import synapse.lib.msgpack as s_msgpack

reqValidLdef = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'lockmemory': {'type': 'boolean'},
        'logedits': {'type': 'boolean'}, 'default': True
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

    async def syncNodeEdits(self, offs):
        '''
        Yield (offs, nodeedits) tuples from the nodeedit log starting from the given offset.

        Once caught up with storage, yield them in realtime.
        '''
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.syncNodeEdits(offs):
            yield item

    async def splices(self, offs=None, size=None):
        '''
        Yield (offs, splice) tuples from the nodeedit log starting from the given offset.

        Nodeedits will be flattened into splices before being yielded.
        '''
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.splices(offs=offs, size=size):
            yield item

    async def getNodeEditOffset(self):
        await self._reqUserAllowed(self.liftperm)
        return self.layr.getNodeEditOffset()

    async def getIden(self):
        await self._reqUserAllowed(self.liftperm)
        return self.layr.iden

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

# STOR_TYPE_TOMB      = ??
# STOR_TYPE_FIXED     = ??

STOR_FLAG_ARRAY = 0x8000

EDIT_NODE_ADD = 0     # (<type>, (<valu>, <type>))
EDIT_NODE_DEL = 1     # (<type>, (<valu>, <type>))
EDIT_PROP_SET = 2     # (<type>, (<prop>, <valu>, <oldv>, <type>))
EDIT_PROP_DEL = 3     # (<type>, (<prop>, <oldv>, <type>))
EDIT_TAG_SET = 4      # (<type>, (<tag>, <valu>, <oldv>))
EDIT_TAG_DEL = 5      # (<type>, (<tag>, <oldv>))
EDIT_TAGPROP_SET = 6  # (<type>, (<tag>, <prop>, <valu>, <oldv>, <type>))
EDIT_TAGPROP_DEL = 7  # (<type>, (<tag>, <prop>, <oldv>, <type>))
EDIT_NODEDATA_SET = 8 # (<type>, (<name>, <valu>, <oldv>))
EDIT_NODEDATA_DEL = 9 # (<type>, (<name>, <valu>))

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

        abrv = layr.getPropAbrv(form, None)
        IndxBy.__init__(self, layr, abrv, layr.byprop)

        self.form = form

    def getNodeValu(self, buid):
        bkey = buid + b'\x00'
        byts = self.layr.layrslab.get(bkey, db=self.layr.bybuid)
        if byts is not None:
            return s_msgpack.un(byts)[1]

class IndxByProp(IndxBy):

    def __init__(self, layr, form, prop):

        abrv = layr.getPropAbrv(form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.byprop)

        self.form = form
        self.prop = prop

    def getNodeValu(self, buid):
        bkey = buid + b'\x01' + self.prop.encode()
        byts = self.layr.layrslab.get(bkey, db=self.layr.bybuid)
        if byts is not None:
            return s_msgpack.un(byts)[0]

class IndxByPropArray(IndxBy):

    def __init__(self, layr, form, prop):

        abrv = layr.getPropAbrv(form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.byarray)

        self.form = form
        self.prop = prop

    def getNodeValu(self, buid):
        bkey = buid + b'\x01' + self.prop.encode()
        byts = self.layr.layrslab.get(bkey, db=self.layr.bybuid)
        if byts is not None:
            return s_msgpack.un(byts)[0]

class IndxByTagProp(IndxBy):

    def __init__(self, layr, form, tag, prop):

        abrv = layr.getTagPropAbrv(form, tag, prop)
        IndxBy.__init__(self, layr, abrv, layr.bytagprop)

        self.form = form
        self.prop = prop
        self.tag = tag

    def getNodeValu(self, buid):
        bkey = buid + b'\x03' + self.tag.encode() + b':' + self.prop.encode()
        byts = self.layr.layrslab.get(bkey, db=self.layr.bybuid)
        if byts is not None:
            return s_msgpack.un(byts)[0]

class StorType:

    def __init__(self, layr, stortype):
        self.layr = layr
        self.stortype = stortype

        self.lifters = {}

    def indxBy(self, liftby, cmpr, valu):
        func = self.lifters.get(cmpr)
        if func is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr)

        yield from func(liftby, valu)

    def indxByForm(self, form, cmpr, valu):
        indxby = IndxByForm(self.layr, form)
        yield from self.indxBy(indxby, cmpr, valu)

    def indxByProp(self, form, prop, cmpr, valu):
        indxby = IndxByProp(self.layr, form, prop)
        yield from self.indxBy(indxby, cmpr, valu)

    def indxByPropArray(self, form, prop, cmpr, valu):
        indxby = IndxByPropArray(self.layr, form, prop)
        yield from self.indxBy(indxby, cmpr, valu)

    def indxByTagProp(self, form, tag, prop, cmpr, valu):
        indxby = IndxByTagProp(self.layr, form, tag, prop)
        yield from self.indxBy(indxby, cmpr, valu)

    def indx(self, valu):
        raise NotImplementedError

class StorTypeUtf8(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_UTF8)
        self.lifters.update({
            '=': self._liftUtf8Eq,
            '~=': self._liftUtf8Regx,
            '^=': self._liftUtf8Prefix,
            'range=': self._liftUtf8Range,
        })

    def _liftUtf8Eq(self, liftby, valu):
        indx = self._getIndxByts(valu)
        yield from liftby.buidsByDups(indx)

    def _liftUtf8Range(self, liftby, valu):
        minindx = self._getIndxByts(valu[0])
        maxindx = self._getIndxByts(valu[1])
        yield from liftby.buidsByRange(minindx, maxindx)

    def _liftUtf8Regx(self, liftby, valu):

        regx = regex.compile(valu)
        lastbuid = None

        for buid in liftby.buidsByPref():
            if buid == lastbuid:
                continue

            lastbuid = buid
            storvalu = liftby.getNodeValu(buid)

            if isinstance(storvalu, (tuple, list)):
                for sv in storvalu:
                    if regx.search(sv) is not None:
                        yield buid
                        break
            else:
                if regx.search(storvalu) is None:
                    continue
                yield buid

    def _liftUtf8Prefix(self, liftby, valu):
        indx = self._getIndxByts(valu)
        yield from liftby.buidsByPref(indx)

    def _getIndxByts(self, valu):

        # include a byte as a "type" of string index value
        # ( to allow sub-types to have special indexing )

        indx = valu.encode('utf8', 'surrogatepass')
        # cut down an index value to 256 bytes...
        if len(indx) <= 256:
            return indx

        base = indx[:248]
        sufx = xxhash.xxh64(indx).digest()
        return base + sufx

    def indx(self, valu):
        return (self._getIndxByts(valu), )

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

    def _liftHierEq(self, liftby, valu):
        indx = self.getHierIndx(valu)
        yield from liftby.buidsByDups(indx)

    def _liftHierPref(self, liftby, valu):
        indx = self.getHierIndx(valu)
        yield from liftby.buidsByPref(indx)

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
            '=': self._liftUtf8Eq,
            '~=': self._liftUtf8Regx,
        })

    def _liftUtf8Eq(self, liftby, valu):

        if valu[0] == '*':
            indx = self._getIndxByts(valu[1:][::-1])
            yield from liftby.buidsByPref(indx)
            return

        yield from StorTypeUtf8._liftUtf8Eq(self, liftby, valu[::-1])

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

    def _liftIPv6Eq(self, liftby, valu):
        indx = self.getIPv6Indx(valu)
        yield from liftby.buidsByDups(indx)

    def _liftIPv6Range(self, liftby, valu):
        minindx = self.getIPv6Indx(valu[0])
        maxindx = self.getIPv6Indx(valu[1])
        yield from liftby.buidsByRange(minindx, maxindx)

class StorTypeInt(StorType):

    def __init__(self, layr, stortype, size, signed):

        StorType.__init__(self, layr, stortype)

        self.size = size
        self.signed = signed

        self.offset = 0
        if signed:
            self.offset = 2 ** ((self.size * 8) - 1) - 1

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

    def _liftIntEq(self, liftby, valu):
        indx = (valu + self.offset).to_bytes(self.size, 'big')
        yield from liftby.buidsByDups(indx)

    def _liftIntGt(self, liftby, valu):
        yield from self._liftIntGe(liftby, valu + 1)

    def _liftIntGe(self, liftby, valu):
        pkeymin = (valu + self.offset).to_bytes(self.size, 'big')
        pkeymax = self.fullbyts
        yield from liftby.buidsByRange(pkeymin, pkeymax)

    def _liftIntLt(self, liftby, valu):
        yield from self._liftIntLe(liftby, valu - 1)

    def _liftIntLe(self, liftby, valu):
        pkeymin = self.zerobyts
        pkeymax = (valu + self.offset).to_bytes(self.size, 'big')
        yield from liftby.buidsByRange(pkeymin, pkeymax)

    def _liftIntRange(self, liftby, valu):
        pkeymin = (valu[0] + self.offset).to_bytes(self.size, 'big')
        pkeymax = (valu[1] + self.offset).to_bytes(self.size, 'big')
        yield from liftby.buidsByRange(pkeymin, pkeymax)

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

    def _liftFloatEq(self, liftby, valu):
        yield from liftby.buidsByDups(self.fpack(valu))

    def _liftFloatGeCommon(self, liftby, valu):
        if math.isnan(valu):
            raise s_exc.NotANumberCompared()

        valupack = self.fpack(valu)

        if math.copysign(1.0, valu) < 0.0:  # negative values and -0.0
            yield from liftby.keyBuidsByRangeBack(self.FloatPackNegMax, valupack)
            valupack = self.FloatPackPosMin

        yield from liftby.keyBuidsByRange(valupack, self.FloatPackPosMax)

    def _liftFloatGe(self, liftby, valu):
        yield from (x[1] for x in self._liftFloatGeCommon(liftby, valu))

    def _liftFloatGt(self, liftby, valu):
        genr = self._liftFloatGeCommon(liftby, valu)
        valupack = self.fpack(valu)
        yield from (x[1] for x in itertools.dropwhile(lambda x: x[0] == valupack, genr))

    def _liftFloatLeCommon(self, liftby, valu):
        if math.isnan(valu):
            raise s_exc.NotANumberCompared()

        valupack = self.fpack(valu)

        if math.copysign(1.0, valu) > 0.0:
            yield from liftby.keyBuidsByRangeBack(self.FloatPackNegMax, self.FloatPackNegMin)
            yield from liftby.keyBuidsByRange(self.FloatPackPosMin, valupack)
        else:
            yield from liftby.keyBuidsByRangeBack(valupack, self.FloatPackNegMin)

    def _liftFloatLe(self, liftby, valu):
        yield from (x[1] for x in self._liftFloatLeCommon(liftby, valu))

    def _liftFloatLt(self, liftby, valu):
        genr = self._liftFloatLeCommon(liftby, valu)
        valupack = self.fpack(valu)
        yield from (x[1] for x in itertools.takewhile(lambda x: x[0] != valupack, genr))

    def _liftFloatRange(self, liftby, valu):
        valumin, valumax = valu

        if math.isnan(valumin) or math.isnan(valumax):
            raise s_exc.NotANumberCompared()

        assert valumin <= valumax

        pkeymin, pkeymax = (self.fpack(v) for v in valu)

        if math.copysign(1.0, valumin) > 0.0:
            # Entire range is nonnegative
            yield from liftby.buidsByRange(pkeymin, pkeymax)
            return

        if math.copysign(1.0, valumax) < 0.0:  # negative values and -0.0
            # Entire range is negative
            yield from liftby.buidsByRangeBack(pkeymax, pkeymin)
            return

        # Yield all values between min and -0
        yield from liftby.buidsByRangeBack(self.FloatPackNegMax, pkeymin)

        # Yield all values between 0 and max
        yield from liftby.buidsByRange(self.FloatPackPosMin, pkeymax)

class StorTypeGuid(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_GUID)
        self.lifters.update({
            '=': self._liftGuidEq,
        })

    def _liftGuidEq(self, liftby, valu):
        indx = s_common.uhex(valu)
        yield from liftby.buidsByDups(indx)

    def indx(self, valu):
        return (s_common.uhex(valu),)

class StorTypeTime(StorTypeInt):

    def __init__(self, layr):
        StorTypeInt.__init__(self, layr, STOR_TYPE_TIME, 8, True)
        self.lifters.update({
            '@=': self._liftAtIval,
        })

    def _liftAtIval(self, liftby, valu):
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

    def _liftIvalEq(self, liftby, valu):
        indx = self.timetype.getIntIndx(valu[0]) + self.timetype.getIntIndx(valu[1])
        yield from liftby.buidsByDups(indx)

    def _liftIvalAt(self, liftby, valu):

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

class StorTypeMsgp(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_MSGP)
        self.lifters.update({
            '=': self._liftMsgpEq,
        })

    def _liftMsgpEq(self, liftby, valu):
        indx = s_common.buid(valu)
        yield from liftby.buidsByDups(indx)

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

    def _liftLatLonEq(self, liftby, valu):
        indx = self._getLatLonIndx(valu)
        yield from liftby.buidsByDups(indx)

    def _liftLatLonNear(self, liftby, valu):

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

class Layer(s_nexus.Pusher):
    '''
    The base class for a cortex layer.
    '''
    def __repr__(self):
        return f'Layer ({self.__class__.__name__}): {self.iden}'

    async def __anit__(self, layrinfo, dirn, nexsroot=None, allow_upstream=True):

        self.nexsroot = nexsroot
        self.layrinfo = layrinfo
        self.allow_upstream = allow_upstream

        self.iden = layrinfo.get('iden')
        await s_nexus.Pusher.__anit__(self, self.iden, nexsroot=nexsroot)

        self.dirn = dirn
        self.readonly = layrinfo.get('readonly')

        self.lockmemory = self.layrinfo.get('lockmemory')
        self.growsize = self.layrinfo.get('growsize')
        self.logedits = self.layrinfo.get('logedits')

        path = s_common.genpath(self.dirn, 'layer_v2.lmdb')

        self.fresh = not os.path.exists(path)

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
        ]

        self.canrev = True
        self.ctorname = f'{self.__class__.__module__}.{self.__class__.__name__}'

        self.windows = []
        self.upstreamwaits = collections.defaultdict(lambda: collections.defaultdict(list))

        uplayr = layrinfo.get('upstream')
        if uplayr is not None and allow_upstream:
            if isinstance(uplayr, (tuple, list)):
                for layr in uplayr:
                    await self.initUpstreamSync(layr)
            else:
                await self.initUpstreamSync(uplayr)

        self.onfini(self._onLayrFini)

    def pack(self):
        return self.layrinfo.pack()

    async def truncate(self):

        await self.layrslab.trash()
        await self.nodeeditslab.trash()
        await self.dataslab.trash()

        await self._initLayerStorage()

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

        self.bybuid = self.layrslab.initdb('bybuid')

        self.bytag = self.layrslab.initdb('bytag', dupsort=True)
        self.byprop = self.layrslab.initdb('byprop', dupsort=True)
        self.byarray = self.layrslab.initdb('byarray', dupsort=True)
        self.bytagprop = self.layrslab.initdb('bytagprop', dupsort=True)

        self.countdb = self.layrslab.initdb('counters')
        self.nodedata = self.dataslab.initdb('nodedata')
        self.dataname = self.dataslab.initdb('dataname', dupsort=True)

        if self.logedits:
            self.nodeeditlog = s_slabseqn.SlabSeqn(self.nodeeditslab, 'nodeedits')

    def getSpawnInfo(self):
        info = self.pack()
        info['dirn'] = self.dirn
        info['ctor'] = self.ctorname
        return info

    @s_nexus.Pusher.onPushAuto('layer:set')
    async def setLayerInfo(self, name, valu):
        '''
        Set a mutable layer property.
        '''
        if name not in ('name',):
            mesg = f'{name} is not a valid layer info key'
            raise s_exc.BadOptValu(mesg=mesg)
        #TODO when we can set more props, we may need to parse values.
        await self.layrinfo.set(name, valu)
        return valu

    async def stat(self):
        return {
            'nodeeditlog_indx': (self.nodeeditlog.index(), 0, 0),
            **self.layrslab.statinfo()
        }

    async def _onLayrFini(self):
        [(await wind.fini()) for wind in self.windows]

    async def getFormCounts(self):
        return self.formcounts.pack()

    @s_cache.memoize(size=10000)
    def getPropAbrv(self, form, prop):
        return self.propabrv.bytsToAbrv(s_msgpack.en((form, prop)))

    @s_cache.memoize(size=10000)
    def getTagPropAbrv(self, *args):
        return self.tagpropabrv.bytsToAbrv(s_msgpack.en(args))

    def getAbrvProp(self, abrv):
        byts = self.propabrv.abrvToByts(abrv)
        if byts is None:
            return None
        return s_msgpack.un(byts)

    def getNodeValu(self, buid, prop=None):
        '''
        Retrieve either the form valu or a prop valu for the given node by buid.
        '''
        if prop is None:

            byts = self.layrslab.get(buid + b'\x00', db=self.bybuid)
            if byts is None:
                return None

            form, valu, stortype = s_msgpack.un(byts)
            return valu

        byts = self.layrslab.get(buid + b'\x01' + prop.encode(), db=self.bybuid)
        if byts is None:
            return None

        valu, stortype = s_msgpack.un(byts)
        return valu

    def getNodeTag(self, buid, tag):
        tenc = tag.encode()
        byts = self.layrslab.get(buid + b'\x02' + tenc, db=self.bybuid)
        if byts is None:
            return None
        return s_msgpack.un(byts)

    async def getStorNode(self, buid):
        '''
        Return a potentially incomplete pode.
        '''
        ndef = None

        tags = {}
        props = {}
        tagprops = {}

        for lkey, lval in self.layrslab.scanByPref(buid, db=self.bybuid):

            flag = lkey[32]

            if flag == 0:
                form, valu, stortype = s_msgpack.un(lval)
                ndef = (form, valu)
                continue

            if flag == 1:
                name = lkey[33:].decode()
                valu, stortype = s_msgpack.un(lval)
                props[name] = valu
                continue

            if flag == 2:
                name = lkey[33:].decode()
                tags[name] = s_msgpack.un(lval)
                continue

            if flag == 3:
                tag, prop = lkey[33:].decode().split(':')
                valu, stortype = s_msgpack.un(lval)
                tagprops[(tag, prop)] = valu
                continue

            logger.warning(f'unrecognized storage row: {flag}')

        info = {}

        if ndef:
            info['ndef'] = ndef

        if props:
            info['props'] = props

        if tags:
            info['tags'] = tags

        if tagprops:
            info['tagprops'] = tagprops

        return (buid, info)

    async def liftByTag(self, tag, form=None):

        abrv = self.tagabrv.bytsToAbrv(tag.encode())
        if form is not None:
            abrv += self.getPropAbrv(form, None)

        for _, buid in self.layrslab.scanByPref(abrv, db=self.bytag):
            yield await self.getStorNode(buid)

    async def liftByTagValu(self, tag, cmpr, valu, form=None):

        abrv = self.tagabrv.bytsToAbrv(tag.encode())
        if form is not None:
            abrv += self.getPropAbrv(form, None)

        filt = StorTypeTag.getTagFilt(cmpr, valu)
        if filt is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr)

        for _, buid in self.layrslab.scanByPref(abrv, db=self.bytag):
            # filter based on the ival value before lifting the node...
            valu = self.getNodeTag(buid, tag)
            if filt(valu):
                yield await self.getStorNode(buid)

    async def hasTagProp(self, name):
        async for _ in self.liftTagProp(name):
            return True

        return False

    async def liftTagProp(self, name):

        async for _, tag in self.iterFormRows('syn:tag'):
            abrv = self.getTagPropAbrv(None, tag, name)
            for _, buid in self.layrslab.scanByPref(abrv, db=self.bytagprop):
                yield buid

    async def liftByTagProp(self, form, tag, prop):
        abrv = self.getTagPropAbrv(form, tag, prop)
        for _, buid in self.layrslab.scanByPref(abrv, db=self.bytagprop):
            yield await self.getStorNode(buid)

    async def liftByTagPropValu(self, form, tag, prop, cmprvals):
        for cmpr, valu, kind in cmprvals:
            for buid in self.stortypes[kind].indxByTagProp(form, tag, prop, cmpr, valu):
                yield await self.getStorNode(buid)

    async def liftByProp(self, form, prop):
        abrv = self.getPropAbrv(form, prop)
        for _, buid in self.layrslab.scanByPref(abrv, db=self.byprop):
            yield await self.getStorNode(buid)

    # NOTE: form vs prop valu lifting is differentiated to allow merge sort
    async def liftByFormValu(self, form, cmprvals):
        for cmpr, valu, kind in cmprvals:
            for buid in self.stortypes[kind].indxByForm(form, cmpr, valu):
                yield await self.getStorNode(buid)

    async def liftByPropValu(self, form, prop, cmprvals):
        for cmpr, valu, kind in cmprvals:
            if kind & 0x8000:
                kind = STOR_TYPE_MSGP
            for buid in self.stortypes[kind].indxByProp(form, prop, cmpr, valu):
                yield await self.getStorNode(buid)

    async def liftByPropArray(self, form, prop, cmprvals):
        for cmpr, valu, kind in cmprvals:
            for buid in self.stortypes[kind].indxByPropArray(form, prop, cmpr, valu):
                yield await self.getStorNode(buid)

    async def liftByDataName(self, name):

        abrv = self.getPropAbrv(name, None)
        for abrv, buid in self.dataslab.scanByDups(abrv, db=self.dataname):

            sode = await self.getStorNode(buid)

            byts = self.dataslab.get(buid + abrv, db=self.nodedata)
            if byts is not None:
                item = s_msgpack.un(byts)
                sode[1]['nodedata'] = {name: item}

            yield sode

    async def storNodeEdits(self, nodeedits, meta):

        results = await self._push('edits', nodeedits, meta)

        retn = []
        for buid, form, edits in results:
            sode = await self.getStorNode(buid)
            sode[1]['edits'] = edits
            sode[1]['form'] = form
            retn.append(sode)

        return retn

    @s_nexus.Pusher.onPush('edits')
    async def _storNodeEdits(self, nodeedits, meta):
        '''
        Execute a series of node edit operations, returning the updated nodes.

        Args:
            nodeedits:  List[Tuple(buid, form, edits)]  List of requested changes per node

        Returns:
            List[Tuple[buid, form, edits]]  Same list, but with only the edits actually applied (plus the old value)
        '''
        results = [(e[0], e[1], await self._storNodeEdit(e)) for e in nodeedits]

        if self.logedits:
            changes = [r for r in results if r[2]]
            if changes:
                offs = self.nodeeditlog.add((changes, meta))
                [(await wind.put((offs, changes))) for wind in tuple(self.windows)]

        return results

    async def _storNodeEdit(self, nodeedit):
        '''
        Execute a series of storage operations for the given node.

        Args:
            nodeedit

        Returns a (buid, form, edits) tuple.  edits contains the actual changes.
        '''
        buid, form, edits = nodeedit

        changed = []
        for edit in edits:
            items = self.editors[edit[0]](buid, form, edit)
            if items is not None:
                changed.extend(items)

        await asyncio.sleep(0)
        return changed

    async def storNodeEditsNoLift(self, nodeedits, meta):
        '''
        Execute a series of node edit operations.

        Does not return the updated nodes.
        '''
        await self._push('edits', nodeedits, meta)

    def _editNodeAdd(self, buid, form, edit):

        valu, stortype = edit[1]

        byts = s_msgpack.en((form, valu, stortype))
        if not self.layrslab.put(buid + b'\x00', byts, db=self.bybuid, overwrite=False):
            return None

        abrv = self.getPropAbrv(form, None)

        if stortype & STOR_FLAG_ARRAY:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byarray)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byprop)

        self.formcounts.inc(form)

        created = (EDIT_PROP_SET, ('.created', s_common.now(), None, STOR_TYPE_MINTIME))

        retn = [(EDIT_NODE_ADD, (valu, stortype))]

        retn.extend(self._editPropSet(buid, form, created))

        return retn

    def _editNodeDel(self, buid, form, edit):

        byts = self.layrslab.pop(buid + b'\x00', db=self.bybuid)
        if byts is None:
            return None

        form, valu, stortype = s_msgpack.un(byts)

        abrv = self.getPropAbrv(form, None)

        if stortype & STOR_FLAG_ARRAY:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byarray)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)

        self.formcounts.inc(form, valu=-1)

        self._wipeNodeData(buid)

        return (
            (EDIT_NODE_DEL, (valu, stortype)),
        )

    def _editPropSet(self, buid, form, edit):

        prop, valu, oldv, stortype = edit[1]

        oldv = None
        penc = prop.encode()
        bkey = buid + b'\x01' + penc

        abrv = self.getPropAbrv(form, prop)
        univabrv = None

        if penc[0] == 46: # '.' to detect universal props (as quickly as possible)
            univabrv = self.getPropAbrv(None, prop)

        # merge interval values
        if stortype == STOR_TYPE_IVAL:
            oldb = self.layrslab.get(bkey, db=self.bybuid)
            if oldb is not None:
                oldv, oldt = s_msgpack.un(oldb)
                valu = (min(*oldv, *valu), max(*oldv, *valu))
                if valu == oldv:
                    return ()

        newb = s_msgpack.en((valu, stortype))
        oldb = self.layrslab.replace(bkey, newb, db=self.bybuid)

        if newb == oldb:
            return ()

        if oldb is not None:

            oldv, oldt = s_msgpack.un(oldb)

            if stortype == STOR_TYPE_MINTIME and oldv < valu:
                self.layrslab.put(bkey, oldb, db=self.bybuid)
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
            (EDIT_PROP_SET, (prop, valu, oldv, stortype)),
        )

    def _editPropDel(self, buid, form, edit):

        prop, oldv, stortype = edit[1]

        penc = prop.encode()
        bkey = buid + b'\x01' + penc

        abrv = self.getPropAbrv(form, prop)
        univabrv = None

        if penc[0] == 46: # '.' to detect universal props (as quickly as possible)
            univabrv = self.getPropAbrv(None, prop)

        byts = self.layrslab.pop(bkey, db=self.bybuid)
        if byts is None:
            return None

        valu, stortype = s_msgpack.un(byts)

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

        return (
            (EDIT_PROP_DEL, (prop, valu, stortype)),
        )

    def _editTagSet(self, buid, form, edit):

        tag, valu, oldv = edit[1]

        tenc = tag.encode()
        tagabrv = self.tagabrv.bytsToAbrv(tenc)
        formabrv = self.getPropAbrv(form, None)

        oldb = self.layrslab.replace(buid + b'\x02' + tenc, s_msgpack.en(valu), db=self.bybuid)

        if oldb is not None:

            oldv = s_msgpack.un(oldb)

            if oldv != (None, None) and valu != (None, None):

                merged = (min(oldv[0], valu[0]), max(oldv[1], valu[1]))

                if merged != valu:
                    self.layrslab.put(buid + b'\x02' + tenc, s_msgpack.en(merged), db=self.bybuid)
                    valu = merged

            if oldv == valu:
                return ()

        self.layrslab.put(tagabrv + formabrv, buid, db=self.bytag)

        return (
            (EDIT_TAG_SET, (tag, valu, oldv)),
        )

    def _editTagDel(self, buid, form, edit):

        tag, oldv = edit[1]

        tenc = tag.encode()

        tagabrv = self.tagabrv.bytsToAbrv(tenc)
        formabrv = self.getPropAbrv(form, None)

        oldb = self.layrslab.pop(buid + b'\x02' + tenc, db=self.bybuid)
        if oldb is None:
            return ()

        self.layrslab.delete(tagabrv + formabrv, buid, db=self.bytag)

        oldv = s_msgpack.un(oldb)

        return (
            (EDIT_TAG_DEL, (tag, oldv)),
        )

    def _editTagPropSet(self, buid, form, edit):

        tag, prop, valu, oldv, stortype = edit[1]

        tenc = tag.encode()
        penc = prop.encode()

        tp_abrv = self.getTagPropAbrv(None, tag, prop)
        ftp_abrv = self.getTagPropAbrv(form, tag, prop)

        bkey = buid + b'\x03' + tenc + b':' + penc

        oldb = self.layrslab.replace(bkey, s_msgpack.en((valu, stortype)), db=self.bybuid)
        if oldb is not None:

            oldv, oldt = s_msgpack.un(oldb)
            if valu == oldv and stortype == oldt:
                return

            for oldi in self.getStorIndx(oldt, oldv):
                self.layrslab.delete(tp_abrv + oldi, buid, db=self.bytagprop)
                self.layrslab.delete(ftp_abrv + oldi, buid, db=self.bytagprop)

        kvpairs = []

        for indx in self.getStorIndx(stortype, valu):
            kvpairs.append((tp_abrv + indx, buid))
            kvpairs.append((ftp_abrv + indx, buid))

        self.layrslab.putmulti(kvpairs, db=self.bytagprop)

        return (
            (EDIT_TAGPROP_SET, (tag, prop, valu, oldv, stortype)),
        )

    def _editTagPropDel(self, buid, form, edit):

        tag, prop, valu, stortype = edit[1]

        tenc = tag.encode()
        penc = prop.encode()

        tp_abrv = self.getTagPropAbrv(None, tag, prop)
        ftp_abrv = self.getTagPropAbrv(form, tag, prop)

        bkey = buid + b'\x03' + tenc + b':' + penc

        oldb = self.layrslab.pop(bkey, db=self.bybuid)
        if oldb is None:
            return

        oldv, oldt = s_msgpack.un(oldb)

        for oldi in self.getStorIndx(oldt, oldv):
            self.layrslab.delete(tp_abrv + oldi, buid, db=self.bytagprop)
            self.layrslab.delete(ftp_abrv + oldi, buid, db=self.bytagprop)

        return (
            (EDIT_TAGPROP_DEL, (tag, prop, oldv, oldt)),
        )

    def _editNodeDataSet(self, buid, form, edit):

        name, valu, oldv = edit[1]
        abrv = self.getPropAbrv(name, None)

        oldb = self.dataslab.replace(buid + abrv, s_msgpack.en(valu), db=self.nodedata)

        if oldb is not None:
            oldv = s_msgpack.un(oldb)
            if oldv == valu:
                return None

        self.dataslab.put(abrv, buid, db=self.dataname)

        return (
            (EDIT_NODEDATA_SET, (name, valu, oldv)),
        )

    def _editNodeDataDel(self, buid, form, edit):

        name, valu = edit[1]
        abrv = self.getPropAbrv(name, None)

        oldb = self.dataslab.pop(buid + abrv, db=self.nodedata)
        if oldb is None:
            return None

        oldv = s_msgpack.un(oldb)
        self.dataslab.delete(abrv, buid, db=self.dataname)

        return (
            (EDIT_NODEDATA_DEL, (name, oldv)),
        )

    def getStorIndx(self, stortype, valu):

        if stortype & 0x8000:

            realtype = stortype & 0x7fff

            retn = []
            [retn.extend(self.getStorIndx(realtype, aval)) for aval in valu]
            return retn

        return self.stortypes[stortype].indx(valu)

    async def iterFormRows(self, form):

        abrv = self.getPropAbrv(form, None)

        for _, buid in self.layrslab.scanByPref(abrv, db=self.byprop):

            bkey = buid + b'\x00'
            byts = self.layrslab.get(bkey, db=self.bybuid)

            await asyncio.sleep(0)

            if byts is None:
                continue

            form, valu, stortype = s_msgpack.un(byts)
            yield buid, valu

    async def iterPropRows(self, form, prop):

        penc = prop.encode()

        abrv = self.getPropAbrv(form, prop)

        for _, buid in self.layrslab.scanByPref(abrv, db=self.byprop):
            bkey = buid + b'\x01' + penc
            byts = self.layrslab.get(bkey, db=self.bybuid)

            await asyncio.sleep(0)

            if byts is None:
                continue

            valu, stortype = s_msgpack.un(byts)
            yield buid, valu

    async def iterUnivRows(self, prop):

        penc = prop.encode()

        abrv = self.getPropAbrv(None, prop)

        for _, buid in self.layrslab.scanByPref(abrv, db=self.byprop):
            bkey = buid + b'\x01' + penc
            byts = self.layrslab.get(bkey, db=self.bybuid)

            await asyncio.sleep(0)

            if byts is None:
                continue

            valu, stortype = s_msgpack.un(byts)
            yield buid, valu

    async def getNodeData(self, buid, name):
        '''
        Return a single element of a buid's node data
        '''
        abrv = self.getPropAbrv(name, None)

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
        nodeedits = (None, None, None)

        for lkey, lval in self.layrslab.scanByFull(db=self.bybuid):
            buid = lkey[:32]
            flag = lkey[32]

            if not buid == nodeedits[0]:
                if nodeedits[0] is not None:
                    async for prop, valu in self.iterNodeData(nodeedits[0]):
                        edit = (EDIT_NODEDATA_SET, (prop, valu, None))
                        nodeedits[2].append(edit)

                    yield nodeedits

            if flag == 0:
                form, valu, stortype = s_msgpack.un(lval)

                nodeedits = (buid, form, [])

                edit = (EDIT_NODE_ADD, (valu, stortype))
                nodeedits[2].append(edit)
                continue

            if flag == 1:
                if not nodeedits[0] == buid:
                    continue

                name = lkey[33:].decode()
                valu, stortype = s_msgpack.un(lval)

                edit = (EDIT_PROP_SET, (name, valu, None, stortype))
                nodeedits[2].append(edit)
                continue

            if flag == 2:
                if not nodeedits[0] == buid:
                    continue

                name = lkey[33:].decode()
                tagv = s_msgpack.un(lval)

                edit = (EDIT_TAG_SET, (name, tagv, None))
                nodeedits[2].append(edit)
                continue

            if flag == 3:
                if not nodeedits[0] == buid:
                    continue

                tag, prop = lkey[33:].decode().split(':')
                valu, stortype = s_msgpack.un(lval)

                buid = lkey[:32]

                edit = (EDIT_TAGPROP_SET, (tag, prop, valu, None, stortype))
                nodeedits[2].append(edit)
                continue

            logger.warning(f'unrecognized storage row: {flag}')

        if nodeedits[0] is not None:
            async for prop, valu in self.iterNodeData(nodeedits[0]):
                edit = (EDIT_NODEDATA_SET, (prop, valu, None))
                nodeedits[2].append(edit)

            yield nodeedits

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
                    logger.warning(f'upstream sync connected ({url} offset={offs})')

                    if offs == 0:
                        offs = await proxy.getNodeEditOffset()
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
            for offset, (nodeedits, meta) in self.nodeeditlog.iter(offs[0]):
                for splice in self.makeSplices(offset, nodeedits, meta):

                    if splice[0] < offs:
                        continue

                    if count >= size:
                        return

                    yield splice
                    count = count + 1
        else:
            for offset, (nodeedits, meta) in self.nodeeditlog.iter(offs[0]):
                for splice in self.makeSplices(offset, nodeedits, meta):

                    if splice[0] < offs:
                        continue

                    yield splice

    async def splicesBack(self, offs=None, size=None):

        if not self.logedits:
            return

        if offs is None:
            offs = (self.nodeeditlog.index(), 0, 0)

        if size is not None:

            count = 0
            for offset, (nodeedits, meta) in self.nodeeditlog.iterBack(offs[0]):
                for splice in self.makeSplices(offset, nodeedits, meta, reverse=True):

                    if splice[0] > offs:
                        continue

                    if count >= size:
                        return

                    yield splice
                    count += 1
        else:
            for offset, (nodeedits, meta) in self.nodeeditlog.iterBack(offs[0]):
                for splice in self.makeSplices(offset, nodeedits, meta, reverse=True):

                    if splice[0] > offs:
                        continue

                    yield splice

    async def syncNodeEdits(self, offs):
        '''
        Yield (offs, nodeedits) tuples from the nodeedit log starting from the given offset.

        Once caught up with storage, yield them in realtime.
        '''
        if not self.logedits:
            return

        for offs, splice in self.nodeeditlog.iter(offs):
            yield (offs, splice[0])

        async with self.getNodeEditWindow() as wind:
            async for offs, splice in wind:
                yield (offs, splice)

    def makeSplices(self, offs, nodeedits, meta, reverse=False):
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

            for editoffs, (edit, info) in editgenr:

                if edit == EDIT_NODEDATA_SET or edit == EDIT_NODEDATA_DEL:
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
                    formvalu = self.getNodeValu(buid)

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

    def getNodeEditOffset(self):
        if not self.logedits:
            return 0

        return self.nodeeditlog.index()

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
        await self.fini()
        shutil.rmtree(self.dirn, ignore_errors=True)
