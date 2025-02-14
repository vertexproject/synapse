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
import contextlib
import collections

import regex
import xxhash

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.gis as s_gis
import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.nexus as s_nexus
import synapse.lib.queue as s_queue
import synapse.lib.urlhelp as s_urlhelp

import synapse.lib.config as s_config
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn

from synapse.lib.msgpack import deepcopy

ipaddress = s_common.ipaddress

logger = logging.getLogger(__name__)

import synapse.lib.msgpack as s_msgpack

reqValidLdef = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
        'lockmemory': {'type': 'boolean'},
        'lmdb:growsize': {'type': 'integer'},
        'logedits': {'type': 'boolean', 'default': True},
        'name': {'type': 'string'},
        'readonly': {'type': 'boolean', 'default': False},
    },
    'additionalProperties': True,
    'required': ['iden', 'creator', 'lockmemory'],
})

WINDOW_MAXSIZE = 10_000
MIGR_COMMIT_SIZE = 1_000

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
            await asyncio.sleep(0)

    @s_cell.adminapi()
    async def saveNodeEdits(self, edits, meta):
        '''
        Save node edits to the layer and return a tuple of (nexsoffs, changes).

        Note: nexsoffs will be None if there are no changes.
        '''
        meta['link:user'] = self.user.iden
        return await self.layr.saveNodeEdits(edits, meta)

    async def storNodeEdits(self, nodeedits, meta=None):

        await self._reqUserAllowed(self.writeperm)

        if meta is None:
            meta = {'time': s_common.now(), 'user': self.user.iden}

        return await self.layr.storNodeEdits(nodeedits, meta)

    async def storNodeEditsNoLift(self, nodeedits, meta=None):

        await self._reqUserAllowed(self.writeperm)

        if meta is None:
            meta = {'time': s_common.now(), 'user': self.user.iden}

        await self.layr.storNodeEditsNoLift(nodeedits, meta)

    async def syncNodeEdits(self, offs, wait=True, reverse=False):
        '''
        Yield (offs, nodeedits) tuples from the nodeedit log starting from the given offset.

        Once caught up with storage, yield them in realtime.
        '''
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.syncNodeEdits(offs, wait=wait, reverse=reverse):
            yield item
            await asyncio.sleep(0)

    async def syncNodeEdits2(self, offs, wait=True):
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.syncNodeEdits2(offs, wait=wait):
            yield item
            await asyncio.sleep(0)

    async def getEditIndx(self):
        '''
        Returns what will be the *next* nodeedit log index.
        '''
        await self._reqUserAllowed(self.liftperm)
        return await self.layr.getEditIndx()

    async def getEditSize(self):
        '''
        Return the total number of (edits, meta) pairs in the layer changelog.
        '''
        await self._reqUserAllowed(self.liftperm)
        return await self.layr.getEditSize()

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

STOR_TYPE_MAXTIME = 24
STOR_TYPE_NDEF = 25

# STOR_TYPE_TOMB      = ??
# STOR_TYPE_FIXED     = ??

STOR_FLAG_ARRAY = 0x8000

# Edit types (etyp)

EDIT_NODE_ADD = 0      # (<etyp>, (<valu>, <type>), ())
EDIT_NODE_DEL = 1      # (<etyp>, (<oldv>, <type>), ())
EDIT_PROP_SET = 2      # (<etyp>, (<prop>, <valu>, <oldv>, <type>), ())
EDIT_PROP_DEL = 3      # (<etyp>, (<prop>, <oldv>, <type>), ())
EDIT_TAG_SET = 4       # (<etyp>, (<tag>, <valu>, <oldv>), ())
EDIT_TAG_DEL = 5       # (<etyp>, (<tag>, <oldv>), ())
EDIT_TAGPROP_SET = 6   # (<etyp>, (<tag>, <prop>, <valu>, <oldv>, <type>), ())
EDIT_TAGPROP_DEL = 7   # (<etyp>, (<tag>, <prop>, <oldv>, <type>), ())
EDIT_NODEDATA_SET = 8  # (<etyp>, (<name>, <valu>, <oldv>), ())
EDIT_NODEDATA_DEL = 9  # (<etyp>, (<name>, <oldv>), ())
EDIT_EDGE_ADD = 10     # (<etyp>, (<verb>, <destnodeiden>), ())
EDIT_EDGE_DEL = 11     # (<etyp>, (<verb>, <destnodeiden>), ())

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

    def keyBuidsByDups(self, indx):
        yield from self.layr.layrslab.scanByDups(self.abrv + indx, db=self.db)

    def keyBuidsByDupsBack(self, indx):
        yield from self.layr.layrslab.scanByDupsBack(self.abrv + indx, db=self.db)

    def buidsByDups(self, indx):
        for _, buid in self.layr.layrslab.scanByDups(self.abrv + indx, db=self.db):
            yield buid

    def keyBuidsByPref(self, indx=b''):
        yield from self.layr.layrslab.scanByPref(self.abrv + indx, db=self.db)

    def keyBuidsByPrefBack(self, indx=b''):
        yield from self.layr.layrslab.scanByPrefBack(self.abrv + indx, db=self.db)

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

    def scanByPrefBack(self, indx=b''):
        for item in self.layr.layrslab.scanByPrefBack(self.abrv + indx, db=self.db):
            yield item

    def scanByRange(self, minindx, maxindx):
        for item in self.layr.layrslab.scanByRange(self.abrv + minindx, self.abrv + maxindx, db=self.db):
            yield item

    def scanByRangeBack(self, minindx, maxindx):
        for item in self.layr.layrslab.scanByRangeBack(self.abrv + maxindx, lmin=self.abrv + minindx, db=self.db):
            yield item

    def hasIndxBuid(self, indx, buid):
        return self.layr.layrslab.hasdup(self.abrv + indx, buid, db=self.db)

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
        if sode is None: # pragma: no cover
            return None

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
        if sode is None: # pragma: no cover
            return None

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
        if sode is None: # pragma: no cover
            return None
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
        if sode is None: # pragma: no cover
            return None
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

    def getNodeValu(self, buid):
        sode = self.layr._getStorNode(buid)
        if sode is None: # pragma: no cover
            return None
        props = sode['tagprops'].get(self.tag)
        if not props:
            return

        valu = props.get(self.prop)
        if valu is not None:
            return valu[0]

