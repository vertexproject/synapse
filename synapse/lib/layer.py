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

    A node edit consists of a (<nid>, <form>, [edits]) tuple.  An edit is Tuple of (<type>, <info>, List[NodeEdits])
    where the first element is an int that matches to an EDIT_* constant below, the info is a tuple that varies
    depending on the first element, and the third element is a list of dependent NodeEdits that will only be applied
    if the edit actually makes a change.

Storage Node (<sode>)

    A storage node is a layer/storage optimized node representation which is similar to a "packed node".
    A storage node *may* be partial ( as it is produced by a given layer ) and are joined by the view/snap
    into "full" storage nodes which are used to construct Node() instances.

    Sode format::

        (<nid>, {

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
import weakref
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

        return await self.layr.saveNodeEdits(nodeedits, meta)

    async def storNodeEditsNoLift(self, nodeedits, meta=None):

        await self._reqUserAllowed(self.writeperm)

        if meta is None:
            meta = {'time': s_common.now(), 'user': self.user.iden}

        await self.layr.storNodeEditsNoLift(nodeedits, meta)

    async def syncNodeEdits(self, offs, wait=True, compat=False):
        '''
        Yield (offs, nodeedits) tuples from the nodeedit log starting from the given offset.

        Once caught up with storage, yield them in realtime.
        '''
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.syncNodeEdits(offs, wait=wait, compat=compat):
            yield item

    async def syncNodeEdits2(self, offs, wait=True, compat=False):
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.syncNodeEdits2(offs, wait=wait, compat=compat):
            yield item

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

NID_CACHE_SIZE = 10000

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

# STOR_TYPE_TOMB      = ??
# STOR_TYPE_FIXED     = ??

STOR_FLAG_ARRAY = 0x8000

# Edit types (etyp)

EDIT_NODE_ADD = 0      # (<etyp>, (<valu>, <type>))
EDIT_NODE_DEL = 1      # (<etyp>, (<oldv>, <type>))
EDIT_PROP_SET = 2      # (<etyp>, (<prop>, <valu>, <oldv>, <type>))
EDIT_PROP_DEL = 3      # (<etyp>, (<prop>, <oldv>, <type>))
EDIT_TAG_SET = 4       # (<etyp>, (<tag>, <valu>, <oldv>))
EDIT_TAG_DEL = 5       # (<etyp>, (<tag>, <oldv>))
EDIT_TAGPROP_SET = 6   # (<etyp>, (<tag>, <prop>, <valu>, <oldv>, <type>))
EDIT_TAGPROP_DEL = 7   # (<etyp>, (<tag>, <prop>, <oldv>, <type>))
EDIT_NODEDATA_SET = 8  # (<etyp>, (<name>, <valu>, <oldv>))
EDIT_NODEDATA_DEL = 9  # (<etyp>, (<name>, <oldv>))
EDIT_EDGE_ADD = 10     # (<etyp>, (<verb>, <destnodeiden>))
EDIT_EDGE_DEL = 11     # (<etyp>, (<verb>, <destnodeiden>))

EDIT_PROGRESS = 100   # (used by syncIndexEvents) (<etyp>, ())

INDX_PROP = b'\x00\x00'
INDX_TAGPROP = b'\x00\x01'

INDX_ARRAY = b'\x00\x02'

INDX_EDGE_N1 = b'\x00\x03'
INDX_EDGE_N2 = b'\x00\x04'
INDX_EDGE_N1N2 = b'\x00\x05'
INDX_EDGE_VERB = b'\x00\x06'

INDX_TAG = b'\x00\x07'
INDX_TAG_MAX = b'\x00\x08'
INDX_TAG_DURATION = b'\x00\x09'

INDX_IVAL_MAX = b'\x00\x0a'
INDX_IVAL_DURATION = b'\x00\x0b'

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

    def getStorType(self):
        raise s_exc.NoSuchImpl(name='getStorType')

    def keyNidsByDups(self, indx, reverse=False):
        if reverse:
            yield from self.layr.layrslab.scanByDupsBack(self.abrv + indx, db=self.db)
        else:
            yield from self.layr.layrslab.scanByDups(self.abrv + indx, db=self.db)

    def keyNidsByPref(self, indx=b'', reverse=False):
        if reverse:
            yield from self.layr.layrslab.scanByPrefBack(self.abrv + indx, db=self.db)
        else:
            yield from self.layr.layrslab.scanByPref(self.abrv + indx, db=self.db)

    def keyNidsByRange(self, minindx, maxindx, reverse=False):
        if reverse:
            yield from self.layr.layrslab.scanByRangeBack(self.abrv + maxindx, lmin=self.abrv + minindx, db=self.db)
        else:
            yield from self.layr.layrslab.scanByRange(self.abrv + minindx, lmax=self.abrv + maxindx, db=self.db)

    def hasIndxNid(self, indx, nid):
        return self.layr.layrslab.hasdup(self.abrv + indx, nid, db=self.db)

    def indxToValu(self, indx):
        stortype = self.getStorType()
        return stortype.decodeIndx(indx)

    def getNodeValu(self, nid, indx=None):

        if indx is not None:
            valu = self.indxToValu(indx)
            if valu is not s_common.novalu:
                return valu

        sode = self.layr._getStorNode(nid)
        if sode is None:
            return s_common.novalu

        return self.getSodeValu(sode)

class IndxByForm(IndxBy):

    def __init__(self, layr, form):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_PROP, form, None)
        IndxBy.__init__(self, layr, abrv, layr.indxdb)

        self.form = form

    def getStorType(self):
        form = self.layr.core.model.form(self.form)
        return self.layr.stortypes[form.type.stortype]

    def getSodeValu(self, sode):

        valt = sode.get('valu')
        if valt is not None:
            return valt[0]

        return s_common.novalu

class IndxByProp(IndxBy):

    def __init__(self, layr, form, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_PROP, form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop

    def getStorType(self):

        if self.form is not None:
            form = self.layr.core.model.form(self.form)
            typeindx = form.props.get(self.prop).type.stortype
        else:
            typeindx = self.layr.core.model.prop(self.prop).type.stortype

        return self.layr.stortypes[typeindx]

    def getSodeValu(self, sode):
        valt = sode['props'].get(self.prop)
        if valt is not None:
            return valt[0]

        return s_common.novalu

    def __repr__(self):
        if self.form:
            return f'IndxByProp: {self.form}:{self.prop}'
        return f'IndxByProp: {self.prop}'

class IndxByPropArray(IndxBy):

    def __init__(self, layr, form, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_ARRAY, form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop

    def getNodeValu(self, nid, indx=None):
        sode = self.layr._getStorNode(nid)
        if sode is None: # pragma: no cover
            return s_common.novalu

        props = sode.get('props')
        if props is None:
            return s_common.novalu

        valt = props.get(self.prop)
        if valt is None:
            return s_common.novalu

        return valt[0]

    def __repr__(self):
        if self.form:
            return f'IndxByPropArray: {self.form}:{self.prop}'
        return f'IndxByPropArray: {self.prop}'

class IndxByPropIvalMin(IndxByProp):

    def keyNidsByRange(self, minindx, maxindx, reverse=False):
        strt = self.abrv + minindx + self.layr.ivaltimetype.zerobyts
        stop = self.abrv + maxindx + self.layr.ivaltimetype.fullbyts
        if reverse:
            yield from self.layr.layrslab.scanByRangeBack(stop, strt, db=self.db)
        else:
            yield from self.layr.layrslab.scanByRange(strt, stop, db=self.db)

class IndxByPropIvalMax(IndxBy):

    def __init__(self, layr, form, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_IVAL_MAX, form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop

class IndxByPropIvalDuration(IndxBy):

    def __init__(self, layr, form, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_IVAL_DURATION, form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop

class IndxByTagIval(IndxBy):

    def __init__(self, layr, form, tag):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_TAG, form, tag)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.tag = tag

class IndxByTagIvalMin(IndxByTagIval):

    def keyNidsByRange(self, minindx, maxindx, reverse=False):
        strt = self.abrv + minindx + self.layr.ivaltimetype.zerobyts
        stop = self.abrv + maxindx + self.layr.ivaltimetype.fullbyts
        if reverse:
            yield from self.layr.layrslab.scanByRangeBack(stop, strt, db=self.db)
        else:
            yield from self.layr.layrslab.scanByRange(strt, stop, db=self.db)

class IndxByTagIvalMax(IndxBy):

    def __init__(self, layr, form, tag):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_TAG_MAX, form, tag)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.tag = tag

class IndxByTagIvalDuration(IndxBy):

    def __init__(self, layr, form, tag):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_TAG_DURATION, form, tag)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.tag = tag

class IndxByTagProp(IndxBy):

    def __init__(self, layr, form, tag, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_TAGPROP, form, tag, prop)
        IndxBy.__init__(self, layr, abrv, layr.indxdb)

        self.form = form
        self.prop = prop
        self.tag = tag

    def getStorType(self):
        typeindx = self.layr.core.model.getTagProp(self.prop).type.stortype
        return self.layr.stortypes[typeindx]

    def getSodeValu(self, sode):

        tagprops = sode.get('tagprops')
        if tagprops is None:
            return s_common.novalu

        props = tagprops.get(self.tag)
        if not props:
            return s_common.novalu

        valt = props.get(self.prop)
        if valt is None:
            return s_common.novalu

        return valt[0]

class IndxByTagPropIvalMin(IndxByTagProp):

    def keyNidsByRange(self, minindx, maxindx, reverse=False):
        strt = self.abrv + minindx + self.layr.ivaltimetype.zerobyts
        stop = self.abrv + maxindx + self.layr.ivaltimetype.fullbyts
        if reverse:
            yield from self.layr.layrslab.scanByRangeBack(stop, strt, db=self.db)
        else:
            yield from self.layr.layrslab.scanByRange(strt, stop, db=self.db)

class IndxByTagPropIvalMax(IndxBy):

    def __init__(self, layr, form, tag, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_IVAL_MAX, form, tag, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop
        self.tag = tag

class IndxByTagPropIvalDuration(IndxBy):

    def __init__(self, layr, form, tag, prop):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_IVAL_DURATION, form, tag, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop
        self.tag = tag

class StorType:

    def __init__(self, layr, stortype):
        self.layr = layr
        self.stortype = stortype

        self.lifters = {}

    async def indxBy(self, liftby, cmpr, valu, reverse=False):
        func = self.lifters.get(cmpr)
        if func is None:
            raise s_exc.NoSuchCmpr(cmpr=cmpr)

        abrvlen = liftby.abrvlen
        async for lkey, buid in func(liftby, valu, reverse=reverse):
            yield lkey[abrvlen:], buid

    async def indxByForm(self, form, cmpr, valu, reverse=False):
        try:
            indxby = IndxByForm(self.layr, form)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def verifyNidProp(self, nid, form, prop, valu):
        indxby = IndxByProp(self.layr, form, prop)
        for indx in self.indx(valu):
            if not indxby.hasIndxNid(indx, nid):
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

        for lkey, nid in liftby.keyNidsByPref(reverse=reverse):

            await asyncio.sleep(0)

            indx = lkey[abrvlen:]
            storvalu = self.decodeIndx(indx)

            if storvalu == s_common.novalu:

                storvalu = liftby.getNodeValu(nid)

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
                yield lkey, nid

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
        indx = self._getIndxByts(valu)
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
            yield item

    async def _liftUtf8Range(self, liftby, valu, reverse=False):
        minindx = self._getIndxByts(valu[0])
        maxindx = self._getIndxByts(valu[1])
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftUtf8Prefix(self, liftby, valu, reverse=False):
        indx = self._getIndxByts(valu)
        for item in liftby.keyNidsByPref(indx, reverse=reverse):
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
        indx = self.getHierIndx(valu)
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
            yield item

    async def _liftHierPref(self, liftby, valu, reverse=False):
        indx = self.getHierIndx(valu)
        for item in liftby.keyNidsByPref(indx, reverse=reverse):
            yield item

class StorTypeLoc(StorTypeHier):
    def __init__(self, layr):
        StorTypeHier.__init__(self, layr, STOR_TYPE_LOC)

class StorTypeTag(StorTypeHier):

    def __init__(self, layr):
        StorTypeHier.__init__(self, layr, STOR_TYPE_TAG)

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
            indx = self._getIndxByts(valu[1:][::-1])
            for item in liftby.keyNidsByPref(indx, reverse=reverse):
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
        indx = self.getIPv6Indx(valu)
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
            yield item

    async def _liftIPv6Range(self, liftby, valu, reverse=False):
        minindx = self.getIPv6Indx(valu[0])
        maxindx = self.getIPv6Indx(valu[1])

        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftIPv6Lt(self, liftby, norm, reverse=False):
        minindx = self.getIPv6Indx('::')
        maxindx = self.getIPv6Indx(norm)
        maxindx = (int.from_bytes(maxindx) - 1).to_bytes(16)

        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftIPv6Gt(self, liftby, norm, reverse=False):
        minindx = self.getIPv6Indx(norm)
        minindx = (int.from_bytes(minindx) + 1).to_bytes(16)
        maxindx = self.getIPv6Indx('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')

        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftIPv6Le(self, liftby, norm, reverse=False):
        minindx = self.getIPv6Indx('::')
        maxindx = self.getIPv6Indx(norm)

        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftIPv6Ge(self, liftby, norm, reverse=False):
        minindx = self.getIPv6Indx(norm)
        maxindx = self.getIPv6Indx('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')

        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
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

        pkey = indx.to_bytes(self.size, 'big')
        for item in liftby.keyNidsByDups(pkey, reverse=reverse):
            yield item

    async def _liftIntGt(self, liftby, valu, reverse=False):
        async for item in self._liftIntGe(liftby, valu + 1, reverse=reverse):
            yield item

    async def _liftIntGe(self, liftby, valu, reverse=False):
        minv = valu + self.offset
        if minv > self.maxval:
            return

        minv = max(minv, 0)

        minindx = minv.to_bytes(self.size, 'big')
        maxindx = self.fullbyts
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftIntLt(self, liftby, valu, reverse=False):
        async for item in self._liftIntLe(liftby, valu - 1, reverse=reverse):
            yield item

    async def _liftIntLe(self, liftby, valu, reverse=False):
        maxv = valu + self.offset
        if maxv < 0:
            return

        maxv = min(maxv, self.maxval)

        minindx = self.zerobyts
        maxindx = maxv.to_bytes(self.size, 'big')
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftIntRange(self, liftby, valu, reverse=False):
        minv = valu[0] + self.offset
        maxv = valu[1] + self.offset
        if minv > self.maxval or maxv < 0:
            return

        minv = max(minv, 0)
        maxv = min(maxv, self.maxval)

        minindx = minv.to_bytes(self.size, 'big')
        maxindx = maxv.to_bytes(self.size, 'big')
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
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
        indx = self.getHugeIndx(valu)
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
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
        minindx = self.getHugeIndx(valu)
        for item in liftby.keyNidsByRange(minindx, self.fullbyts, reverse=reverse):
            yield item

    async def _liftHugeLe(self, liftby, valu, reverse=False):
        maxindx = self.getHugeIndx(valu)
        for item in liftby.keyNidsByRange(self.zerobyts, maxindx, reverse=reverse):
            yield item

    async def _liftHugeRange(self, liftby, valu, reverse=False):
        minindx = self.getHugeIndx(valu[0])
        maxindx = self.getHugeIndx(valu[1])
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
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
        for item in liftby.keyNidsByDups(self.fpack(valu), reverse=reverse):
            yield item

    async def _liftFloatGeCommon(self, liftby, valu, reverse=False):
        if math.isnan(valu):
            raise s_exc.NotANumberCompared()

        valupack = self.fpack(valu)

        if reverse:
            if math.copysign(1.0, valu) < 0.0:  # negative values and -0.0
                for item in liftby.keyNidsByRange(self.FloatPackPosMin, self.FloatPackPosMax, reverse=True):
                    yield item
                for item in liftby.keyNidsByRange(self.FloatPackNegMax, valupack):
                    yield item
            else:
                for item in liftby.keyNidsByRange(valupack, self.FloatPackPosMax, reverse=True):
                    yield item

        else:
            if math.copysign(1.0, valu) < 0.0:  # negative values and -0.0
                for item in liftby.keyNidsByRange(self.FloatPackNegMax, valupack, reverse=True):
                    yield item
                valupack = self.FloatPackPosMin

            for item in liftby.keyNidsByRange(valupack, self.FloatPackPosMax):
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
                for item in liftby.keyNidsByRange(self.FloatPackPosMin, valupack, reverse=True):
                    yield item
                valupack = self.FloatPackNegMax

            for item in liftby.keyNidsByRange(valupack, self.FloatPackNegMin):
                yield item
        else:
            if math.copysign(1.0, valu) > 0.0:
                for item in liftby.keyNidsByRange(self.FloatPackNegMax, self.FloatPackNegMin, reverse=True):
                    yield item
                for item in liftby.keyNidsByRange(self.FloatPackPosMin, valupack):
                    yield item
            else:
                for item in liftby.keyNidsByRange(valupack, self.FloatPackNegMin, reverse=True):
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
            for item in liftby.keyNidsByRange(pkeymin, pkeymax, reverse=reverse):
                yield item
            return

        if math.copysign(1.0, valumax) < 0.0:  # negative values and -0.0
            # Entire range is negative
            for item in liftby.keyNidsByRange(pkeymax, pkeymin, reverse=(not reverse)):
                yield item
            return

        if reverse:
            # Yield all values between max and 0
            for item in liftby.keyNidsByRange(self.FloatPackPosMin, pkeymax, reverse=True):
                yield item

            # Yield all values between -0 and min
            for item in liftby.keyNidsByRange(self.FloatPackNegMax, pkeymin):
                yield item

        else:
            # Yield all values between min and -0
            for item in liftby.keyNidsByRange(self.FloatPackNegMax, pkeymin, reverse=True):
                yield item

            # Yield all values between 0 and max
            for item in liftby.keyNidsByRange(self.FloatPackPosMin, pkeymax):
                yield item

class StorTypeGuid(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_GUID)
        self.lifters.update({
            '=': self._liftGuidEq,
            '^=': self._liftGuidPref,
        })

    async def _liftGuidPref(self, liftby, byts, reverse=False):
        # valu is already bytes of the guid prefix
        for item in liftby.keyNidsByPref(byts, reverse=reverse):
            yield item

    async def _liftGuidEq(self, liftby, valu, reverse=False):
        indx = s_common.uhex(valu)
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
            yield item

    def indx(self, valu):
        return (s_common.uhex(valu),)

    def decodeIndx(self, bytz):
        return s_common.ehex(bytz)

class StorTypeTime(StorTypeInt):

    def __init__(self, layr):
        StorTypeInt.__init__(self, layr, STOR_TYPE_TIME, 8, True)
        self.futsize = 0x7fffffffffffffff
        self.futbyts = (self.futsize + self.offset).to_bytes(8, 'big')
        self.maxbyts = (self.futsize + self.offset - 1).to_bytes(8, 'big')
        self.lifters.update({
            '@=': self._liftAtIval,
        })

    async def _liftAtIval(self, liftby, valu, reverse=False):
        minindx = self.getIntIndx(valu[0])
        maxindx = self.getIntIndx(valu[1] - 1)
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

class StorTypeIval(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IVAL)
        self.timetype = StorTypeTime(layr)
        self.maxdura = (2 ** (8 * 8) - 1).to_bytes(8, 'big')
        self.lifters.update({
            '=': self._liftIvalEq,
            '@=': self._liftIvalAt,
            'min@=': self._liftIvalPartAt,
            'max@=': self._liftIvalPartAt,
        })

        for part in ('min', 'max', 'duration'):
            self.lifters.update({
                f'{part}=': self._liftIvalPartEq,
                f'{part}<': self._liftIvalPartLt,
                f'{part}>': self._liftIvalPartGt,
                f'{part}<=': self._liftIvalPartLe,
                f'{part}>=': self._liftIvalPartGe,
            })

        self.propindx = {
            'min@=': IndxByPropIvalMin,
            'max@=': IndxByPropIvalMax,
        }

        self.tagpropindx = {
            'min@=': IndxByTagPropIvalMin,
            'max@=': IndxByTagPropIvalMax,
        }

        self.tagindx = {
            'min@=': IndxByTagIvalMin,
            'max@=': IndxByTagIvalMax
        }

        for cmpr in ('=', '<', '>', '<=', '>='):
            self.tagindx[f'min{cmpr}'] = IndxByTagIvalMin
            self.propindx[f'min{cmpr}'] = IndxByPropIvalMin
            self.tagpropindx[f'min{cmpr}'] = IndxByTagPropIvalMin

            self.tagindx[f'max{cmpr}'] = IndxByTagIvalMax
            self.propindx[f'max{cmpr}'] = IndxByPropIvalMax
            self.tagpropindx[f'max{cmpr}'] = IndxByTagPropIvalMax

            self.tagindx[f'duration{cmpr}'] = IndxByTagIvalDuration
            self.propindx[f'duration{cmpr}'] = IndxByPropIvalDuration
            self.tagpropindx[f'duration{cmpr}'] = IndxByTagPropIvalDuration

    async def indxByProp(self, form, prop, cmpr, valu, reverse=False):
        try:
            indxtype = self.propindx.get(cmpr, IndxByProp)
            indxby = indxtype(self.layr, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByTagProp(self, form, tag, prop, cmpr, valu, reverse=False):
        try:
            indxtype = self.tagpropindx.get(cmpr, IndxByTagProp)
            indxby = indxtype(self.layr, form, tag, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByTag(self, tag, cmpr, valu, form=None, reverse=False):
        try:
            indxtype = self.tagindx.get(cmpr, IndxByTagIval)
            indxby = indxtype(self.layr, form, tag)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def _liftIvalEq(self, liftby, valu, reverse=False):
        indx = self.timetype.getIntIndx(valu[0]) + self.timetype.getIntIndx(valu[1])
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
            yield item

    async def _liftIvalAt(self, liftby, valu, reverse=False):
        minindx = self.timetype.getIntIndx(valu[0])
        maxindx = self.timetype.getIntIndx(valu[1] - 1)

        pkeymin = self.timetype.zerobyts * 2
        pkeymax = maxindx + self.timetype.fullbyts

        for lkey, nid in liftby.keyNidsByRange(pkeymin, pkeymax, reverse=reverse):

            # check for non-overlap right
            if lkey[-8:] <= minindx:
                continue

            yield lkey, nid

    async def _liftIvalPartEq(self, liftby, valu, reverse=False):
        indx = self.timetype.getIntIndx(valu)
        for item in liftby.keyNidsByPref(indx, reverse=reverse):
            yield item

    async def _liftIvalPartGt(self, liftby, valu, reverse=False):
        async for item in self._liftIvalPartGe(liftby, valu + 1, reverse=reverse):
            yield item

    async def _liftIvalPartGe(self, liftby, valu, reverse=False):
        pkeymin = self.timetype.getIntIndx(max(valu, 0))
        pkeymax = self.timetype.maxbyts
        for item in liftby.keyNidsByRange(pkeymin, pkeymax, reverse=reverse):
            yield item

    async def _liftIvalPartLt(self, liftby, valu, reverse=False):
        async for item in self._liftIvalPartLe(liftby, valu - 1, reverse=reverse):
            yield item

    async def _liftIvalPartLe(self, liftby, valu, reverse=False):
        maxv = min(valu, self.timetype.maxval)

        pkeymin = self.timetype.zerobyts
        pkeymax = self.timetype.getIntIndx(maxv)
        for item in liftby.keyNidsByRange(pkeymin, pkeymax, reverse=reverse):
            yield item

    async def _liftIvalPartAt(self, liftby, valu, reverse=False):
        pkeymin = self.timetype.getIntIndx(valu[0])
        pkeymax = self.timetype.getIntIndx(valu[1] - 1)
        for item in liftby.keyNidsByRange(pkeymin, pkeymax, reverse=reverse):
            yield item

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
        indx = s_common.buid(valu)
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
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
        indx = self._getLatLonIndx(valu)
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
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

        # scan by lon range and down-select the results to matches.
        for lkey, nid in liftby.keyNidsByRange(lonminindx, lonmaxindx, reverse=reverse):

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
                yield lkey, nid

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

class SodeEnvl:
    def __init__(self, layriden, sode):
        self.layriden = layriden
        self.sode = sode

    # any sorting that falls back to the envl are equal already...
    def __lt__(self, envl): return False

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

        self.mapasync = core.conf.get('layer:lmdb:map_async')
        self.maxreplaylog = core.conf.get('layer:lmdb:max_replay_log')

        # slim hooks to avoid async/fire
        self.nodeAddHook = None
        self.nodeDelHook = None

        path = s_common.genpath(self.dirn, 'layer_v2.lmdb')

        self.fresh = not os.path.exists(path)

        self.dirty = {}

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
        ]

        self.ivaltimetype = self.stortypes[STOR_TYPE_IVAL].timetype

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

        self.resolvers = [
            self._calcNodeAdd,
            self._calcNodeDel,
            self._calcPropSet,
            self._calcPropDel,
            self._calcTagSet,
            self._calcTagDel,
            self._calcTagPropSet,
            self._calcTagPropDel,
            self._calcNodeDataSet,
            self._calcNodeDataDel,
            self._calcNodeEdgeAdd,
            self._calcNodeEdgeDel,
        ]

        self.canrev = True
        self.ctorname = f'{self.__class__.__module__}.{self.__class__.__name__}'

        self.windows = []

        self.nidcache = s_cache.LruDict(NID_CACHE_SIZE)
        self.weakcache = weakref.WeakValueDictionary()

        self.onfini(self._onLayrFini)

        # this must be last!
        self.readonly = layrinfo.get('readonly')

    def _reqNotReadOnly(self):
        if self.readonly and not self.core.migration:
            mesg = f'Layer {self.iden} is read only!'
            raise s_exc.IsReadOnly(mesg=mesg)

    async def getEditSize(self):
        return self.nodeeditlog.size

    async def verifyNidTag(self, nid, formname, tagname, tagvalu):
        abrv = self.core.getIndxAbrv(INDX_TAG, None, tagname)
        if not self.layrslab.hasdup(abrv, nid, db=self.indxdb):
            yield ('NoTagIndex', {'nid': nid, 'tag': tagname, 'valu': tagvalu})

        abrv = self.core.getIndxAbrv(INDX_TAG, formname, tagname)
        if not self.layrslab.hasdup(abrv, nid, db=self.indxdb):
            yield ('NoTagIndex', {'nid': nid, 'form': formname, 'tag': tagname, 'valu': tagvalu})

    def _testDelTagIndx(self, nid, form, tag):
        tagabrv = self.core.setIndxAbrv(INDX_TAG, None, tag)
        tagformabrv = self.core.setIndxAbrv(INDX_TAG, form, tag)
        self.layrslab.delete(tagabrv, nid, db=self.indxdb)
        self.layrslab.delete(tagformabrv, nid, db=self.indxdb)

    def _testDelPropIndx(self, nid, form, prop):
        sode = self._getStorNode(nid)
        storvalu, stortype = sode['props'][prop]

        abrv = self.core.setIndxAbrv(INDX_PROP, form, prop)
        for indx in self.stortypes[stortype].indx(storvalu):
            self.layrslab.delete(abrv + indx, nid, db=self.indxdb)

    def _testDelTagStor(self, nid, form, tag):
        sode = self._getStorNode(nid)
        sode['tags'].pop(tag, None)
        self.dirty[nid] = sode

    def _testDelPropStor(self, nid, form, prop):
        sode = self._getStorNode(nid)
        sode['props'].pop(prop, None)
        self.dirty[nid] = sode

    def _testDelFormValuStor(self, nid, form):
        sode = self._getStorNode(nid)
        sode['valu'] = None
        self.dirty[nid] = sode

    def _testAddPropIndx(self, nid, form, prop, valu):
        modlprop = self.core.model.prop(f'{form}:{prop}')
        abrv = self.core.setIndxAbrv(INDX_PROP, form, prop)
        for indx in self.stortypes[modlprop.type.stortype].indx(valu):
            self.layrslab.put(abrv + indx, nid, db=self.indxdb)
            self.indxcounts.inc(abrv)

    def _testAddPropArrayIndx(self, nid, form, prop, valu):
        modlprop = self.core.model.prop(f'{form}:{prop}')
        abrv = self.core.setIndxAbrv(INDX_ARRAY, form, prop)
        for indx in self.getStorIndx(modlprop.type.stortype, valu):
            self.layrslab.put(abrv + indx, nid, db=self.indxdb)
            self.indxcounts.inc(abrv)

    def _testAddTagIndx(self, nid, form, tag):
        tagabrv = self.core.setIndxAbrv(INDX_TAG, None, tag)
        tagformabrv = self.core.setIndxAbrv(INDX_TAG, form, tag)
        self.layrslab.put(tagabrv, nid, db=self.indxdb)
        self.layrslab.put(tagformabrv, nid, db=self.indxdb)
        self.indxcounts.inc(tagabrv)
        self.indxcounts.inc(tagformabrv)

    def _testAddTagPropIndx(self, nid, form, tag, prop, valu):
        tpabrv = self.core.setIndxAbrv(INDX_TAGPROP, None, tag, prop)
        ftpabrv = self.core.setIndxAbrv(INDX_TAGPROP, form, tag, prop)

        tagprop = self.core.model.tagprop(prop)
        for indx in self.stortypes[tagprop.type.stortype].indx(valu):
            self.layrslab.put(tpabrv + indx, nid, db=self.indxdb)
            self.layrslab.put(ftpabrv + indx, nid, db=self.indxdb)
            self.indxcounts.inc(tpabrv)
            self.indxcounts.inc(ftpabrv)

    async def verify(self, config=None):

        if config is None:
            config = {}

        defconf = None
        if config.get('scanall', True):
            defconf = {}

        scans = config.get('scans', {})

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

        nodescan = scans.get('nodes', defconf)
        if nodescan is not None:
            async for error in self.verifyAllNids(nodescan):
                yield error

    async def verifyAllNids(self, scanconf=None):
        if scanconf is None:
            scanconf = {}

        async for nid, sode in self.getStorNodes():
            async for error in self.verifyByNid(nid, sode):
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

        for (form, name) in self.getTags():
            if form is None:
                continue

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

        for form, prop in self.getArrayFormProps():

            if include is not None and (form, prop) not in include:
                continue

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
        tagabrv = self.core.getIndxAbrv(INDX_TAG, None, tag)

        async def tryfix(lkey, nid, form):
            if autofix == 'node':
                sode = self._genStorNode(nid)
                sode.setdefault('form', form)
                sode['tags'][tag] = (None, None)
                self.dirty[nid] = sode
            elif autofix == 'index':
                self.layrslab.delete(lkey, nid, db=self.indxdb)

        for lkey, nid in self.layrslab.scanByPref(tagabrv, db=self.indxdb):

            await asyncio.sleep(0)

            (form, tag) = self.core.getAbrvIndx(lkey[:8])

            sode = self._getStorNode(nid)
            if not sode:
                await tryfix(lkey, nid, form)
                yield ('NoNodeForTagIndex', {'nid': s_common.ehex(nid), 'form': form, 'tag': tag})
                continue

            tags = sode.get('tags')
            if tags.get(tag) is None:
                await tryfix(lkey, nid, form)
                yield ('NoTagForTagIndex', {'nid': s_common.ehex(nid), 'form': form, 'tag': tag})
                continue

    async def verifyByProp(self, form, prop, autofix=None):

        abrv = self.core.getIndxAbrv(INDX_PROP, form, prop)

        async def tryfix(lkey, nid):
            if autofix == 'index':
                self.layrslab.delete(lkey, nid, db=self.indxdb)

        for lkey, nid in self.layrslab.scanByPref(abrv, db=self.indxdb):

            await asyncio.sleep(0)

            indx = lkey[len(abrv):]

            sode = self._getStorNode(nid)
            if not sode:
                await tryfix(lkey, nid)
                yield ('NoNodeForPropIndex', {'nid': s_common.ehex(nid), 'form': form, 'prop': prop, 'indx': indx})
                continue

            if prop is not None:
                props = sode.get('props')
                if props is None:
                    await tryfix(lkey, nid)
                    yield ('NoValuForPropIndex', {'nid': s_common.ehex(nid), 'form': form, 'prop': prop, 'indx': indx})
                    continue

                valu = props.get(prop)
                if valu is None:
                    await tryfix(lkey, nid)
                    yield ('NoValuForPropIndex', {'nid': s_common.ehex(nid), 'form': form, 'prop': prop, 'indx': indx})
                    continue
            else:
                valu = sode.get('valu')
                if valu is None:
                    await tryfix(lkey, nid)
                    yield ('NoValuForPropIndex', {'nid': s_common.ehex(nid), 'form': form, 'prop': prop, 'indx': indx})
                    continue

            propvalu, stortype = valu
            if stortype & STOR_FLAG_ARRAY:
                stortype = STOR_TYPE_MSGP

            try:
                for indx in self.stortypes[stortype].indx(propvalu):
                    if abrv + indx == lkey:
                        break
                else:
                    await tryfix(lkey, nid)
                    yield ('SpurPropKeyForIndex', {'nid': s_common.ehex(nid), 'form': form,
                                                   'prop': prop, 'indx': indx})

            except IndexError:
                await tryfix(lkey, nid)
                yield ('NoStorTypeForProp', {'nid': s_common.ehex(nid), 'form': form, 'prop': prop,
                                             'stortype': stortype})

    async def verifyByPropArray(self, form, prop, autofix=None):

        abrv = self.core.getIndxAbrv(INDX_ARRAY, form, prop)

        async def tryfix(lkey, nid):
            if autofix == 'index':
                self.layrslab.delete(lkey, nid, db=self.indxdb)

        for lkey, nid in self.layrslab.scanByPref(abrv, db=self.indxdb):

            await asyncio.sleep(0)

            indx = lkey[len(abrv):]

            sode = self._getStorNode(nid)
            if not sode:
                await tryfix(lkey, nid)
                yield ('NoNodeForPropArrayIndex', {'nid': s_common.ehex(nid), 'form': form,
                                                   'prop': prop, 'indx': indx})
                continue

            if prop is not None:
                props = sode.get('props')
                if props is None:
                    await tryfix(lkey, nid)
                    yield ('NoValuForPropArrayIndex', {'nid': s_common.ehex(nid), 'form': form,
                                                       'prop': prop, 'indx': indx})
                    continue

                valu = props.get(prop)
                if valu is None:
                    await tryfix(lkey, nid)
                    yield ('NoValuForPropArrayIndex', {'nid': s_common.ehex(nid),
                                                       'form': form, 'prop': prop, 'indx': indx})
                    continue
            else:
                valu = sode.get('valu')
                if valu is None:
                    await tryfix(lkey, nid)
                    yield ('NoValuForPropArrayIndex', {'nid': s_common.ehex(nid),
                                                       'form': form, 'prop': prop, 'indx': indx})
                    continue

            propvalu, stortype = valu

            try:
                for indx in self.getStorIndx(stortype, propvalu):
                    if abrv + indx == lkey:
                        break
                else:
                    await tryfix(lkey, nid)
                    yield ('SpurPropArrayKeyForIndex', {'nid': s_common.ehex(nid), 'form': form,
                                                        'prop': prop, 'indx': indx})

            except IndexError:
                await tryfix(lkey, nid)
                yield ('NoStorTypeForPropArray', {'nid': s_common.ehex(nid), 'form': form,
                                                  'prop': prop, 'stortype': stortype})

    async def verifyByTagProp(self, form, tag, prop, autofix=None):

        abrv = self.core.getIndxAbrv(INDX_TAGPROP, form, tag, prop)

        async def tryfix(lkey, nid):
            if autofix == 'index':
                self.layrslab.delete(lkey, nid, db=self.indxdb)

        for lkey, nid in self.layrslab.scanByPref(abrv, db=self.indxdb):

            await asyncio.sleep(0)

            indx = lkey[len(abrv):]

            sode = self._getStorNode(nid)
            if not sode:
                await tryfix(lkey, nid)
                yield ('NoNodeForTagPropIndex', {'nid': s_common.ehex(nid), 'form': form,
                                                 'tag': tag, 'prop': prop, 'indx': indx})
                continue

            tags = sode.get('tagprops')
            if tags is None:
                yield ('NoPropForTagPropIndex', {'nid': s_common.ehex(nid), 'form': form,
                                                 'tag': tag, 'prop': prop, 'indx': indx})
                continue

            props = tags.get(tag)
            if props is None:
                await tryfix(lkey, nid)
                yield ('NoPropForTagPropIndex', {'nid': s_common.ehex(nid), 'form': form,
                                                 'tag': tag, 'prop': prop, 'indx': indx})
                continue

            valu = props.get(prop)
            if valu is None:
                await tryfix(lkey, nid)
                yield ('NoValuForTagPropIndex', {'nid': s_common.ehex(nid), 'form': form,
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
                    await tryfix(lkey, nid)
                    yield ('SpurTagPropKeyForIndex', {'nid': s_common.ehex(nid), 'form': form,
                                                      'tag': tag, 'prop': prop, 'indx': indx})
            except IndexError:
                await tryfix(lkey, nid)
                yield ('NoStorTypeForTagProp', {'nid': s_common.ehex(nid), 'form': form,
                                                'tag': tag, 'prop': prop, 'stortype': stortype})

    async def verifyByNid(self, nid, sode):

        await asyncio.sleep(0)

        form = sode.get('form')
        stortags = sode.get('tags')
        if stortags:
            for tagname, storvalu in stortags.items():
                async for error in self.verifyNidTag(nid, form, tagname, storvalu):
                    yield error

        storprops = sode.get('props')
        if storprops:
            for propname, (storvalu, stortype) in storprops.items():

                # TODO: we dont support verifying array property indexes just yet...
                if stortype & STOR_FLAG_ARRAY:
                    continue

                try:
                    async for error in self.stortypes[stortype].verifyNidProp(nid, form, propname, storvalu):
                        yield error
                except IndexError as e:
                    yield ('NoStorTypeForProp', {'nid': s_common.ehex(nid), 'form': form, 'prop': propname,
                                                 'stortype': stortype})

    async def pack(self):
        ret = self.layrinfo.pack()
        ret['offset'] = await self.getEditIndx()
        ret['totalsize'] = await self.getLayerSize()
        return ret

    async def iterWipeNodeEdits(self):

        await self._saveDirtySodes()

        async for nid, sode in self.getStorNodes():

            edits = []

            async for verb, n2nid in self.iterNodeEdgesN1(nid):
                edits.append((EDIT_EDGE_DEL, (verb, n2nid)))

            async for prop, valu in self.iterNodeData(nid):
                edits.append((EDIT_NODEDATA_DEL, (prop, valu)))

            for tag, propdict in sode.get('tagprops', {}).items():
                for prop, (valu, stortype) in propdict.items():
                    edits.append((EDIT_TAGPROP_DEL, (tag, prop, valu, stortype)))

            for tag, tagv in sode.get('tags', {}).items():
                edits.append((EDIT_TAG_DEL, (tag, tagv)))

            for prop, (valu, stortype) in sode.get('props', {}).items():
                edits.append((EDIT_PROP_DEL, (prop, valu, stortype)))

            valu = sode.get('valu')
            if valu is not None:
                edits.append((EDIT_NODE_DEL, valu))

            yield (nid, sode.get('form'), edits)

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

        nodeeditpath = s_common.genpath(self.dirn, 'nodeedits.lmdb')
        self.nodeeditslab = await s_lmdbslab.Slab.anit(nodeeditpath, **otherslabopts)

        self.offsets = await self.layrslab.getHotCount('offsets')

        self.bynid = self.layrslab.initdb('bynid', integerkey=True)

        self.indxdb = self.layrslab.initdb('indx', dupsort=True, dupfixed=True, integerdup=True)

        self.edgen1abrv = self.core.setIndxAbrv(INDX_EDGE_N1)
        self.edgen2abrv = self.core.setIndxAbrv(INDX_EDGE_N2)
        self.edgen1n2abrv = self.core.setIndxAbrv(INDX_EDGE_N1N2)

        self.indxcounts = await self.layrslab.getLruHotCount('indxcounts')

        self.nodedata = self.dataslab.initdb('nodedata')
        self.dataname = self.dataslab.initdb('dataname', dupsort=True)

        self.nodeeditlog = self.nodeeditctor(self.nodeeditslab, 'nodeedits')

    async def _initLayerStorage(self):

        slabopts = {
            'readahead': True,
            'lockmemory': self.lockmemory,
            'map_async': self.mapasync,
            'max_replay_log': self.maxreplaylog,
        }

        if self.growsize is not None:
            slabopts['growsize'] = self.growsize

        await self._initSlabs(slabopts)

        if self.fresh:
            self.meta.set('version', 10)

        self.layrslab.addResizeCallback(self.core.checkFreeSpace)
        self.dataslab.addResizeCallback(self.core.checkFreeSpace)
        self.nodeeditslab.addResizeCallback(self.core.checkFreeSpace)

        self.onfini(self.layrslab)
        self.onfini(self.dataslab)
        self.onfini(self.nodeeditslab)

        self.layrslab.on('commit', self._onLayrSlabCommit)

        self.layrvers = self.meta.get('version', 10)
        if self.layrvers != 10:
            mesg = f'Got layer version {self.layrvers}.  Expected 10.  Accidental downgrade?'
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
            await self.layrinfo.pop(name)
        else:
            await self.layrinfo.set(name, valu)

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

    async def getFormCounts(self):
        formcounts = {}

        for byts, abrv in self.core.indxabrv.iterByPref(INDX_PROP):
            (form, prop) = s_msgpack.un(byts[2:])

            if prop is None and (valu := self.indxcounts.get(abrv)) > 0:
                formcounts[form] = valu

        return formcounts

    def getFormProps(self):
        for byts, abrv in self.core.indxabrv.iterByPref(INDX_PROP):
            if self.indxcounts.get(abrv) > 0:
                yield s_msgpack.un(byts[2:])

    def getArrayFormProps(self):
        for byts, abrv in self.core.indxabrv.iterByPref(INDX_ARRAY):
            if self.indxcounts.get(abrv) > 0:
                yield s_msgpack.un(byts[2:])

    def getTags(self):
        for byts, abrv in self.core.indxabrv.iterByPref(INDX_TAG):
            if self.indxcounts.get(abrv) > 0:
                yield s_msgpack.un(byts[2:])

    def getTagProps(self):
        for byts, abrv in self.core.indxabrv.iterByPref(INDX_TAGPROP):
            if self.indxcounts.get(abrv) > 0:
                yield s_msgpack.un(byts[2:])

    async def _onLayrSlabCommit(self, mesg):
        await self._saveDirtySodes()

    async def _saveDirtySodes(self):

        if not self.dirty:
            return

        # flush any dirty storage nodes before the commit
        kvlist = []

        for nid, sode in self.dirty.items():
            self.nidcache[nid] = sode
            kvlist.append((nid, s_msgpack.en(sode)))

        self.layrslab.putmulti(kvlist, db=self.bynid)
        self.dirty.clear()

    def getStorNodeCount(self):
        info = self.layrslab.stat(db=self.bynid)
        return info.get('entries', 0)

    async def getStorNode(self, nid):
        sode = self._getStorNode(nid)
        if sode is not None:
            return deepcopy(sode)
        return {}

    def _getStorNode(self, nid):
        '''
        Return the storage node for the given nid.
        '''
        # check the dirty nodes first
        sode = self.dirty.get(nid)
        if sode is not None:
            return sode

        sode = self.nidcache.get(nid)
        if sode is not None:
            return sode

        envl = self.weakcache.get(nid)
        if envl is not None:
            return envl.sode

        byts = self.layrslab.get(nid, db=self.bynid)
        if byts is None:
            return None

        sode = collections.defaultdict(dict)
        sode |= s_msgpack.un(byts)

        self.nidcache[nid] = sode

        return sode

    def genStorNodeRef(self, nid):

        envl = self.weakcache.get(nid)
        if envl is not None:
            return envl

        envl = SodeEnvl(self.iden, self._genStorNode(nid))

        self.weakcache[nid] = envl
        return envl

    def _genStorNode(self, nid):
        # get or create the storage node. this returns the *actual* storage node

        sode = self._getStorNode(nid)
        if sode is not None:
            return sode

        sode = collections.defaultdict(dict)
        self.nidcache[nid] = sode

        return sode

    async def getTagCount(self, tagname, formname=None):
        '''
        Return the number of tag rows in the layer for the given tag/form.
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_TAG, formname, tagname)
        except s_exc.NoSuchAbrv:
            return 0

        return self.indxcounts.get(abrv, 0)

    async def getPropCount(self, formname, propname=None):
        '''
        Return the number of property rows in the layer for the given form/prop.
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, formname, propname)
        except s_exc.NoSuchAbrv:
            return 0

        return self.indxcounts.get(abrv, 0)

    def getPropValuCount(self, formname, propname, stortype, valu):
        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, formname, propname)
        except s_exc.NoSuchAbrv:
            return 0

        if stortype & 0x8000:
            stortype = STOR_TYPE_MSGP

        count = 0
        for indx in self.getStorIndx(stortype, valu):
            count += self.layrslab.count(abrv + indx, db=self.indxdb)

        return count

    async def getPropArrayCount(self, formname, propname=None):
        '''
        Return the number of invidiual value rows in the layer for the given array form/prop.
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_ARRAY, formname, propname)
        except s_exc.NoSuchAbrv:
            return 0

        return self.indxcounts.get(abrv, 0)

    def getPropArrayValuCount(self, formname, propname, stortype, valu):
        try:
            abrv = self.core.getIndxAbrv(INDX_ARRAY, formname, propname)
        except s_exc.NoSuchAbrv:
            return 0

        count = 0
        for indx in self.getStorIndx(stortype, valu):
            count += self.layrslab.count(abrv + indx, db=self.indxdb)

        return count

    async def getTagPropCount(self, form, tag, prop):
        '''
        Return the number of property rows in the layer for the given form/tag/prop.
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_TAGPROP, form, tag, prop)
        except s_exc.NoSuchAbrv:
            return 0

        return self.indxcounts.get(abrv, 0)

    def getTagPropValuCount(self, form, tag, prop, stortype, valu):
        try:
            abrv = self.core.getIndxAbrv(INDX_TAGPROP, form, tag, prop)
        except s_exc.NoSuchAbrv:
            return 0

        count = 0
        for indx in self.getStorIndx(stortype, valu):
            count += self.layrslab.count(abrv + indx, db=self.indxdb)

        return count

    async def getEdgeVerbCount(self, verb):
        '''
        Return the number of edges in the layer with a specific verb.
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return 0

        return self.indxcounts.get(abrv, 0)

    async def getFormEdgeVerbCount(self, form, verb, reverse=False):
        '''
        Return the number of edges in the layer for the given form and verb.
        '''
        try:
            verbabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
            formabrv = self.core.getIndxAbrv(INDX_PROP, form, None)
        except s_exc.NoSuchAbrv:
            return 0

        if reverse:
            return self.indxcounts.get(INDX_EDGE_N2 + formabrv + verbabrv, 0)
        else:
            return self.indxcounts.get(INDX_EDGE_N1 + formabrv + verbabrv, 0)

    async def liftByTag(self, tag, form=None, reverse=False, indx=None):

        if indx is not None:
            try:
                abrv = self.core.getIndxAbrv(indx, form, tag)
            except s_exc.NoSuchAbrv:
                return

            if reverse:
                scan = self.layrslab.scanByRangeBack
                pkeymin = self.ivaltimetype.fullbyts
                pkeymax = self.ivaltimetype.getIntIndx(0)
            else:
                scan = self.layrslab.scanByRange
                pkeymin = self.ivaltimetype.getIntIndx(0)
                pkeymax = self.ivaltimetype.fullbyts

            for lkey, nid in scan(abrv + pkeymin, abrv + pkeymax, db=self.indxdb):
                yield lkey, nid, self.genStorNodeRef(nid)

        else:
            try:
                abrv = self.core.getIndxAbrv(INDX_TAG, form, tag)
            except s_exc.NoSuchAbrv:
                return

            if reverse:
                scan = self.layrslab.scanByPrefBack
            else:
                scan = self.layrslab.scanByPref

            for lkey, nid in scan(abrv, db=self.indxdb):
                # yield <sortkey>, <nid>, <SodeEnvl>
                yield lkey, nid, self.genStorNodeRef(nid)

    async def liftByTagValu(self, tag, cmprvals, form=None, reverse=False):

        for cmpr, valu, kind in cmprvals:
            async for indx, nid in self.stortypes[kind].indxByTag(tag, cmpr, valu, form=form, reverse=reverse):
                yield indx, nid, self.genStorNodeRef(nid)

    async def hasTagProp(self, name):
        async for _ in self.liftTagProp(name):
            return True

        return False

    async def hasNodeData(self, nid, name):
        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, name, None)
        except s_exc.NoSuchAbrv:
            return False

        return self.dataslab.has(nid + abrv, db=self.nodedata)

    async def liftTagProp(self, name):

        for form, tag, prop in self.getTagProps():

            if form is not None or prop != name:
                continue

            try:
                abrv = self.core.getIndxAbrv(INDX_TAGPROP, None, tag, name)

            except s_exc.NoSuchAbrv:
                continue

            for _, nid in self.layrslab.scanByPref(abrv, db=self.indxdb):
                yield nid

    async def liftByTagProp(self, form, tag, prop, reverse=False, indx=None):

        if indx is None:
            indx = INDX_TAGPROP

        try:
            abrv = self.core.getIndxAbrv(indx, form, tag, prop)
        except s_exc.NoSuchAbrv:
            return

        if reverse:
            scan = self.layrslab.scanByPrefBack
        else:
            scan = self.layrslab.scanByPref

        for lval, nid in scan(abrv, db=self.indxdb):
            yield lval, nid, self.genStorNodeRef(nid)

    async def liftByTagPropValu(self, form, tag, prop, cmprvals, reverse=False):
        '''
        Note:  form may be None
        '''
        for cmpr, valu, kind in cmprvals:
            async for indx, nid in self.stortypes[kind].indxByTagProp(form, tag, prop, cmpr, valu, reverse=reverse):
                yield indx, nid, self.genStorNodeRef(nid)

    async def liftByProp(self, form, prop, reverse=False, indx=None):

        if indx is None:
            indx = INDX_PROP

        try:
            abrv = self.core.getIndxAbrv(indx, form, prop)
        except s_exc.NoSuchAbrv:
            return

        if reverse:
            scan = self.layrslab.scanByPrefBack
        else:
            scan = self.layrslab.scanByPref

        for lval, nid in scan(abrv, db=self.indxdb):
            sref = self.genStorNodeRef(nid)
            yield lval, nid, sref

    # NOTE: form vs prop valu lifting is differentiated to allow merge sort
    async def liftByFormValu(self, form, cmprvals, reverse=False):
        for cmpr, valu, kind in cmprvals:

            if kind & 0x8000:
                kind = STOR_TYPE_MSGP

            async for indx, nid in self.stortypes[kind].indxByForm(form, cmpr, valu, reverse=reverse):
                yield indx, nid, self.genStorNodeRef(nid)

    async def liftByPropValu(self, form, prop, cmprvals, reverse=False):

        for cmpr, valu, kind in cmprvals:

            if kind & 0x8000:
                kind = STOR_TYPE_MSGP

            async for indx, nid in self.stortypes[kind].indxByProp(form, prop, cmpr, valu, reverse=reverse):
                yield indx, nid, self.genStorNodeRef(nid)

    async def liftByPropArray(self, form, prop, cmprvals, reverse=False):
        for cmpr, valu, kind in cmprvals:
            async for indx, nid in self.stortypes[kind].indxByPropArray(form, prop, cmpr, valu, reverse=reverse):
                yield indx, nid, self.genStorNodeRef(nid)

    async def liftByDataName(self, name):
        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, name, None)

        except s_exc.NoSuchAbrv:
            return

        for abrv, nid in self.dataslab.scanByDups(abrv, db=self.dataname):
            await asyncio.sleep(0)

            yield nid, nid, self.genStorNodeRef(nid)

    async def saveNodeEdits(self, edits, meta):
        '''
        Save node edits to the layer and return a tuple of (nexsoffs, changes).

        Note: nexsoffs will be None if there are no changes.
        '''
        self._reqNotReadOnly()

        if not self.core.isactive:
            proxy = await self.core.nexsroot.getIssueProxy()
            indx, changes = await proxy.saveLayerNodeEdits(self.iden, edits, meta)
            if indx is not None:
                await self.core.nexsroot.waitOffs(indx)
            return indx, changes

        async with self.core.nexsroot.applylock:
            if (realedits := await self.calcEdits(edits, meta)):
                return await self.saveToNexs('edits', realedits, meta)
            return None, ()

    async def calcEdits(self, nodeedits, meta):

        if (tick := meta.get('time')) is None:
            tick = s_common.now()

        realedits = []
        for (nid, form, edits) in nodeedits:

            if nid is None:
                if edits[0][0] != 0:
                    continue

                # Generate NID without a nexus event, mirrors will populate
                # the mapping from the node add edit
                nid = await self.core._genNdefNid((form, edits[0][1][0]))

            newsode = False

            sode = self._getStorNode(nid)
            if sode is None:
                newsode = {'.created': tick}

            elif sode.get('valu') is None:
                if (props := sode.get('props')) is not None and (ctime := props.get('.created')) is not None:
                    oldv = ctime[0]
                    newsode = {'oldv': oldv, '.created': min(oldv, tick)}
                else:
                    newsode = {'.created': tick}

            changes = []
            for edit in edits:

                delt = await self.resolvers[edit[0]](nid, edit, sode, newsode)
                if delt is not None:
                    changes.extend(delt)

                await asyncio.sleep(0)

            if changes:
                if newsode and newsode.get('valu'):
                    oldv = newsode.get('oldv')
                    ctime = newsode.get('.created')
                    if oldv != ctime:
                        changes.append((EDIT_PROP_SET, ('.created', ctime, oldv, STOR_TYPE_MINTIME)))

                realedits.append((nid, form, changes))

        await asyncio.sleep(0)
        return realedits

    @s_nexus.Pusher.onPush('edits', passitem=True)
    async def _storNodeEdits(self, nodeedits, meta, nexsitem):
        '''
        Execute a series of node edit operations, returning the updated nodes.

        Args:
            nodeedits:  List[Tuple(nid, form, edits)]  List of requested changes per node

        Returns:
            None
        '''
        kvpairs = []
        for (nid, form, edits) in nodeedits:

            sode = self._genStorNode(nid)

            for edit in edits:
                kvpairs.extend(await self.editors[edit[0]](nid, form, edit, sode, meta))

                if len(kvpairs) > 20:
                    self.layrslab.putmulti(kvpairs, db=self.indxdb)
                    kvpairs.clear()
                    await asyncio.sleep(0)

        if kvpairs:
            self.layrslab.putmulti(kvpairs, db=self.indxdb)

        if self.logedits and nexsitem is not None:
            nexsindx = nexsitem[0] if nexsitem is not None else None
            offs = self.nodeeditlog.add(None, indx=nexsindx)
            [(await wind.put((offs, nodeedits, meta))) for wind in tuple(self.windows)]

        await asyncio.sleep(0)
        return nodeedits

    def mayDelNid(self, nid, sode):
        if sode.get('valu'):
            return False

        if sode.get('props'):
            return False

        if sode.get('tags'):
            return False

        if sode.get('tagprops'):
            return False

        if sode.get('n1verbs'):
            return False

        if sode.get('n2verbs'):
            return False

        if self.dataslab.prefexists(nid, self.nodedata):
            return False

        # no more refs in this layer.  time to pop it...
        self.dirty.pop(nid, None)
        self.nidcache.pop(nid, None)
        self.layrslab.delete(nid, db=self.bynid)

        envl = self.weakcache.get(nid)
        if envl is not None:
            envl.sode.clear()

        return True

    async def storNodeEditsNoLift(self, nodeedits, meta):
        '''
        Execute a series of node edit operations.

        Does not return the updated nodes.
        '''
        self._reqNotReadOnly()
        await self._push('edits', nodeedits, meta)

    async def _calcNodeAdd(self, nid, edit, sode, newsode):

        if not newsode:
            return

        newsode['valu'] = True

        return (
            (EDIT_NODE_ADD, edit[1]),
        )

    async def _calcNodeDel(self, nid, edit, sode, newsode):

        if sode is None or (oldv := sode.get('valu')) is None:
            return

        return (
            (EDIT_NODE_DEL, oldv),
        )

    async def _calcPropSet(self, nid, edit, sode, newsode):

        prop, valu, _, stortype = edit[1]

        if newsode and prop == '.created':
            newsode['.created'] = min(valu, newsode['.created'])
            return

        if sode is None or (props := sode.get('props')) is None:
            oldv = None

        else:
            oldv, oldt = props.get(prop, (None, None))

            if valu == oldv:
                return

            if oldv is not None:
                # merge intervals and min times
                if stortype == STOR_TYPE_IVAL:
                    allv = oldv + valu
                    valu = (min(allv), max(allv))

                elif stortype == STOR_TYPE_MINTIME:
                    valu = min(valu, oldv)

                elif stortype == STOR_TYPE_MAXTIME:
                    valu = max(valu, oldv)

                if valu == oldv and stortype == oldt:
                    return

        return (
            (EDIT_PROP_SET, (prop, valu, oldv, stortype)),
        )

    async def _calcPropDel(self, nid, edit, sode, newsode):

        if sode is None or (props := sode.get('props')) is None:
            return

        prop = edit[1][0]
        if (valt := props.get(prop)) is None:
            return

        return (
            (EDIT_PROP_DEL, (prop, *valt)),
        )

    async def _calcTagSet(self, nid, edit, sode, newsode):

        tag, valu, _ = edit[1]

        if sode is None or (tags := sode.get('tags')) is None:
            oldv = None

        elif (oldv := tags.get(tag)) is not None:

            if oldv != (None, None) and valu != (None, None):
                allv = oldv + valu
                valu = (min(allv), max(allv))

            if oldv == valu:
                return

        return (
            (EDIT_TAG_SET, (tag, valu, oldv)),
        )

    async def _calcTagDel(self, nid, edit, sode, newsode):

        if sode is None or (tags := sode.get('tags')) is None:
            return

        tag = edit[1][0]
        if (oldv := tags.get(tag)) is None:
            return

        return (
            (EDIT_TAG_DEL, (tag, oldv)),
        )

    async def _calcTagPropSet(self, nid, edit, sode, newsode):

        tag, prop, valu, _, stortype = edit[1]
        oldv = None

        if sode is not None and (tagprops := sode.get('tagprops')) is not None:
            if (tp_dict := tagprops.get(tag)) is not None:
                if (valt := tp_dict.get(prop)) is not None:

                    oldv, oldt = valt

                    if stortype == STOR_TYPE_IVAL:
                        allv = oldv + valu
                        valu = (min(allv), max(allv))

                    elif stortype == STOR_TYPE_MINTIME:
                        valu = min(valu, oldv)

                    elif stortype == STOR_TYPE_MAXTIME:
                        valu = max(valu, oldv)

                    if valu == oldv and stortype == oldt:
                        return

        return (
            (EDIT_TAGPROP_SET, (tag, prop, valu, oldv, stortype)),
        )

    async def _calcTagPropDel(self, nid, edit, sode, newsode):

        if sode is None or (tagprops := sode.get('tagprops')) is None:
            return

        tag, prop, _, _ = edit[1]

        if (tp_dict := tagprops.get(tag)) is None:
            return

        if (oldv := tp_dict.get(prop)) is None:
            return

        return (
            (EDIT_TAGPROP_DEL, (tag, prop, *oldv)),
        )

    async def _calcNodeDataSet(self, nid, edit, sode, newsode):

        name, valu, _ = edit[1]

        if sode is None:
            return (
                (EDIT_NODEDATA_SET, (name, valu, None)),
            )

        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, name, None)
        except s_exc.NoSuchAbrv:
            return (
                (EDIT_NODEDATA_SET, (name, valu, None)),
            )

        oldv = None
        byts = s_msgpack.en(valu)

        if (oldb := self.dataslab.get(nid + abrv, db=self.nodedata)) is not None:
            if oldb == byts:
                return
            oldv = s_msgpack.un(oldb)

        return (
            (EDIT_NODEDATA_SET, (name, valu, oldv)),
        )

    async def _calcNodeDataDel(self, nid, edit, sode, newsode):

        if sode is None:
            return

        name, valu = edit[1]
        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, name, None)
        except s_exc.NoSuchAbrv:
            return

        if (oldb := self.dataslab.get(nid + abrv, db=self.nodedata)) is None:
            return

        return (
            (EDIT_NODEDATA_DEL, (name, s_msgpack.un(oldb))),
        )

    async def _calcNodeEdgeAdd(self, nid, edit, sode, newsode):

        verb, n2nid = edit[1]

        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return (
                (EDIT_EDGE_ADD, (verb, n2nid)),
            )

        if sode is not None and self.layrslab.hasdup(self.edgen1n2abrv + nid + n2nid, vabrv, db=self.indxdb):
            return

        return (
            (EDIT_EDGE_ADD, (verb, n2nid)),
        )

    async def _calcNodeEdgeDel(self, nid, edit, sode, newsode):

        if sode is None:
            return

        verb, n2nid = edit[1]

        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return

        if not self.layrslab.hasdup(self.edgen1n2abrv + nid + n2nid, vabrv, db=self.indxdb):
            return

        return (
            (EDIT_EDGE_DEL, (verb, n2nid)),
        )

    async def _editNodeAdd(self, nid, form, edit, sode, meta):

        if sode.get('valu') is not None:
            return ()

        valu, stortype = sode['valu'] = edit[1]
        sode['form'] = form

        if self.core.getBuidByNid(nid) is None:
            self.core.setNidNdef(nid, (form, valu))

        self.dirty[nid] = sode

        kvpairs = []

        abrv = self.core.setIndxAbrv(INDX_PROP, form, None)

        if stortype & STOR_FLAG_ARRAY:

            arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, None)

            for indx in self.getStorIndx(stortype, valu):
                kvpairs.append((arryabrv + indx, nid))
                self.indxcounts.inc(arryabrv)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                kvpairs.append((abrv + indx, nid))
                self.indxcounts.inc(abrv)

        else:

            for indx in self.getStorIndx(stortype, valu):
                kvpairs.append((abrv + indx, nid))
                self.indxcounts.inc(abrv)

            if stortype == STOR_TYPE_IVAL:
                if valu[1] == self.ivaltimetype.futsize:
                    dura = self.stortypes[STOR_TYPE_IVAL].maxdura
                else:
                    dura = self.ivaltimetype.getIntIndx(valu[1] - valu[0])

                duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, None)
                kvpairs.append((duraabrv + dura, nid))
                self.indxcounts.inc(duraabrv)

                indx = indx[8:]
                maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, None)
                kvpairs.append((maxabrv + indx, nid))

        if self.nodeAddHook is not None:
            self.nodeAddHook()

        return kvpairs

    async def _editNodeDel(self, nid, form, edit, sode, meta):

        if (valt := sode.pop('valu', None)) is None:
            return ()

        (valu, stortype) = valt

        abrv = self.core.setIndxAbrv(INDX_PROP, form, None)

        if stortype & STOR_FLAG_ARRAY:

            arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, None)

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(arryabrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(arryabrv, -1)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(abrv, -1)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(abrv, -1)

            if stortype == STOR_TYPE_IVAL:
                if valu[1] == self.ivaltimetype.futsize:
                    dura = self.stortypes[STOR_TYPE_IVAL].maxdura
                else:
                    dura = self.ivaltimetype.getIntIndx(valu[1] - valu[0])

                duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, None)
                self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
                self.indxcounts.inc(duraabrv, -1)

                indx = indx[8:]
                maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, None)
                self.layrslab.delete(maxabrv + indx, nid, db=self.indxdb)

        if self.nodeDelHook is not None:
            self.nodeDelHook()

        await self._wipeNodeData(nid, sode)
        await self._delNodeEdges(nid, abrv, sode)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editPropSet(self, nid, form, edit, sode, meta):

        prop, valu, oldv, stortype = edit[1]

        oldv, oldt = sode['props'].get(prop, (None, None))

        if valu == oldv:
            return ()

        abrv = self.core.setIndxAbrv(INDX_PROP, form, prop)
        univabrv = None

        if prop[0] == '.':  # '.' to detect universal props (as quickly as possible)
            univabrv = self.core.setIndxAbrv(INDX_PROP, None, prop)

        if oldv is not None:

            if oldt & STOR_FLAG_ARRAY:
                arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, prop)
                self.indxcounts.inc(arryabrv, len(oldv) * -1)

                if univabrv is not None:
                    univarryabrv = self.core.setIndxAbrv(INDX_ARRAY, None, prop)
                    self.indxcounts.inc(univarryabrv, len(oldv) * -1)

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(arryabrv + oldi, nid, db=self.indxdb)
                    if univabrv is not None:
                        self.layrslab.delete(univarryabrv + oldi, nid, db=self.indxdb)

                for indx in self.getStorIndx(STOR_TYPE_MSGP, oldv):
                    self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                    self.indxcounts.inc(abrv, -1)

                    if univabrv is not None:
                        self.layrslab.delete(univabrv + indx, nid, db=self.indxdb)
                        self.indxcounts.inc(univabrv, -1)

            else:

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(abrv + oldi, nid, db=self.indxdb)
                    self.indxcounts.inc(abrv, -1)

                    if univabrv is not None:
                        self.layrslab.delete(univabrv + oldi, nid, db=self.indxdb)
                        self.indxcounts.inc(univabrv, -1)

                if oldt == STOR_TYPE_IVAL:
                    if oldv[1] == self.ivaltimetype.futsize:
                        dura = self.stortypes[STOR_TYPE_IVAL].maxdura
                    else:
                        dura = self.ivaltimetype.getIntIndx(oldv[1] - oldv[0])

                    duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, prop)
                    self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
                    self.indxcounts.inc(duraabrv, -1)

                    if univabrv is not None:
                        univduraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, prop)
                        self.layrslab.delete(univduraabrv + dura, nid, db=self.indxdb)
                        self.indxcounts.inc(univduraabrv, -1)

                    if not oldv[1] == valu[1]:
                        oldi = oldi[8:]
                        maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, prop)

                        self.layrslab.delete(maxabrv + oldi, nid, db=self.indxdb)
                        if univabrv is not None:
                            univmaxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, prop)
                            self.layrslab.delete(univmaxabrv + oldi, nid, db=self.indxdb)

        sode['props'][prop] = (valu, stortype)
        self.dirty[nid] = sode

        kvpairs = []

        if stortype & STOR_FLAG_ARRAY:

            arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, prop)
            if univabrv is not None:
                univarryabrv = self.core.setIndxAbrv(INDX_ARRAY, None, prop)

            for indx in self.getStorIndx(stortype, valu):
                kvpairs.append((arryabrv + indx, nid))
                self.indxcounts.inc(arryabrv)
                if univabrv is not None:
                    kvpairs.append((univarryabrv + indx, nid))
                    self.indxcounts.inc(univarryabrv)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                kvpairs.append((abrv + indx, nid))
                self.indxcounts.inc(abrv)
                if univabrv is not None:
                    kvpairs.append((univabrv + indx, nid))
                    self.indxcounts.inc(univabrv)

        else:

            for indx in self.getStorIndx(stortype, valu):
                kvpairs.append((abrv + indx, nid))
                self.indxcounts.inc(abrv)
                if univabrv is not None:
                    kvpairs.append((univabrv + indx, nid))
                    self.indxcounts.inc(univabrv)

            if stortype == STOR_TYPE_IVAL:
                if valu[1] == self.ivaltimetype.futsize:
                    dura = self.stortypes[STOR_TYPE_IVAL].maxdura
                else:
                    dura = self.ivaltimetype.getIntIndx(valu[1] - valu[0])

                duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, prop)
                kvpairs.append((duraabrv + dura, nid))
                self.indxcounts.inc(duraabrv)

                if univabrv is not None:
                    univduraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, prop)
                    kvpairs.append((univduraabrv + dura, nid))
                    self.indxcounts.inc(univduraabrv)

                if oldv is None or oldv[1] != valu[1]:
                    indx = indx[8:]
                    maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, prop)
                    kvpairs.append((maxabrv + indx, nid))

                    if univabrv is not None:
                        univmaxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, prop)
                        kvpairs.append((univmaxabrv + indx, nid))

        return kvpairs

    async def _editPropDel(self, nid, form, edit, sode, meta):

        prop = edit[1][0]

        if (valt := sode['props'].pop(prop, None)) is None:
            return ()

        valu, stortype = valt

        abrv = self.core.setIndxAbrv(INDX_PROP, form, prop)
        univabrv = None

        if prop[0] == '.':  # '.' to detect universal props (as quickly as possible)
            univabrv = self.core.setIndxAbrv(INDX_PROP, None, prop)

        if stortype & STOR_FLAG_ARRAY:

            realtype = stortype & 0x7fff

            arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, prop)
            self.indxcounts.inc(arryabrv, len(valu) * -1)
            if univabrv is not None:
                univarryabrv = self.core.setIndxAbrv(INDX_ARRAY, None, prop)
                self.indxcounts.inc(univarryabrv, len(valu) * -1)

            for aval in valu:
                for indx in self.getStorIndx(realtype, aval):
                    self.layrslab.delete(arryabrv + indx, nid, db=self.indxdb)
                    if univabrv is not None:
                        self.layrslab.delete(univarryabrv + indx, nid, db=self.indxdb)

            for indx in self.getStorIndx(STOR_TYPE_MSGP, valu):
                self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(abrv, -1)
                if univabrv is not None:
                    self.layrslab.delete(univabrv + indx, nid, db=self.indxdb)
                    self.indxcounts.inc(univabrv, -1)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(abrv, -1)
                if univabrv is not None:
                    self.layrslab.delete(univabrv + indx, nid, db=self.indxdb)
                    self.indxcounts.inc(univabrv, -1)

            if stortype == STOR_TYPE_IVAL:
                if valu[1] == self.ivaltimetype.futsize:
                    dura = self.stortypes[STOR_TYPE_IVAL].maxdura
                else:
                    dura = self.ivaltimetype.getIntIndx(valu[1] - valu[0])

                indx = indx[8:]

                maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, prop)
                duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, prop)

                self.layrslab.delete(maxabrv + indx, nid, db=self.indxdb)
                self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
                self.indxcounts.inc(duraabrv, -1)

                if univabrv is not None:
                    univmaxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, prop)
                    univduraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, prop)
                    self.layrslab.delete(univmaxabrv + indx, nid, db=self.indxdb)
                    self.layrslab.delete(univduraabrv + dura, nid, db=self.indxdb)
                    self.indxcounts.inc(univduraabrv, -1)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editTagSet(self, nid, form, edit, sode, meta):

        tag, valu, _ = edit[1]

        oldv = sode['tags'].get(tag)
        if valu == oldv:
            return ()

        abrv = self.core.setIndxAbrv(INDX_TAG, None, tag)
        formabrv = self.core.setIndxAbrv(INDX_TAG, form, tag)

        if oldv is None:
            self.indxcounts.inc(abrv)
            self.indxcounts.inc(formabrv)

        else:

            if oldv == (None, None):
                self.layrslab.delete(abrv, nid, db=self.indxdb)
                self.layrslab.delete(formabrv, nid, db=self.indxdb)
            else:
                if oldv[1] == self.ivaltimetype.futsize:
                    dura = self.stortypes[STOR_TYPE_IVAL].maxdura
                else:
                    dura = self.ivaltimetype.getIntIndx(oldv[1] - oldv[0])

                duraabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, None, tag)
                duraformabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, form, tag)

                self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
                self.layrslab.delete(duraformabrv + dura, nid, db=self.indxdb)
                self.indxcounts.inc(duraabrv, -1)
                self.indxcounts.inc(duraformabrv, -1)

                minindx = self.ivaltimetype.getIntIndx(oldv[0])
                maxindx = self.ivaltimetype.getIntIndx(oldv[1])

                self.layrslab.delete(abrv + minindx + maxindx, nid, db=self.indxdb)
                self.layrslab.delete(formabrv + minindx + maxindx, nid, db=self.indxdb)

                if not oldv[1] == valu[1]:
                    maxabrv = self.core.setIndxAbrv(INDX_TAG_MAX, None, tag)
                    maxformabrv = self.core.setIndxAbrv(INDX_TAG_MAX, form, tag)

                    self.layrslab.delete(maxabrv + maxindx, nid, db=self.indxdb)
                    self.layrslab.delete(maxformabrv + maxindx, nid, db=self.indxdb)

        sode['tags'][tag] = valu
        self.dirty[nid] = sode

        kvpairs = []

        if valu == (None, None):
            kvpairs.append((abrv, nid))
            kvpairs.append((formabrv, nid))
        else:
            if valu[1] == self.ivaltimetype.futsize:
                dura = self.stortypes[STOR_TYPE_IVAL].maxdura
            else:
                dura = self.ivaltimetype.getIntIndx(valu[1] - valu[0])

            duraabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, None, tag)
            duraformabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, form, tag)

            kvpairs.append((duraabrv + dura, nid))
            kvpairs.append((duraformabrv + dura, nid))
            self.indxcounts.inc(duraabrv)
            self.indxcounts.inc(duraformabrv)

            minindx = self.ivaltimetype.getIntIndx(valu[0])
            maxindx = self.ivaltimetype.getIntIndx(valu[1])

            kvpairs.append((abrv + minindx + maxindx, nid))
            kvpairs.append((formabrv + minindx + maxindx, nid))

            if oldv is None or oldv[1] != valu[1]:
                maxabrv = self.core.setIndxAbrv(INDX_TAG_MAX, None, tag)
                maxformabrv = self.core.setIndxAbrv(INDX_TAG_MAX, form, tag)

                kvpairs.append((maxabrv + maxindx, nid))
                kvpairs.append((maxformabrv + maxindx, nid))

        return kvpairs

    async def _editTagDel(self, nid, form, edit, sode, meta):

        tag = edit[1][0]

        if (oldv := sode['tags'].pop(tag, None)) is None:
            return ()

        abrv = self.core.setIndxAbrv(INDX_TAG, None, tag)
        formabrv = self.core.setIndxAbrv(INDX_TAG, form, tag)

        self.indxcounts.inc(abrv, -1)
        self.indxcounts.inc(formabrv, -1)

        if oldv == (None, None):
            self.layrslab.delete(abrv, nid, db=self.indxdb)
            self.layrslab.delete(formabrv, nid, db=self.indxdb)
        else:
            if oldv[1] == self.ivaltimetype.futsize:
                dura = self.stortypes[STOR_TYPE_IVAL].maxdura
            else:
                dura = self.ivaltimetype.getIntIndx(oldv[1] - oldv[0])

            duraabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, None, tag)
            duraformabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, form, tag)

            self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
            self.layrslab.delete(duraformabrv + dura, nid, db=self.indxdb)
            self.indxcounts.inc(duraabrv, -1)
            self.indxcounts.inc(duraformabrv, -1)

            minindx = self.ivaltimetype.getIntIndx(oldv[0])
            maxindx = self.ivaltimetype.getIntIndx(oldv[1])

            self.layrslab.delete(abrv + minindx + maxindx, nid, db=self.indxdb)
            self.layrslab.delete(formabrv + minindx + maxindx, nid, db=self.indxdb)

            maxabrv = self.core.setIndxAbrv(INDX_TAG_MAX, None, tag)
            maxformabrv = self.core.setIndxAbrv(INDX_TAG_MAX, form, tag)

            self.layrslab.delete(maxabrv + maxindx, nid, db=self.indxdb)
            self.layrslab.delete(maxformabrv + maxindx, nid, db=self.indxdb)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editTagPropSet(self, nid, form, edit, sode, meta):

        tag, prop, valu, oldv, stortype = edit[1]

        tp_abrv = self.core.setIndxAbrv(INDX_TAGPROP, None, tag, prop)
        ftp_abrv = self.core.setIndxAbrv(INDX_TAGPROP, form, tag, prop)

        if (tp_dict := sode['tagprops'].get(tag)) is not None:
            if (oldv := tp_dict.get(prop)) is not None:

                if (valu, stortype) == oldv:
                    return ()

                (oldv, oldt) = oldv

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(tp_abrv + oldi, nid, db=self.indxdb)
                    self.layrslab.delete(ftp_abrv + oldi, nid, db=self.indxdb)
                    self.indxcounts.inc(tp_abrv, -1)
                    self.indxcounts.inc(ftp_abrv, -1)

                if oldt == STOR_TYPE_IVAL:
                    if oldv[1] == self.ivaltimetype.futsize:
                        dura = self.stortypes[STOR_TYPE_IVAL].maxdura
                    else:
                        dura = self.ivaltimetype.getIntIndx(oldv[1] - oldv[0])

                    duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, tag, prop)
                    duraformabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, tag, prop)

                    self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
                    self.layrslab.delete(duraformabrv + dura, nid, db=self.indxdb)
                    self.indxcounts.inc(duraabrv, -1)
                    self.indxcounts.inc(duraformabrv, -1)

                    if not oldv[1] == valu[1]:
                        oldi = oldi[8:]
                        maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, tag, prop)
                        maxformabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, tag, prop)

                        self.layrslab.delete(maxabrv + oldi, nid, db=self.indxdb)
                        self.layrslab.delete(maxformabrv + oldi, nid, db=self.indxdb)

        else:
            sode['tagprops'][tag] = {}

        sode['tagprops'][tag][prop] = (valu, stortype)
        self.dirty[nid] = sode

        kvpairs = []
        for indx in self.getStorIndx(stortype, valu):
            kvpairs.append((tp_abrv + indx, nid))
            kvpairs.append((ftp_abrv + indx, nid))
            self.indxcounts.inc(tp_abrv)
            self.indxcounts.inc(ftp_abrv)

        if stortype == STOR_TYPE_IVAL:
            if valu[1] == self.ivaltimetype.futsize:
                dura = self.stortypes[STOR_TYPE_IVAL].maxdura
            else:
                dura = self.ivaltimetype.getIntIndx(valu[1] - valu[0])

            duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, tag, prop)
            duraformabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, tag, prop)
            kvpairs.append((duraabrv + dura, nid))
            kvpairs.append((duraformabrv + dura, nid))
            self.indxcounts.inc(duraabrv)
            self.indxcounts.inc(duraformabrv)

            if oldv is None or oldv[1] != valu[1]:
                indx = indx[8:]
                maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, tag, prop)
                maxformabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, tag, prop)
                kvpairs.append((maxabrv + indx, nid))
                kvpairs.append((maxformabrv + indx, nid))

        return kvpairs

    async def _editTagPropDel(self, nid, form, edit, sode, meta):

        tag, prop, _, _ = edit[1]

        if (tp_dict := sode['tagprops'].get(tag)) is None:
            return ()

        if (oldv := tp_dict.pop(prop, None)) is None:
            return ()

        (oldv, oldt) = oldv

        if len(tp_dict) == 0:
            sode['tagprops'].pop(tag)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        tp_abrv = self.core.setIndxAbrv(INDX_TAGPROP, None, tag, prop)
        ftp_abrv = self.core.setIndxAbrv(INDX_TAGPROP, form, tag, prop)

        for oldi in self.getStorIndx(oldt, oldv):
            self.layrslab.delete(tp_abrv + oldi, nid, db=self.indxdb)
            self.layrslab.delete(ftp_abrv + oldi, nid, db=self.indxdb)
            self.indxcounts.inc(tp_abrv, -1)
            self.indxcounts.inc(ftp_abrv, -1)

        if oldt == STOR_TYPE_IVAL:
            if oldv[1] == self.ivaltimetype.futsize:
                dura = self.stortypes[STOR_TYPE_IVAL].maxdura
            else:
                dura = self.ivaltimetype.getIntIndx(oldv[1] - oldv[0])

            duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, tag, prop)
            duraformabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, tag, prop)
            self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
            self.layrslab.delete(duraformabrv + dura, nid, db=self.indxdb)
            self.indxcounts.inc(duraabrv, -1)
            self.indxcounts.inc(duraformabrv, -1)

            indx = oldi[8:]
            maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, tag, prop)
            maxformabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, tag, prop)
            self.layrslab.delete(maxabrv + indx, nid, db=self.indxdb)
            self.layrslab.delete(maxformabrv + indx, nid, db=self.indxdb)

        return ()

    async def _editNodeDataSet(self, nid, form, edit, sode, meta):

        name, valu, _ = edit[1]
        abrv = self.core.setIndxAbrv(INDX_PROP, name, None)

        self.dataslab.put(nid + abrv, s_msgpack.en(valu), db=self.nodedata)
        self.dataslab.put(abrv, nid, db=self.dataname)

        return ()

    async def _editNodeDataDel(self, nid, form, edit, sode, meta):

        name, valu = edit[1]
        abrv = self.core.setIndxAbrv(INDX_PROP, name, None)

        if self.dataslab.delete(nid + abrv, db=self.nodedata):
            self.dataslab.delete(abrv, nid, db=self.dataname)
            self.mayDelNid(nid, sode)

        return ()

    async def _editNodeEdgeAdd(self, nid, form, edit, sode, meta):

        verb, n2nid = edit[1]

        vabrv = self.core.setIndxAbrv(INDX_EDGE_VERB, verb)

        if self.layrslab.hasdup(self.edgen1n2abrv + nid + n2nid, vabrv, db=self.indxdb):
            return ()

        n2sode = self._genStorNode(n2nid)

        # we are creating a new edge for this layer.
        sode['n1verbs'][verb] = sode['n1verbs'].get(verb, 0) + 1
        n2sode['n2verbs'][verb] = n2sode['n2verbs'].get(verb, 0) + 1

        self.dirty[nid] = sode
        self.dirty[n2nid] = n2sode

        formabrv = self.core.setIndxAbrv(INDX_PROP, form, None)

        self.indxcounts.inc(vabrv, 1)
        self.indxcounts.inc(INDX_EDGE_N1 + formabrv + vabrv, 1)

        if (n2form := n2sode.get('form')) is None:
            n2form = self.core.getNidNdef(n2nid)[0]

        if n2form is not None:
            n2formabrv = self.core.setIndxAbrv(INDX_PROP, n2form, None)
            self.indxcounts.inc(INDX_EDGE_N2 + n2formabrv + vabrv, 1)

        kvpairs = [
            (vabrv + nid, n2nid),
            (self.edgen1abrv + nid + vabrv, n2nid),
            (self.edgen2abrv + n2nid + vabrv, nid),
            (self.edgen1n2abrv + nid + n2nid, vabrv)
        ]

        return kvpairs

    async def _editNodeEdgeDel(self, nid, form, edit, sode, meta):

        verb, n2nid = edit[1]

        vabrv = self.core.setIndxAbrv(INDX_EDGE_VERB, verb)

        if not self.layrslab.delete(vabrv + nid, n2nid, db=self.indxdb):
            return ()

        self.layrslab.delete(self.edgen1abrv + nid + vabrv, n2nid, db=self.indxdb)
        self.layrslab.delete(self.edgen2abrv + n2nid + vabrv, nid, db=self.indxdb)
        self.layrslab.delete(self.edgen1n2abrv + nid + n2nid, vabrv, db=self.indxdb)

        newvalu = sode['n1verbs'].get(verb, 0) - 1
        if newvalu == 0:
            sode['n1verbs'].pop(verb)
            if not self.mayDelNid(nid, sode):
                self.dirty[nid] = sode
        else:
            sode['n1verbs'][verb] = newvalu
            self.dirty[nid] = sode

        n2sode = self._genStorNode(n2nid)
        newvalu = n2sode['n2verbs'].get(verb, 0) - 1
        if newvalu == 0:
            n2sode['n2verbs'].pop(verb)
            if not self.mayDelNid(n2nid, n2sode):
                self.dirty[n2nid] = n2sode
        else:
            n2sode['n2verbs'][verb] = newvalu
            self.dirty[n2nid] = n2sode

        formabrv = self.core.setIndxAbrv(INDX_PROP, form, None)

        self.indxcounts.inc(vabrv, -1)
        self.indxcounts.inc(INDX_EDGE_N1 + formabrv + vabrv, -1)

        if (n2form := n2sode.get('form')) is None:
            n2form = self.core.getNidNdef(n2nid)[0]

        if n2form is not None:
            n2formabrv = self.core.setIndxAbrv(INDX_PROP, n2form, None)
            self.indxcounts.inc(INDX_EDGE_N2 + n2formabrv + vabrv, -1)

        return ()

    async def getEdgeVerbs(self):
        for byts, abrv in self.core.indxabrv.iterByPref(INDX_EDGE_VERB):
            if self.indxcounts.get(abrv) > 0:
                yield s_msgpack.un(byts[2:])[0]

    async def getEdges(self, verb=None):

        if verb is None:
            for lkey, lval in self.layrslab.scanByPref(self.edgen1abrv, db=self.indxdb):
                yield (lkey[-16:-8], self.core.getAbrvIndx(lkey[-8:])[0], lval)
            return

        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return

        for lkey, lval in self.layrslab.scanByPref(vabrv, db=self.indxdb):
            yield (lkey[-8:], verb, lval)

    async def _delNodeEdges(self, nid, formabrv, sode):

        sode.pop('n1verbs', None)

        for lkey, n2nid in self.layrslab.scanByPref(self.edgen1abrv + nid, db=self.indxdb):
            await asyncio.sleep(0)
            vabrv = lkey[-8:]

            self.layrslab.delete(vabrv + nid, n2nid, db=self.indxdb)
            self.layrslab.delete(self.edgen1abrv + nid + vabrv, n2nid, db=self.indxdb)
            self.layrslab.delete(self.edgen2abrv + n2nid + vabrv, nid, db=self.indxdb)
            self.layrslab.delete(self.edgen1n2abrv + nid + n2nid, vabrv, db=self.indxdb)

            verb = self.core.getAbrvIndx(vabrv)[0]
            n2sode = self._genStorNode(n2nid)
            newvalu = n2sode['n2verbs'].get(verb, 0) - 1
            if newvalu == 0:
                n2sode['n2verbs'].pop(verb)
                if not self.mayDelNid(n2nid, n2sode):
                    self.dirty[n2nid] = n2sode
            else:
                n2sode['n2verbs'][verb] = newvalu
                self.dirty[n2nid] = n2sode

            self.indxcounts.inc(vabrv, -1)
            self.indxcounts.inc(INDX_EDGE_N1 + formabrv + vabrv, -1)

            if (n2form := n2sode.get('form')) is None:
                n2form = self.core.getNidNdef(n2nid)[0]

            if n2form is not None:
                n2formabrv = self.core.setIndxAbrv(INDX_PROP, n2form, None)
                self.indxcounts.inc(INDX_EDGE_N2 + n2formabrv + vabrv, -1)

    def getStorIndx(self, stortype, valu):

        if stortype & 0x8000:

            realtype = stortype & 0x7fff

            retn = []
            [retn.extend(self.getStorIndx(realtype, aval)) for aval in valu]
            return retn

        return self.stortypes[stortype].indx(valu)

    async def iterNodeEdgesN1(self, nid, verb=None):

        pref = self.edgen1abrv + nid
        if verb is not None:
            try:
                pref += self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
            except s_exc.NoSuchAbrv:
                return

            for lkey, n2nid in self.layrslab.scanByPref(pref, db=self.indxdb):
                yield verb, n2nid
            return

        for lkey, n2nid in self.layrslab.scanByPref(pref, db=self.indxdb):
            yield self.core.getAbrvIndx(lkey[-8:])[0], n2nid

    async def iterNodeEdgesN2(self, nid, verb=None):

        pref = self.edgen2abrv + nid
        if verb is not None:
            try:
                pref += self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
            except s_exc.NoSuchAbrv:
                return

            for lkey, n1nid in self.layrslab.scanByPref(pref, db=self.indxdb):
                yield verb, n1nid
            return

        for lkey, n1nid in self.layrslab.scanByPref(pref, db=self.indxdb):
            yield self.core.getAbrvIndx(lkey[-8:])[0], n1nid

    async def iterEdgeVerbs(self, n1nid, n2nid):
        for lkey, vabrv in self.layrslab.scanByDups(self.edgen1n2abrv + n1nid + n2nid, db=self.indxdb):
            yield self.core.getAbrvIndx(vabrv)[0]

    async def hasNodeEdge(self, n1nid, verb, n2nid):
        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return

        return self.layrslab.hasdup(self.edgen1abrv + n1nid + vabrv, n2nid, db=self.indxdb)

    async def iterFormRows(self, form, stortype=None, startvalu=None):
        '''
        Yields nid, valu tuples of nodes of a single form, optionally (re)starting at startvalu.

        Args:
            form (str):  A form name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(nid, valu)]
        '''
        try:
            indxby = IndxByForm(self, form)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterPropRows(self, form, prop, stortype=None, startvalu=None):
        '''
        Yields nid, valu tuples of nodes with a particular secondary property, optionally (re)starting at startvalu.

        Args:
            form (str):  A form name.
            prop (str):  A property name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(nid, valu)]
        '''
        try:
            indxby = IndxByProp(self, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterUnivRows(self, prop, stortype=None, startvalu=None):
        '''
        Yields nid, valu tuples of nodes with a particular universal property, optionally (re)starting at startvalu.

        Args:
            prop (str):  A universal property name.
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(nid, valu)]
        '''
        try:
            indxby = IndxByProp(self, None, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self._iterRows(indxby, stortype=stortype, startvalu=startvalu):
            yield item

    async def iterTagRows(self, tag, form=None):
        '''
        Yields (nid, (valu, form)) values that match a tag and optional form.

        Args:
            tag (str): the tag to match
            form (Optional[str]):  if present, only yields nids of nodes that match the form.

        Yields:
            (nid, (ival, form))
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_TAG, form, tag)
        except s_exc.NoSuchAbrv:
            return

        for lkey, nid in self.layrslab.scanByPref(abrv, db=self.indxdb):
            await asyncio.sleep(0)

            sref = self.genStorNodeRef(nid)
            ndef = self.core.getNidNdef(nid)
            valu = sref.sode['tags'].get(tag)

            yield nid, (valu, ndef[0])

    async def iterTagPropRows(self, tag, prop, form=None, stortype=None, startvalu=None):
        '''
        Yields (nid, valu) that match a tag:prop, optionally (re)starting at startvalu.

        Args:
            tag (str):  tag name
            prop (str):  prop name
            form (Optional[str]):  optional form name
            stortype (Optional[int]): a STOR_TYPE_* integer representing the type of form:prop
            startvalu (Any):  The value to start at.  May only be not None if stortype is not None.

        Returns:
            AsyncIterator[Tuple(nid, valu)]
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
            AsyncIterator[Tuple[nid,valu]]
        '''
        assert stortype is not None or startvalu is None

        abrv = indxby.abrv
        abrvlen = indxby.abrvlen
        startbytz = None

        if startvalu is not None:
            stortype = indxby.getStorType()
            startbytz = stortype.indx(startvalu)[0]

        for key, nid in self.layrslab.scanByPref(abrv, startkey=startbytz, db=indxby.db):

            await asyncio.sleep(0)

            indx = key[abrvlen:]

            valu = indxby.getNodeValu(nid, indx=indx)
            if valu is s_common.novalu:
                continue

            yield nid, valu

    async def getNodeData(self, nid, name):
        '''
        Return a single element of a nid's node data
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, name, None)

        except s_exc.NoSuchAbrv:
            return False, None

        byts = self.dataslab.get(nid + abrv, db=self.nodedata)
        if byts is None:
            return False, None

        return True, s_msgpack.un(byts)

    async def iterNodeData(self, nid):
        '''
        Return a generator of all a node's data by nid.
        '''
        for lkey, byts in self.dataslab.scanByPref(nid, db=self.nodedata):
            abrv = lkey[8:]

            valu = s_msgpack.un(byts)
            prop = self.core.getAbrvIndx(abrv)

            yield prop[0], valu

    async def iterNodeDataKeys(self, nid):
        '''
        Return a generator of all a nid's node data keys
        '''
        for lkey in self.dataslab.scanKeysByPref(nid, db=self.nodedata):
            abrv = lkey[8:]
            prop = self.core.getAbrvIndx(abrv)
            yield prop[0]

    async def iterLayerNodeEdits(self):
        '''
        Scan the full layer and yield artificial sets of nodeedits.
        '''
        await self._saveDirtySodes()

        for nid, byts in self.layrslab.scanByFull(db=self.bynid):

            sode = s_msgpack.un(byts)
            ndef = self.core.getNidNdef(nid)

            form = ndef[0]

            edits = []
            nodeedit = (nid, form, edits)

            # TODO tombstones
            valt = sode.get('valu')
            if valt is not None:
                edits.append((EDIT_NODE_ADD, valt))

            for prop, (valu, stortype) in sode.get('props', {}).items():
                edits.append((EDIT_PROP_SET, (prop, valu, None, stortype)))

            for tag, tagv in sode.get('tags', {}).items():
                edits.append((EDIT_TAG_SET, (tag, tagv, None)))

            for tag, propdict in sode.get('tagprops', {}).items():
                for prop, (valu, stortype) in propdict.items():
                    edits.append((EDIT_TAGPROP_SET, (tag, prop, valu, None, stortype)))

            async for prop, valu in self.iterNodeData(nid):
                edits.append((EDIT_NODEDATA_SET, (prop, valu, None)))

            async for verb, n2nid in self.iterNodeEdgesN1(nid):
                edits.append((EDIT_EDGE_ADD, (verb, n2nid)))

            yield nodeedit

    async def _wipeNodeData(self, nid, sode):
        '''
        Remove all node data for a nid
        '''
        for lkey, _ in self.dataslab.scanByPref(nid, db=self.nodedata):
            await asyncio.sleep(0)
            self.dataslab.delete(lkey, db=self.nodedata)
            self.dataslab.delete(lkey[8:], nid, db=self.dataname)

    async def getModelVers(self):
        return self.layrinfo.get('model:version', (-1, -1, -1))

    async def setModelVers(self, vers):
        self._reqNotReadOnly()
        return await self._push('layer:set:modelvers', vers)

    @s_nexus.Pusher.onPush('layer:set:modelvers')
    async def _setModelVers(self, vers):
        await self.layrinfo.set('model:version', vers)

    async def getStorNodes(self):
        '''
        Yield (nid, sode) tuples for all the nodes with props/tags/tagprops stored in this layer.
        '''
        # flush any dirty sodes so we can yield them from the index in nid order
        await self._saveDirtySodes()

        for nid, byts in self.layrslab.scanByFull(db=self.bynid):
            await asyncio.sleep(0)
            yield nid, s_msgpack.un(byts)

    def getStorNode(self, nid):
        '''
        Return a *COPY* of the storage node (or an empty default dict).
        '''
        sode = self._getStorNode(nid)
        if sode is not None:
            return deepcopy(sode)
        return collections.defaultdict(dict)

    async def syncNodeEdits2(self, offs, wait=True, compat=False):
        '''
        Once caught up with storage, yield them in realtime.

        Returns:
            Tuple of offset(int), nodeedits, meta(dict)
        '''
        if not self.logedits:
            return

        if not compat:
            for offi, _ in self.nodeeditlog.iter(offs):
                nexsitem = await self.core.nexsroot.nexslog.get(offi)
                yield (offi, *nexsitem[2])

            if wait:
                async with self.getNodeEditWindow() as wind:
                    async for item in wind:
                        yield item
            return

        for offi, _ in self.nodeeditlog.iter(offs):
            nexsitem = await self.core.nexsroot.nexslog.get(offi)
            (nodeedits, meta) = nexsitem[2]

            realnodeedits = self.core.localToRemoteEdits(nodeedits)
            if realnodeedits:
                yield (offi, realnodeedits, meta)

        if wait:
            async with self.getNodeEditWindow() as wind:
                async for (offi, nodeedits, meta) in wind:
                    realnodeedits = self.core.localToRemoteEdits(nodeedits)
                    if realnodeedits:
                        yield (offi, realnodeedits, meta)

    async def syncNodeEdits(self, offs, wait=True, compat=False):
        '''
        Identical to syncNodeEdits2, but doesn't yield meta
        '''
        async for offi, nodeedits, _meta in self.syncNodeEdits2(offs, wait=wait, compat=compat):
            yield (offi, nodeedits)

    async def syncIndexEvents(self, offs, matchdef, wait=True):
        '''
        Yield (offs, (nid, form, ETYPE, VALS)) tuples from the nodeedit log starting from the given offset.
        Only edits that match the filter in matchdef will be yielded.

        Notes:

            ETYPE is an constant EDIT_* above.  VALS is a tuple whose format depends on ETYPE, outlined in the comment
            next to the constant.

            Additionally, every 1000 entries, an entry (offs, (None, None, EDIT_PROGRESS, ())) message is emitted.

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
            for nid, form, edit in editses:
                for etyp, vals in edit:
                    if ((form in formm and etyp in (EDIT_NODE_ADD, EDIT_NODE_DEL))
                            or (etyp in (EDIT_PROP_SET, EDIT_PROP_DEL)
                                and (vals[0] in propm or f'{form}:{vals[0]}' in propm))
                            or (etyp in (EDIT_TAG_SET, EDIT_TAG_DEL) and vals[0] in tagm)
                            or (etyp in (EDIT_TAGPROP_SET, EDIT_TAGPROP_DEL)
                                and (vals[1] in tagpropm or f'{vals[0]}:{vals[1]}' in tagpropm))):

                        yield (curoff, (nid, form, etyp, vals))

            await asyncio.sleep(0)

            count += 1
            if count % 1000 == 0:
                yield (curoff, (None, None, EDIT_PROGRESS, ()))

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

    async def delete(self):
        '''
        Delete the underlying storage
        '''
        self.isdeleted = True
        await self.fini()
        shutil.rmtree(self.dirn, ignore_errors=True)

