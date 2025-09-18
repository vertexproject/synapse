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
    A storage node *may* be partial ( as it is produced by a given layer ) and are joined by the view
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
import synapse.lib.spooled as s_spooled
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
        'growsize': {'type': 'integer'},
        'logedits': {'type': 'boolean', 'default': True},
        'name': {'type': 'string'},
        'readonly': {'type': 'boolean', 'default': False},
    },
    'additionalProperties': True,
    'required': ['iden', 'creator'],
})

WINDOW_MAXSIZE = 10_000
MIGR_COMMIT_SIZE = 1_000

class LayerApi(s_cell.CellApi):

    async def __anit__(self, core, link, user, layr):

        await s_cell.CellApi.__anit__(self, core, link, user)

        self.layr = layr
        self.readperm = ('layer', 'read', self.layr.iden)
        self.writeperm = ('layer', 'write', self.layr.iden)

    async def iterLayerNodeEdits(self, *, meta=False):
        '''
        Scan the full layer and yield artificial nodeedit sets.
        '''

        await self._reqUserAllowed(self.readperm)
        async for item in self.layr.iterLayerNodeEdits(meta=meta):
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

    async def storNodeEdits(self, nodeedits, *, meta=None):

        await self._reqUserAllowed(self.writeperm)

        if meta is None:
            meta = {'time': s_common.now(), 'user': self.user.iden}

        return await self.layr.saveNodeEdits(nodeedits, meta)

    async def storNodeEditsNoLift(self, nodeedits, *, meta=None):

        await self._reqUserAllowed(self.writeperm)

        if meta is None:
            meta = {'time': s_common.now(), 'user': self.user.iden}

        await self.layr.storNodeEditsNoLift(nodeedits, meta)

    async def syncNodeEdits(self, offs, *, wait=True, reverse=False, compat=False):
        '''
        Yield (offs, nodeedits) tuples from the nodeedit log starting from the given offset.

        Once caught up with storage, yield them in realtime.
        '''
        await self._reqUserAllowed(self.readperm)
        async for item in self.layr.syncNodeEdits(offs, wait=wait, reverse=reverse, compat=compat):
            yield item
            await asyncio.sleep(0)

    async def syncNodeEdits2(self, offs, *, wait=True, compat=False):
        await self._reqUserAllowed(self.readperm)
        async for item in self.layr.syncNodeEdits2(offs, wait=wait, compat=compat):
            yield item
            await asyncio.sleep(0)

    async def getEditIndx(self):
        '''
        Returns what will be the *next* nodeedit log index.
        '''
        await self._reqUserAllowed(self.readperm)
        return await self.layr.getEditIndx()

    async def getEditSize(self):
        '''
        Return the total number of (edits, meta) pairs in the layer changelog.
        '''
        await self._reqUserAllowed(self.readperm)
        return await self.layr.getEditSize()

    async def getIden(self):
        await self._reqUserAllowed(self.readperm)
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
STOR_TYPE_IPV6 = 18  # no longer in use, migrated to STOR_TYPE_IPADDR

STOR_TYPE_U128 = 19
STOR_TYPE_I128 = 20

STOR_TYPE_MINTIME = 21

STOR_TYPE_FLOAT64 = 22
STOR_TYPE_HUGENUM = 23

STOR_TYPE_MAXTIME = 24
STOR_TYPE_NDEF = 25
STOR_TYPE_IPADDR = 26

STOR_TYPE_ARRAY = 27

STOR_TYPE_NODEPROP = 28

STOR_FLAG_ARRAY = 0x8000

# Edit types (etyp)

EDIT_NODE_ADD = 0      # (<etyp>, (<valu>, <type>, <virts>))
EDIT_NODE_DEL = 1      # (<etyp>, ())
EDIT_PROP_SET = 2      # (<etyp>, (<prop>, <valu>, <type>, <virts>))
EDIT_PROP_DEL = 3      # (<etyp>, (<prop>,))
EDIT_TAG_SET = 4       # (<etyp>, (<tag>, <valu>))
EDIT_TAG_DEL = 5       # (<etyp>, (<tag>,))
EDIT_TAGPROP_SET = 6   # (<etyp>, (<tag>, <prop>, <valu>, <type>))
EDIT_TAGPROP_DEL = 7   # (<etyp>, (<tag>, <prop>))
EDIT_NODEDATA_SET = 8  # (<etyp>, (<name>, <valu>))
EDIT_NODEDATA_DEL = 9  # (<etyp>, (<name>,))
EDIT_EDGE_ADD = 10     # (<etyp>, (<verb>, <destnodeiden>))
EDIT_EDGE_DEL = 11     # (<etyp>, (<verb>, <destnodeiden>))

EDIT_NODE_TOMB = 12          # (<etyp>, ())
EDIT_NODE_TOMB_DEL = 13      # (<etyp>, ())
EDIT_PROP_TOMB = 14          # (<etyp>, (<prop>))
EDIT_PROP_TOMB_DEL = 15      # (<etyp>, (<prop>))
EDIT_TAG_TOMB = 16           # (<etyp>, (<tag>))
EDIT_TAG_TOMB_DEL = 17       # (<etyp>, (<tag>))
EDIT_TAGPROP_TOMB = 18       # (<etyp>, (<tag>, <prop>))
EDIT_TAGPROP_TOMB_DEL = 19   # (<etyp>, (<tag>, <prop>))
EDIT_NODEDATA_TOMB = 20      # (<etyp>, (<name>))
EDIT_NODEDATA_TOMB_DEL = 21  # (<etyp>, (<name>))
EDIT_EDGE_TOMB = 22          # (<etyp>, (<verb>, <destnodeiden>))
EDIT_EDGE_TOMB_DEL = 23      # (<etyp>, (<verb>, <destnodeiden>))

EDIT_META_SET = 24           # (<etyp>, (<prop>, <valu>, <type>))

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

INDX_NODEDATA = b'\x00\x0c'

INDX_TOMB = b'\x00\x0d'

INDX_NDEF = b'\x00\x0e'

INDX_FORM = b'\x00\x0f'

INDX_VIRTUAL = b'\x00\x10'
INDX_VIRTUAL_ARRAY = b'\x00\x11'

INDX_NODEPROP = b'\x00\x12'

FLAG_TOMB = b'\x00'
FLAG_NORM = b'\x01'

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

class IndxByFormArrayValu(IndxByForm):

    def __repr__(self):
        return f'IndxByFormArrayValu: {self.form}'

    def keyNidsByDups(self, indx, reverse=False):
        indxvalu = len(indx).to_bytes(4, 'big') + s_common.buid(indx)
        if reverse:
            yield from self.layr.layrslab.scanByDupsBack(self.abrv + indxvalu, db=self.db)
        else:
            yield from self.layr.layrslab.scanByDups(self.abrv + indxvalu, db=self.db)

class IndxByFormArraySize(IndxByForm):

    def __repr__(self):
        return f'IndxByFormArraySize: {self.form}'

    def keyNidsByRange(self, minindx, maxindx, reverse=False):

        strt = self.abrv + minindx + (b'\x00' * 16)
        stop = self.abrv + maxindx + (b'\xff' * 16)
        if reverse:
            yield from self.layr.layrslab.scanByRangeBack(stop, strt, db=self.db)
        else:
            yield from self.layr.layrslab.scanByRange(strt, stop, db=self.db)

    def keyNidsByDups(self, indx, reverse=False):
        indx = indx.to_bytes(4, 'big')
        if reverse:
            yield from self.layr.layrslab.scanByPrefBack(self.abrv + indx, db=self.db)
        else:
            yield from self.layr.layrslab.scanByPref(self.abrv + indx, db=self.db)

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
        form = self.layr.core.model.form(self.form)
        if self.prop is None:
            typeindx = form.type.stortype
        else:
            typeindx = form.props.get(self.prop).type.stortype

        return self.layr.stortypes[typeindx]

    def getSodeValu(self, sode):
        valt = sode['props'].get(self.prop)
        if valt is not None:
            return valt[0]

        return s_common.novalu

    def __repr__(self):
        return f'IndxByProp: {self.form}:{self.prop}'

class IndxByPropKeys(IndxByProp):
    '''
    IndxBy sub-class for retrieving unique property values.
    '''
    def keyNidsByDups(self, indx, reverse=False):
        lkey = self.abrv + indx
        if self.layr.layrslab.has(lkey, db=self.db):
            yield lkey, None

    def keyNidsByPref(self, indx=b'', reverse=False):
        for lkey in self.layr.layrslab.scanKeysByPref(self.abrv + indx, db=self.db, nodup=True):
            yield lkey, None

    def keyNidsByRange(self, minindx, maxindx, reverse=False):
        for lkey in self.layr.layrslab.scanKeysByRange(self.abrv + minindx, lmax=self.abrv + maxindx, db=self.db, nodup=True):
            yield lkey, None

    def getNodeValu(self, nid, indx=None):

        if indx is None:  # pragma: no cover
            return s_common.novalu

        if (valu := self.indxToValu(indx)) is not s_common.novalu:
            return valu

        if (nid := self.layr.layrslab.get(self.abrv + indx, db=self.db)) is None:  # pragma: no cover
            return s_common.novalu

        if (sode := self.layr._getStorNode(nid)) is not None:
            if self.prop is None:
                valt = sode.get('valu')
            else:
                valt = sode['props'].get(self.prop)

            if valt is not None:
                return valt[0]

        return s_common.novalu

    def __repr__(self):
        return f'IndxByPropKeys: {self.form}:{self.prop}'

class IndxByPropArrayKeys(IndxByPropKeys):
    '''
    IndxBy sub-class for retrieving unique property array values.
    '''
    def __init__(self, layr, form, prop):
        abrv = layr.core.getIndxAbrv(INDX_ARRAY, form, prop)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop

    def getStorType(self):
        form = self.layr.core.model.form(self.form)
        if self.prop is None:
            typeindx = form.type.arraytype.stortype
        else:
            typeindx = form.props.get(self.prop).type.arraytype.stortype

        return self.layr.stortypes[typeindx]

    def __repr__(self):
        return f'IndxByPropArrayKeys: {self.form}:{self.prop}'

class IndxByVirt(IndxBy):

    def __init__(self, layr, form, prop, virts):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_VIRTUAL, form, prop, *virts)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop
        self.virts = virts

    def __repr__(self):
        return f'IndxByVirt: {self.form}:{self.prop}.{".".join(self.virts)}'

class IndxByVirtArray(IndxBy):

    def __init__(self, layr, form, prop, virts):
        '''
        Note:  may raise s_exc.NoSuchAbrv
        '''
        abrv = layr.core.getIndxAbrv(INDX_VIRTUAL_ARRAY, form, prop, *virts)
        IndxBy.__init__(self, layr, abrv, db=layr.indxdb)

        self.form = form
        self.prop = prop
        self.virts = virts

    def __repr__(self):
        return f'IndxByVirtArray: {self.form}:{self.prop}.{".".join(self.virts)}'

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
        return f'IndxByPropArray: {self.form}:{self.prop}'

class IndxByPropArrayValu(IndxByProp):

    def __repr__(self):
        return f'IndxByPropArrayValu: {self.form}:{self.prop}'

    def keyNidsByDups(self, indx, reverse=False):
        indxvalu = len(indx).to_bytes(4, 'big') + s_common.buid(indx)
        if reverse:
            yield from self.layr.layrslab.scanByDupsBack(self.abrv + indxvalu, db=self.db)
        else:
            yield from self.layr.layrslab.scanByDups(self.abrv + indxvalu, db=self.db)