class StorType:

    def __init__(self, layr, stortype):
        self.layr = layr
        self.stortype = stortype

        self.lifters = {}

    async def indxBy(self, liftby, cmpr, valu, reverse=False):
        func = self.lifters.get(cmpr)
        if func is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr)

        async for item in func(liftby, valu, reverse=reverse):
            yield item

    async def indxByForm(self, form, cmpr, valu, reverse=False):
        try:
            indxby = IndxByForm(self.layr, form)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def verifyBuidProp(self, buid, form, prop, valu):
        indxby = IndxByProp(self.layr, form, prop)
        for indx in self.indx(valu):
            if not indxby.hasIndxBuid(indx, buid):
                yield ('NoPropIndex', {'prop': prop, 'valu': valu})

    async def indxByProp(self, form, prop, cmpr, valu, reverse=False):
        try:
            indxby = IndxByProp(self.layr, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByPropArray(self, form, prop, cmpr, valu, reverse=False):
        try:
            indxby = IndxByPropArray(self.layr, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByTagProp(self, form, tag, prop, cmpr, valu, reverse=False):
        try:
            indxby = IndxByTagProp(self.layr, form, tag, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    def indx(self, valu):  # pragma: no cover
        raise NotImplementedError

    def decodeIndx(self, valu):  # pragma: no cover
        return s_common.novalu

    async def _liftRegx(self, liftby, valu, reverse=False):

        regx = regex.compile(valu, flags=regex.I)

        abrvlen = liftby.abrvlen
        isarray = isinstance(liftby, IndxByPropArray)

        if reverse:
            scan = liftby.keyBuidsByPrefBack
        else:
            scan = liftby.keyBuidsByPref

        for lkey, buid in scan():

            await asyncio.sleep(0)

            indx = lkey[abrvlen:]
            storvalu = self.decodeIndx(indx)

            if storvalu == s_common.novalu:

                storvalu = liftby.getNodeValu(buid)

                if isarray:
                    for sval in storvalu:
                        if self.indx(sval)[0] == indx:
                            storvalu = sval
                            break
                    else:
                        continue

            def regexin(regx, storvalu):
                if isinstance(storvalu, str):
                    if regx.search(storvalu) is not None:
                        return True

                elif isinstance(storvalu, (tuple, list)):
                    return any(regexin(regx, sv) for sv in storvalu)

                return False

            if regexin(regx, storvalu):
                yield lkey, buid

class StorTypeUtf8(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_UTF8)

        self.lifters.update({
            '=': self._liftUtf8Eq,
            '~=': self._liftRegx,
            '^=': self._liftUtf8Prefix,
            'range=': self._liftUtf8Range,
        })

    async def _liftUtf8Eq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        indx = self._getIndxByts(valu)
        for item in scan(indx):
            yield item

    async def _liftUtf8Range(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        minindx = self._getIndxByts(valu[0])
        maxindx = self._getIndxByts(valu[1])
        for item in scan(minindx, maxindx):
            yield item

    async def _liftUtf8Prefix(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByPrefBack
        else:
            scan = liftby.keyBuidsByPref

        indx = self._getIndxByts(valu)
        for item in scan(indx):
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

    async def _liftHierEq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        indx = self.getHierIndx(valu)
        for item in scan(indx):
            yield item

    async def _liftHierPref(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByPrefBack
        else:
            scan = liftby.keyBuidsByPref

        indx = self.getHierIndx(valu)
        for item in scan(indx):
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

    def decodeIndx(self, bytz):
        if len(bytz) >= 256:
            return s_common.novalu
        return bytz.decode('utf8', 'surrogatepass')[::-1]

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_UTF8)
        self.lifters.update({
            '=': self._liftFqdnEq,
            '~=': self._liftRegx,
        })

    async def _liftFqdnEq(self, liftby, valu, reverse=False):

        if valu[0] == '*':
            if reverse:
                scan = liftby.keyBuidsByPrefBack
            else:
                scan = liftby.keyBuidsByPref

            indx = self._getIndxByts(valu[1:][::-1])
            for item in scan(indx):
                yield item
            return

        async for item in StorTypeUtf8._liftUtf8Eq(self, liftby, valu[::-1], reverse=reverse):
            yield item

class StorTypeIpv6(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IPV6)

        self.lifters.update({
            '=': self._liftIPv6Eq,
            'range=': self._liftIPv6Range,
            '<': self._liftIPv6Lt,
            '>': self._liftIPv6Gt,
            '<=': self._liftIPv6Le,
            '>=': self._liftIPv6Ge,
        })

    def getIPv6Indx(self, valu):
        return ipaddress.IPv6Address(valu).packed

    def indx(self, valu):
        return (
            self.getIPv6Indx(valu),
        )

    def decodeIndx(self, bytz):
        return str(ipaddress.IPv6Address(bytz))

    async def _liftIPv6Eq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        indx = self.getIPv6Indx(valu)
        for item in scan(indx):
            yield item

    async def _liftIPv6Range(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        minindx = self.getIPv6Indx(valu[0])
        maxindx = self.getIPv6Indx(valu[1])
        for item in scan(minindx, maxindx):
            yield item

    async def _liftIPv6Lt(self, liftby, norm, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        minindx = self.getIPv6Indx('::')
        maxindx = self.getIPv6Indx(norm)
        maxindx = (int.from_bytes(maxindx) - 1).to_bytes(16)
        for item in scan(minindx, maxindx):
            yield item

    async def _liftIPv6Gt(self, liftby, norm, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        minindx = self.getIPv6Indx(norm)
        minindx = (int.from_bytes(minindx) + 1).to_bytes(16)
        maxindx = self.getIPv6Indx('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')

        for item in scan(minindx, maxindx):
            yield item

    async def _liftIPv6Le(self, liftby, norm, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        minindx = self.getIPv6Indx('::')
        maxindx = self.getIPv6Indx(norm)

        for item in scan(minindx, maxindx):
            yield item

    async def _liftIPv6Ge(self, liftby, norm, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        minindx = self.getIPv6Indx(norm)
        maxindx = self.getIPv6Indx('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')

        for item in scan(minindx, maxindx):
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

    async def _liftIntEq(self, liftby, valu, reverse=False):
        indx = valu + self.offset
        if indx < 0 or indx > self.maxval:
            return

        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        pkey = indx.to_bytes(self.size, 'big')
        for item in scan(pkey):
            yield item

    async def _liftIntGt(self, liftby, valu, reverse=False):
        async for item in self._liftIntGe(liftby, valu + 1, reverse=reverse):
            yield item

    async def _liftIntGe(self, liftby, valu, reverse=False):
        minv = valu + self.offset
        if minv > self.maxval:
            return

        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        minv = max(minv, 0)

        pkeymin = minv.to_bytes(self.size, 'big')
        pkeymax = self.fullbyts
        for item in scan(pkeymin, pkeymax):
            yield item

    async def _liftIntLt(self, liftby, valu, reverse=False):
        async for item in self._liftIntLe(liftby, valu - 1, reverse=reverse):
            yield item

    async def _liftIntLe(self, liftby, valu, reverse=False):
        maxv = valu + self.offset
        if maxv < 0:
            return

        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        maxv = min(maxv, self.maxval)

        pkeymin = self.zerobyts
        pkeymax = maxv.to_bytes(self.size, 'big')
        for item in scan(pkeymin, pkeymax):
            yield item

    async def _liftIntRange(self, liftby, valu, reverse=False):
        minv = valu[0] + self.offset
        maxv = valu[1] + self.offset
        if minv > self.maxval or maxv < 0:
            return

        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        minv = max(minv, 0)
        maxv = min(maxv, self.maxval)

        pkeymin = minv.to_bytes(self.size, 'big')
        pkeymax = maxv.to_bytes(self.size, 'big')
        for item in scan(pkeymin, pkeymax):
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

        self.one = s_common.hugeexp
        self.offset = s_common.hugenum(0x7fffffffffffffffffffffffffffffffffffffff)

        self.zerobyts = b'\x00' * 20
        self.fullbyts = b'\xff' * 20

    def getHugeIndx(self, norm):
        scaled = s_common.hugescaleb(s_common.hugenum(norm), 24)
        byts = int(s_common.hugeadd(scaled, self.offset)).to_bytes(20, byteorder='big')
        return byts

    def indx(self, norm):
        return (self.getHugeIndx(norm),)

    def decodeIndx(self, bytz):
        huge = s_common.hugenum(int.from_bytes(bytz, 'big'))
        valu = s_common.hugescaleb(s_common.hugesub(huge, self.offset), -24)
        return '{:f}'.format(valu.normalize(s_common.hugectx))

    async def _liftHugeEq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        byts = self.getHugeIndx(valu)
        for item in scan(byts):
            yield item

    async def _liftHugeGt(self, liftby, valu, reverse=False):
        valu = s_common.hugenum(valu)
        async for item in self._liftHugeGe(liftby, s_common.hugeadd(valu, self.one), reverse=reverse):
            yield item

    async def _liftHugeLt(self, liftby, valu, reverse=False):
        valu = s_common.hugenum(valu)
        async for item in self._liftHugeLe(liftby, s_common.hugesub(valu, self.one), reverse=reverse):
            yield item

    async def _liftHugeGe(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        pkeymin = self.getHugeIndx(valu)
        pkeymax = self.fullbyts
        for item in scan(pkeymin, pkeymax):
            yield item

    async def _liftHugeLe(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        pkeymin = self.zerobyts
        pkeymax = self.getHugeIndx(valu)
        for item in scan(pkeymin, pkeymax):
            yield item

    async def _liftHugeRange(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByRangeBack
        else:
            scan = liftby.keyBuidsByRange

        pkeymin = self.getHugeIndx(valu[0])
        pkeymax = self.getHugeIndx(valu[1])
        for item in scan(pkeymin, pkeymax):
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

    async def _liftFloatEq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        for item in scan(self.fpack(valu)):
            yield item

    async def _liftFloatGeCommon(self, liftby, valu, reverse=False):
        if math.isnan(valu):
            raise s_exc.NotANumberCompared()

        valupack = self.fpack(valu)

        if reverse:
            if math.copysign(1.0, valu) < 0.0:  # negative values and -0.0
                for item in liftby.keyBuidsByRangeBack(self.FloatPackPosMin, self.FloatPackPosMax):
                    yield item
                for item in liftby.keyBuidsByRange(self.FloatPackNegMax, valupack):
                    yield item
            else:
                for item in liftby.keyBuidsByRangeBack(valupack, self.FloatPackPosMax):
                    yield item

        else:
            if math.copysign(1.0, valu) < 0.0:  # negative values and -0.0
                for item in liftby.keyBuidsByRangeBack(self.FloatPackNegMax, valupack):
                    yield item
                valupack = self.FloatPackPosMin

            for item in liftby.keyBuidsByRange(valupack, self.FloatPackPosMax):
                yield item

    async def _liftFloatGe(self, liftby, valu, reverse=False):
        async for item in self._liftFloatGeCommon(liftby, valu, reverse=reverse):
            yield item

    async def _liftFloatGt(self, liftby, valu, reverse=False):
        abrvlen = liftby.abrvlen
        valupack = self.fpack(valu)
        async for item in self._liftFloatGeCommon(liftby, valu, reverse=reverse):
            if item[0][abrvlen:] == valupack:
                continue
            yield item

    async def _liftFloatLeCommon(self, liftby, valu, reverse=False):
        if math.isnan(valu):
            raise s_exc.NotANumberCompared()

        valupack = self.fpack(valu)

        if reverse:
            if math.copysign(1.0, valu) > 0.0:
                for item in liftby.keyBuidsByRangeBack(self.FloatPackPosMin, valupack):
                    yield item
                valupack = self.FloatPackNegMax

            for item in liftby.keyBuidsByRange(valupack, self.FloatPackNegMin):
                yield item
        else:
            if math.copysign(1.0, valu) > 0.0:
                for item in liftby.keyBuidsByRangeBack(self.FloatPackNegMax, self.FloatPackNegMin):
                    yield item
                for item in liftby.keyBuidsByRange(self.FloatPackPosMin, valupack):
                    yield item
            else:
                for item in liftby.keyBuidsByRangeBack(valupack, self.FloatPackNegMin):
                    yield item

    async def _liftFloatLe(self, liftby, valu, reverse=False):
        async for item in self._liftFloatLeCommon(liftby, valu, reverse=reverse):
            yield item

    async def _liftFloatLt(self, liftby, valu, reverse=False):
        abrvlen = liftby.abrvlen
        valupack = self.fpack(valu)
        async for item in self._liftFloatLeCommon(liftby, valu, reverse=reverse):
            if item[0][abrvlen:] == valupack:
                continue
            yield item

    async def _liftFloatRange(self, liftby, valu, reverse=False):
        valumin, valumax = valu

        if math.isnan(valumin) or math.isnan(valumax):
            raise s_exc.NotANumberCompared()

        assert valumin <= valumax

        pkeymin, pkeymax = (self.fpack(v) for v in valu)

        if math.copysign(1.0, valumin) > 0.0:
            # Entire range is nonnegative
            if reverse:
                for item in liftby.keyBuidsByRangeBack(pkeymin, pkeymax):
                    yield item
            else:
                for item in liftby.keyBuidsByRange(pkeymin, pkeymax):
                    yield item
            return

        if math.copysign(1.0, valumax) < 0.0:  # negative values and -0.0
            # Entire range is negative
            if reverse:
                for item in liftby.keyBuidsByRange(pkeymax, pkeymin):
                    yield item
            else:
                for item in liftby.keyBuidsByRangeBack(pkeymax, pkeymin):
                    yield item
            return

        if reverse:
            # Yield all values between max and 0
            for item in liftby.keyBuidsByRangeBack(self.FloatPackPosMin, pkeymax):
                yield item

            # Yield all values between -0 and min
            for item in liftby.keyBuidsByRange(self.FloatPackNegMax, pkeymin):
                yield item

        else:
            # Yield all values between min and -0
            for item in liftby.keyBuidsByRangeBack(self.FloatPackNegMax, pkeymin):
                yield item

            # Yield all values between 0 and max
            for item in liftby.keyBuidsByRange(self.FloatPackPosMin, pkeymax):
                yield item

class StorTypeGuid(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_GUID)
        self.lifters.update({
            '=': self._liftGuidEq,
            '^=': self._liftGuidPref,
        })

    async def _liftGuidPref(self, liftby, byts, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByPrefBack
        else:
            scan = liftby.keyBuidsByPref

        # valu is already bytes of the guid prefix
        for item in scan(byts):
            yield item

    async def _liftGuidEq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        indx = s_common.uhex(valu)
        for item in scan(indx):
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

    async def _liftAtIval(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.scanByRangeBack
        else:
            scan = liftby.scanByRange

        minindx = self.getIntIndx(valu[0])
        maxindx = self.getIntIndx(valu[1] - 1)
        for item in scan(minindx, maxindx):
            yield item

class StorTypeIval(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IVAL)
        self.timetype = StorTypeTime(layr)
        self.lifters.update({
            '=': self._liftIvalEq,
            '@=': self._liftIvalAt,
        })

    async def _liftIvalEq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        indx = self.timetype.getIntIndx(valu[0]) + self.timetype.getIntIndx(valu[1])
        for item in scan(indx):
            yield item

    async def _liftIvalAt(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.scanByPrefBack
        else:
            scan = liftby.scanByPref

        minindx = self.timetype.getIntIndx(valu[0])
        maxindx = self.timetype.getIntIndx(valu[1])

        for lkey, buid in scan():

            tick = lkey[-16:-8]
            tock = lkey[-8:]

            # check for non-ovelap left and right
            if tick >= maxindx:
                continue

            if tock <= minindx:
                continue

            yield lkey, buid

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

    async def _liftMsgpEq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        indx = s_common.buid(valu)
        for item in scan(indx):
            yield item

    def indx(self, valu):
        return (s_common.buid(valu),)

class StorTypeNdef(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_NDEF)
        self.lifters.update({
            '=': self._liftNdefEq,
        })

    async def _liftNdefEq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        indx = s_common.buid(valu)
        for item in scan(indx):
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

    async def _liftLatLonEq(self, liftby, valu, reverse=False):
        if reverse:
            scan = liftby.keyBuidsByDupsBack
        else:
            scan = liftby.keyBuidsByDups

        indx = self._getLatLonIndx(valu)
        for item in scan(indx):
            yield item

    async def _liftLatLonNear(self, liftby, valu, reverse=False):

        (lat, lon), dist = valu

        # latscale = (lat * self.scale) + self.latspace
        # lonscale = (lon * self.scale) + self.lonspace

        latmin, latmax, lonmin, lonmax = s_gis.bbox(lat, lon, dist)

        lonminindx = (round(lonmin * self.scale) + self.lonspace).to_bytes(5, 'big')
        lonmaxindx = (round(lonmax * self.scale) + self.lonspace).to_bytes(5, 'big')

        latminindx = (round(latmin * self.scale) + self.latspace).to_bytes(5, 'big')
        latmaxindx = (round(latmax * self.scale) + self.latspace).to_bytes(5, 'big')

        if reverse:
            scan = liftby.scanByRangeBack
        else:
            scan = liftby.scanByRange

        # scan by lon range and down-select the results to matches.
        for lkey, buid in scan(lonminindx, lonmaxindx):

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
                yield lkey, buid

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

    async def __anit__(self, core, layrinfo):

        self.core = core
        self.layrinfo = layrinfo

        self.addoffs = None  # The nexus log index where I was created
        self.deloffs = None  # The nexus log index where I was deleted
        self.isdeleted = False

        self.iden = layrinfo.get('iden')
        await s_nexus.Pusher.__anit__(self, self.iden, nexsroot=core.nexsroot)

        self.dirn = s_common.gendir(core.dirn, 'layers', self.iden)
        self.readonly = False

        self.lockmemory = self.layrinfo.get('lockmemory')
        self.growsize = self.layrinfo.get('growsize')
        self.logedits = self.layrinfo.get('logedits')

        # slim hooks to avoid async/fire
        self.nodeAddHook = None
        self.nodeDelHook = None

        path = s_common.genpath(self.dirn, 'layer_v2.lmdb')

        self.fresh = not os.path.exists(path)

        self.dirty = {}
        self.futures = {}

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

            StorTypeTime(self),  # STOR_TYPE_MINTIME

            StorTypeFloat(self, STOR_TYPE_FLOAT64, 8),
            StorTypeHugeNum(self, STOR_TYPE_HUGENUM),

            StorTypeTime(self),  # STOR_TYPE_MAXTIME
            StorTypeNdef(self),
        ]

        await self._initLayerStorage()

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

        self.onfini(self._onLayrFini)

        # if we are a mirror, we upstream all our edits and
        # wait for them to make it back down the pipe...
        self.leader = None
        self.leadtask = None
        self.ismirror = layrinfo.get('mirror') is not None
        self.activetasks = []

        # this must be last!
        self.readonly = layrinfo.get('readonly')

    def _reqNotReadOnly(self):
        if self.readonly and not self.core.migration:
            mesg = f'Layer {self.iden} is read only!'
            raise s_exc.IsReadOnly(mesg=mesg)

    @contextlib.contextmanager
    def getIdenFutu(self, iden=None):

        if iden is None:
            iden = s_common.guid()

        futu = self.loop.create_future()
        self.futures[iden] = futu

        try:
            yield iden, futu
        finally:
            self.futures.pop(iden, None)

    async def getMirrorStatus(self):
        # TODO plumb back to upstream on not self.core.isactive
        retn = {'mirror': self.leader is not None}
        if self.leader:
            proxy = await self.leader.proxy()
            retn['local'] = {'size': await self.getEditSize()}
            retn['remote'] = {'size': await proxy.getEditSize()}
        return retn

    async def initLayerActive(self):

        if self.leadtask is not None:
            self.leadtask.cancel()

        mirror = self.layrinfo.get('mirror')
        if mirror is not None:
            s_common.deprecated('mirror layer configuration option', curv='2.162.0')
            conf = {'retrysleep': 2}
            self.leader = await s_telepath.Client.anit(mirror, conf=conf)
            self.leadtask = self.schedCoro(self._runMirrorLoop())

        uplayr = self.layrinfo.get('upstream')
        if uplayr is not None:
            s_common.deprecated('upstream layer configuration option', curv='2.162.0')
            if isinstance(uplayr, (tuple, list)):
                for layr in uplayr:
                    await self.initUpstreamSync(layr)
            else:
                await self.initUpstreamSync(uplayr)

    async def initLayerPassive(self):

        if self.leadtask is not None:
            self.leadtask.cancel()
            self.leadtask = None

        if self.leader is not None:
            await self.leader.fini()
            self.leader = None

        [t.cancel() for t in self.activetasks]
        self.activetasks.clear()

    async def getEditSize(self):
        return self.nodeeditlog.size

    async def _runMirrorLoop(self):

        while not self.isfini:

            try:

                proxy = await self.leader.proxy()

                leadoffs = await self._getLeadOffs()

                async for offs, edits, meta in proxy.syncNodeEdits2(leadoffs + 1):

                    iden = meta.get('task')
                    futu = self.futures.pop(iden, None)

                    meta['indx'] = offs

                    try:
                        item = await self.saveToNexs('edits', edits, meta)
                        if futu is not None:
                            futu.set_result(item)

                    except asyncio.CancelledError:  # pragma: no cover
                        raise

                    except s_exc.LinkShutDown:
                        raise

                    except Exception as e:
                        if futu is not None:
                            futu.set_exception(e)
                            continue
                        logger.error(f'Error consuming mirror nodeedit at offset {offs} for (layer: {self.iden}): {e}')

            except asyncio.CancelledError as e:  # pragma: no cover
                raise

            except Exception as e:  # pragma: no cover
                logger.exception(f'error in runMirrorLoop() (layer: {self.iden}): ')
                await self.waitfini(timeout=2)

    async def _getLeadOffs(self):
        last = self.nodeeditlog.last()
        if last is None:
            return -1
        return last[1][1].get('indx', -1)

    async def verifyBuidTag(self, buid, formname, tagname, tagvalu):
        abrv = self.tagabrv.bytsToAbrv(tagname.encode())
        abrv += self.getPropAbrv(formname, None)
        if not self.layrslab.hasdup(abrv, buid, db=self.bytag):
            yield ('NoTagIndex', {'buid': buid, 'form': formname, 'tag': tagname, 'valu': tagvalu})

    def _testDelTagIndx(self, buid, form, tag):
        formabrv = self.setPropAbrv(form, None)
        tagabrv = self.tagabrv.bytsToAbrv(tag.encode())
        self.layrslab.delete(tagabrv + formabrv, buid, db=self.bytag)

    def _testDelPropIndx(self, buid, form, prop):
        sode = self._getStorNode(buid)
        storvalu, stortype = sode['props'][prop]

        abrv = self.setPropAbrv(form, prop)
        for indx in self.stortypes[stortype].indx(storvalu):
            self.layrslab.delete(abrv + indx, buid, db=self.byprop)

    def _testDelTagStor(self, buid, form, tag):
        sode = self._getStorNode(buid)
        sode['tags'].pop(tag, None)
        self.setSodeDirty(buid, sode, form)

    def _testDelPropStor(self, buid, form, prop):
        sode = self._getStorNode(buid)
        sode['props'].pop(prop, None)
        self.setSodeDirty(buid, sode, form)

    def _testDelFormValuStor(self, buid, form):
        sode = self._getStorNode(buid)
        sode['valu'] = None
        self.setSodeDirty(buid, sode, form)

    def _testAddPropIndx(self, buid, form, prop, valu):
        modlprop = self.core.model.prop(f'{form}:{prop}')
        abrv = self.setPropAbrv(form, prop)
        for indx in self.stortypes[modlprop.type.stortype].indx(valu):
            self.layrslab.put(abrv + indx, buid, db=self.byprop)

    def _testAddPropArrayIndx(self, buid, form, prop, valu):
        modlprop = self.core.model.prop(f'{form}:{prop}')
        abrv = self.setPropAbrv(form, prop)
        for indx in self.getStorIndx(modlprop.type.stortype, valu):
            self.layrslab.put(abrv + indx, buid, db=self.byarray)

    def _testAddTagIndx(self, buid, form, tag):
        formabrv = self.setPropAbrv(form, None)
        tagabrv = self.tagabrv.bytsToAbrv(tag.encode())
        self.layrslab.put(tagabrv + formabrv, buid, db=self.bytag)

    def _testAddTagPropIndx(self, buid, form, tag, prop, valu):
        tpabrv = self.setTagPropAbrv(None, tag, prop)
        ftpabrv = self.setTagPropAbrv(form, tag, prop)

        tagprop = self.core.model.tagprop(prop)
        for indx in self.stortypes[tagprop.type.stortype].indx(valu):
            self.layrslab.put(tpabrv + indx, buid, db=self.bytagprop)
            self.layrslab.put(ftpabrv + indx, buid, db=self.bytagprop)

    async def verify(self, config=None):

        if config is None:
            config = {}

        defconf = None
        if config.get('scanall', True):
            defconf = {}

        scans = config.get('scans', {})

        nodescan = scans.get('nodes', defconf)
        if nodescan is not None:
            async for error in self.verifyAllBuids(nodescan):
                yield error

        tagsscan = scans.get('tagindex', defconf)
        if tagsscan is not None:
            async for error in self.verifyAllTags(tagsscan):
                yield error

        propscan = scans.get('propindex', defconf)
        if propscan is not None:
            async for error in self.verifyAllProps(propscan):
                yield error

        tagpropscan = scans.get('tagpropindex', defconf)
        if tagpropscan is not None:
            async for error in self.verifyAllTagProps(tagpropscan):
                yield error

    async def verifyAllBuids(self, scanconf=None):
        if scanconf is None:
            scanconf = {}

        async for buid, sode in self.getStorNodes():
            async for error in self.verifyByBuid(buid, sode):
                yield error

    async def verifyAllTags(self, scanconf=None):

        if scanconf is None:
            scanconf = {}

        globs = None

        includes = scanconf.get('include', ())
        if includes:
            globs = s_cache.TagGlobs()
            for incname in includes:
                globs.add(incname, True)

        autofix = scanconf.get('autofix')
        if autofix not in (None, 'node', 'index'):
            mesg = f'invalid tag index autofix strategy "{autofix}"'
            raise s_exc.BadArg(mesg=mesg)

        for name in self.tagabrv.names():

            if globs is not None and not globs.get(name):
                continue

            async for error in self.verifyByTag(name, autofix=autofix):
                yield error

    async def verifyAllProps(self, scanconf=None):

        if scanconf is None:
            scanconf = {}

        autofix = scanconf.get('autofix')
        if autofix not in (None, 'index'):
            mesg = f'invalid prop index autofix strategy "{autofix}"'
            raise s_exc.BadArg(mesg=mesg)

        include = scanconf.get('include', None)

        for form, prop in self.getFormProps():

            if include is not None and (form, prop) not in include:
                continue

            async for error in self.verifyByProp(form, prop, autofix=autofix):
                yield error

            async for error in self.verifyByPropArray(form, prop, autofix=autofix):
                yield error

    async def verifyAllTagProps(self, scanconf=None):

        if scanconf is None:
            scanconf = {}

        autofix = scanconf.get('autofix')
        if autofix not in (None, 'index'):
            mesg = f'invalid tagprop index autofix strategy "{autofix}"'
            raise s_exc.BadArg(mesg=mesg)

        include = scanconf.get('include', None)

        for form, tag, prop in self.getTagProps():

            if include is not None and prop not in include:
                continue

            async for error in self.verifyByTagProp(form, tag, prop, autofix=autofix):
                yield error

    async def verifyByTag(self, tag, autofix=None):
        tagabrv = self.tagabrv.bytsToAbrv(tag.encode())

        async def tryfix(lkey, buid, form):
            if autofix == 'node':
                sode = self._genStorNode(buid)
                sode.setdefault('form', form)
                sode['tags'][tag] = (None, None)
                self.setSodeDirty(buid, sode, form)
            elif autofix == 'index':
                self.layrslab.delete(lkey, buid, db=self.bytag)

        for lkey, buid in self.layrslab.scanByPref(tagabrv, db=self.bytag):

            await asyncio.sleep(0)

            (form, prop) = self.getAbrvProp(lkey[8:])

            sode = self._getStorNode(buid)
            if sode is None: # pragma: no cover
                await tryfix(lkey, buid, form)
                yield ('NoNodeForTagIndex', {'buid': s_common.ehex(buid), 'form': form, 'tag': tag})
                continue

            tags = sode.get('tags')
            if tags.get(tag) is None:
                await tryfix(lkey, buid, form)
                yield ('NoTagForTagIndex', {'buid': s_common.ehex(buid), 'form': form, 'tag': tag})
                continue

    async def verifyByProp(self, form, prop, autofix=None):

        abrv = self.getPropAbrv(form, prop)

        async def tryfix(lkey, buid):
            if autofix == 'index':
                self.layrslab.delete(lkey, buid, db=self.byprop)

        for lkey, buid in self.layrslab.scanByPref(abrv, db=self.byprop):

            await asyncio.sleep(0)

            indx = lkey[len(abrv):]

            sode = self._getStorNode(buid)
            if sode is None:
                await tryfix(lkey, buid)
                yield ('NoNodeForPropIndex', {'buid': s_common.ehex(buid), 'form': form, 'prop': prop, 'indx': indx})
                continue

            if prop is not None:
                props = sode.get('props')
                if props is None:
                    await tryfix(lkey, buid)
                    yield ('NoValuForPropIndex', {'buid': s_common.ehex(buid), 'form': form, 'prop': prop, 'indx': indx})
                    continue

                valu = props.get(prop)
                if valu is None:
                    await tryfix(lkey, buid)
                    yield ('NoValuForPropIndex', {'buid': s_common.ehex(buid), 'form': form, 'prop': prop, 'indx': indx})
                    continue
            else:
                valu = sode.get('valu')
                if valu is None:
                    await tryfix(lkey, buid)
                    yield ('NoValuForPropIndex', {'buid': s_common.ehex(buid), 'form': form, 'prop': prop, 'indx': indx})
                    continue

            propvalu, stortype = valu
            if stortype & STOR_FLAG_ARRAY:
                stortype = STOR_TYPE_MSGP

            try:
                for indx in self.stortypes[stortype].indx(propvalu):
                    if abrv + indx == lkey:
                        break
                else:
                    await tryfix(lkey, buid)
                    yield ('SpurPropKeyForIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                   'prop': prop, 'indx': indx})

            except IndexError:
                await tryfix(lkey, buid)
                yield ('NoStorTypeForProp', {'buid': s_common.ehex(buid), 'form': form, 'prop': prop,
                                             'stortype': stortype})

    async def verifyByPropArray(self, form, prop, autofix=None):

        abrv = self.getPropAbrv(form, prop)

        async def tryfix(lkey, buid):
            if autofix == 'index':
                self.layrslab.delete(lkey, buid, db=self.byarray)

        for lkey, buid in self.layrslab.scanByPref(abrv, db=self.byarray):

            await asyncio.sleep(0)

            indx = lkey[len(abrv):]

            sode = self._getStorNode(buid)
            if sode is None:
                await tryfix(lkey, buid)
                yield ('NoNodeForPropArrayIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                   'prop': prop, 'indx': indx})
                continue

            if prop is not None:
                props = sode.get('props')
                if props is None:
                    await tryfix(lkey, buid)
                    yield ('NoValuForPropArrayIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                       'prop': prop, 'indx': indx})
                    continue

                valu = props.get(prop)
                if valu is None:
                    await tryfix(lkey, buid)
                    yield ('NoValuForPropArrayIndex', {'buid': s_common.ehex(buid),
                                                       'form': form, 'prop': prop, 'indx': indx})
                    continue
            else:
                valu = sode.get('valu')
                if valu is None:
                    await tryfix(lkey, buid)
                    yield ('NoValuForPropArrayIndex', {'buid': s_common.ehex(buid),
                                                       'form': form, 'prop': prop, 'indx': indx})
                    continue

            propvalu, stortype = valu

            try:
                for indx in self.getStorIndx(stortype, propvalu):
                    if abrv + indx == lkey:
                        break
                else:
                    await tryfix(lkey, buid)
                    yield ('SpurPropArrayKeyForIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                        'prop': prop, 'indx': indx})

            except IndexError:
                await tryfix(lkey, buid)
                yield ('NoStorTypeForPropArray', {'buid': s_common.ehex(buid), 'form': form,
                                                  'prop': prop, 'stortype': stortype})

    async def verifyByTagProp(self, form, tag, prop, autofix=None):

        abrv = self.getTagPropAbrv(form, tag, prop)

        async def tryfix(lkey, buid):
            if autofix == 'index':
                self.layrslab.delete(lkey, buid, db=self.bytagprop)

        for lkey, buid in self.layrslab.scanByPref(abrv, db=self.bytagprop):

            await asyncio.sleep(0)

            indx = lkey[len(abrv):]

            sode = self._getStorNode(buid)
            if sode is None:
                await tryfix(lkey, buid)
                yield ('NoNodeForTagPropIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                 'tag': tag, 'prop': prop, 'indx': indx})
                continue

            tags = sode.get('tagprops')
            if tags is None:
                yield ('NoPropForTagPropIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                 'tag': tag, 'prop': prop, 'indx': indx})
                continue

            props = tags.get(tag)
            if props is None:
                await tryfix(lkey, buid)
                yield ('NoPropForTagPropIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                 'tag': tag, 'prop': prop, 'indx': indx})
                continue

            valu = props.get(prop)
            if valu is None:
                await tryfix(lkey, buid)
                yield ('NoValuForTagPropIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                 'tag': tag, 'prop': prop, 'indx': indx})
                continue

            propvalu, stortype = valu

            if stortype & STOR_FLAG_ARRAY: # pragma: no cover
                # TODO: These aren't possible yet
                stortype = STOR_TYPE_MSGP

            try:
                for indx in self.stortypes[stortype].indx(propvalu):
                    if abrv + indx == lkey:
                        break
                else:
                    await tryfix(lkey, buid)
                    yield ('SpurTagPropKeyForIndex', {'buid': s_common.ehex(buid), 'form': form,
                                                      'tag': tag, 'prop': prop, 'indx': indx})
            except IndexError:
                await tryfix(lkey, buid)
                yield ('NoStorTypeForTagProp', {'buid': s_common.ehex(buid), 'form': form,
                                                'tag': tag, 'prop': prop, 'stortype': stortype})

    async def verifyByBuid(self, buid, sode):

        await asyncio.sleep(0)

        form = sode.get('form')
        stortags = sode.get('tags')
        if stortags:
            for tagname, storvalu in stortags.items():
                async for error in self.verifyBuidTag(buid, form, tagname, storvalu):
                    yield error

        storprops = sode.get('props')
        if storprops:
            for propname, (storvalu, stortype) in storprops.items():

                # TODO: we dont support verifying array property indexes just yet...
                if stortype & STOR_FLAG_ARRAY:
                    continue

                try:
                    async for error in self.stortypes[stortype].verifyBuidProp(buid, form, propname, storvalu):
                        yield error
                except IndexError as e:
                    yield ('NoStorTypeForProp', {'buid': s_common.ehex(buid), 'form': form, 'prop': propname,
                                                 'stortype': stortype})

    async def pack(self):
        ret = deepcopy(self.layrinfo)
        if ret.get('mirror'):
            ret['mirror'] = s_urlhelp.sanitizeUrl(ret['mirror'])
        ret['offset'] = await self.getEditIndx()
        ret['totalsize'] = await self.getLayerSize()
        return ret

    @s_nexus.Pusher.onPush('layer:truncate')
    async def _truncate(self):
        '''
        Nuke all the contents in the layer, leaving an empty layer
        NOTE: This internal API is deprecated but is kept for Nexus event backward compatibility
        '''
        # TODO: Remove this in 3.0.0
        s_common.deprecated('layer:truncate Nexus handler', curv='2.156.0')

        self.dirty.clear()
        self.buidcache.clear()

        await self.layrslab.trash()
        await self.nodeeditslab.trash()
        await self.dataslab.trash()

        await self._initLayerStorage()

    async def iterWipeNodeEdits(self):

        await self._saveDirtySodes()

        async for buid, sode in self.getStorNodes():

            edits = []

            async for verb, n2iden in self.iterNodeEdgesN1(buid):
                edits.append((EDIT_EDGE_DEL, (verb, n2iden), ()))

            async for prop, valu in self.iterNodeData(buid):
                edits.append((EDIT_NODEDATA_DEL, (prop, valu), ()))

            for tag, propdict in sode.get('tagprops', {}).items():
                for prop, (valu, stortype) in propdict.items():
                    edits.append((EDIT_TAGPROP_DEL, (tag, prop, valu, stortype), ()))

            for tag, tagv in sode.get('tags', {}).items():
                edits.append((EDIT_TAG_DEL, (tag, tagv), ()))

            for prop, (valu, stortype) in sode.get('props', {}).items():
                edits.append((EDIT_PROP_DEL, (prop, valu, stortype), ()))

            valu = sode.get('valu')
            if valu is not None:
                edits.append((EDIT_NODE_DEL, valu, ()))

            yield (buid, sode.get('form'), edits)

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
                        await self.layrslab.putmulti(tostor, db=self.bybuidv3)
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
                if tag not in sode['tagprops']:
                    sode['tagprops'][tag] = {}
                sode['tagprops'][tag][prop] = s_msgpack.un(lval)
                continue

            if flag == 9:
                sode['form'] = lval.decode()
                continue

            logger.warning('Invalid flag %d found for buid %s during migration', flag, buid)  # pragma: no cover

        count += 1

        # Mop up the leftovers
        if lastbuid is not None:
            count += 1
            tostor.append((lastbuid, s_msgpack.en(sode)))
        if tostor:
            await self.layrslab.putmulti(tostor, db=self.bybuidv3)

        logger.warning('...removing old bybuid index')
        self.layrslab.dropdb('bybuid')

        self.meta.set('version', 3)
        self.layrvers = 3

        logger.warning(f'...complete! ({count} nodes)')

    async def _layrV3toV5(self):

        sode = collections.defaultdict(dict)

        logger.warning(f'Cleaning layer byarray index: {self.dirn}')

        for lkey, lval in self.layrslab.scanByFull(db=self.byarray):

            abrv = lkey[:8]
            (form, prop) = self.getAbrvProp(abrv)

            if form is None or prop is None:
                continue

            byts = self.layrslab.get(lval, db=self.bybuidv3)
            if byts is not None:
                sode.update(s_msgpack.un(byts))

            pval = sode['props'].get(prop)
            if pval is None:
                self.layrslab.delete(lkey, lval, db=self.byarray)
                sode.clear()
                continue

            indxbyts = lkey[8:]
            valu, stortype = pval
            realtype = stortype & 0x7fff
            realstor = self.stortypes[realtype]

            for aval in valu:
                if indxbyts in realstor.indx(aval):
                    break
            else:
                self.layrslab.delete(lkey, lval, db=self.byarray)

            sode.clear()

        self.meta.set('version', 5)
        self.layrvers = 5

        logger.warning(f'...complete!')

    async def _layrV4toV5(self):

        sode = collections.defaultdict(dict)

        logger.warning(f'Rebuilding layer byarray index: {self.dirn}')

        for byts, abrv in self.propabrv.slab.scanByFull(db=self.propabrv.name2abrv):

            form, prop = s_msgpack.un(byts)
            if form is None or prop is None:
                continue

            for lkey, buid in self.layrslab.scanByPref(abrv, db=self.byprop):
                byts = self.layrslab.get(buid, db=self.bybuidv3)
                if byts is not None:
                    sode.clear()
                    sode.update(s_msgpack.un(byts))

                pval = sode['props'].get(prop)
                if pval is None:
                    continue

                valu, stortype = pval
                if not stortype & STOR_FLAG_ARRAY:
                    break

                for indx in self.getStorIndx(stortype, valu):
                    self.layrslab.put(abrv + indx, buid, db=self.byarray)

        self.meta.set('version', 5)
        self.layrvers = 5

        logger.warning(f'...complete!')

    async def _v5ToV7Buid(self, buid):

        byts = self.layrslab.get(buid, db=self.bybuidv3)
        if byts is None:
            return

        sode = s_msgpack.un(byts)
        tagprops = sode.get('tagprops')
        if tagprops is None:
            return
        edited_sode = False
        # do this in a partially-covered / replay safe way
        for tpkey, tpval in list(tagprops.items()):
            if isinstance(tpkey, tuple):
                tagprops.pop(tpkey)
                edited_sode = True
                tag, prop = tpkey

                if tagprops.get(tag) is None:
                    tagprops[tag] = {}
                if prop in tagprops[tag]:
                    continue
                tagprops[tag][prop] = tpval

        if edited_sode:
            self.layrslab.put(buid, s_msgpack.en(sode), db=self.bybuidv3)

    async def _layrV5toV7(self):

        logger.warning(f'Updating tagprop keys in bytagprop index: {self.dirn}')

        for lkey, buid in self.layrslab.scanByFull(db=self.bytagprop):
            await self._v5ToV7Buid(buid)

        self.meta.set('version', 7)
        self.layrvers = 7

        logger.warning('...complete!')

    async def _v7toV8Prop(self, prop):

        propname = prop.name
        form = prop.form
        if form:
            form = form.name

        try:
            abrv = self.getPropAbrv(form, propname)

        except s_exc.NoSuchAbrv:
            return

        isarray = False
        if prop.type.stortype & STOR_FLAG_ARRAY:
            isarray = True
            araystor = self.stortypes[STOR_TYPE_MSGP]

            for lkey, buid in self.layrslab.scanByPref(abrv, db=self.byarray):
                self.layrslab.delete(lkey, buid, db=self.byarray)

        hugestor = self.stortypes[STOR_TYPE_HUGENUM]
        sode = collections.defaultdict(dict)

        for lkey, buid in self.layrslab.scanByPref(abrv, db=self.byprop):

            if isarray is False and len(lkey) == 28:
                continue

            byts = self.layrslab.get(buid, db=self.bybuidv3)
            if byts is None:
                self.layrslab.delete(lkey, buid, db=self.byprop)
                continue

            sode.update(s_msgpack.un(byts))
            pval = sode['props'].get(propname)
            if pval is None:
                self.layrslab.delete(lkey, buid, db=self.byprop)
                sode.clear()
                continue

            valu, _ = pval
            if isarray:
                try:
                    newval = prop.type.norm(valu)[0]
                except s_exc.BadTypeValu:
                    logger.warning(f'Invalid value {valu} for prop {propname} for buid {buid}')
                    continue

                if valu != newval:

                    nkey = abrv + araystor.indx(newval)[0]
                    if nkey != lkey:
                        self.layrslab.put(nkey, buid, db=self.byprop)
                        self.layrslab.delete(lkey, buid, db=self.byprop)

                for aval in valu:
                    indx = hugestor.indx(aval)[0]
                    self.layrslab.put(abrv + indx, buid, db=self.byarray)
            else:
                try:
                    indx = hugestor.indx(valu)[0]
                except Exception:
                    logger.warning(f'Invalid value {valu} for prop {propname} for buid {buid}')
                    continue

                self.layrslab.put(abrv + indx, buid, db=self.byprop)
                self.layrslab.delete(lkey, buid, db=self.byprop)

            sode.clear()

    async def _v7toV8TagProp(self, form, tag, prop):

        try:
            ftpabrv = self.getTagPropAbrv(form, tag, prop)
            tpabrv = self.getTagPropAbrv(None, tag, prop)

        except s_exc.NoSuchAbrv:
            return

        abrvlen = len(ftpabrv)

        hugestor = self.stortypes[STOR_TYPE_HUGENUM]
        sode = collections.defaultdict(dict)

        for lkey, buid in self.layrslab.scanByPref(ftpabrv, db=self.bytagprop):

            if len(lkey) == 28:
                continue

            byts = self.layrslab.get(buid, db=self.bybuidv3)
            if byts is None:
                self.layrslab.delete(lkey, buid, db=self.bytagprop)
                continue

            sode.update(s_msgpack.un(byts))

            props = sode['tagprops'].get(tag)
            if not props:
                self.layrslab.delete(lkey, buid, db=self.bytagprop)
                sode.clear()
                continue

            pval = props.get(prop)
            if pval is None:
                self.layrslab.delete(lkey, buid, db=self.bytagprop)
                sode.clear()
                continue

            valu, _ = pval
            try:
                indx = hugestor.indx(valu)[0]
            except Exception:
                logger.warning(f'Invalid value {valu} for tagprop {tag}:{prop} for buid {buid}')
                continue
            self.layrslab.put(ftpabrv + indx, buid, db=self.bytagprop)
            self.layrslab.put(tpabrv + indx, buid, db=self.bytagprop)

            oldindx = lkey[abrvlen:]
            self.layrslab.delete(lkey, buid, db=self.bytagprop)
            self.layrslab.delete(tpabrv + oldindx, buid, db=self.bytagprop)

            sode.clear()

    async def _layrV7toV8(self):

        logger.warning(f'Updating hugenum index values: {self.dirn}')

        for name, prop in self.core.model.props.items():
            stortype = prop.type.stortype
            if stortype & STOR_FLAG_ARRAY:
                stortype = stortype & 0x7fff

            if stortype == STOR_TYPE_HUGENUM:
                await self._v7toV8Prop(prop)

        tagprops = set()
        for name, prop in self.core.model.tagprops.items():
            if prop.type.stortype == STOR_TYPE_HUGENUM:
                tagprops.add(prop.name)

        for form, tag, prop in self.getTagProps():
            if form is None or prop not in tagprops:
                continue

            await self._v7toV8TagProp(form, tag, prop)

        self.meta.set('version', 8)
        self.layrvers = 8

        logger.warning('...complete!')

    async def _v8toV9Prop(self, prop):

        propname = prop.name
        form = prop.form
        if form:
            form = form.name

        try:
            if prop.isform:
                abrv = self.getPropAbrv(form, None)
            else:
                abrv = self.getPropAbrv(form, propname)
        except s_exc.NoSuchAbrv:
            return

        isarray = False
        if prop.type.stortype & STOR_FLAG_ARRAY:
            isarray = True
            araystor = self.stortypes[STOR_TYPE_MSGP]

            for lkey, buid in self.layrslab.scanByPref(abrv, db=self.byarray):
                self.layrslab.delete(lkey, buid, db=self.byarray)

        abrvlen = len(abrv)
        hugestor = self.stortypes[STOR_TYPE_HUGENUM]
        sode = collections.defaultdict(dict)

        for lkey, buid in self.layrslab.scanByPref(abrv, db=self.byprop):

            byts = self.layrslab.get(buid, db=self.bybuidv3)
            if byts is None:
                self.layrslab.delete(lkey, buid, db=self.byprop)
                continue

            sode.clear()
            sode.update(s_msgpack.un(byts))
            if prop.isform:
                valu = sode['valu']
            else:
                valu = sode['props'].get(propname)

            if valu is None:
                self.layrslab.delete(lkey, buid, db=self.byprop)
                continue

            valu = valu[0]
            if isarray:
                for aval in valu:
                    try:
                        indx = hugestor.indx(aval)[0]
                    except Exception:
                        logger.warning(f'Invalid value {valu} for prop {propname} for buid {s_common.ehex(buid)}')
                        continue

                    self.layrslab.put(abrv + indx, buid, db=self.byarray)
            else:
                try:
                    indx = hugestor.indx(valu)[0]
                except Exception:
                    logger.warning(f'Invalid value {valu} for prop {propname} for buid {s_common.ehex(buid)}')
                    continue

                if indx == lkey[abrvlen:]:
                    continue
                self.layrslab.put(abrv + indx, buid, db=self.byprop)
                self.layrslab.delete(lkey, buid, db=self.byprop)

    async def _v8toV9TagProp(self, form, tag, prop):

        try:
            ftpabrv = self.getTagPropAbrv(form, tag, prop)
            tpabrv = self.getTagPropAbrv(None, tag, prop)
        except s_exc.NoSuchAbrv:
            return

        abrvlen = len(ftpabrv)

        hugestor = self.stortypes[STOR_TYPE_HUGENUM]
        sode = collections.defaultdict(dict)

        for lkey, buid in self.layrslab.scanByPref(ftpabrv, db=self.bytagprop):

            byts = self.layrslab.get(buid, db=self.bybuidv3)
            if byts is None:
                self.layrslab.delete(lkey, buid, db=self.bytagprop)
                continue

            sode.clear()
            sode.update(s_msgpack.un(byts))

            props = sode['tagprops'].get(tag)
            if not props:
                self.layrslab.delete(lkey, buid, db=self.bytagprop)
                continue

            pval = props.get(prop)
            if pval is None:
                self.layrslab.delete(lkey, buid, db=self.bytagprop)
                continue

            valu, _ = pval
            try:
                indx = hugestor.indx(valu)[0]
            except Exception:
                logger.warning(f'Invalid value {valu} for tagprop {tag}:{prop} for buid {s_common.ehex(buid)}')
                continue

            if indx == lkey[abrvlen:]:
                continue

            self.layrslab.put(ftpabrv + indx, buid, db=self.bytagprop)
            self.layrslab.put(tpabrv + indx, buid, db=self.bytagprop)

            oldindx = lkey[abrvlen:]
            self.layrslab.delete(lkey, buid, db=self.bytagprop)
            self.layrslab.delete(tpabrv + oldindx, buid, db=self.bytagprop)

    async def _layrV8toV9(self):

        logger.warning(f'Checking hugenum index values: {self.dirn}')

        for name, prop in self.core.model.props.items():
            stortype = prop.type.stortype
            if stortype & STOR_FLAG_ARRAY:
                stortype = stortype & 0x7fff

            if stortype == STOR_TYPE_HUGENUM:
                await self._v8toV9Prop(prop)

        tagprops = set()
        for name, prop in self.core.model.tagprops.items():
            if prop.type.stortype == STOR_TYPE_HUGENUM:
                tagprops.add(prop.name)

        for form, tag, prop in self.getTagProps():
            if form is None or prop not in tagprops:
                continue

            await self._v8toV9TagProp(form, tag, prop)

        self.meta.set('version', 9)
        self.layrvers = 9

        logger.warning('...complete!')

    async def _layrV9toV10(self):

        logger.warning(f'Adding n1+n2 index to edges in layer {self.iden}')

        async def commit():
            await self.layrslab.putmulti(putkeys, db=self.edgesn1n2)
            putkeys.clear()

        putkeys = []
        for lkey, n2buid in self.layrslab.scanByFull(db=self.edgesn1):

            n1buid = lkey[:32]
            venc = lkey[32:]

            putkeys.append((n1buid + n2buid, venc))
            if len(putkeys) > MIGR_COMMIT_SIZE:
                await commit()

        if len(putkeys):
            await commit()

        self.meta.set('version', 10)
        self.layrvers = 10

        logger.warning(f'...complete!')

    async def _layrV10toV11(self):

        logger.warning(f'Adding byform index to layer {self.iden}')

        async def commit():
            await self.layrslab.putmulti(putkeys, db=self.byform)
            putkeys.clear()

        putkeys = []
        async for buid, sode in self.getStorNodes():
            if not (form := sode.get('form')):
                continue

            abrv = self.setPropAbrv(form, None)
            putkeys.append((abrv, buid))

            if len(putkeys) > MIGR_COMMIT_SIZE:
                await commit()

        if putkeys:
            await commit()

        self.meta.set('version', 11)
        self.layrvers = 11

        logger.warning('...complete!')

    async def _initSlabs(self, slabopts):

        otherslabopts = {
            **slabopts,
            'readahead': False,   # less-used slabs don't need readahead
            'lockmemory': False,  # less-used slabs definitely don't get dedicated memory
        }

        path = s_common.genpath(self.dirn, 'layer_v2.lmdb')
        nodedatapath = s_common.genpath(self.dirn, 'nodedata.lmdb')

        self.layrslab = await s_lmdbslab.Slab.anit(path, **slabopts)
        self.dataslab = await s_lmdbslab.Slab.anit(nodedatapath, **otherslabopts)

        metadb = self.layrslab.initdb('layer:meta')
        self.meta = s_lmdbslab.SlabDict(self.layrslab, db=metadb)

        self.formcounts = await self.layrslab.getHotCount('count:forms')

        nodeeditpath = s_common.genpath(self.dirn, 'nodeedits.lmdb')
        self.nodeeditslab = await s_lmdbslab.Slab.anit(nodeeditpath, **otherslabopts)

        self.offsets = await self.layrslab.getHotCount('offsets')

        self.tagabrv = self.layrslab.getNameAbrv('tagabrv')
        self.propabrv = self.layrslab.getNameAbrv('propabrv')
        self.tagpropabrv = self.layrslab.getNameAbrv('tagpropabrv')

        self.bybuidv3 = self.layrslab.initdb('bybuidv3')

        self.byverb = self.layrslab.initdb('byverb', dupsort=True)
        self.edgesn1 = self.layrslab.initdb('edgesn1', dupsort=True)
        self.edgesn2 = self.layrslab.initdb('edgesn2', dupsort=True)
        self.edgesn1n2 = self.layrslab.initdb('edgesn1n2', dupsort=True)

        self.bytag = self.layrslab.initdb('bytag', dupsort=True)
        self.byform = self.layrslab.initdb('byform', dupsort=True)
        self.byndef = self.layrslab.initdb('byndef', dupsort=True)
        self.byprop = self.layrslab.initdb('byprop', dupsort=True)
        self.byarray = self.layrslab.initdb('byarray', dupsort=True)
        self.bytagprop = self.layrslab.initdb('bytagprop', dupsort=True)

        self.countdb = self.layrslab.initdb('counters')
        self.nodedata = self.dataslab.initdb('nodedata')
        self.dataname = self.dataslab.initdb('dataname', dupsort=True)

        self.nodeeditlog = self.nodeeditctor(self.nodeeditslab, 'nodeedits')

    async def _initLayerStorage(self):

        slabopts = {
            'readahead': s_common.envbool('SYNDEV_CORTEX_LAYER_READAHEAD', 'true'),
            'lockmemory': self.lockmemory,
        }

        if self.growsize is not None:
            slabopts['growsize'] = self.growsize

        await self._initSlabs(slabopts)

        if self.fresh:
            self.meta.set('version', 11)

        self.layrslab.addResizeCallback(self.core.checkFreeSpace)
        self.dataslab.addResizeCallback(self.core.checkFreeSpace)
        self.nodeeditslab.addResizeCallback(self.core.checkFreeSpace)

        self.onfini(self.layrslab)
        self.onfini(self.dataslab)
        self.onfini(self.nodeeditslab)

        self.layrslab.on('commit', self._onLayrSlabCommit)

        self.layrvers = self.meta.get('version', 2)

        if self.layrvers < 3:
            await self._layrV2toV3()

        if self.layrvers < 4:
            await self._layrV3toV5()

        if self.layrvers < 5:
            await self._layrV4toV5()

        if self.layrvers < 7:
            await self._layrV5toV7()

        if self.layrvers < 8:
            await self._layrV7toV8()

        if self.layrvers < 9:
            await self._layrV8toV9()

        if self.layrvers < 10:
            await self._layrV9toV10()

        if self.layrvers < 11:
            await self._layrV10toV11()

        if self.layrvers != 11:
            mesg = f'Got layer version {self.layrvers}.  Expected 11.  Accidental downgrade?'
            raise s_exc.BadStorageVersion(mesg=mesg)

    async def getLayerSize(self):
        '''
        Get the total storage size for the layer.
        '''
        realsize, _ = s_common.getDirSize(self.dirn)
        return realsize

    async def setLayerInfo(self, name, valu):
        if name != 'readonly':
            self._reqNotReadOnly()
        return await self._push('layer:set', name, valu)

    @s_nexus.Pusher.onPush('layer:set')
    async def _setLayerInfo(self, name, valu):
        '''
        Set a mutable layer property.
        '''
        if name not in ('name', 'desc', 'logedits', 'readonly'):
            mesg = f'{name} is not a valid layer info key'
            raise s_exc.BadOptValu(mesg=mesg)

        if name == 'logedits':
            valu = bool(valu)
            self.logedits = valu
        elif name == 'readonly':
            valu = bool(valu)
            self.readonly = valu

        # TODO when we can set more props, we may need to parse values.
        if valu is None:
            self.layrinfo.pop(name, None)
        else:
            self.layrinfo[name] = valu

        self.core.layerdefs.set(self.iden, self.layrinfo)

        await self.core.feedBeholder('layer:set', {'iden': self.iden, 'name': name, 'valu': valu}, gates=[self.iden])
        return valu

    async def stat(self):
        ret = {**self.layrslab.statinfo(),
               }
        if self.logedits:
            ret['nodeeditlog_indx'] = (self.nodeeditlog.index(), 0, 0)
        return ret

    async def _onLayrFini(self):
        [(await wind.fini()) for wind in self.windows]
        [futu.cancel() for futu in self.futures.values()]
        if self.leader is not None:
            await self.leader.fini()

    async def getFormCounts(self):
        return self.formcounts.pack()

    @s_cache.memoizemethod()
    def getPropAbrv(self, form, prop):
        return self.propabrv.bytsToAbrv(s_msgpack.en((form, prop)))

    def setPropAbrv(self, form, prop):
        return self.propabrv.setBytsToAbrv(s_msgpack.en((form, prop)))

    def getFormProps(self):
        for byts in self.propabrv.keys():
            yield s_msgpack.un(byts)

    def getTagProps(self):
        for byts in self.tagpropabrv.keys():
            yield s_msgpack.un(byts)

    @s_cache.memoizemethod()
    def getTagPropAbrv(self, *args):
        return self.tagpropabrv.bytsToAbrv(s_msgpack.en(args))

    def setTagPropAbrv(self, *args):
        return self.tagpropabrv.setBytsToAbrv(s_msgpack.en(args))

    @s_cache.memoizemethod()
    def getAbrvProp(self, abrv):
        byts = self.propabrv.abrvToByts(abrv)
        return s_msgpack.un(byts)

    async def getNodeValu(self, buid, prop=None):
        '''
        Retrieve either the form valu or a prop valu for the given node by buid.
        '''
        sode = self._getStorNode(buid)
        if sode is None: # pragma: no cover
            return (None, None)
        if prop is None:
            return sode.get('valu', (None, None))[0]
        return sode['props'].get(prop, (None, None))[0]

    async def getNodeTag(self, buid, tag):
        sode = self._getStorNode(buid)
        if sode is None: # pragma: no cover
            return None
        return sode['tags'].get(tag)

    async def getNodeForm(self, buid):
        sode = self._getStorNode(buid)
        if sode is None: # pragma: no cover
            return None
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

        self.layrslab._putmulti(kvlist, db=self.bybuidv3)
        self.dirty.clear()

    def getStorNodeCount(self):
        info = self.layrslab.stat(db=self.bybuidv3)
        return info.get('entries', 0)

    async def getStorNode(self, buid):
        sode = self._getStorNode(buid)
        if sode is not None:
            return deepcopy(sode)
        return {}

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

        byts = self.layrslab.get(buid, db=self.bybuidv3)
        if byts is None:
            return None

        sode = collections.defaultdict(dict)
        sode.update(s_msgpack.un(byts))
        self.buidcache[buid] = sode

        return sode

    def _genStorNode(self, buid):
        # get or create the storage node. this returns the *actual* storage node

        sode = self._getStorNode(buid)
        if sode is not None:
            return sode

        sode = collections.defaultdict(dict)
        self.buidcache[buid] = sode

        return sode

    async def getTagCount(self, tagname, formname=None):
        '''
        Return the number of tag rows in the layer for the given tag/form.
        '''
        try:
            abrv = self.tagabrv.bytsToAbrv(tagname.encode())
            if formname is not None:
                abrv += self.getPropAbrv(formname, None)
                return self.layrslab.count(abrv, db=self.bytag)

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

    def getPropValuCount(self, formname, propname, stortype, valu):
        try:
            abrv = self.getPropAbrv(formname, propname)
        except s_exc.NoSuchAbrv:
            return 0

        if stortype & 0x8000:
            stortype = STOR_TYPE_MSGP

        count = 0
        for indx in self.getStorIndx(stortype, valu):
            count += self.layrslab.count(abrv + indx, db=self.byprop)

        return count

    async def getPropArrayCount(self, formname, propname=None):
        '''
        Return the number of invidiual value rows in the layer for the given array form/prop.
        '''
        try:
            abrv = self.getPropAbrv(formname, propname)
        except s_exc.NoSuchAbrv:
            return 0

        return await self.layrslab.countByPref(abrv, db=self.byarray)

    def getPropArrayValuCount(self, formname, propname, stortype, valu):
        try:
            abrv = self.getPropAbrv(formname, propname)
        except s_exc.NoSuchAbrv:
            return 0

        count = 0
        for indx in self.getStorIndx(stortype, valu):
            count += self.layrslab.count(abrv + indx, db=self.byarray)

        return count

    async def getUnivPropCount(self, propname, maxsize=None):
        '''
        Return the number of universal property rows in the layer for the given prop.
        '''
        try:
            abrv = self.getPropAbrv(None, propname)
        except s_exc.NoSuchAbrv:
            return 0

        return await self.layrslab.countByPref(abrv, db=self.byprop, maxsize=maxsize)

    async def getTagPropCount(self, form, tag, prop):
        '''
        Return the number of property rows in the layer for the given form/tag/prop.
        '''
        try:
            abrv = self.getTagPropAbrv(form, tag, prop)
        except s_exc.NoSuchAbrv:
            return 0

        return await self.layrslab.countByPref(abrv, db=self.bytagprop)

    def getTagPropValuCount(self, form, tag, prop, stortype, valu):
        try:
            abrv = self.getTagPropAbrv(form, tag, prop)
        except s_exc.NoSuchAbrv:
            return 0

        count = 0
        for indx in self.getStorIndx(stortype, valu):
            count += self.layrslab.count(abrv + indx, db=self.bytagprop)

        return count

    async def iterPropValues(self, formname, propname, stortype):
        try:
            abrv = self.getPropAbrv(formname, propname)
        except s_exc.NoSuchAbrv:
            return

        if stortype & 0x8000:
            stortype = STOR_TYPE_MSGP

        stor = self.stortypes[stortype]
        abrvlen = len(abrv)

        async for lkey in s_coro.pause(self.layrslab.scanKeysByPref(abrv, db=self.byprop, nodup=True)):

            indx = lkey[abrvlen:]
            valu = stor.decodeIndx(indx)
            if valu is not s_common.novalu:
                yield indx, valu
                continue

            buid = self.layrslab.get(lkey, db=self.byprop)
            if buid is not None:
                sode = self._getStorNode(buid)
                if sode is not None:
                    if propname is None:
                        valt = sode.get('valu')
                    else:
                        valt = sode['props'].get(propname)

                    if valt is not None:
                        yield indx, valt[0]

    async def iterPropIndxBuids(self, formname, propname, indx):
        try:
            abrv = self.getPropAbrv(formname, propname)
        except s_exc.NoSuchAbrv:
            return

        async for _, buid in s_coro.pause(self.layrslab.scanByDups(abrv + indx, db=self.byprop)):
            yield buid

    async def liftByTag(self, tag, form=None, reverse=False):

        try:
            abrv = self.tagabrv.bytsToAbrv(tag.encode())
            if form is not None:
                abrv += self.getPropAbrv(form, None)

        except s_exc.NoSuchAbrv:
            return

        if reverse:
            scan = self.layrslab.scanByPrefBack
        else:
            scan = self.layrslab.scanByPref

        for lkey, buid in scan(abrv, db=self.bytag):

            sode = self._getStorNode(buid)
            if sode is None: # pragma: no cover
                # logger.warning(f'TagIndex for #{tag} has {s_common.ehex(buid)} but no storage node.')
                continue

            yield None, buid, deepcopy(sode)

    async def liftByTags(self, tags):
        # todo: support form and reverse kwargs

        genrs = []

        for tag in tags:
            try:
                abrv = self.tagabrv.bytsToAbrv(tag.encode())
                genrs.append(s_coro.agen(self.layrslab.scanByPref(abrv, db=self.bytag)))
            except s_exc.NoSuchAbrv:
                continue

        lastbuid = None

        async for lkey, buid in s_common.merggenr2(genrs, cmprkey=lambda x: x[1]):

            if buid == lastbuid:
                lastbuid = buid
                await asyncio.sleep(0)
                continue

            lastbuid = buid

            sode = self._getStorNode(buid)
            if sode is None: # pragma: no cover
                continue

            yield None, buid, deepcopy(sode)

    async def liftByTagValu(self, tag, cmpr, valu, form=None, reverse=False):

        try:
            abrv = self.tagabrv.bytsToAbrv(tag.encode())
            if form is not None:
                abrv += self.getPropAbrv(form, None)

        except s_exc.NoSuchAbrv:
            return

        filt = StorTypeTag.getTagFilt(cmpr, valu)
        if filt is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr)

        if reverse:
            scan = self.layrslab.scanByPrefBack
        else:
            scan = self.layrslab.scanByPref

        for lkey, buid in scan(abrv, db=self.bytag):
            # filter based on the ival value before lifting the node...
            valu = await self.getNodeTag(buid, tag)
            if filt(valu):
                sode = self._getStorNode(buid)
                if sode is None: # pragma: no cover
                    # logger.warning(f'TagValuIndex for #{tag} has {s_common.ehex(buid)} but no storage node.')
                    continue
                yield None, buid, deepcopy(sode)

    async def hasTagProp(self, name):
        async for _ in self.liftTagProp(name):
            return True

        return False

    async def hasNodeData(self, buid, name):
        try:
            abrv = self.getPropAbrv(name, None)
        except s_exc.NoSuchAbrv:
            return False
        return self.dataslab.has(buid + abrv, db=self.nodedata)

    async def liftTagProp(self, name):

        for form, tag, prop in self.getTagProps():

            if form is not None or prop != name:
                continue

            try:
                abrv = self.getTagPropAbrv(None, tag, name)

            except s_exc.NoSuchAbrv:
                continue

            for _, buid in self.layrslab.scanByPref(abrv, db=self.bytagprop):
                yield buid

    async def liftByTagProp(self, form, tag, prop, reverse=False):
        try:
            abrv = self.getTagPropAbrv(form, tag, prop)

        except s_exc.NoSuchAbrv:
            return

        if reverse:
            scan = self.layrslab.scanByPrefBack
        else:
            scan = self.layrslab.scanByPref

        for lkey, buid in scan(abrv, db=self.bytagprop):

            sode = self._getStorNode(buid)
            if sode is None: # pragma: no cover
                # logger.warning(f'TagPropIndex for {form}#{tag}:{prop} has {s_common.ehex(buid)} but no storage node.')
                continue

            yield lkey[8:], buid, deepcopy(sode)

    async def liftByTagPropValu(self, form, tag, prop, cmprvals, reverse=False):
        '''
        Note:  form may be None
        '''
        for cmpr, valu, kind in cmprvals:

            async for lkey, buid in self.stortypes[kind].indxByTagProp(form, tag, prop, cmpr, valu, reverse=reverse):

                sode = self._getStorNode(buid)
                if sode is None: # pragma: no cover
                    # logger.warning(f'TagPropValuIndex for {form}#{tag}:{prop} has {s_common.ehex(buid)} but no storage node.')
                    continue

                yield lkey[8:], buid, deepcopy(sode)

    async def liftByProp(self, form, prop, reverse=False):

        try:
            abrv = self.getPropAbrv(form, prop)

        except s_exc.NoSuchAbrv:
            return

        if reverse:
            scan = self.layrslab.scanByPrefBack
        else:
            scan = self.layrslab.scanByPref

        for lkey, buid in scan(abrv, db=self.byprop):
            sode = self._getStorNode(buid)
            if sode is None: # pragma: no cover
                # logger.warning(f'PropIndex for {form}:{prop} has {s_common.ehex(buid)} but no storage node.')
                continue
            yield lkey[8:], buid, deepcopy(sode)

    # NOTE: form vs prop valu lifting is differentiated to allow merge sort
    async def liftByFormValu(self, form, cmprvals, reverse=False):
        for cmpr, valu, kind in cmprvals:

            if kind & 0x8000:
                kind = STOR_TYPE_MSGP

            async for lkey, buid in self.stortypes[kind].indxByForm(form, cmpr, valu, reverse=reverse):
                sode = self._getStorNode(buid)
                if sode is None: # pragma: no cover
                    # logger.warning(f'FormValuIndex for {form} has {s_common.ehex(buid)} but no storage node.')
                    continue
                yield lkey[8:], buid, deepcopy(sode)

    async def liftByPropValu(self, form, prop, cmprvals, reverse=False):
        for cmpr, valu, kind in cmprvals:

            if kind & 0x8000:
                kind = STOR_TYPE_MSGP

            async for lkey, buid in self.stortypes[kind].indxByProp(form, prop, cmpr, valu, reverse=reverse):

                sode = self._getStorNode(buid)
                if sode is None: # pragma: no cover
                    # logger.warning(f'PropValuIndex for {form}:{prop} has {s_common.ehex(buid)} but no storage node.')
                    continue

                yield lkey[8:], buid, deepcopy(sode)

    async def liftByPropArray(self, form, prop, cmprvals, reverse=False):
        for cmpr, valu, kind in cmprvals:
            async for lkey, buid in self.stortypes[kind].indxByPropArray(form, prop, cmpr, valu, reverse=reverse):
                sode = self._getStorNode(buid)
                if sode is None: # pragma: no cover
                    # logger.warning(f'PropArrayIndex for {form}:{prop} has {s_common.ehex(buid)} but no storage node.')
                    continue
                yield lkey[8:], buid, deepcopy(sode)

    async def liftByDataName(self, name):
        try:
            abrv = self.getPropAbrv(name, None)

        except s_exc.NoSuchAbrv:
            return

        for abrv, buid in self.dataslab.scanByDups(abrv, db=self.dataname):

            sode = self._getStorNode(buid)
            if sode is None: # pragma: no cover
                # logger.warning(f'PropArrayIndex for {form}:{prop} has {s_common.ehex(buid)} but no storage node.')
                continue

            sode = deepcopy(sode)

            byts = self.dataslab.get(buid + abrv, db=self.nodedata)
            if byts is None:
                # logger.warning(f'NodeData for {name} has {s_common.ehex(buid)} but no data.')
                continue

            sode['nodedata'] = {name: s_msgpack.un(byts)}
            yield None, buid, sode

    async def storNodeEdits(self, nodeedits, meta):

        saveoff, results = await self.saveNodeEdits(nodeedits, meta)

        retn = []
        for buid, _, edits in results:
            sode = await self.getStorNode(buid)
            retn.append((buid, sode, edits))

        return retn

    async def _realSaveNodeEdits(self, edits, meta):

        saveoff, changes = await self.saveNodeEdits(edits, meta)

        retn = []
        for buid, _, edits in changes:
            sode = await self.getStorNode(buid)
            retn.append((buid, sode, edits))

        return saveoff, changes, retn

    async def saveNodeEdits(self, edits, meta):
        '''
        Save node edits to the layer and return a tuple of (nexsoffs, changes).

        Note: nexsoffs will be None if there are no changes.
        '''
        self._reqNotReadOnly()

        if self.ismirror:

            if self.core.isactive:
                proxy = await self.leader.proxy()

                with self.getIdenFutu(iden=meta.get('task')) as (iden, futu):
                    meta['task'] = iden
                    moff, changes = await proxy.saveNodeEdits(edits, meta)
                    if any(c[2] for c in changes):
                        return await futu
                    return None, ()

            proxy = await self.core.nexsroot.client.proxy()
            indx, changes = await proxy.saveLayerNodeEdits(self.iden, edits, meta)
            await self.core.nexsroot.waitOffs(indx)
            return indx, changes

        return await self.saveToNexs('edits', edits, meta)

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

            sode = self._genStorNode(buid)

            changes = []
            for edit in edits:

                delt = await self.editors[edit[0]](buid, form, edit, sode, meta)
                if delt and edit[2]:
                    nodeedits.extend(edit[2])

                changes.extend(delt)

                await asyncio.sleep(0)

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
            return False

        if sode.get('props'):
            return False

        if sode.get('tags'):
            return False

        if sode.get('tagprops'):
            return False

        if self.dataslab.prefexists(buid, self.nodedata):
            return False

        if self.layrslab.prefexists(buid, db=self.edgesn1):
            return False

        # no more refs in this layer.  time to pop it...
        try:
            abrv = self.getPropAbrv(sode.get('form'), None)
            self.layrslab.delete(abrv, val=buid, db=self.byform)
        except s_exc.NoSuchAbrv:
            pass
        self.dirty.pop(buid, None)
        self.buidcache.pop(buid, None)
        self.layrslab.delete(buid, db=self.bybuidv3)

        return True

    async def storNodeEditsNoLift(self, nodeedits, meta):
        '''
        Execute a series of node edit operations.

        Does not return the updated nodes.
        '''
        self._reqNotReadOnly()
        await self._push('edits', nodeedits, meta)

    async def _editNodeAdd(self, buid, form, edit, sode, meta):

        valt = edit[1]
        valu, stortype = valt
        if sode.get('valu') == valt:
            return ()

        abrv = self.setPropAbrv(form, None)

        if sode.get('form') is None:
            self.layrslab.put(abrv, buid, db=self.byform)

        sode['valu'] = valt
        self.setSodeDirty(buid, sode, form)

        if stortype & STOR_FLAG_ARRAY:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byarray)
                await asyncio.sleep(0)

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
        retn.extend(await self._editPropSet(buid, form, edit, sode, meta))

        return retn

    async def _editNodeDel(self, buid, form, edit, sode, meta):

        valt = sode.get('valu', None)
        if valt is None:
            self.mayDelBuid(buid, sode)
            return ()

        valu, stortype = valt

        abrv = self.setPropAbrv(form, None)

        if stortype & STOR_FLAG_ARRAY:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byarray)
                await asyncio.sleep(0)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)

        self.formcounts.inc(form, valu=-1)
        if self.nodeDelHook is not None:
            self.nodeDelHook()

        await self._wipeNodeData(buid)
        await self._delNodeEdges(buid)

        self.buidcache.pop(buid, None)

        sode.pop('valu', None)

        if not self.mayDelBuid(buid, sode):
            self.setSodeDirty(buid, sode, form)

        return (
            (EDIT_NODE_DEL, (valu, stortype), ()),
        )

    async def _editPropSet(self, buid, form, edit, sode, meta):

        prop, valu, oldv, stortype = edit[1]

        oldv, oldt = sode['props'].get(prop, (None, None))

        abrv = self.setPropAbrv(form, prop)
        univabrv = None

        if prop[0] == '.':  # '.' to detect universal props (as quickly as possible)
            univabrv = self.setPropAbrv(None, prop)

        if oldv is not None:

            # merge intervals and min times
            if stortype == STOR_TYPE_IVAL:
                valu = (min(*oldv, *valu), max(*oldv, *valu))

            elif stortype == STOR_TYPE_MINTIME:
                valu = min(valu, oldv)

            elif stortype == STOR_TYPE_MAXTIME:
                valu = max(valu, oldv)

            if valu == oldv and stortype == oldt:
                return ()

            if oldt & STOR_FLAG_ARRAY:

                realtype = oldt & 0x7fff

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(abrv + oldi, buid, db=self.byarray)
                    if univabrv is not None:
                        self.layrslab.delete(univabrv + oldi, buid, db=self.byarray)

                    if realtype == STOR_TYPE_NDEF:
                        self.layrslab.delete(oldi, buid + abrv, db=self.byndef)

                    await asyncio.sleep(0)

                for indx in self.getStorIndx(STOR_TYPE_MSGP, oldv):
                    self.layrslab.delete(abrv + indx, buid, db=self.byprop)
                    if univabrv is not None:
                        self.layrslab.delete(univabrv + indx, buid, db=self.byprop)

            else:

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(abrv + oldi, buid, db=self.byprop)
                    if univabrv is not None:
                        self.layrslab.delete(univabrv + oldi, buid, db=self.byprop)

                    if oldt == STOR_TYPE_NDEF:
                        self.layrslab.delete(oldi, buid + abrv, db=self.byndef)

        if sode.get('form') is None:
            formabrv = self.setPropAbrv(form, None)
            self.layrslab.put(formabrv, buid, db=self.byform)

        sode['props'][prop] = (valu, stortype)
        self.setSodeDirty(buid, sode, form)

        if stortype & STOR_FLAG_ARRAY:

            realtype = stortype & 0x7fff

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byarray)
                if univabrv is not None:
                    self.layrslab.put(univabrv + indx, buid, db=self.byarray)

                if realtype == STOR_TYPE_NDEF:
                    self.layrslab.put(indx, buid + abrv, db=self.byndef)

                await asyncio.sleep(0)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.put(univabrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.put(abrv + indx, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.put(univabrv + indx, buid, db=self.byprop)

                if stortype == STOR_TYPE_NDEF:
                    self.layrslab.put(indx, buid + abrv, db=self.byndef)

        return (
            (EDIT_PROP_SET, (prop, valu, oldv, stortype), ()),
        )

    async def _editPropDel(self, buid, form, edit, sode, meta):

        prop, oldv, stortype = edit[1]

        abrv = self.setPropAbrv(form, prop)
        univabrv = None

        if prop[0] == '.':  # '.' to detect universal props (as quickly as possible)
            univabrv = self.setPropAbrv(None, prop)

        valt = sode['props'].get(prop, None)
        if valt is None:
            self.mayDelBuid(buid, sode)
            return ()

        valu, stortype = valt

        if stortype & STOR_FLAG_ARRAY:

            realtype = stortype & 0x7fff

            for aval in valu:
                for indx in self.getStorIndx(realtype, aval):
                    self.layrslab.delete(abrv + indx, buid, db=self.byarray)
                    if univabrv is not None:
                        self.layrslab.delete(univabrv + indx, buid, db=self.byarray)

                    if realtype == STOR_TYPE_NDEF:
                        self.layrslab.delete(indx, buid + abrv, db=self.byndef)

                await asyncio.sleep(0)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.delete(univabrv + indx, buid, db=self.byprop)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.delete(univabrv + indx, buid, db=self.byprop)

                if stortype == STOR_TYPE_NDEF:
                    self.layrslab.delete(indx, buid + abrv, db=self.byndef)

        sode['props'].pop(prop, None)

        if not self.mayDelBuid(buid, sode):
            self.setSodeDirty(buid, sode, form)

        return (
            (EDIT_PROP_DEL, (prop, valu, stortype), ()),
        )

    async def _editTagSet(self, buid, form, edit, sode, meta):

        if form is None:  # pragma: no cover
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

        if sode.get('form') is None:
            self.layrslab.put(formabrv, buid, db=self.byform)

        sode['tags'][tag] = valu
        self.setSodeDirty(buid, sode, form)

        self.layrslab.put(tagabrv + formabrv, buid, db=self.bytag)

        return (
            (EDIT_TAG_SET, (tag, valu, oldv), ()),
        )

    async def _editTagDel(self, buid, form, edit, sode, meta):

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

    async def _editTagPropSet(self, buid, form, edit, sode, meta):

        if form is None:  # pragma: no cover
            logger.warning(f'Invalid tagprop set edit, form is None: {edit}')
            return ()

        tag, prop, valu, oldv, stortype = edit[1]

        tp_abrv = self.setTagPropAbrv(None, tag, prop)
        ftp_abrv = self.setTagPropAbrv(form, tag, prop)

        tp_dict = sode['tagprops'].get(tag)
        if tp_dict:
            oldv, oldt = tp_dict.get(prop, (None, None))
            if oldv is not None:

                if stortype == STOR_TYPE_IVAL:
                    valu = (min(*oldv, *valu), max(*oldv, *valu))

                elif stortype == STOR_TYPE_MINTIME:
                    valu = min(valu, oldv)

                elif stortype == STOR_TYPE_MAXTIME:
                    valu = max(valu, oldv)

                if valu == oldv and stortype == oldt:
                    return ()

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(tp_abrv + oldi, buid, db=self.bytagprop)
                    self.layrslab.delete(ftp_abrv + oldi, buid, db=self.bytagprop)

        if sode.get('form') is None:
            formabrv = self.setPropAbrv(form, None)
            self.layrslab.put(formabrv, buid, db=self.byform)

        if tag not in sode['tagprops']:
            sode['tagprops'][tag] = {}
        sode['tagprops'][tag][prop] = (valu, stortype)
        self.setSodeDirty(buid, sode, form)

        kvpairs = []
        for indx in self.getStorIndx(stortype, valu):
            kvpairs.append((tp_abrv + indx, buid))
            kvpairs.append((ftp_abrv + indx, buid))

        await self.layrslab.putmulti(kvpairs, db=self.bytagprop)

        return (
            (EDIT_TAGPROP_SET, (tag, prop, valu, oldv, stortype), ()),
        )

    async def _editTagPropDel(self, buid, form, edit, sode, meta):
        tag, prop, valu, stortype = edit[1]

        tp_dict = sode['tagprops'].get(tag)
        if not tp_dict:
            self.mayDelBuid(buid, sode)
            return ()

        oldv, oldt = tp_dict.pop(prop, (None, None))
        if not tp_dict.get(tag):
            sode['tagprops'].pop(tag, None)
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

    async def _editNodeDataSet(self, buid, form, edit, sode, meta):

        name, valu, oldv = edit[1]
        abrv = self.setPropAbrv(name, None)

        byts = s_msgpack.en(valu)
        oldb = self.dataslab.replace(buid + abrv, byts, db=self.nodedata)
        if oldb == byts:
            return ()

        # a bit of special case...
        if sode.get('form') is None:
            self.setSodeDirty(buid, sode, form)
            formabrv = self.setPropAbrv(form, None)
            self.layrslab.put(formabrv, buid, db=self.byform)

        if oldb is not None:
            oldv = s_msgpack.un(oldb)

        self.dataslab.put(abrv, buid, db=self.dataname)

        return (
            (EDIT_NODEDATA_SET, (name, valu, oldv), ()),
        )

    async def _editNodeDataDel(self, buid, form, edit, sode, meta):

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

    async def _editNodeEdgeAdd(self, buid, form, edit, sode, meta):

        if form is None:  # pragma: no cover
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
            formabrv = self.setPropAbrv(form, None)
            self.layrslab.put(formabrv, buid, db=self.byform)

        self.layrslab.put(venc, buid + n2buid, db=self.byverb)
        self.layrslab.put(n1key, n2buid, db=self.edgesn1)
        self.layrslab.put(n2buid + venc, buid, db=self.edgesn2)
        self.layrslab.put(buid + n2buid, venc, db=self.edgesn1n2)

        return (
            (EDIT_EDGE_ADD, (verb, n2iden), ()),
        )

    async def _editNodeEdgeDel(self, buid, form, edit, sode, meta):

        verb, n2iden = edit[1]

        venc = verb.encode()
        n2buid = s_common.uhex(n2iden)

        if not self.layrslab.delete(buid + venc, n2buid, db=self.edgesn1):
            self.mayDelBuid(buid, sode)
            return ()

        self.layrslab.delete(venc, buid + n2buid, db=self.byverb)
        self.layrslab.delete(n2buid + venc, buid, db=self.edgesn2)
        self.layrslab.delete(buid + n2buid, venc, db=self.edgesn1n2)

        self.mayDelBuid(buid, sode)
        return (
            (EDIT_EDGE_DEL, (verb, n2iden), ()),
        )

    async def getEdgeVerbs(self):

        for lkey in self.layrslab.scanKeys(db=self.byverb, nodup=True):
            yield lkey.decode()

    async def getEdges(self, verb=None):

        if verb is None:

            for lkey, lval in self.layrslab.scanByFull(db=self.byverb):
                yield (s_common.ehex(lval[:32]), lkey.decode(), s_common.ehex(lval[32:]))

            return

        for _, lval in self.layrslab.scanByDups(verb.encode(), db=self.byverb):
            yield (s_common.ehex(lval[:32]), verb, s_common.ehex(lval[32:]))

    async def _delNodeEdges(self, buid):
        for lkey, n2buid in self.layrslab.scanByPref(buid, db=self.edgesn1):
            venc = lkey[32:]
            self.layrslab.delete(venc, buid + n2buid, db=self.byverb)
            self.layrslab.delete(lkey, n2buid, db=self.edgesn1)
            self.layrslab.delete(n2buid + venc, buid, db=self.edgesn2)
            self.layrslab.delete(buid + n2buid, venc, db=self.edgesn1n2)
            await asyncio.sleep(0)

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

    async def iterNodeEdgeVerbsN1(self, buid):
        for lkey in self.layrslab.scanKeysByPref(buid, db=self.edgesn1, nodup=True):
            yield lkey[32:].decode()

    async def iterNodeEdgesN2(self, buid, verb=None):
        pref = buid
        if verb is not None:
            pref += verb.encode()

        for lkey, n1buid in self.layrslab.scanByPref(pref, db=self.edgesn2):
            verb = lkey[32:].decode()
            yield verb, s_common.ehex(n1buid)

    async def iterEdgeVerbs(self, n1buid, n2buid):
        for lkey, venc in self.layrslab.scanByDups(n1buid + n2buid, db=self.edgesn1n2):
            yield venc.decode()

    async def hasNodeEdge(self, buid1, verb, buid2):
        lkey = buid1 + verb.encode()
        return self.layrslab.hasdup(lkey, buid2, db=self.edgesn1)

    async def getNdefRefs(self, buid):
        for _, byts in self.layrslab.scanByDups(buid, db=self.byndef):
            yield byts[:32], byts[32:]

    async def iterFormRows(self, form, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes of a single form, optionally (re)starting at startvalu.

        Args:
            form (str):  A form name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        try:
            indxby = IndxByForm(self, form)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterPropRows(self, form, prop, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes with a particular secondary property, optionally (re)starting at startvalu.

        Args:
            form (str):  A form name.
            prop (str):  A universal property name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        try:
            indxby = IndxByProp(self, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterUnivRows(self, prop, stortype=None, startvalu=None):
        '''
        Yields buid, valu tuples of nodes with a particular universal property, optionally (re)starting at startvalu.

        Args:
            prop (str):  A universal property name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(buid, valu)]
        '''
        try:
            indxby = IndxByProp(self, None, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterTagRows(self, tag, form=None, starttupl=None):
        '''
        Yields (buid, (valu, form)) values that match a tag and optional form, optionally (re)starting at starttupl.

        Args:
            tag (str): the tag to match
            form (Optional[str]):  if present, only yields buids of nodes that match the form.
            starttupl (Optional[Tuple[buid, form]]):  if present, (re)starts the stream of values there.

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
        Yields (buid, valu) that match a tag:prop, optionally (re)starting at startvalu.

        Args:
            tag (str):  tag name
            prop (str):  prop name
            form (Optional[str]):  optional form name
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

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

    async def iterNodeDataKeys(self, buid):
        '''
        Return a generator of all a buid's node data keys
        '''
        for lkey in self.dataslab.scanKeysByPref(buid, db=self.nodedata, nodup=True):
            abrv = lkey[32:]
            prop = self.getAbrvProp(abrv)
            yield prop[0]

    async def confirmLayerEditPerms(self, user, gateiden, delete=False):
        if delete:
            perm_forms = ('node', 'del')
            perm_props = ('node', 'prop', 'del')
            perm_tags = ('node', 'tag', 'del')
            perm_ndata = ('node', 'data', 'pop')
            perm_edges = ('node', 'edge', 'del')
        else:
            perm_forms = ('node', 'add')
            perm_props = ('node', 'prop', 'set')
            perm_tags = ('node', 'tag', 'add')
            perm_ndata = ('node', 'data', 'set')
            perm_edges = ('node', 'edge', 'add')

        if user.allowed(('node',), gateiden=gateiden, deepdeny=True):
            return

        allow_forms = user.allowed(perm_forms, gateiden=gateiden, deepdeny=True)
        allow_props = user.allowed(perm_props, gateiden=gateiden, deepdeny=True)
        allow_tags = user.allowed(perm_tags, gateiden=gateiden, deepdeny=True)
        allow_ndata = user.allowed(perm_ndata, gateiden=gateiden, deepdeny=True)
        allow_edges = user.allowed(perm_edges, gateiden=gateiden, deepdeny=True)

        if all((allow_forms, allow_props, allow_tags, allow_ndata, allow_edges)):
            return

        # nodes & props
        if not allow_forms or not allow_props:
            async for byts, abrv in s_coro.pause(self.propabrv.slab.scanByFull(db=self.propabrv.name2abrv)):
                form, prop = s_msgpack.un(byts)
                if form is None: # pragma: no cover
                    continue

                if self.layrslab.prefexists(abrv, db=self.byprop):
                    if prop and not allow_props:
                        realform = self.core.model.form(form)
                        if not realform: # pragma: no cover
                            mesg = f'Invalid form: {form}'
                            raise s_exc.NoSuchForm(mesg=mesg, form=form)

                        realprop = realform.prop(prop)
                        if not realprop: # pragma: no cover
                            mesg = f'Invalid prop: {form}:{prop}'
                            raise s_exc.NoSuchProp(mesg=mesg, form=form, prop=prop)

                        if delete:
                            self.core.confirmPropDel(user, realprop, gateiden)
                        else:
                            self.core.confirmPropSet(user, realprop, gateiden)

                    elif not prop and not allow_forms:
                        user.confirm(perm_forms + (form,), gateiden=gateiden)

        # tagprops
        if not allow_tags:
            async for byts, abrv in s_coro.pause(self.tagpropabrv.slab.scanByFull(db=self.tagpropabrv.name2abrv)):
                info = s_msgpack.un(byts)
                if None in info or len(info) != 3:
                    continue

                if self.layrslab.prefexists(abrv, db=self.bytagprop):
                    perm = perm_tags + tuple(info[1].split('.'))
                    user.confirm(perm, gateiden=gateiden)

        # nodedata
        if not allow_ndata:
            async for abrv in s_coro.pause(self.dataslab.scanKeys(db=self.dataname, nodup=True)):
                name, _ = self.getAbrvProp(abrv)
                perm = perm_ndata + (name,)
                user.confirm(perm, gateiden=gateiden)

        # edges
        if not allow_edges:
            async for verb in s_coro.pause(self.layrslab.scanKeys(db=self.byverb, nodup=True)):
                perm = perm_edges + (verb.decode(),)
                user.confirm(perm, gateiden=gateiden)

        # tags
        # NB: tag perms should be yielded for every leaf on every node in the layer
        if not allow_tags:
            async with self.core.getSpooledDict() as tags:

                # Collect all tag abrvs for all nodes in the layer
                async for lkey, buid in s_coro.pause(self.layrslab.scanByFull(db=self.bytag)):
                    abrv = lkey[:8]
                    abrvs = list(tags.get(buid, []))
                    abrvs.append(abrv)
                    await tags.set(buid, abrvs)

                # Iterate over each node and it's tags
                async for buid, abrvs in s_coro.pause(tags.items()):
                    seen = {}

                    if len(abrvs) == 1:
                        # Easy optimization: If there's only one tag abrv, then it's a
                        # leaf by default
                        name = self.tagabrv.abrvToName(abrv)
                        key = tuple(name.split('.'))
                        perm = perm_tags + key
                        user.confirm(perm, gateiden=gateiden)

                    else:
                        for abrv in abrvs:
                            name = self.tagabrv.abrvToName(abrv)
                            parts = tuple(name.split('.'))
                            for idx in range(1, len(parts) + 1):
                                key = tuple(parts[:idx])
                                seen.setdefault(key, 0)
                                seen[key] += 1

                        for key, count in seen.items():
                            if count == 1:
                                perm = perm_tags + key
                                user.confirm(perm, gateiden=gateiden)

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

            for tag, propdict in sode.get('tagprops', {}).items():
                for prop, (valu, stortype) in propdict.items():
                    edits.append((EDIT_TAGPROP_SET, (tag, prop, valu, None, stortype), ()))

            async for prop, valu in self.iterNodeData(buid):
                edits.append((EDIT_NODEDATA_SET, (prop, valu, None), ()))

            async for verb, n2iden in self.iterNodeEdgesN1(buid):
                edits.append((EDIT_EDGE_ADD, (verb, n2iden), ()))

            yield nodeedit

    async def initUpstreamSync(self, url):
        self.activetasks.append(self.schedCoro(self._initUpstreamSync(url)))

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

            except asyncio.CancelledError:  # pragma: no cover
                return

            except Exception:
                logger.exception('error in initUpstreamSync loop')

            await self.waitfini(1)

    async def _wipeNodeData(self, buid):
        '''
        Remove all node data for a buid
        '''
        for lkey, _ in self.dataslab.scanByPref(buid, db=self.nodedata):
            abrv = lkey[32:]
            buid = lkey[:32]
            self.dataslab.delete(lkey, db=self.nodedata)
            self.dataslab.delete(abrv, buid, db=self.dataname)
            await asyncio.sleep(0)

    async def getModelVers(self):
        return self.layrinfo.get('model:version', (-1, -1, -1))

    async def setModelVers(self, vers):
        self._reqNotReadOnly()
        return await self._push('layer:set:modelvers', vers)

    @s_nexus.Pusher.onPush('layer:set:modelvers')
    async def _setModelVers(self, vers):
        self.layrinfo['model:version'] = vers
        self.core.layerdefs.set(self.iden, self.layrinfo)

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

    async def getStorNodesByForm(self, form):
        '''
        Yield (buid, sode) tuples for nodes of a given form with props/tags/tagprops/edges/nodedata in this layer.
        '''
        try:
            abrv = self.getPropAbrv(form, None)
        except s_exc.NoSuchAbrv:
            return

        for _, buid in self.layrslab.scanByDups(abrv, db=self.byform):
            sode = await self.getStorNode(buid)
            yield buid, sode
            await asyncio.sleep(0)

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

    async def syncNodeEdits2(self, offs, wait=True, reverse=False):
        '''
        Once caught up with storage, yield them in realtime.

        Returns:
            Tuple of offset(int), nodeedits, meta(dict)
        '''
        if not self.logedits:
            return

        for offi, (nodeedits, meta) in self.nodeeditlog.iter(offs, reverse=reverse):
            yield (offi, nodeedits, meta)

        if wait:
            async with self.getNodeEditWindow() as wind:
                async for item in wind:
                    yield item

    async def syncNodeEdits(self, offs, wait=True, reverse=False):
        '''
        Identical to syncNodeEdits2, but doesn't yield meta
        '''
        async for offi, nodeedits, _meta in self.syncNodeEdits2(offs, wait=wait, reverse=reverse):
            yield (offi, nodeedits)

    async def syncIndexEvents(self, offs, matchdef, wait=True):
        '''
        Yield (offs, (buid, form, ETYPE, VALS, META)) tuples from the nodeedit log starting from the given offset.
        Only edits that match the filter in matchdef will be yielded.

        Notes:

            ETYPE is an constant EDIT_* above.  VALS is a tuple whose format depends on ETYPE, outlined in the comment
            next to the constant.  META is a dict that may contain keys 'user' and 'time' to represent the iden of the
            user that initiated the change, and the time that it took place, respectively.

            Additionally, every 1000 entries, an entry (offs, (None, None, EDIT_PROGRESS, (), ())) message is emitted.

            The matchdef dict may contain the following keys:  forms, props, tags, tagprops.  The value must be a
            sequence of strings.  Each key/val combination is treated as an "or", so each key and value yields more events.
            forms: EDIT_NODE_ADD and EDIT_NODE_DEL events.  Matches events for nodes with forms in the value list.
            props: EDIT_PROP_SET and EDIT_PROP_DEL events.  Values must be in form:prop or .universal form
            tags:  EDIT_TAG_SET and EDIT_TAG_DEL events.  Values must be the raw tag with no #.
            tagprops: EDIT_TAGPROP_SET and EDIT_TAGPROP_DEL events.   Values must be just the prop or tag:prop.

            Will not yield any values if this layer was not created with logedits enabled

        Args:
            offs(int): starting nexus/editlog offset
            matchdef(Dict[str, Sequence[str]]):  a dict describing which events are yielded
            wait(bool):  whether to pend and stream value until this layer is fini'd
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

    @contextlib.asynccontextmanager
    async def getNodeEditWindow(self):
        if not self.logedits:
            raise s_exc.BadConfValu(mesg='Layer logging must be enabled for getting nodeedits')

        async with await s_queue.Window.anit(maxsize=WINDOW_MAXSIZE) as wind:

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