def getNodeEditPerms(nodeedits):
    '''
    Yields (offs, perm) tuples that can be used in user.allowed()
    '''
    tags = []
    tagadds = []

    for nodeoffs, (nid, form, edits) in enumerate(nodeedits):

        tags.clear()
        tagadds.clear()

        for editoffs, (edit, info) in enumerate(edits):

            permoffs = (nodeoffs, editoffs)

            if edit == EDIT_NODE_ADD:
                yield (permoffs, ('node', 'add', form))
                continue

            if edit == EDIT_NODE_DEL:
                yield (permoffs, ('node', 'del', form))
                continue

            if edit == EDIT_PROP_SET:
                yield (permoffs, ('node', 'prop', 'set', f'{form}:{info[0]}'))
                continue

            if edit == EDIT_PROP_DEL:
                yield (permoffs, ('node', 'prop', 'del', f'{form}:{info[0]}'))
                continue

            if edit == EDIT_TAG_SET:
                if info[1] != (None, None):
                    tagadds.append(info[0])
                    yield (permoffs, ('node', 'tag', 'add', *info[0].split('.')))
                else:
                    tags.append((len(info[0]), editoffs, info[0]))
                continue

            if edit == EDIT_TAG_DEL:
                yield (permoffs, ('node', 'tag', 'del', *info[0].split('.')))
                continue

            if edit == EDIT_TAGPROP_SET:
                yield (permoffs, ('node', 'tag', 'add', *info[0].split('.')))
                continue

            if edit == EDIT_TAGPROP_DEL:
                yield (permoffs, ('node', 'tag', 'del', *info[0].split('.')))
                continue

            if edit == EDIT_NODEDATA_SET:
                yield (permoffs, ('node', 'data', 'set', info[0]))
                continue

            if edit == EDIT_NODEDATA_DEL:
                yield (permoffs, ('node', 'data', 'pop', info[0]))
                continue

            if edit == EDIT_EDGE_ADD:
                yield (permoffs, ('node', 'edge', 'add', info[0]))
                continue

            if edit == EDIT_EDGE_DEL:
                yield (permoffs, ('node', 'edge', 'del', info[0]))
                continue

        for _, editoffs, tag in sorted(tags, reverse=True):
            look = tag + '.'
            if any([tagadd.startswith(look) for tagadd in tagadds]):
                continue

            yield ((nodeoffs, editoffs), ('node', 'tag', 'add', *tag.split('.')))
            tagadds.append(tag)