class IndxByPropArraySize(IndxByProp):

    def __repr__(self):
        return f'IndxByPropArraySize: {self.form}:{self.prop}'

    def keyNidsByRange(self, minindx, maxindx, reverse=False):

        strt = self.abrv + minindx + (b'\x00' * 16)
        stop = self.abrv + maxindx + (b'\xff' * 16)
        if reverse:
            yield from self.layr.layrslab.scanByRangeBack(stop, strt, db=self.db)
        else:
            yield from self.layr.layrslab.scanByRange(strt, stop, db=self.db)

    def keyNidsByDups(self, indx, reverse=False):
        indx = indx.to_bytes(4, 'big')
        if reverse:
            yield from self.layr.layrslab.scanByPrefBack(self.abrv + indx, db=self.db)
        else:
            yield from self.layr.layrslab.scanByPref(self.abrv + indx, db=self.db)

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
        async for lkey, nid in func(liftby, valu, reverse=reverse):
            yield lkey[abrvlen:], nid

    async def indxByForm(self, form, cmpr, valu, reverse=False, virts=None):
        try:
            if virts:
                indxby = IndxByVirt(self.layr, form, None, virts)
            else:
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

    async def indxByProp(self, form, prop, cmpr, valu, reverse=False, virts=None):
        try:
            if virts:
                indxby = IndxByVirt(self.layr, form, prop, virts)
            else:
                indxby = IndxByProp(self.layr, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByPropArray(self, form, prop, cmpr, valu, reverse=False, virts=None):
        try:
            if virts:
                indxby = IndxByVirtArray(self.layr, form, prop, virts)
            else:
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

    def getVirtIndxVals(self, nid, form, prop, virts):

        layr = self.layr
        kvpairs = []

        for name, (valu, vtyp) in virts.items():

            abrv = layr.core.setIndxAbrv(INDX_VIRTUAL, form, prop, name)

            if vtyp & STOR_FLAG_ARRAY:

                arryabrv = layr.core.setIndxAbrv(INDX_VIRTUAL_ARRAY, form, prop, name)

                for indx in layr.getStorIndx(vtyp, valu):
                    kvpairs.append((arryabrv + indx, nid))
                    layr.indxcounts.inc(arryabrv)

                for indx in layr.getStorIndx(STOR_TYPE_MSGP, valu):
                    kvpairs.append((abrv + indx, nid))
                    layr.indxcounts.inc(abrv)

            else:
                for indx in layr.getStorIndx(vtyp, valu):
                    kvpairs.append((abrv + indx, nid))
                    layr.indxcounts.inc(abrv)

        return kvpairs

    def delVirtIndxVals(self, nid, form, prop, virts):

        layr = self.layr

        for name, (valu, vtyp) in virts.items():

            abrv = layr.core.setIndxAbrv(INDX_VIRTUAL, form, prop, name)

            if vtyp & STOR_FLAG_ARRAY:

                arryabrv = layr.core.setIndxAbrv(INDX_VIRTUAL_ARRAY, form, prop, name)

                for indx in layr.getStorIndx(vtyp, valu):
                    layr.layrslab.delete(arryabrv + indx, nid, db=layr.indxdb)
                    layr.indxcounts.inc(arryabrv, -1)

                for indx in layr.getStorIndx(STOR_TYPE_MSGP, valu):
                    layr.layrslab.delete(abrv + indx, nid, db=layr.indxdb)
                    layr.indxcounts.inc(abrv, -1)

            else:
                for indx in layr.getStorIndx(vtyp, valu):
                    layr.layrslab.delete(abrv + indx, nid, db=layr.indxdb)
                    layr.indxcounts.inc(abrv, -1)

    async def _liftRegx(self, liftby, valu, reverse=False):

        regx = regex.compile(valu, flags=regex.I)

        abrvlen = liftby.abrvlen
        isarray = isinstance(liftby, IndxByPropArray)

        for lkey, nid in liftby.keyNidsByPref(reverse=reverse):

            await asyncio.sleep(0)

            indx = lkey[abrvlen:]

            if (storvalu := liftby.getNodeValu(nid, indx=indx)) is s_common.novalu:
                continue

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

        indx = valu.encode('utf8')
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
        return bytz.decode('utf8')

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
        return bytz.decode('utf8')[::-1]

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

    # no longer in use, remove after 3.0.0 migration is no longer needed

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
        self.unksize = 0x7ffffffffffffffe
        self.unkbyts = (self.futsize + self.offset).to_bytes(8, 'big')
        self.futbyts = (self.unksize + self.offset).to_bytes(8, 'big')
        self.maxbyts = (self.unksize + self.offset - 1).to_bytes(8, 'big')
        self.lifters.update({
            '@=': self._liftAtIval,
        })

    def getVirtIndxVals(self, nid, form, prop, virts):
        return ()

    def delVirtIndxVals(self, nid, form, prop, virts):
        return

    async def _liftAtIval(self, liftby, valu, reverse=False):
        minindx = self.getIntIndx(valu[0])
        maxindx = self.getIntIndx(valu[1] - 1)
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

class StorTypeIval(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IVAL)
        self.timetype = StorTypeTime(layr)

        self.unkdura = 0xffffffffffffffff
        self.futdura = 0xfffffffffffffffe
        self.maxdura = 0xfffffffffffffffd
        self.unkdurabyts = self.unkdura.to_bytes(8, 'big')
        self.futdurabyts = self.futdura.to_bytes(8, 'big')
        self.maxdurabyts = self.maxdura.to_bytes(8, 'big')

        self.lifters.update({
            '=': self._liftIvalEq,
            '@=': self._liftIvalAt,
            'min@=': self._liftIvalPartAt,
            'max@=': self._liftIvalPartAt,
            'duration=': self._liftIvalDurationEq,
            'duration<': self._liftIvalDurationLt,
            'duration>': self._liftIvalDurationGt,
            'duration<=': self._liftIvalDurationLe,
            'duration>=': self._liftIvalDurationGe,
        })

        for part in ('min', 'max'):
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

    async def indxByForm(self, form, cmpr, valu, reverse=False, virts=None):
        try:
            indxtype = self.propindx.get(cmpr, IndxByProp)
            indxby = indxtype(self.layr, form, None)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByProp(self, form, prop, cmpr, valu, reverse=False, virts=None):
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

    async def _liftIvalDurationEq(self, liftby, valu, reverse=False):
        norm, futstart = valu
        duraindx = norm.to_bytes(8, 'big')

        if futstart is not None:
            futindx = self.futdurabyts + (self.unkdura - (futstart + self.timetype.offset)).to_bytes(8, 'big')
            if reverse:
                indxs = (futindx, duraindx)
            else:
                indxs = (duraindx, futindx)
        else:
            indxs = (duraindx,)

        for indx in indxs:
            for item in liftby.keyNidsByPref(indx, reverse=reverse):
                yield item

    async def _liftIvalDurationGt(self, liftby, valu, reverse=False):
        norm, futstart = valu
        if futstart is None:
            return

        async for item in self._liftIvalDurationGe(liftby, (norm + 1, futstart - 1), reverse=reverse):
            yield item

    async def _liftIvalDurationGe(self, liftby, valu, reverse=False):
        norm, futstart = valu

        if futstart is not None:
            duraindx = (norm.to_bytes(8, 'big'), self.maxdurabyts)

            strtindx = (self.unkdura - (futstart + self.timetype.offset)).to_bytes(8, 'big')
            futindx = (self.futdurabyts + strtindx, self.futdurabyts + self.unkdurabyts)
            if reverse:
                indxs = (futindx, duraindx)
            else:
                indxs = (duraindx, futindx)
        else:
            # If we got a >= ? or *, we're just going to get values = because > doesn't make sense.
            byts = norm.to_bytes(8, 'big')
            indxs = ((byts, byts),)

        for (pkeymin, pkeymax) in indxs:
            for item in liftby.keyNidsByRange(pkeymin, pkeymax, reverse=reverse):
                yield item

    async def _liftIvalDurationLt(self, liftby, valu, reverse=False):
        norm, futstart = valu
        if futstart is None:
            return

        async for item in self._liftIvalDurationLe(liftby, (norm - 1, futstart + 1), reverse=reverse):
            yield item

    async def _liftIvalDurationLe(self, liftby, valu, reverse=False):
        norm, futstart = valu

        if futstart is not None:
            duraindx = (self.timetype.zerobyts, norm.to_bytes(8, 'big'))

            strtindx = (self.unkdura - (futstart + self.timetype.offset)).to_bytes(8, 'big')
            futindx = (self.futdurabyts + self.timetype.zerobyts, self.futdurabyts + strtindx)
            if reverse:
                indxs = (futindx, duraindx)
            else:
                indxs = (duraindx, futindx)
        else:
            # If we got a <= ? or *, we're just going to get values = because < doesn't make sense.
            byts = norm.to_bytes(8, 'big')
            indxs = ((byts, byts),)

        for (pkeymin, pkeymax) in indxs:
            for item in liftby.keyNidsByRange(pkeymin, pkeymax, reverse=reverse):
                yield item

    def indx(self, valu):
        return (self.timetype.getIntIndx(valu[0]) + self.timetype.getIntIndx(valu[1]),)

    def decodeIndx(self, bytz):
        minv = self.timetype.decodeIndx(bytz[:8])
        maxv = self.timetype.decodeIndx(bytz[8:16])

        if maxv == self.timetype.futsize:
            return (minv, maxv, self.futdura)

        elif minv == self.timetype.unksize or maxv == self.timetype.unksize:
            return (minv, maxv, self.unkdura)

        return (minv, maxv, maxv - minv)

    def getDurationIndx(self, valu):

        if (dura := valu[2]) == self.unkdura:
            return self.unkdurabyts

        elif dura != self.futdura:
            return dura.to_bytes(8, 'big')

        return self.futdurabyts + (self.unkdura - (valu[0] + self.timetype.offset)).to_bytes(8, 'big')

    def getVirtIndxVals(self, nid, form, prop, virts):
        return ()

    def delVirtIndxVals(self, nid, form, prop, virts):
        return

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

class StorTypeArray(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_ARRAY)
        self.sizetype = StorTypeInt(layr, STOR_TYPE_U32, 4, False)
        self.lifters.update({
            '=': self._liftArrayEq,
            '<': self.sizetype._liftIntLt,
            '>': self.sizetype._liftIntGt,
            '<=': self.sizetype._liftIntLe,
            '>=': self.sizetype._liftIntGe,
            'range=': self.sizetype._liftIntRange,
        })

        self.formindx = {
            'size': IndxByFormArraySize
        }

        self.propindx = {
            'size': IndxByPropArraySize
        }

    async def indxByForm(self, form, cmpr, valu, reverse=False, virts=None):
        try:
            indxtype = IndxByFormArrayValu
            if virts:
                indxtype = self.formindx.get(virts[0], IndxByFormArrayValu)

            indxby = indxtype(self.layr, form)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByProp(self, form, prop, cmpr, valu, reverse=False, virts=None):
        try:
            indxtype = IndxByPropArrayValu
            if virts:
                indxtype = self.propindx.get(virts[0], IndxByPropArrayValu)

            indxby = indxtype(self.layr, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    def indx(self, valu):
        return (len(valu).to_bytes(4, 'big') + s_common.buid(valu),)

    async def _liftArrayEq(self, liftby, valu, reverse=False):
        for item in liftby.keyNidsByDups(valu, reverse=reverse):
            yield item

class StorTypeNdef(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_NDEF)
        self.lifters |= {
            '=': self._liftNdefEq,
            'form=': self._liftNdefFormEq,
        }

    def indx(self, valu):
        formabrv = self.layr.core.setIndxAbrv(INDX_PROP, valu[0], None)
        return (formabrv + s_common.buid(valu),)

    async def indxByProp(self, form, prop, cmpr, valu, reverse=False, virts=None):
        try:
            indxby = IndxByProp(self.layr, form, prop)
        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByPropArray(self, form, prop, cmpr, valu, reverse=False, virts=None):
        try:
            indxby = IndxByPropArray(self.layr, form, prop)

        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def _liftNdefEq(self, liftby, valu, reverse=False):
        try:
            formabrv = self.layr.core.getIndxAbrv(INDX_PROP, valu[0], None)
        except s_exc.NoSuchAbrv:
            return

        for item in liftby.keyNidsByDups(formabrv + s_common.buid(valu), reverse=reverse):
            yield item

    async def _liftNdefFormEq(self, liftby, valu, reverse=False):
        try:
            formabrv = self.layr.core.getIndxAbrv(INDX_PROP, valu, None)
        except s_exc.NoSuchAbrv:
            return

        for item in liftby.keyNidsByPref(formabrv, reverse=reverse):
            yield item

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

class StorTypeIPAddr(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IPADDR)
        self.lifters.update({
            '=': self._liftAddrEq,
            '<': self._liftAddrLt,
            '>': self._liftAddrGt,
            '<=': self._liftAddrLe,
            '>=': self._liftAddrGe,
            'range=': self._liftAddrRange,
        })

        self.maxval = 2 ** 128 - 1

    async def _liftAddrEq(self, liftby, valu, reverse=False):
        indx = self._getIndxByts(valu)
        for item in liftby.keyNidsByDups(indx, reverse=reverse):
            yield item

    def _getMaxIndx(self, valu):

        if valu[0] == 4:
            return b'\x04\xff\xff\xff\xff'

        return b'\x06\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'

    def _getMinIndx(self, valu):

        if valu[0] == 4:
            return b'\x04\x00\x00\x00\x00'

        return b'\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    async def _liftAddrLe(self, liftby, valu, reverse=False):
        if valu[1] < 0:
            return

        minindx = self._getMinIndx(valu)
        maxindx = self._getIndxByts(valu)
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftAddrGe(self, liftby, valu, reverse=False):
        if valu[1] > self.maxval:
            return

        minindx = self._getIndxByts(valu)
        maxindx = self._getMaxIndx(valu)
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    async def _liftAddrLt(self, liftby, valu, reverse=False):
        async for item in self._liftAddrLe(liftby, (valu[0], valu[1] - 1), reverse=reverse):
            yield item

    async def _liftAddrGt(self, liftby, valu, reverse=False):
        async for item in self._liftAddrGe(liftby, (valu[0], valu[1] + 1), reverse=reverse):
            yield item

    async def _liftAddrRange(self, liftby, valu, reverse=False):

        minindx = self._getIndxByts(valu[0])
        maxindx = self._getIndxByts(valu[1])
        for item in liftby.keyNidsByRange(minindx, maxindx, reverse=reverse):
            yield item

    def indx(self, valu):
        return (self._getIndxByts(valu),)

    def _getIndxByts(self, valu):

        if valu[0] == 4:
            return b'\x04' + valu[1].to_bytes(4, 'big')

        if valu[0] == 6:
            return b'\x06' + valu[1].to_bytes(16, 'big')

        mesg = 'Invalid STOR_TYPE_IPADDR: {valu}'
        raise s_exc.BadTypeValu(mesg=mesg)

class StorTypeNodeProp(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_NODEPROP)
        self.lifters |= {
            '=': self._liftNodePropEq,
            'prop=': self._liftNodePropNameEq,
        }

    def indx(self, valu):
        propabrv = self.layr.core.setIndxAbrv(INDX_NODEPROP, valu[0])
        return (propabrv + s_common.buid(valu),)

    async def indxByProp(self, form, prop, cmpr, valu, reverse=False, virts=None):
        try:
            indxby = IndxByProp(self.layr, form, prop)
        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def indxByPropArray(self, form, prop, cmpr, valu, reverse=False, virts=None):
        try:
            indxby = IndxByPropArray(self.layr, form, prop)
        except s_exc.NoSuchAbrv:
            return

        async for item in self.indxBy(indxby, cmpr, valu, reverse=reverse):
            yield item

    async def _liftNodePropEq(self, liftby, valu, reverse=False):
        try:
            propabrv = self.layr.core.getIndxAbrv(INDX_NODEPROP, valu[0])
        except s_exc.NoSuchAbrv:
            return

        for item in liftby.keyNidsByDups(propabrv + s_common.buid(valu), reverse=reverse):
            yield item

    async def _liftNodePropNameEq(self, liftby, valu, reverse=False):
        try:
            propabrv = self.layr.core.getIndxAbrv(INDX_NODEPROP, valu)
        except s_exc.NoSuchAbrv:
            return

        for item in liftby.keyNidsByPref(propabrv, reverse=reverse):
            yield item

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

        self.growsize = self.layrinfo.get('growsize')
        self.logedits = self.layrinfo.get('logedits')

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
            StorTypeNdef(self),
            StorTypeIPAddr(self),

            StorTypeArray(self),

            StorTypeNodeProp(self),
        ]

        self.timetype = self.stortypes[STOR_TYPE_TIME]
        self.ivaltype = self.stortypes[STOR_TYPE_IVAL]
        self.ivaltimetype = self.ivaltype.timetype

        self.createdabrv = self.core.setIndxAbrv(INDX_VIRTUAL, None, None, 'created')
        self.updatedabrv = self.core.setIndxAbrv(INDX_VIRTUAL, None, None, 'updated')

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
            self._editNodeTomb,
            self._editNodeTombDel,
            self._editPropTomb,
            self._editPropTombDel,
            self._editTagTomb,
            self._editTagTombDel,
            self._editTagPropTomb,
            self._editTagPropTombDel,
            self._editNodeDataTomb,
            self._editNodeDataTombDel,
            self._editNodeEdgeTomb,
            self._editNodeEdgeTombDel,
            self._editMetaSet,
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
            self._calcNodeTomb,
            self._calcNodeTombDel,
            self._calcPropTomb,
            self._calcPropTombDel,
            self._calcTagTomb,
            self._calcTagTombDel,
            self._calcTagPropTomb,
            self._calcTagPropTombDel,
            self._calcNodeDataTomb,
            self._calcNodeDataTombDel,
            self._calcNodeEdgeTomb,
            self._calcNodeEdgeTombDel,
            self._calcMetaSet,
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
        storvalu, stortype, _ = sode['props'][prop]

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
            self.layrslab._put(abrv + indx, nid, db=self.indxdb)
            self.indxcounts.inc(abrv)

    def _testAddPropArrayIndx(self, nid, form, prop, valu):
        modlprop = self.core.model.prop(f'{form}:{prop}')
        abrv = self.core.setIndxAbrv(INDX_ARRAY, form, prop)
        for indx in self.getStorIndx(modlprop.type.stortype, valu):
            self.layrslab._put(abrv + indx, nid, db=self.indxdb)
            self.indxcounts.inc(abrv)

    def _testAddTagIndx(self, nid, form, tag):
        tagabrv = self.core.setIndxAbrv(INDX_TAG, None, tag)
        tagformabrv = self.core.setIndxAbrv(INDX_TAG, form, tag)
        self.layrslab._put(tagabrv, nid, db=self.indxdb)
        self.layrslab._put(tagformabrv, nid, db=self.indxdb)
        self.indxcounts.inc(tagabrv)
        self.indxcounts.inc(tagformabrv)

    def _testAddTagPropIndx(self, nid, form, tag, prop, valu):
        tpabrv = self.core.setIndxAbrv(INDX_TAGPROP, None, tag, prop)
        ftpabrv = self.core.setIndxAbrv(INDX_TAGPROP, form, tag, prop)

        tagprop = self.core.model.tagprop(prop)
        for indx in self.stortypes[tagprop.type.stortype].indx(valu):
            self.layrslab._put(tpabrv + indx, nid, db=self.indxdb)
            self.layrslab._put(ftpabrv + indx, nid, db=self.indxdb)
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
                sode['tags'][tag] = (None, None, None)
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

            propvalu, stortype, _ = valu
            if stortype & STOR_FLAG_ARRAY:
                stortype = STOR_TYPE_ARRAY

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

            propvalu, stortype, _ = valu

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
                stortype = STOR_TYPE_ARRAY

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
            for propname, (storvalu, stortype, _) in storprops.items():

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
        ret = deepcopy(self.layrinfo)
        ret['offset'] = await self.getEditIndx()
        ret['totalsize'] = await self.getLayerSize()
        return ret

    async def iterWipeNodeEdits(self):

        await self._saveDirtySodes()

        async for nid, sode in self.getStorNodes():

            edits = []
            async for abrv, n2nid, tomb in self.iterNodeEdgesN1(nid):
                verb = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    edits.append((EDIT_EDGE_TOMB_DEL, (verb, s_common.int64un(n2nid))))
                else:
                    edits.append((EDIT_EDGE_DEL, (verb, s_common.int64un(n2nid))))

            async for abrv, valu, tomb in self.iterNodeData(nid):
                prop = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    edits.append((EDIT_NODEDATA_TOMB_DEL, (prop,)))
                else:
                    edits.append((EDIT_NODEDATA_DEL, (prop,)))

            for tag, propdict in sode.get('tagprops', {}).items():
                for prop, (valu, stortype) in propdict.items():
                    edits.append((EDIT_TAGPROP_DEL, (tag, prop)))

            for tag, propdict in sode.get('antitagprops', {}).items():
                for prop  in propdict.keys():
                    edits.append((EDIT_TAGPROP_TOMB_DEL, (tag, prop)))

            for tag, tagv in sode.get('tags', {}).items():
                edits.append((EDIT_TAG_DEL, (tag,)))

            for tag in sode.get('antitags', {}).keys():
                edits.append((EDIT_TAG_TOMB_DEL, (tag,)))

            for prop, (valu, stortype, virts) in sode.get('props', {}).items():
                edits.append((EDIT_PROP_DEL, (prop,)))

            for prop in sode.get('antiprops', {}).keys():
                edits.append((EDIT_PROP_TOMB_DEL, (prop,)))

            valu = sode.get('valu')
            if valu is not None:
                edits.append((EDIT_NODE_DEL, ()))
            elif sode.get('antivalu') is not None:
                edits.append((EDIT_NODE_TOMB_DEL, ()))

            if (form := sode.get('form')) is None:
                ndef = self.core.getNidNdef(nid)
                form = ndef[0]

            yield (s_common.int64un(nid), form, edits)

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

    async def _initSlabs(self, slabopts):

        otherslabopts = {
            **slabopts,
            'readahead': False,   # less-used slabs don't need readahead
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

        self.bynid = self.layrslab.initdb('bynid')

        self.indxdb = self.layrslab.initdb('indx', dupsort=True, dupfixed=True)

        self.ndefabrv = self.core.setIndxAbrv(INDX_NDEF)
        self.nodepropabrv = self.core.setIndxAbrv(INDX_NODEPROP)

        self.edgen1abrv = self.core.setIndxAbrv(INDX_EDGE_N1)
        self.edgen2abrv = self.core.setIndxAbrv(INDX_EDGE_N2)
        self.edgen1n2abrv = self.core.setIndxAbrv(INDX_EDGE_N1N2)

        self.indxcounts = await self.layrslab.getLruHotCount('indxcounts')

        self.nodedata = self.dataslab.initdb('nodedata')
        self.dataname = self.dataslab.initdb('dataname', dupsort=True, dupfixed=True)

        self.nodeeditlog = self.nodeeditctor(self.nodeeditslab, 'nodeedits')

    async def _initLayerStorage(self):

        slabopts = {
            'readahead': s_common.envbool('SYNDEV_CORTEX_LAYER_READAHEAD', 'true'),
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

        self.layrvers = self.meta.get('version', 11)
        if self.layrvers != 11:
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

        self.layrslab._putmulti(kvlist, db=self.bynid)
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

    def getPropCount(self, formname, propname=None):
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
            stortype = STOR_TYPE_ARRAY

        count = 0
        for indx in self.getStorIndx(stortype, valu):
            count += self.layrslab.count(abrv + indx, db=self.indxdb)

        return count

    def getPropArrayCount(self, formname, propname=None):
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

    def getEdgeVerbCount(self, verb, n1form=None, n2form=None):
        '''
        Return the number of edges in the layer with a specific verb and optional
        N1 form and/or N2 form.
        '''
        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)

            if n1form is not None:
                n1abrv = self.core.getIndxAbrv(INDX_FORM, n1form)

            if n2form is not None:
                n2abrv = self.core.getIndxAbrv(INDX_FORM, n2form)

        except s_exc.NoSuchAbrv:
            return 0

        if n1form is None:
            if n2form is None:
                return self.indxcounts.get(vabrv, 0)
            else:
                return self.indxcounts.get(INDX_EDGE_N2 + n2abrv + vabrv, 0)
        else:
            return self.indxcounts.get(INDX_EDGE_N1 + n1abrv + vabrv, 0)

        return self.indxcounts.get(INDX_EDGE_N1N2 + n1abrv + vabrv + n2abrv, 0)

    async def iterPropValues(self, formname, propname, stortype):
        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, formname, propname)
        except s_exc.NoSuchAbrv:
            return

        if stortype & 0x8000:
            stortype = STOR_TYPE_ARRAY

        stor = self.stortypes[stortype]
        abrvlen = len(abrv)

        async for lkey in s_coro.pause(self.layrslab.scanKeysByPref(abrv, db=self.indxdb, nodup=True)):

            indx = lkey[abrvlen:]
            valu = stor.decodeIndx(indx)
            if valu is not s_common.novalu:
                yield indx, valu
                continue

            nid = self.layrslab.get(lkey, db=self.indxdb)
            if nid is not None:
                sode = self._getStorNode(nid)
                if sode is not None:
                    if propname is None:
                        valt = sode.get('valu')
                    else:
                        valt = sode['props'].get(propname)

                    if valt is not None:
                        yield indx, valt[0]

    async def iterPropValuesWithCmpr(self, form, prop, cmprvals, array=False):

        try:
            if array:
                indxby = IndxByPropArrayKeys(self, form, prop)
            else:
                indxby = IndxByPropKeys(self, form, prop)
        except s_exc.NoSuchAbrv:
            return

        abrvlen = indxby.abrvlen

        for cmpr, valu, kind in cmprvals:

            styp = self.stortypes[kind]

            if (func := styp.lifters.get(cmpr)) is None:
                raise s_exc.NoSuchCmpr(cmpr=cmpr)

            async for lkey, _ in func(indxby, valu):

                indx = lkey[abrvlen:]
                pval = styp.decodeIndx(indx)
                if pval is not s_common.novalu:
                    yield indx, pval
                    continue

                nid = self.layrslab.get(lkey, db=self.indxdb)
                if nid is None or (sode := self._getStorNode(nid)) is None:  # pragma: no cover
                    continue

                if prop is None:
                    valt = sode.get('valu')
                else:
                    valt = sode['props'].get(prop)

                if valt is not None:
                    if array:
                        for aval in valt[0]:
                            if styp.indx(aval)[0] == indx:
                                yield indx, aval
                                break
                    else:
                        yield indx, valt[0]

    async def iterPropIndxNids(self, formname, propname, indx, array=False):

        ityp = INDX_PROP
        if array:
            ityp = INDX_ARRAY

        try:
            abrv = self.core.getIndxAbrv(ityp, formname, propname)
        except s_exc.NoSuchAbrv:
            return

        async for _, nid in s_coro.pause(self.layrslab.scanByDups(abrv + indx, db=self.indxdb)):
            yield nid

    async def liftByTag(self, tag, form=None, reverse=False, indx=None):

        if indx is not None:
            try:
                abrv = self.core.getIndxAbrv(indx, form, tag)
            except s_exc.NoSuchAbrv:
                return

            if reverse:
                scan = self.layrslab.scanByRangeBack
                pkeymin = self.ivaltimetype.fullbyts * 2
                pkeymax = self.ivaltimetype.zerobyts
            else:
                scan = self.layrslab.scanByRange
                pkeymin = self.ivaltimetype.zerobyts
                pkeymax = self.ivaltimetype.fullbyts * 2

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

    async def liftByTags(self, tags):
        # todo: support form and reverse kwargs

        async with await s_spooled.Set.anit(dirn=self.core.dirn) as nidset:
            for tag in tags:
                try:
                    abrv = self.core.getIndxAbrv(INDX_TAG, None, tag)
                except s_exc.NoSuchAbrv:
                    continue

                for lkey, nid in self.layrslab.scanByPref(abrv, db=self.indxdb):
                    if nid in nidset:
                        await asyncio.sleep(0)
                        continue

                    await nidset.add(nid)
                    yield nid, self.genStorNodeRef(nid)

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
            abrv = self.core.getIndxAbrv(INDX_NODEDATA, name)
        except s_exc.NoSuchAbrv:
            return

        if self.dataslab.hasdup(abrv + FLAG_NORM, nid, db=self.dataname):
            return True

        if self.dataslab.hasdup(abrv + FLAG_TOMB, nid, db=self.dataname):
            return False

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

    async def liftByMeta(self, name, reverse=False):

        abrv = self.core.getIndxAbrv(INDX_VIRTUAL, None, None, name)

        if reverse:
            scan = self.layrslab.scanByPrefBack
        else:
            scan = self.layrslab.scanByPref

        for lval, nid in scan(abrv, db=self.indxdb):
            sref = self.genStorNodeRef(nid)
            yield lval, nid, sref

    async def liftByMetaValu(self, name, cmprvals, reverse=False):
        for cmpr, valu, kind in cmprvals:
            async for indx, nid in self.stortypes[kind].indxByProp(None, None, cmpr, valu, reverse=reverse, virts=(name,)):
                yield indx, nid, self.genStorNodeRef(nid)

    async def liftByProp(self, form, prop, reverse=False, indx=None):

        if indx is None:
            indx = INDX_PROP

        try:
            if indx is None:
                abrv = self.core.getIndxAbrv(INDX_PROP, form, prop)
            elif isinstance(indx, bytes):
                abrv = self.core.getIndxAbrv(indx, form, prop)
            else:
                abrv = self.core.getIndxAbrv(INDX_VIRTUAL, form, prop, indx)

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
    async def liftByFormValu(self, form, cmprvals, reverse=False, virts=None):
        for cmpr, valu, kind in cmprvals:

            if kind & 0x8000:
                kind = STOR_TYPE_ARRAY

            async for indx, nid in self.stortypes[kind].indxByForm(form, cmpr, valu, reverse=reverse, virts=virts):
                yield indx, nid, self.genStorNodeRef(nid)

    async def liftByPropValu(self, form, prop, cmprvals, reverse=False, virts=None):
        for cmpr, valu, kind in cmprvals:

            if kind & 0x8000:
                kind = STOR_TYPE_ARRAY

            async for indx, nid in self.stortypes[kind].indxByProp(form, prop, cmpr, valu, reverse=reverse, virts=virts):
                yield indx, nid, self.genStorNodeRef(nid)

    async def liftByPropArray(self, form, prop, cmprvals, reverse=False, virts=None):
        for cmpr, valu, kind in cmprvals:
            async for indx, nid in self.stortypes[kind].indxByPropArray(form, prop, cmpr, valu, reverse=reverse, virts=virts):
                yield indx, nid, self.genStorNodeRef(nid)

    async def liftByDataName(self, name):
        try:
            abrv = self.core.getIndxAbrv(INDX_NODEDATA, name)

        except s_exc.NoSuchAbrv:
            return

        genrs = [
            s_coro.agen(self.dataslab.scanByDups(abrv + FLAG_TOMB, db=self.dataname)),
            s_coro.agen(self.dataslab.scanByDups(abrv + FLAG_NORM, db=self.dataname))
        ]

        async for lkey, nid in s_common.merggenr2(genrs, cmprkey=lambda x: x[1]):
            await asyncio.sleep(0)

            yield nid, self.genStorNodeRef(nid), lkey[-1:] == FLAG_TOMB

    async def setStorNodeProp(self, nid, prop, valu, meta):
        newp = self.core.model.reqProp(prop)

        newp_valu, info = await newp.type.norm(valu)
        newp_name = newp.name
        newp_stortype = newp.type.stortype
        newp_formname = newp.form.name

        set_edit = (EDIT_PROP_SET, (newp_name, newp_valu, newp_stortype, info.get('virts')))
        nodeedits = [(s_common.int64un(nid), newp_formname, [set_edit])]

        _, changes = await self.saveNodeEdits(nodeedits, meta)
        return bool(changes)

    async def delStorNode(self, nid, meta):
        '''
        Delete all node information in this layer.

        Deletes props, tagprops, tags, n1edges, n2edges, nodedata, tombstones, and node valu.
        '''
        if (sode := self._getStorNode(nid)) is None:
            return False

        formname = sode.get('form')

        edits = []
        nodeedits = []
        intnid = s_common.int64un(nid)

        for propname in sode.get('props', {}).keys():
            edits.append((EDIT_PROP_DEL, (propname,)))

        for propname in sode.get('antiprops', {}).keys():
            edits.append((EDIT_PROP_TOMB_DEL, (propname,)))

        for tagname, tprops in sode.get('tagprops', {}).items():
            for propname, propvalu in tprops.items():
                edits.append((EDIT_TAGPROP_DEL, (tagname, propname)))

        for tagname, tprops in sode.get('antitagprops', {}).items():
            for propname in tprops.keys():
                edits.append((EDIT_TAGPROP_TOMB_DEL, (tagname, propname)))

        for tagname in sode.get('tags', {}).keys():
            edits.append((EDIT_TAG_DEL, (tagname,)))

        for tagname in sode.get('antitags', {}).keys():
            edits.append((EDIT_TAG_TOMB_DEL, (tagname,)))

        # EDIT_NODE_DEL will delete all nodedata and n1 edges if there is a valu in the sode
        if (valu := sode.get('valu')):
            edits.append((EDIT_NODE_DEL,))
        else:
            if (valu := sode.get('antivalu')):
                edits.append((EDIT_NODE_TOMB_DEL,))

            async for abrv, tomb in self.iterNodeDataKeys(nid):
                name = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    edits.append((EDIT_NODEDATA_TOMB_DEL, (name,)))
                else:
                    edits.append((EDIT_NODEDATA_DEL, (name,)))
                await asyncio.sleep(0)

            async for abrv, n2nid, tomb in self.iterNodeEdgesN1(nid):
                verb = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    edits.append((EDIT_EDGE_TOMB_DEL, (verb, s_common.int64un(n2nid))))
                else:
                    edits.append((EDIT_EDGE_DEL, (verb, s_common.int64un(n2nid))))
                await asyncio.sleep(0)

        nodeedits.append((intnid, formname, edits))

        n2edges = {}
        async for abrv, n2nid, tomb in self.iterNodeEdgesN2(nid):
            n2edges.setdefault(n2nid, []).append((abrv, tomb))
            await asyncio.sleep(0)

        @s_cache.memoize()
        def getN2Form(n2nid):
            return self.core.getNidNdef(n2nid)[0]

        changed = False

        async def batchEdits(size=1000):
            if len(nodeedits) < size:
                return changed

            _, changes = await self.saveNodeEdits(nodeedits, meta)

            nodeedits.clear()

            if changed: # pragma: no cover
                return changed

            return bool(changes)

        for n2nid, edges in n2edges.items():
            edits = []
            for (abrv, tomb) in edges:
                verb = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    edits.append((EDIT_EDGE_TOMB_DEL, (verb, intnid)))
                else:
                    edits.append((EDIT_EDGE_DEL, (verb, intnid)))

            nodeedits.append((s_common.int64un(n2nid), getN2Form(n2nid), edits))

            changed = await batchEdits()

        return await batchEdits(size=1)

    async def delStorNodeProp(self, nid, prop, meta):
        pprop = self.core.model.reqProp(prop)

        oldp_name = pprop.name
        oldp_formname = pprop.form.name
        oldp_stortype = pprop.type.stortype

        del_edit = (EDIT_PROP_DEL, (oldp_name,))
        nodeedits = [(s_common.int64un(nid), oldp_formname, [del_edit])]

        _, changes = await self.saveNodeEdits(nodeedits, meta)
        return bool(changes)

    async def delNodeData(self, nid, meta, name=None):
        '''
        Delete nodedata from a node in this layer. If name is not specified, delete all nodedata.
        '''
        if (sode := self._getStorNode(nid)) is None:
            return False

        edits = []
        if name is None:
            async for abrv, tomb in self.iterNodeDataKeys(nid):
                name = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    edits.append((EDIT_NODEDATA_TOMB_DEL, (name,)))
                else:
                    edits.append((EDIT_NODEDATA_DEL, (name,)))
                await asyncio.sleep(0)

        elif (data := await self.hasNodeData(nid, name)) is not None:
            if data:
                edits.append((EDIT_NODEDATA_DEL, (name,)))
            else:
                edits.append((EDIT_NODEDATA_TOMB_DEL, (name,)))

        if not edits:
            return False

        nodeedits = [(s_common.int64un(nid), sode.get('form'), edits)]

        _, changes = await self.saveNodeEdits(nodeedits, meta)

        return bool(changes)

    async def delEdge(self, n1nid, verb, n2nid, meta):
        if (sode := self._getStorNode(n1nid)) is None:
            return False

        if (edge := await self.hasNodeEdge(n1nid, verb, n2nid)) is None:
            return False

        if edge:
            edits = [(EDIT_EDGE_DEL, (verb, s_common.int64un(n2nid)))]
        else:
            edits = [(EDIT_EDGE_TOMB_DEL, (verb, s_common.int64un(n2nid)))]

        nodeedits = [(s_common.int64un(n1nid), sode.get('form'), edits)]

        _, changes = await self.saveNodeEdits(nodeedits, meta)
        return bool(changes)

    async def saveNodeEdits(self, edits, meta):
        '''
        Save node edits to the layer and return a tuple of (nexsoffs, changes).

        Note: nexsoffs will be None if there are no changes.
        '''
        self._reqNotReadOnly()

        if self.isdeleted:
            mesg = f'Layer {self.iden} has been deleted!'
            raise s_exc.NoSuchLayer(mesg=mesg)

        if not self.core.isactive:
            proxy = await self.core.nexsroot.getIssueProxy()
            indx, changes = await proxy.saveLayerNodeEdits(self.iden, edits, meta)
            if indx is not None:
                await self.core.nexsroot.waitOffs(indx)
            return indx, changes

        async with self.core.nexsroot.cell.nexslock:
            if self.isdeleted:
                mesg = f'Layer {self.iden} has been deleted!'
                raise s_exc.NoSuchLayer(mesg=mesg)

            if (realedits := await self.calcEdits(edits, meta)):
                return await self.saveToNexs('edits', realedits, meta)
            return None, ()

    async def calcEdits(self, nodeedits, meta):

        if meta.get('time') is None:
            meta['time'] = s_common.now()

        realedits = []
        for (nid, form, edits) in nodeedits:

            if nid is None:
                if edits[0][0] != 0:
                    continue

                # Generate NID without a nexus event, mirrors will populate
                # the mapping from the node add edit
                nid = await self.core._genNdefNid((form, edits[0][1][0]))
            else:
                nid = s_common.int64en(nid)

            sode = self._getStorNode(nid)
            changes = []
            for edit in edits:

                delt = await self.resolvers[edit[0]](nid, edit, sode)
                if delt is not None:
                    changes.append(delt)

                await asyncio.sleep(0)

            if changes:
                realedits.append((s_common.int64un(nid), form, changes))

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

        utime = meta['time']
        ubyts = self.timetype.getIntIndx(utime)

        for (nid, form, edits) in nodeedits:

            nid = s_common.int64en(nid)
            sode = self._genStorNode(nid)

            for edit in edits:
                kvpairs.extend(await self.editors[edit[0]](nid, form, edit, sode, meta))

                if len(kvpairs) > 20:
                    await self.layrslab.putmulti(kvpairs, db=self.indxdb)
                    kvpairs.clear()
                    await asyncio.sleep(0)

            if nid in self.dirty:
                metaabrv = self.core.setIndxAbrv(INDX_VIRTUAL, form, None, 'updated')

                if (last := sode['meta'].get('updated')) is not None:
                    oldbyts = self.timetype.getIntIndx(last[0])
                    self.layrslab.delete(metaabrv + oldbyts, nid, db=self.indxdb)
                    self.layrslab.delete(self.updatedabrv + oldbyts, nid, db=self.indxdb)

                kvpairs.append((metaabrv + ubyts, nid))
                kvpairs.append((self.updatedabrv + ubyts, nid))

                sode['meta']['updated'] = (utime, STOR_TYPE_TIME)

        if kvpairs:
            await self.layrslab.putmulti(kvpairs, db=self.indxdb)

        if self.logedits and nexsitem is not None:
            nexsindx = nexsitem[0]
            if nexsindx >= self.nodeeditlog.index():
                offs = self.nodeeditlog.add(None, indx=nexsindx)
                [(await wind.put((offs, nodeedits, meta))) for wind in tuple(self.windows)]

        await asyncio.sleep(0)
        return nodeedits

    def mayDelNid(self, nid, sode):
        if sode.get('valu') or sode.get('antivalu'):
            return False

        if sode.get('props') or sode.get('antiprops'):
            return False

        if sode.get('tags') or sode.get('antitags'):
            return False

        if sode.get('tagprops') or sode.get('antitagprops'):
            return False

        if sode.get('n1verbs') or sode.get('n1antiverbs'):
            return False

        if sode.get('n2verbs') or sode.get('n2antiverbs'):
            return False

        if self.dataslab.prefexists(nid, self.nodedata):
            return False

        # no more refs in this layer.  time to pop it...
        form = sode.get('form')
        try:
            abrv = self.core.getIndxAbrv(INDX_FORM, form)
            self.layrslab.delete(abrv, val=nid, db=self.indxdb)
        except s_exc.NoSuchAbrv:
            pass

        if (last := sode['meta'].get('updated')) is not None:
            ubyts = self.timetype.getIntIndx(last[0])

            metaabrv = self.core.getIndxAbrv(INDX_VIRTUAL, form, None, 'updated')
            self.layrslab.delete(metaabrv + ubyts, nid, db=self.indxdb)
            self.layrslab.delete(self.updatedabrv + ubyts, nid, db=self.indxdb)

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

    async def _calcNodeAdd(self, nid, edit, sode):

        if sode is not None and sode.get('valu') is not None:
            return

        return edit

    async def _calcNodeDel(self, nid, edit, sode):

        if sode is None or (oldv := sode.get('valu')) is None:
            return

        return edit

    async def _calcNodeTomb(self, nid, edit, sode):

        if sode is not None and sode.get('antivalu') is not None:
            return

        return edit

    async def _calcNodeTombDel(self, nid, edit, sode):

        if sode is None or sode.get('antivalu') is None:
            return

        return edit

    async def _calcMetaSet(self, nid, edit, sode):

        name, valu, stortype = edit[1]

        if sode is not None and (meta := sode.get('meta')) is not None:

            oldv, oldt = meta.get(name, (None, None))

            if valu == oldv:
                return

            if oldv is not None:
                if stortype == STOR_TYPE_MINTIME:
                    if valu >= oldv:
                        return

        return edit

    async def _calcPropSet(self, nid, edit, sode):

        prop, valu, stortype, virts = edit[1]

        if sode is not None and (props := sode.get('props')) is not None:

            oldv, _, oldvirts = props.get(prop, (None, None, None))

            if valu == oldv and virts == oldvirts:
                return

        return edit

    async def _calcPropDel(self, nid, edit, sode):

        if sode is None or (props := sode.get('props')) is None:
            return

        if (valt := props.get(edit[1][0])) is None:
            return

        return edit

    async def _calcPropTomb(self, nid, edit, sode):

        if sode is not None:
            antiprops = sode.get('antiprops')
            if antiprops is not None and antiprops.get(edit[1][0]) is not None:
                return

        return edit

    async def _calcPropTombDel(self, nid, edit, sode):

        if sode is None:
            return
        else:
            antiprops = sode.get('antiprops')
            if antiprops is None or antiprops.get(edit[1][0]) is None:
                return

        return edit

    async def _calcTagSet(self, nid, edit, sode):

        if sode is not None and (tags := sode.get('tags')) is not None:
            tag, valu = edit[1]
            if (oldv := tags.get(tag)) is not None and oldv == valu:
                return

        return edit

    async def _calcTagDel(self, nid, edit, sode):

        if sode is None or (tags := sode.get('tags')) is None:
            return

        if tags.get(edit[1][0]) is None:
            return

        return edit

    async def _calcTagTomb(self, nid, edit, sode):

        if sode is not None:
            antitags = sode.get('antitags')
            if antitags is not None and antitags.get(edit[1][0]) is not None:
                return

        return edit

    async def _calcTagTombDel(self, nid, edit, sode):

        if sode is None:
            return
        else:
            antitags = sode.get('antitags')
            if antitags is None or antitags.get(edit[1][0]) is None:
                return

        return edit

    async def _calcTagPropSet(self, nid, edit, sode):

        if sode is not None and (tagprops := sode.get('tagprops')) is not None:
            tag, prop, valu, stortype = edit[1]
            if (tp_dict := tagprops.get(tag)) is not None:
                if tp_dict.get(prop) == (valu, stortype):
                    return

        return edit

    async def _calcTagPropDel(self, nid, edit, sode):

        if sode is None or (tagprops := sode.get('tagprops')) is None:
            return

        tag, prop = edit[1]

        if (tp_dict := tagprops.get(tag)) is None:
            return

        if (oldv := tp_dict.get(prop)) is None:
            return

        return edit

    async def _calcTagPropTomb(self, nid, edit, sode):

        if sode is not None:
            if (antitags := sode.get('antitagprops')) is not None:
                tag, prop = edit[1]
                if (antiprops := antitags.get(tag)) is not None and prop in antiprops:
                    return

        return edit

    async def _calcTagPropTombDel(self, nid, edit, sode):

        if sode is None:
            return
        else:
            if (antitags := sode.get('antitagprops')) is None:
                return

            tag, prop = edit[1]
            if (antiprops := antitags.get(tag)) is None or prop not in antiprops:
                return

        return edit

    async def _calcNodeDataSet(self, nid, edit, sode):

        if sode is None:
            return edit

        name, valu = edit[1]
        try:
            abrv = self.core.getIndxAbrv(INDX_NODEDATA, name)
        except s_exc.NoSuchAbrv:
            return edit

        byts = s_msgpack.en(valu)

        if (oldb := self.dataslab.get(nid + abrv + FLAG_NORM, db=self.nodedata)) is not None:
            if oldb == byts:
                return

        return edit

    async def _calcNodeDataDel(self, nid, edit, sode):

        if sode is None:
            return

        name = edit[1][0]
        try:
            abrv = self.core.getIndxAbrv(INDX_NODEDATA, name)
        except s_exc.NoSuchAbrv:
            return

        if not self.dataslab.has(nid + abrv + FLAG_NORM, db=self.nodedata):
            return

        return edit

    async def _calcNodeDataTomb(self, nid, edit, sode):

        name = edit[1][0]

        try:
            abrv = self.core.getIndxAbrv(INDX_NODEDATA, name)
        except s_exc.NoSuchAbrv:
            return

        if self.dataslab.has(nid + abrv + FLAG_TOMB, db=self.nodedata):
            return

        return edit

    async def _calcNodeDataTombDel(self, nid, edit, sode):

        name = edit[1][0]

        try:
            abrv = self.core.getIndxAbrv(INDX_NODEDATA, name)
        except s_exc.NoSuchAbrv:
            return

        if not self.dataslab.has(nid + abrv + FLAG_TOMB, db=self.nodedata):
            return

        return edit

    async def _calcNodeEdgeAdd(self, nid, edit, sode):

        verb, n2nid = edit[1]

        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return edit

        if sode is not None and self.layrslab.hasdup(self.edgen1n2abrv + nid + s_common.int64en(n2nid) + FLAG_NORM, vabrv, db=self.indxdb):
            return

        return edit

    async def _calcNodeEdgeDel(self, nid, edit, sode):

        if sode is None:
            return

        verb, n2nid = edit[1]

        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return

        if not self.layrslab.hasdup(self.edgen1n2abrv + nid + s_common.int64en(n2nid) + FLAG_NORM, vabrv, db=self.indxdb):
            return

        return edit

    async def _calcNodeEdgeTomb(self, nid, edit, sode):

        verb, n2nid = edit[1]

        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return

        if sode is not None and self.layrslab.hasdup(self.edgen1n2abrv + nid + s_common.int64en(n2nid) + FLAG_TOMB, vabrv, db=self.indxdb):
            return

        return edit

    async def _calcNodeEdgeTombDel(self, nid, edit, sode):

        verb, n2nid = edit[1]

        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return

        if sode is None or not self.layrslab.hasdup(self.edgen1n2abrv + nid + s_common.int64en(n2nid) + FLAG_TOMB, vabrv, db=self.indxdb):
            return

        return edit

    async def _editNodeAdd(self, nid, form, edit, sode, meta):

        if sode.get('valu') is not None:
            return ()

        valu, stortype, virts = sode['valu'] = edit[1]

        if not self.core.hasNidNdef(nid):
            self.core.setNidNdef(nid, (form, valu))

        self.dirty[nid] = sode

        kvpairs = []

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        ctime = meta['time']
        sode['meta']['created'] = (ctime, STOR_TYPE_MINTIME)
        cbyts = self.timetype.getIntIndx(ctime)

        metaabrv = self.core.setIndxAbrv(INDX_VIRTUAL, form, None, 'created')
        kvpairs.append((metaabrv + cbyts, nid))
        kvpairs.append((self.createdabrv + cbyts, nid))

        abrv = self.core.setIndxAbrv(INDX_PROP, form, None)

        if stortype & STOR_FLAG_ARRAY:

            arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, None)

            for indx in self.getStorIndx(stortype, valu):
                kvpairs.append((arryabrv + indx, nid))
                self.indxcounts.inc(arryabrv)
                await asyncio.sleep(0)

            for indx in self.getStorIndx(STOR_TYPE_ARRAY, valu):
                kvpairs.append((abrv + indx, nid))
                self.indxcounts.inc(abrv)

        else:

            for indx in self.getStorIndx(stortype, valu):
                kvpairs.append((abrv + indx, nid))
                self.indxcounts.inc(abrv)

            if stortype == STOR_TYPE_IVAL:
                dura = self.ivaltype.getDurationIndx(valu)
                duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, None)
                kvpairs.append((duraabrv + dura, nid))

                maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, None)
                kvpairs.append((maxabrv + indx[8:], nid))

        if virts is not None:
            if stortype & 0x8000:
                stortype = stortype & 0x7fff
            kvpairs.extend(self.stortypes[stortype].getVirtIndxVals(nid, form, None, virts))

        if sode.pop('antivalu', None) is not None:
            self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        if self.nodeAddHook is not None:
            self.nodeAddHook()

        return kvpairs

    async def _editMetaSet(self, nid, form, edit, sode, meta):

        name, valu, stortype = edit[1]

        oldv, oldt = sode['meta'].get(name, (None, None))

        if valu == oldv:
            return ()

        kvpairs = []

        metaabrv = self.core.setIndxAbrv(INDX_VIRTUAL, form, None, name)
        univabrv = self.core.setIndxAbrv(INDX_VIRTUAL, None, None, name)

        if oldv is not None:
            for oldi in self.getStorIndx(oldt, oldv):
                self.layrslab.delete(metaabrv + oldi, nid, db=self.indxdb)
                self.layrslab.delete(univabrv + oldi, nid, db=self.indxdb)

        sode['meta'][name] = (valu, stortype)
        self.dirty[nid] = sode

        for indx in self.getStorIndx(stortype, valu):
            kvpairs.append((metaabrv + indx, nid))
            kvpairs.append((univabrv + indx, nid))

        return kvpairs

    async def _editNodeDel(self, nid, form, edit, sode, meta):

        if (valt := sode.pop('valu', None)) is None:
            self.mayDelNid(nid, sode)
            return ()

        (valu, stortype, virts) = valt

        ctime = sode['meta']['created'][0]
        cbyts = self.timetype.getIntIndx(ctime)

        metaabrv = self.core.setIndxAbrv(INDX_VIRTUAL, form, None, 'created')
        self.layrslab.delete(metaabrv + cbyts, nid, db=self.indxdb)
        self.layrslab.delete(self.createdabrv + cbyts, nid, db=self.indxdb)

        abrv = self.core.setIndxAbrv(INDX_PROP, form, None)

        if stortype & STOR_FLAG_ARRAY:

            arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, None)

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(arryabrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(arryabrv, -1)
                await asyncio.sleep(0)

            for indx in self.getStorIndx(STOR_TYPE_ARRAY, valu):
                self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(abrv, -1)

        else:

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(abrv, -1)

            if stortype == STOR_TYPE_IVAL:
                dura = self.ivaltype.getDurationIndx(valu)
                duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, None)
                self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)

                indx = indx[8:]
                maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, None)
                self.layrslab.delete(maxabrv + indx, nid, db=self.indxdb)

        if virts is not None:
            if stortype & 0x8000:
                stortype = stortype & 0x7fff
            self.stortypes[stortype].delVirtIndxVals(nid, form, None, virts)

        if self.nodeDelHook is not None:
            self.nodeDelHook()

        await self._wipeNodeData(nid, sode)
        await self._delNodeEdges(nid, form, sode)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editNodeTomb(self, nid, form, edit, sode, meta):

        if sode.get('antivalu') is not None:
            return ()

        abrv = self.core.setIndxAbrv(INDX_PROP, form, None)

        sode['antivalu'] = True

        kvpairs = [(INDX_TOMB + abrv, nid)]

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        self.dirty[nid] = sode

        await self._wipeNodeData(nid, sode)
        await self._delNodeEdges(nid, form, sode)

        return kvpairs

    async def _editNodeTombDel(self, nid, form, edit, sode, meta):

        if sode.pop('antivalu', None) is None:
            self.mayDelNid(nid, sode)
            return ()

        abrv = self.core.setIndxAbrv(INDX_PROP, form, None)

        self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editPropSet(self, nid, form, edit, sode, meta):

        prop, valu, stortype, virts = edit[1]

        oldv, oldt, oldvirts = sode['props'].get(prop, (None, None, None))

        if valu == oldv:
            if virts != oldvirts:
                sode['props'][prop] = (valu, stortype, virts)
                self.dirty[nid] = sode
            return ()

        abrv = self.core.setIndxAbrv(INDX_PROP, form, prop)

        if oldv is not None:

            if oldt & STOR_FLAG_ARRAY:

                realtype = oldt & 0x7fff

                arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, prop)
                self.indxcounts.inc(arryabrv, len(oldv) * -1)

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(arryabrv + oldi, nid, db=self.indxdb)

                    if realtype == STOR_TYPE_NDEF:
                        self.layrslab.delete(self.ndefabrv + oldi[8:] + abrv, nid, db=self.indxdb)

                    elif realtype == STOR_TYPE_NODEPROP:
                        self.layrslab.delete(self.nodepropabrv + oldi[8:] + abrv, nid, db=self.indxdb)

                    await asyncio.sleep(0)

                for indx in self.getStorIndx(STOR_TYPE_ARRAY, oldv):
                    self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                    self.indxcounts.inc(abrv, -1)

            else:

                realtype = oldt

                for oldi in self.getStorIndx(oldt, oldv):
                    self.layrslab.delete(abrv + oldi, nid, db=self.indxdb)
                    self.indxcounts.inc(abrv, -1)

                if oldt == STOR_TYPE_NDEF:
                    self.layrslab.delete(self.ndefabrv + oldi[8:] + abrv, nid, db=self.indxdb)

                elif oldt == STOR_TYPE_NODEPROP:
                    self.layrslab.delete(self.nodepropabrv + oldi[8:] + abrv, nid, db=self.indxdb)

                elif oldt == STOR_TYPE_IVAL:
                    dura = self.ivaltype.getDurationIndx(oldv)
                    duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, prop)
                    self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)

                    if not oldv[1] == valu[1]:
                        maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, prop)
                        self.layrslab.delete(maxabrv + oldi[8:], nid, db=self.indxdb)

            if oldvirts is not None:
                self.stortypes[realtype].delVirtIndxVals(nid, form, prop, oldvirts)

        if (antiprops := sode.get('antiprops')) is not None:
            tomb = antiprops.pop(prop, None)
            if tomb is not None:
                self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        sode['props'][prop] = (valu, stortype, virts)
        self.dirty[nid] = sode

        kvpairs = []

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        if stortype & STOR_FLAG_ARRAY:

            realtype = stortype & 0x7fff

            arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, prop)

            for indx in self.getStorIndx(stortype, valu):
                kvpairs.append((arryabrv + indx, nid))
                self.indxcounts.inc(arryabrv)

                if realtype == STOR_TYPE_NDEF:
                    kvpairs.append((self.ndefabrv + indx[8:] + abrv, nid))

                elif realtype == STOR_TYPE_NODEPROP:
                    kvpairs.append((self.nodepropabrv + indx[8:] + abrv, nid))

                await asyncio.sleep(0)

            for indx in self.getStorIndx(STOR_TYPE_ARRAY, valu):
                kvpairs.append((abrv + indx, nid))
                self.indxcounts.inc(abrv)

        else:

            for indx in self.getStorIndx(stortype, valu):
                kvpairs.append((abrv + indx, nid))
                self.indxcounts.inc(abrv)

            if stortype == STOR_TYPE_NDEF:
                kvpairs.append((self.ndefabrv + indx[8:] + abrv, nid))

            elif stortype == STOR_TYPE_NODEPROP:
                kvpairs.append((self.nodepropabrv + indx[8:] + abrv, nid))

            elif stortype == STOR_TYPE_IVAL:
                dura = self.ivaltype.getDurationIndx(valu)
                duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, prop)
                kvpairs.append((duraabrv + dura, nid))

                if oldv is None or oldv[1] != valu[1]:
                    maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, prop)
                    kvpairs.append((maxabrv + indx[8:], nid))

        if virts is not None:
            if stortype & 0x8000:
                stortype = stortype & 0x7fff

            if (virtkeys := self.stortypes[stortype].getVirtIndxVals(nid, form, prop, virts)):
                kvpairs.extend(virtkeys)

        return kvpairs

    async def _editPropDel(self, nid, form, edit, sode, meta):

        prop = edit[1][0]

        if (valt := sode['props'].pop(prop, None)) is None:
            self.mayDelNid(nid, sode)
            return ()

        valu, stortype, virts = valt

        abrv = self.core.setIndxAbrv(INDX_PROP, form, prop)

        if stortype & STOR_FLAG_ARRAY:

            realtype = stortype & 0x7fff

            arryabrv = self.core.setIndxAbrv(INDX_ARRAY, form, prop)
            self.indxcounts.inc(arryabrv, len(valu) * -1)

            for aval in valu:
                for indx in self.getStorIndx(realtype, aval):
                    self.layrslab.delete(arryabrv + indx, nid, db=self.indxdb)

                    if realtype == STOR_TYPE_NDEF:
                        self.layrslab.delete(self.ndefabrv + indx[8:] + abrv, nid, db=self.indxdb)

                    elif realtype == STOR_TYPE_NODEPROP:
                        self.layrslab.delete(self.nodepropabrv + indx[8:] + abrv, nid, db=self.indxdb)

                await asyncio.sleep(0)

            for indx in self.getStorIndx(STOR_TYPE_ARRAY, valu):
                self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(abrv, -1)

        else:

            realtype = stortype

            for indx in self.getStorIndx(stortype, valu):
                self.layrslab.delete(abrv + indx, nid, db=self.indxdb)
                self.indxcounts.inc(abrv, -1)

            if stortype == STOR_TYPE_NDEF:
                self.layrslab.delete(self.ndefabrv + indx[8:] + abrv, nid, db=self.indxdb)

            elif stortype == STOR_TYPE_NODEPROP:
                self.layrslab.delete(self.nodepropabrv + indx[8:] + abrv, nid, db=self.indxdb)

            elif stortype == STOR_TYPE_IVAL:
                maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, prop)
                self.layrslab.delete(maxabrv + indx[8:], nid, db=self.indxdb)

                dura = self.ivaltype.getDurationIndx(valu)
                duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, prop)
                self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)

        if virts is not None:
            self.stortypes[realtype].delVirtIndxVals(nid, form, prop, virts)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editPropTomb(self, nid, form, edit, sode, meta):

        prop = edit[1][0]

        if (antiprops := sode.get('antiprops')) is not None and prop in antiprops:
            return ()

        abrv = self.core.setIndxAbrv(INDX_PROP, form, prop)

        kvpairs = [(INDX_TOMB + abrv, nid)]

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        sode['antiprops'][prop] = True
        self.dirty[nid] = sode

        return kvpairs

    async def _editPropTombDel(self, nid, form, edit, sode, meta):

        prop = edit[1][0]

        if (antiprops := sode.get('antiprops')) is None or antiprops.pop(prop, None) is None:
            self.mayDelNid(nid, sode)
            return ()

        abrv = self.core.setIndxAbrv(INDX_PROP, form, prop)

        self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editTagSet(self, nid, form, edit, sode, meta):

        tag, valu = edit[1]

        oldv = sode['tags'].get(tag)
        if valu == oldv:
            return ()

        abrv = self.core.setIndxAbrv(INDX_TAG, None, tag)
        formabrv = self.core.setIndxAbrv(INDX_TAG, form, tag)

        if oldv is None:
            self.indxcounts.inc(abrv)
            self.indxcounts.inc(formabrv)

        else:

            if oldv == (None, None, None):
                self.layrslab.delete(abrv, nid, db=self.indxdb)
                self.layrslab.delete(formabrv, nid, db=self.indxdb)
            else:
                dura = self.ivaltype.getDurationIndx(oldv)
                duraabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, None, tag)
                duraformabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, form, tag)

                self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
                self.layrslab.delete(duraformabrv + dura, nid, db=self.indxdb)

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

        if (antitags := sode.get('antitags')) is not None:
            tomb = antitags.pop(tag, None)
            if tomb is not None:
                self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        kvpairs = []

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        if valu == (None, None, None):
            kvpairs.append((abrv, nid))
            kvpairs.append((formabrv, nid))
        else:
            dura = self.ivaltype.getDurationIndx(valu)
            duraabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, None, tag)
            duraformabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, form, tag)

            kvpairs.append((duraabrv + dura, nid))
            kvpairs.append((duraformabrv + dura, nid))

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
            self.mayDelNid(nid, sode)
            return ()

        abrv = self.core.setIndxAbrv(INDX_TAG, None, tag)
        formabrv = self.core.setIndxAbrv(INDX_TAG, form, tag)

        self.indxcounts.inc(abrv, -1)
        self.indxcounts.inc(formabrv, -1)

        if oldv == (None, None, None):
            self.layrslab.delete(abrv, nid, db=self.indxdb)
            self.layrslab.delete(formabrv, nid, db=self.indxdb)
        else:
            dura = self.ivaltype.getDurationIndx(oldv)
            duraabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, None, tag)
            duraformabrv = self.core.setIndxAbrv(INDX_TAG_DURATION, form, tag)

            self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
            self.layrslab.delete(duraformabrv + dura, nid, db=self.indxdb)

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

    async def _editTagTomb(self, nid, form, edit, sode, meta):

        tag = edit[1][0]

        if (antitags := sode.get('antitags')) is not None and tag in antitags:
            return ()

        abrv = self.core.setIndxAbrv(INDX_TAG, None, tag)

        kvpairs = [(INDX_TOMB + abrv, nid)]

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        sode['antitags'][tag] = True
        self.dirty[nid] = sode

        return kvpairs

    async def _editTagTombDel(self, nid, form, edit, sode, meta):

        tag = edit[1][0]

        if (antitags := sode.get('antitags')) is None or antitags.pop(tag, None) is None:
            self.mayDelNid(nid, sode)
            return ()

        abrv = self.core.setIndxAbrv(INDX_TAG, None, tag)

        self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editTagPropSet(self, nid, form, edit, sode, meta):

        tag, prop, valu, stortype = edit[1]

        tp_abrv = self.core.setIndxAbrv(INDX_TAGPROP, None, tag, prop)
        ftp_abrv = self.core.setIndxAbrv(INDX_TAGPROP, form, tag, prop)

        oldv = None

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
                    dura = self.ivaltype.getDurationIndx(oldv)
                    duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, tag, prop)
                    duraformabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, tag, prop)

                    self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
                    self.layrslab.delete(duraformabrv + dura, nid, db=self.indxdb)

                    if not oldv[1] == valu[1]:
                        oldi = oldi[8:]
                        maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, tag, prop)
                        maxformabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, tag, prop)

                        self.layrslab.delete(maxabrv + oldi, nid, db=self.indxdb)
                        self.layrslab.delete(maxformabrv + oldi, nid, db=self.indxdb)

        else:
            sode['tagprops'][tag] = {}

        if (antitags := sode.get('antitagprops')) is not None:
            if (antiprops := antitags.get(tag)) is not None:
                tomb = antiprops.pop(prop, None)
                if tomb is not None:
                    self.layrslab.delete(INDX_TOMB + tp_abrv, nid, db=self.indxdb)

                    if len(antiprops) == 0:
                        antitags.pop(tag)

        sode['tagprops'][tag][prop] = (valu, stortype)
        self.dirty[nid] = sode

        kvpairs = []

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        for indx in self.getStorIndx(stortype, valu):
            kvpairs.append((tp_abrv + indx, nid))
            kvpairs.append((ftp_abrv + indx, nid))
            self.indxcounts.inc(tp_abrv)
            self.indxcounts.inc(ftp_abrv)

        if stortype == STOR_TYPE_IVAL:
            dura = self.ivaltype.getDurationIndx(valu)
            duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, tag, prop)
            duraformabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, tag, prop)
            kvpairs.append((duraabrv + dura, nid))
            kvpairs.append((duraformabrv + dura, nid))

            if oldv is None or oldv[1] != valu[1]:
                indx = indx[8:]
                maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, tag, prop)
                maxformabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, tag, prop)
                kvpairs.append((maxabrv + indx, nid))
                kvpairs.append((maxformabrv + indx, nid))

        return kvpairs

    async def _editTagPropDel(self, nid, form, edit, sode, meta):

        tag, prop = edit[1]

        if (tp_dict := sode['tagprops'].get(tag)) is None or (oldv := tp_dict.pop(prop, None)) is None:
            self.mayDelNid(nid, sode)
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
            dura = self.ivaltype.getDurationIndx(oldv)
            duraabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, None, tag, prop)
            duraformabrv = self.core.setIndxAbrv(INDX_IVAL_DURATION, form, tag, prop)
            self.layrslab.delete(duraabrv + dura, nid, db=self.indxdb)
            self.layrslab.delete(duraformabrv + dura, nid, db=self.indxdb)

            indx = oldi[8:]
            maxabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, None, tag, prop)
            maxformabrv = self.core.setIndxAbrv(INDX_IVAL_MAX, form, tag, prop)
            self.layrslab.delete(maxabrv + indx, nid, db=self.indxdb)
            self.layrslab.delete(maxformabrv + indx, nid, db=self.indxdb)

        return ()

    async def _editTagPropTomb(self, nid, form, edit, sode, meta):

        tag, prop = edit[1]

        if (antitags := sode.get('antitagprops')) is not None:
            if (antiprops := antitags.get(tag)) is not None and prop in antiprops:
                return ()

        abrv = self.core.setIndxAbrv(INDX_TAGPROP, None, tag, prop)

        kvpairs = [(INDX_TOMB + abrv, nid)]

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        if antitags is None or antiprops is None:
            sode['antitagprops'][tag] = {}

        sode['antitagprops'][tag][prop] = True
        self.dirty[nid] = sode

        return kvpairs

    async def _editTagPropTombDel(self, nid, form, edit, sode, meta):

        tag, prop = edit[1]

        if (antitags := sode.get('antitagprops')) is None:
            self.mayDelNid(nid, sode)
            return ()

        if (antiprops := antitags.get(tag)) is None or antiprops.pop(prop, None) is None:
            self.mayDelNid(nid, sode)
            return ()

        if len(antiprops) == 0:
            antitags.pop(tag)

        abrv = self.core.setIndxAbrv(INDX_TAGPROP, None, tag, prop)

        self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editNodeDataSet(self, nid, form, edit, sode, meta):

        name, valu = edit[1]
        abrv = self.core.setIndxAbrv(INDX_NODEDATA, name)

        await self.dataslab.put(nid + abrv + FLAG_NORM, s_msgpack.en(valu), db=self.nodedata)
        await self.dataslab.put(abrv + FLAG_NORM, nid, db=self.dataname)

        if self.dataslab.delete(abrv + FLAG_TOMB, nid, db=self.dataname):
            self.dataslab.delete(nid + abrv + FLAG_TOMB, db=self.nodedata)
            self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        self.dirty[nid] = sode

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            return ((formabrv, nid),)

        return ()

    async def _editNodeDataDel(self, nid, form, edit, sode, meta):

        name = edit[1][0]
        abrv = self.core.setIndxAbrv(INDX_NODEDATA, name)

        if self.dataslab.delete(nid + abrv + FLAG_NORM, db=self.nodedata):
            self.dataslab.delete(abrv + FLAG_NORM, nid, db=self.dataname)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editNodeDataTomb(self, nid, form, edit, sode, meta):

        name = edit[1][0]
        abrv = self.core.setIndxAbrv(INDX_NODEDATA, name)

        if not await self.dataslab.put(abrv + FLAG_TOMB, nid, db=self.dataname):
            return ()

        await self.dataslab.put(nid + abrv + FLAG_TOMB, s_msgpack.en(None), db=self.nodedata)
        self.dirty[nid] = sode

        kvpairs = [(INDX_TOMB + abrv, nid)]

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        return kvpairs

    async def _editNodeDataTombDel(self, nid, form, edit, sode, meta):

        name = edit[1][0]
        abrv = self.core.setIndxAbrv(INDX_NODEDATA, name)

        if not self.dataslab.delete(abrv + FLAG_TOMB, nid, db=self.dataname):
            self.mayDelNid(nid, sode)
            return ()

        self.dataslab.delete(nid + abrv + FLAG_TOMB, db=self.nodedata)
        self.layrslab.delete(INDX_TOMB + abrv, nid, db=self.indxdb)

        if not self.mayDelNid(nid, sode):
            self.dirty[nid] = sode

        return ()

    async def _editNodeEdgeAdd(self, nid, form, edit, sode, meta):

        verb, n2nid = edit[1]
        n2nid = s_common.int64en(n2nid)

        vabrv = self.core.setIndxAbrv(INDX_EDGE_VERB, verb)

        if self.layrslab.hasdup(self.edgen1n2abrv + nid + n2nid + FLAG_NORM, vabrv, db=self.indxdb):
            return ()

        n2sode = self._genStorNode(n2nid)

        if self.layrslab.delete(INDX_TOMB + vabrv + nid, n2nid, db=self.indxdb):
            self.layrslab.delete(vabrv + nid + FLAG_TOMB, n2nid, db=self.indxdb)
            self.layrslab.delete(self.edgen1abrv + nid + vabrv + FLAG_TOMB, n2nid, db=self.indxdb)
            self.layrslab.delete(self.edgen2abrv + n2nid + vabrv + FLAG_TOMB, nid, db=self.indxdb)
            self.layrslab.delete(self.edgen1n2abrv + nid + n2nid + FLAG_TOMB, vabrv, db=self.indxdb)

        self.dirty[nid] = sode
        self.dirty[n2nid] = n2sode

        kvpairs = [
            (vabrv + nid + FLAG_NORM, n2nid),
            (self.edgen1abrv + nid + vabrv + FLAG_NORM, n2nid),
            (self.edgen2abrv + n2nid + vabrv + FLAG_NORM, nid),
            (self.edgen1n2abrv + nid + n2nid + FLAG_NORM, vabrv)
        ]

        formabrv = self.core.setIndxAbrv(INDX_FORM, form)

        if sode.get('form') is None:
            sode['form'] = form
            kvpairs.append((formabrv, nid))

        self.indxcounts.inc(vabrv, 1)
        self.indxcounts.inc(INDX_EDGE_N1 + formabrv + vabrv, 1)

        if (n2form := n2sode.get('form')) is None:
            n2form = self.core.getNidNdef(n2nid)[0]
            n2sode['form'] = n2form
            n2formabrv = self.core.setIndxAbrv(INDX_FORM, n2form)
            kvpairs.append((n2formabrv, n2nid))
        else:
            n2formabrv = self.core.setIndxAbrv(INDX_FORM, n2form)

        if (n1cnts := sode['n1verbs'].get(verb)) is None:
            n1cnts = sode['n1verbs'][verb] = {}

        if (n2cnts := n2sode['n2verbs'].get(verb)) is None:
            n2cnts = n2sode['n2verbs'][verb] = {}

        n1cnts[n2form] = n1cnts.get(n2form, 0) + 1
        n2cnts[form] = n2cnts.get(form, 0) + 1

        self.indxcounts.inc(INDX_EDGE_N2 + n2formabrv + vabrv, 1)
        self.indxcounts.inc(INDX_EDGE_N1N2 + formabrv + vabrv + n2formabrv, 1)

        return kvpairs

    async def _editNodeEdgeDel(self, nid, form, edit, sode, meta):

        verb, n2nid = edit[1]
        n2nid = s_common.int64en(n2nid)

        vabrv = self.core.setIndxAbrv(INDX_EDGE_VERB, verb)

        if not self.layrslab.delete(vabrv + nid + FLAG_NORM, n2nid, db=self.indxdb):
            self.mayDelNid(nid, sode)
            return ()

        self.layrslab.delete(self.edgen1abrv + nid + vabrv + FLAG_NORM, n2nid, db=self.indxdb)
        self.layrslab.delete(self.edgen2abrv + n2nid + vabrv + FLAG_NORM, nid, db=self.indxdb)
        self.layrslab.delete(self.edgen1n2abrv + nid + n2nid + FLAG_NORM, vabrv, db=self.indxdb)

        n2sode = self._genStorNode(n2nid)
        if (n2form := n2sode.get('form')) is None:
            n2form = self.core.getNidNdef(n2nid)[0]

        n1cnts = sode['n1verbs'][verb]
        n2cnts = n2sode['n2verbs'][verb]

        newvalu = n1cnts.get(n2form, 0) - 1
        if newvalu == 0:
            n1cnts.pop(n2form)
            if not n1cnts:
                sode['n1verbs'].pop(verb)
                if not self.mayDelNid(nid, sode):
                    self.dirty[nid] = sode
        else:
            n1cnts[n2form] = newvalu
            self.dirty[nid] = sode

        newvalu = n2cnts.get(form, 0) - 1
        if newvalu == 0:
            n2cnts.pop(form)
            if not n2cnts:
                n2sode['n2verbs'].pop(verb)
                if not self.mayDelNid(n2nid, n2sode):
                    self.dirty[n2nid] = n2sode
        else:
            n2cnts[form] = newvalu
            self.dirty[n2nid] = n2sode

        formabrv = self.core.setIndxAbrv(INDX_FORM, form)
        n2formabrv = self.core.setIndxAbrv(INDX_FORM, n2form)

        self.indxcounts.inc(vabrv, -1)
        self.indxcounts.inc(INDX_EDGE_N1 + formabrv + vabrv, -1)
        self.indxcounts.inc(INDX_EDGE_N2 + n2formabrv + vabrv, -1)
        self.indxcounts.inc(INDX_EDGE_N1N2 + formabrv + vabrv + n2formabrv, -1)

        return ()

    async def _editNodeEdgeTomb(self, nid, form, edit, sode, meta):

        verb, n2nid = edit[1]
        n2nid = s_common.int64en(n2nid)

        vabrv = self.core.setIndxAbrv(INDX_EDGE_VERB, verb)

        if not await self.layrslab.put(INDX_TOMB + vabrv + nid, n2nid, db=self.indxdb):
            return ()

        n2sode = self._genStorNode(n2nid)

        self.dirty[nid] = sode
        self.dirty[n2nid] = n2sode

        kvpairs = [
            (vabrv + nid + FLAG_TOMB, n2nid),
            (self.edgen1abrv + nid + vabrv + FLAG_TOMB, n2nid),
            (self.edgen2abrv + n2nid + vabrv + FLAG_TOMB, nid),
            (self.edgen1n2abrv + nid + n2nid + FLAG_TOMB, vabrv)
        ]

        self.indxcounts.inc(INDX_TOMB + vabrv)

        if sode.get('form') is None:
            sode['form'] = form
            formabrv = self.core.setIndxAbrv(INDX_FORM, form)
            kvpairs.append((formabrv, nid))

        if (n2form := n2sode.get('form')) is None:
            n2form = self.core.getNidNdef(n2nid)[0]
            n2sode['form'] = n2form
            n2formabrv = self.core.setIndxAbrv(INDX_FORM, n2form)
            kvpairs.append((n2formabrv, n2nid))

        if (n1cnts := sode['n1antiverbs'].get(verb)) is None:
            n1cnts = sode['n1antiverbs'][verb] = {}

        if (n2cnts := n2sode['n2antiverbs'].get(verb)) is None:
            n2cnts = n2sode['n2antiverbs'][verb] = {}

        n1cnts[n2form] = n1cnts.get(n2form, 0) + 1
        n2cnts[form] = n2cnts.get(form, 0) + 1

        return kvpairs

    async def _editNodeEdgeTombDel(self, nid, form, edit, sode, meta):

        verb, n2nid = edit[1]
        n2nid = s_common.int64en(n2nid)

        vabrv = self.core.setIndxAbrv(INDX_EDGE_VERB, verb)

        if not self.layrslab.delete(INDX_TOMB + vabrv + nid, n2nid, db=self.indxdb):
            self.mayDelNid(nid, sode)
            return ()

        self.layrslab.delete(vabrv + nid + FLAG_TOMB, n2nid, db=self.indxdb)
        self.layrslab.delete(self.edgen1abrv + nid + vabrv + FLAG_TOMB, n2nid, db=self.indxdb)
        self.layrslab.delete(self.edgen2abrv + n2nid + vabrv + FLAG_TOMB, nid, db=self.indxdb)
        self.layrslab.delete(self.edgen1n2abrv + nid + n2nid + FLAG_TOMB, vabrv, db=self.indxdb)

        n2sode = self._genStorNode(n2nid)
        if (n2form := n2sode.get('form')) is None:
            n2form = self.core.getNidNdef(n2nid)[0]

        n1cnts = sode['n1antiverbs'][verb]
        n2cnts = n2sode['n2antiverbs'][verb]

        newvalu = n1cnts.get(n2form, 0) - 1
        if newvalu == 0:
            n1cnts.pop(n2form)
            if not n1cnts:
                sode['n1antiverbs'].pop(verb)
                if not self.mayDelNid(nid, sode):
                    self.dirty[nid] = sode
        else:
            n1cnts[n2form] = newvalu
            self.dirty[nid] = sode

        newvalu = n2cnts.get(form, 0) - 1
        if newvalu == 0:
            n2cnts.pop(form)
            if not n2cnts:
                n2sode['n2antiverbs'].pop(verb)
                if not self.mayDelNid(n2nid, n2sode):
                    self.dirty[n2nid] = n2sode
        else:
            n2cnts[form] = newvalu
            self.dirty[n2nid] = n2sode

        self.indxcounts.inc(INDX_TOMB + vabrv, -1)

        return ()

    async def getEdgeVerbs(self):
        for byts, abrv in self.core.indxabrv.iterByPref(INDX_EDGE_VERB):
            if self.indxcounts.get(abrv) > 0:
                yield s_msgpack.un(byts[2:])[0]

    async def getEdges(self, verb=None):

        if verb is None:
            for lkey, lval in self.layrslab.scanByPref(self.edgen1abrv, db=self.indxdb):
                yield lkey[-17:-9], lkey[-9:-1], lval, lkey[-1:] == FLAG_TOMB
            return

        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return

        for lkey, lval in self.layrslab.scanByPref(vabrv, db=self.indxdb):
            # n1nid, verbabrv, n2nid, tomb
            yield lkey[-9:-1], vabrv, lval, lkey[-1:] == FLAG_TOMB

    async def _delNodeEdges(self, nid, form, sode):

        formabrv = self.core.setIndxAbrv(INDX_FORM, form)

        sode.pop('n1verbs', None)
        sode.pop('n1antiverbs', None)

        for lkey, n2nid in self.layrslab.scanByPref(self.edgen1abrv + nid, db=self.indxdb):
            await asyncio.sleep(0)

            tomb = lkey[-1:]
            vabrv = lkey[-9:-1]

            self.layrslab.delete(vabrv + nid + tomb, n2nid, db=self.indxdb)
            self.layrslab.delete(self.edgen1abrv + nid + vabrv + tomb, n2nid, db=self.indxdb)
            self.layrslab.delete(self.edgen2abrv + n2nid + vabrv + tomb, nid, db=self.indxdb)
            self.layrslab.delete(self.edgen1n2abrv + nid + n2nid + tomb, vabrv, db=self.indxdb)

            verb = self.core.getAbrvIndx(vabrv)[0]
            n2sode = self._genStorNode(n2nid)

            if tomb == FLAG_TOMB:
                self.layrslab.delete(INDX_TOMB + vabrv + nid, n2nid, db=self.indxdb)
                n2cnts = n2sode['n2antiverbs'][verb]
                newvalu = n2cnts.get(form, 0) - 1
                if newvalu == 0:
                    n2cnts.pop(form)
                    if not n2cnts:
                        n2sode['n2antiverbs'].pop(verb)
                        if not self.mayDelNid(n2nid, n2sode):
                            self.dirty[n2nid] = n2sode
                else:
                    n2cnts[form] = newvalu
                    self.dirty[n2nid] = n2sode

            else:
                n2cnts = n2sode['n2verbs'][verb]
                newvalu = n2cnts.get(form, 0) - 1
                if newvalu == 0:
                    n2cnts.pop(form)
                    if not n2cnts:
                        n2sode['n2verbs'].pop(verb)
                        if not self.mayDelNid(n2nid, n2sode):
                            self.dirty[n2nid] = n2sode
                else:
                    n2cnts[form] = newvalu
                    self.dirty[n2nid] = n2sode

            self.indxcounts.inc(vabrv, -1)
            self.indxcounts.inc(INDX_EDGE_N1 + formabrv + vabrv, -1)

            if (n2form := n2sode.get('form')) is None:
                n2form = self.core.getNidNdef(n2nid)[0]

            n2formabrv = self.core.setIndxAbrv(INDX_FORM, n2form)
            self.indxcounts.inc(INDX_EDGE_N2 + n2formabrv + vabrv, -1)
            self.indxcounts.inc(INDX_EDGE_N1N2 + formabrv + vabrv + n2formabrv, -1)

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
                vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
                pref += vabrv
            except s_exc.NoSuchAbrv:
                return

            for lkey, n2nid in self.layrslab.scanByPref(pref, db=self.indxdb):
                yield vabrv, n2nid, lkey[-1:] == FLAG_TOMB
            return

        for lkey, n2nid in self.layrslab.scanByPref(pref, db=self.indxdb):
            yield lkey[-9:-1], n2nid, lkey[-1:] == FLAG_TOMB

    async def iterNodeEdgesN2(self, nid, verb=None):

        pref = self.edgen2abrv + nid
        if verb is not None:
            try:
                vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
                pref += vabrv
            except s_exc.NoSuchAbrv:
                return

            for lkey, n1nid in self.layrslab.scanByPref(pref, db=self.indxdb):
                yield vabrv, n1nid, lkey[-1:] == FLAG_TOMB
            return

        for lkey, n1nid in self.layrslab.scanByPref(pref, db=self.indxdb):
            yield lkey[-9:-1], n1nid, lkey[-1:] == FLAG_TOMB

    async def iterEdgeVerbs(self, n1nid, n2nid):
        for lkey, vabrv in self.layrslab.scanByPref(self.edgen1n2abrv + n1nid + n2nid, db=self.indxdb):
            yield vabrv, lkey[-1:] == FLAG_TOMB

    async def iterNodeEdgeVerbsN1(self, nid):

        pref = self.edgen1abrv + nid
        for lkey in self.layrslab.scanKeysByPref(pref, db=self.indxdb, nodup=True):
            yield lkey[-9:-1], lkey[-1:] == FLAG_TOMB

    async def hasNodeEdge(self, n1nid, verb, n2nid):
        try:
            vabrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
        except s_exc.NoSuchAbrv:
            return None

        if self.layrslab.hasdup(self.edgen1abrv + n1nid + vabrv + FLAG_NORM, n2nid, db=self.indxdb):
            return True

        elif self.layrslab.hasdup(self.edgen1abrv + n1nid + vabrv + FLAG_TOMB, n2nid, db=self.indxdb):
            return False

    async def getNdefRefs(self, buid):
        for lkey, refsnid in self.layrslab.scanByPref(self.ndefabrv + buid, db=self.indxdb):
            yield refsnid, lkey[40:]

    async def getNodePropRefs(self, buid):
        for lkey, refsnid in self.layrslab.scanByPref(self.nodepropabrv + buid, db=self.indxdb):
            yield refsnid, lkey[40:]

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

    async def iterTagRows(self, tag, form=None, starttupl=None):
        '''
        Yields (nid, valu) values that match a tag and optional form.

        Args:
            tag (str): the tag to match
            form (Optional[str]):  if present, only yields nids of nodes that match the form.
            starttupl (Optional[Tuple[nid, Tuple[int, int, int] | Tuple[None, None, None]]]): if present, (re)starts the stream of values there.

        Yields:
            (nid, valu)
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_TAG, form, tag)
        except s_exc.NoSuchAbrv:
            return

        abrvlen = len(abrv)
        ivallen = self.ivaltimetype.size

        nonetupl = (None, None, None)
        startkey = None
        startvalu = None

        if starttupl is not None:
            (nid, valu) = starttupl
            startvalu = nid
            if valu != (None, None, None):
                minindx = self.ivaltimetype.getIntIndx(valu[0])
                maxindx = self.ivaltimetype.getIntIndx(valu[1])
                startkey = minindx + maxindx

        for lkey, nid in self.layrslab.scanByPref(abrv, startkey=startkey, startvalu=startvalu, db=self.indxdb):
            await asyncio.sleep(0)

            if len(lkey) == abrvlen:
                yield nid, nonetupl
                continue

            yield nid, self.ivaltype.decodeIndx(lkey[abrvlen:])

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
            abrv = self.core.getIndxAbrv(INDX_NODEDATA, name)
        except s_exc.NoSuchAbrv:
            return False, None, None

        byts = self.dataslab.get(nid + abrv + FLAG_NORM, db=self.nodedata)
        if byts is None:
            if self.dataslab.get(nid + abrv + FLAG_TOMB, db=self.nodedata):
                return True, None, True
            return False, None, None

        return True, s_msgpack.un(byts), False

    async def iterNodeData(self, nid):
        '''
        Return a generator of all a node's data by nid.
        '''
        for lkey, byts in self.dataslab.scanByPref(nid, db=self.nodedata):
            abrv = lkey[8:-1]
            valu = s_msgpack.un(byts)
            yield abrv, valu, lkey[-1:] == FLAG_TOMB

    async def iterNodeDataKeys(self, nid):
        '''
        Return a generator of all a nid's node data keys
        '''
        for lkey in self.dataslab.scanKeysByPref(nid, db=self.nodedata):
            abrv = lkey[8:-1]
            yield abrv, lkey[-1:] == FLAG_TOMB

    async def iterPropTombstones(self, form, prop):
        try:
            abrv = self.core.getIndxAbrv(INDX_PROP, form, prop)
        except s_exc.NoSuchAbrv:
            return

        for _, nid in self.layrslab.scanByPref(INDX_TOMB + abrv, db=self.indxdb):
            yield nid

    async def iterEdgeTombstones(self, verb=None):
        if verb is not None:
            try:
                abrv = self.core.getIndxAbrv(INDX_EDGE_VERB, verb)
            except s_exc.NoSuchAbrv:
                return

            for lkey in self.layrslab.scanKeysByPref(INDX_TOMB + abrv, db=self.indxdb):
                n1nid = s_common.int64un(lkey[10:18])
                for _, n2nid in self.layrslab.scanByDups(lkey, db=self.indxdb):
                    yield (n1nid, verb, s_common.int64un(n2nid))
            return

        for byts, abrv in self.core.indxabrv.iterByPref(INDX_EDGE_VERB):
            if self.indxcounts.get(INDX_TOMB + abrv) == 0:
                continue

            verb = s_msgpack.un(byts[2:])[0]

            for lkey in self.layrslab.scanKeysByPref(INDX_TOMB + abrv, db=self.indxdb):
                n1nid = s_common.int64un(lkey[10:18])
                for _, n2nid in self.layrslab.scanByDups(lkey, db=self.indxdb):
                    yield (n1nid, verb, s_common.int64un(n2nid))

    async def iterTombstones(self):

        for lkey in self.layrslab.scanKeysByPref(INDX_TOMB, db=self.indxdb):
            byts = self.core.indxabrv.abrvToByts(lkey[2:10])
            tombtype = byts[:2]
            tombinfo = s_msgpack.un(byts[2:])

            if tombtype == INDX_EDGE_VERB:
                n1nid = lkey[10:18]

                for _, n2nid in self.layrslab.scanByDups(lkey, db=self.indxdb):
                    yield (n1nid, tombtype, (tombinfo[0], n2nid))

            else:

                for _, nid in self.layrslab.scanByDups(lkey, db=self.indxdb):
                    yield (nid, tombtype, tombinfo)

    async def confirmLayerEditPerms(self, user, gateiden, delete=False):
        if user.allowed(('node',), gateiden=gateiden, deepdeny=True):
            return

        perm_del_form = ('node', 'del')
        perm_del_prop = ('node', 'prop', 'del')
        perm_del_tag = ('node', 'tag', 'del')
        perm_del_ndata = ('node', 'data', 'del')
        perm_del_edge = ('node', 'edge', 'del')

        perm_add_form = ('node', 'add')
        perm_add_prop = ('node', 'prop', 'set')
        perm_add_tag = ('node', 'tag', 'add')
        perm_add_ndata = ('node', 'data', 'set')
        perm_add_edge = ('node', 'edge', 'add')

        if all((
            (allow_add_forms := user.allowed(perm_add_form, gateiden=gateiden, deepdeny=True)),
            (allow_add_props := user.allowed(perm_add_prop, gateiden=gateiden, deepdeny=True)),
            (allow_add_tags := user.allowed(perm_add_tag, gateiden=gateiden, deepdeny=True)),
            (allow_add_ndata := user.allowed(perm_add_ndata, gateiden=gateiden, deepdeny=True)),
            (allow_add_edges := user.allowed(perm_add_edge, gateiden=gateiden, deepdeny=True)),

            (allow_del_forms := user.allowed(perm_del_form, gateiden=gateiden, deepdeny=True)),
            (allow_del_props := user.allowed(perm_del_prop, gateiden=gateiden, deepdeny=True)),
            (allow_del_tags := user.allowed(perm_del_tag, gateiden=gateiden, deepdeny=True)),
            (allow_del_ndata := user.allowed(perm_del_ndata, gateiden=gateiden, deepdeny=True)),
            (allow_del_edges := user.allowed(perm_del_edge, gateiden=gateiden, deepdeny=True)),
        )):
            return

        if delete:
            perm_forms = perm_del_form
            allow_forms = allow_del_forms

            allow_props = allow_del_props

            perm_tags = perm_del_tag
            allow_tags = allow_del_tags

            perm_ndata = perm_del_ndata
            allow_ndata = allow_del_ndata

            perm_edges = perm_del_edge
            allow_edges = allow_del_edges
        else:
            perm_forms = perm_add_form
            allow_forms = allow_add_forms

            allow_props = allow_add_props

            perm_tags = perm_add_tag
            allow_tags = allow_add_tags

            perm_ndata = perm_add_ndata
            allow_ndata = allow_add_ndata

            perm_edges = perm_add_edge
            allow_edges = allow_add_edges

        # nodes & props
        if not allow_forms or not allow_props:
            async for form, prop in s_coro.pause(self.getFormProps()):
                if form is None: # pragma: no cover
                    continue

                if prop:
                    if allow_props:
                        continue

                    realform = self.core.model.form(form)
                    if not realform: # pragma: no cover
                        mesg = f'Invalid form: {form}'
                        raise s_exc.NoSuchForm(mesg=mesg, form=form)

                    realprop = realform.prop(prop)
                    if not realprop: # pragma: no cover
                        mesg = f'Invalid prop: {form}:{prop}'
                        raise s_exc.NoSuchProp(mesg=mesg, form=form, prop=prop)

                    if delete:
                        user.confirm(realprop.delperm, gateiden=gateiden)
                    else:
                        user.confirm(realprop.setperm, gateiden=gateiden)

                elif not allow_forms:
                    user.confirm(perm_forms + (form,), gateiden=gateiden)

        # tagprops
        if not allow_tags:
            async for tagprop in s_coro.pause(self.getTagProps()):
                perm = perm_tags + tuple(tagprop[1].split('.'))
                user.confirm(perm, gateiden=gateiden)

        # nodedata
        if not allow_ndata:
            async for abrv in s_coro.pause(self.dataslab.scanKeys(db=self.dataname, nodup=True)):
                if abrv[8:] == FLAG_TOMB:
                    continue

                key = self.core.getAbrvIndx(abrv[:8])
                perm = perm_ndata + key
                user.confirm(perm, gateiden=gateiden)

        # edges
        if not allow_edges:
            async for verb in s_coro.pause(self.getEdgeVerbs()):
                perm = perm_edges + (verb,)
                user.confirm(perm, gateiden=gateiden)

        # tombstones
        async for lkey in s_coro.pause(self.layrslab.scanKeysByPref(INDX_TOMB, db=self.indxdb, nodup=True)):
            byts = self.core.indxabrv.abrvToByts(lkey[2:10])
            tombtype = byts[:2]
            tombinfo = s_msgpack.un(byts[2:])

            if tombtype == INDX_PROP:
                (form, prop) = tombinfo
                if delete:
                    if prop:
                        perm = perm_add_prop + tombinfo
                    else:
                        perm = perm_add_form + (form,)
                    allowed = allow_del_props
                else:
                    if prop:
                        perm = perm_del_prop + tombinfo
                    else:
                        perm = perm_del_form + (form,)
                    allowed = allow_add_props

            elif tombtype == INDX_TAG:
                if delete:
                    perm = perm_add_tag + tuple(tombinfo[1].split('.'))
                    allowed = allow_del_tags
                else:
                    perm = perm_del_tag + tuple(tombinfo[1].split('.'))
                    allowed = allow_add_tags

            elif tombtype == INDX_TAGPROP:
                if delete:
                    perm = perm_add_tag + tombinfo[1:]
                    allowed = allow_del_tags
                else:
                    perm = perm_del_tag + tombinfo[1:]
                    allowed = allow_add_tags

            elif tombtype == INDX_NODEDATA:
                if delete:
                    perm = perm_add_ndata + tombinfo
                    allowed = allow_del_ndata
                else:
                    perm = perm_del_ndata + tombinfo
                    allowed = allow_add_ndata

            elif tombtype == INDX_EDGE_VERB:
                if delete:
                    perm = perm_add_edge + tombinfo
                    allowed = allow_del_edges
                else:
                    perm = perm_del_edge + tombinfo
                    allowed = allow_add_edges

            else: # pragma: no cover
                extra = await self.core.getLogExtra(tombtype=tombtype, delete=delete, tombinfo=tombinfo)
                logger.debug(f'Encountered unknown tombstone type: {tombtype}.', extra=extra)
                continue

            if not allowed:
                user.confirm(perm, gateiden=gateiden)

        # tags
        # NB: tag perms should be yielded for every leaf on every node in the layer
        if not allow_tags:
            async with self.core.getSpooledDict() as tagdict:
                async for byts, abrv in s_coro.pause(self.core.indxabrv.iterByPref(INDX_TAG)):
                    (form, tag) = s_msgpack.un(byts[2:])
                    if form is None:
                        continue

                    async for _, nid in s_coro.pause(self.layrslab.scanByPref(abrv, db=self.indxdb)):
                        tags = list(tagdict.get(nid, []))
                        tags.append(tag)
                        await tagdict.set(nid, tags)

                # Iterate over each node and it's tags
                async for nid, tags in s_coro.pause(tagdict.items()):
                    leaf = {}

                    if len(tags) == 1:
                        # Easy optimization: If there's only one tag, then it's a
                        # leaf by default
                        perm = perm_tags + tuple(tags[0].split('.'))
                        user.confirm(perm, gateiden=gateiden)

                    else:
                        for tag in tags:
                            parts = tag.split('.')
                            for idx in range(1, len(parts) + 1):
                                key = tuple(parts[:idx])
                                leaf.setdefault(key, 0)
                                leaf[key] += 1

                        for key, count in leaf.items():
                            if count == 1:
                                perm = perm_tags + key
                                user.confirm(perm, gateiden=gateiden)

    async def iterLayerNodeEdits(self, meta=False):
        '''
        Scan the full layer and yield artificial sets of nodeedits.
        '''
        await self._saveDirtySodes()

        for nid, byts in self.layrslab.scanByFull(db=self.bynid):

            sode = s_msgpack.un(byts)
            ndef = self.core.getNidNdef(nid)

            form = ndef[0]

            edits = []
            intnid = s_common.int64un(nid)
            nodeedit = (intnid, form, edits)

            valt = sode.get('valu')
            if valt is not None:
                edits.append((EDIT_NODE_ADD, valt))

            elif sode.get('antivalu') is not None:
                edits.append((EDIT_NODE_TOMB, ()))
                yield nodeedit
                continue

            if meta and (mval := sode.get('meta')) is not None:
                if (cval := mval.get('created')) is not None:
                    (valu, stortype) = cval
                    edits.append((EDIT_META_SET, ('created', valu, stortype)))

            for prop, (valu, stortype, virts) in sode.get('props', {}).items():
                edits.append((EDIT_PROP_SET, (prop, valu, stortype, virts)))

            for prop in sode.get('antiprops', {}).keys():
                edits.append((EDIT_PROP_TOMB, (prop,)))

            for tag, tagv in sode.get('tags', {}).items():
                edits.append((EDIT_TAG_SET, (tag, tagv)))

            for tag in sode.get('antitags', {}).keys():
                edits.append((EDIT_TAG_TOMB, (tag,)))

            for tag, propdict in sode.get('tagprops', {}).items():
                for prop, (valu, stortype) in propdict.items():
                    edits.append((EDIT_TAGPROP_SET, (tag, prop, valu, stortype)))

            for tag, propdict in sode.get('antitagprops', {}).items():
                for prop in propdict.keys():
                    edits.append((EDIT_TAGPROP_TOMB, (tag, prop)))

            async for abrv, valu, tomb in self.iterNodeData(nid):
                prop = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    edits.append((EDIT_NODEDATA_TOMB, (prop,)))
                else:
                    edits.append((EDIT_NODEDATA_SET, (prop, valu)))

            async for abrv, n2nid, tomb in self.iterNodeEdgesN1(nid):
                verb = self.core.getAbrvIndx(abrv)[0]
                if tomb:
                    edits.append((EDIT_EDGE_TOMB, (verb, s_common.int64un(n2nid))))
                else:
                    edits.append((EDIT_EDGE_ADD, (verb, s_common.int64un(n2nid))))

                if len(edits) >= 100:
                    yield nodeedit
                    edits = []
                    nodeedit = (intnid, form, edits)

            yield nodeedit

    async def _wipeNodeData(self, nid, sode):
        '''
        Remove all node data for a nid
        '''
        for lkey, _ in self.dataslab.scanByPref(nid, db=self.nodedata):
            await asyncio.sleep(0)
            self.dataslab.delete(lkey, db=self.nodedata)
            self.dataslab.delete(lkey[8:], nid, db=self.dataname)

            if lkey[-1:] == FLAG_TOMB:
                self.layrslab.delete(INDX_TOMB + lkey[8:-1], nid, db=self.indxdb)

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
        Yield (nid, sode) tuples for all the nodes with props/tags/tagprops stored in this layer.
        '''
        # flush any dirty sodes so we can yield them from the index in nid order
        await self._saveDirtySodes()

        for nid, byts in self.layrslab.scanByFull(db=self.bynid):
            await asyncio.sleep(0)
            yield nid, s_msgpack.un(byts)

    async def getStorNodesByForm(self, form):
        '''
        Yield (nid, sode) tuples for nodes of a given form with any data in this layer.
        '''
        try:
            abrv = self.core.getIndxAbrv(INDX_FORM, form)
        except s_exc.NoSuchAbrv:
            return

        for _, nid in self.layrslab.scanByDups(abrv, db=self.indxdb):
            sode = self.getStorNode(nid)
            yield nid, sode
            await asyncio.sleep(0)

    def getStorNode(self, nid):
        '''
        Return a *COPY* of the storage node (or an empty default dict).
        '''
        sode = self._getStorNode(nid)
        if sode is not None:
            return deepcopy(sode)
        return collections.defaultdict(dict)

    async def syncNodeEdits2(self, offs, wait=True, reverse=False, compat=False):
        '''
        Once caught up with storage, yield them in realtime.

        Returns:
            Tuple of offset(int), nodeedits, meta(dict)
        '''
        if not self.logedits:
            return

        if not compat:
            for offi, _ in self.nodeeditlog.iter(offs, reverse=reverse):
                nexsitem = await self.core.nexsroot.nexslog.get(offi)
                yield (offi, *nexsitem[2])

            if wait:
                async with self.getNodeEditWindow() as wind:
                    async for item in wind:
                        yield item
            return

        for offi, _ in self.nodeeditlog.iter(offs, reverse=reverse):
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

    async def syncNodeEdits(self, offs, wait=True, reverse=False, compat=False):
        '''
        Identical to syncNodeEdits2, but doesn't yield meta
        '''
        async for offi, nodeedits, _meta in self.syncNodeEdits2(offs, wait=wait, reverse=reverse, compat=compat):
            yield (offi, nodeedits)

    async def syncIndexEvents(self, offs, matchdef, wait=True):
        '''
        Yield (offs, (nid, form, ETYPE, VALS)) tuples from the nodeedit log starting from the given offset.
        Only edits that match the filter in matchdef will be yielded.

        Notes:

            ETYPE is a constant EDIT_* above. VALS is a tuple whose format depends on ETYPE, outlined in the comment
            next to the constant.

            Additionally, every 1000 entries, an entry (offs, (None, None, EDIT_PROGRESS, ())) message is emitted.

            The matchdef dict may contain the following keys:  forms, props, tags, tagprops.  The value must be a
            sequence of strings.  Each key/val combination is treated as an "or", so each key and value yields more events.
            forms: EDIT_NODE_ADD and EDIT_NODE_DEL events.  Matches events for nodes with forms in the value list.
            props: EDIT_PROP_SET and EDIT_PROP_DEL events.  Values must be in form:prop format.
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

        ntypes = (EDIT_NODE_ADD, EDIT_NODE_DEL, EDIT_NODE_TOMB, EDIT_NODE_TOMB_DEL)
        ptypes = (EDIT_PROP_SET, EDIT_PROP_DEL, EDIT_PROP_TOMB, EDIT_PROP_TOMB_DEL)
        ttypes = (EDIT_TAG_SET, EDIT_TAG_DEL, EDIT_TAG_TOMB, EDIT_TAG_TOMB_DEL)
        tptypes = (EDIT_TAGPROP_SET, EDIT_TAGPROP_DEL,
                   EDIT_TAGPROP_TOMB, EDIT_TAGPROP_TOMB_DEL)

        async for curoff, editses in self.syncNodeEdits(offs, wait=wait):
            for nid, form, edit in editses:
                for etyp, vals in edit:
                    if ((form in formm and etyp in ntypes)
                            or (etyp in ptypes and (vals[0] in propm or f'{form}:{vals[0]}' in propm))
                            or (etyp in ttypes and vals[0] in tagm)
                            or (etyp in tptypes and (vals[1] in tagpropm or f'{vals[0]}:{vals[1]}' in tagpropm))):

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
