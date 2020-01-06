'''
The layer library contains the base Layer object and helpers used for
cortex construction.

Note:  this interface is subject to change between minor revisions.
'''
import os
import shutil
import asyncio
import logging
import contextlib

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.gis as s_gis
import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.hive as s_hive
import synapse.lib.cache as s_cache
import synapse.lib.queue as s_queue

import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn


logger = logging.getLogger(__name__)

FAIR_ITERS = 10  # every this many rows, yield CPU to other tasks
BUID_CACHE_SIZE = 10000

import synapse.lib.msgpack as s_msgpack

#class LayerApi(s_cell.CellApi):

    #async def __anit__(self, core, link, user, layr):

        #await s_cell.CellApi.__anit__(self, core, link, user)

        #self.layr = layr
        #self.liftperm = ('layer:lift', self.layr.iden)
        #self.storperm = ('layer:stor', self.layr.iden)

    #async def getLiftRows(self, lops):
        #await self._reqUserAllowed(self.liftperm)
        #async for item in self.layr.getLiftRows(lops):
            #yield item

    #async def iterFormRows(self, form):
        #await self._reqUserAllowed(self.liftperm)
        #async for item in self.layr.iterFormRows(form):
            #yield item

    #async def iterPropRows(self, form, prop):
        #await self._reqUserAllowed(self.liftperm)
        #async for item in self.layr.iterPropRows(form, prop):
            #yield item

    #async def iterUnivRows(self, univ):
        #await self._reqUserAllowed(self.liftperm)
        #async for item in self.layr.iterUnivRows(univ):
            #yield item

    #async def stor(self, sops, splices=None):
        #await self._reqUserAllowed(self.storperm)
        #return await self.layr.stor(sops, splices=splices)

    #async def getBuidProps(self, buid):
        #await self._reqUserAllowed(self.liftperm)
        #return await self.layr.getBuidProps(buid)

    #async def getModelVers(self):
        #return await self.layr.getModelVers()

    #async def getOffset(self, iden):
        #return await self.layr.getOffset(iden)

    #async def setOffset(self, iden, valu):
        #return await self.layr.setOffset(iden, valu)

    #async def delOffset(self, iden):
        #return await self.layr.delOffset(iden)

    #async def splices(self, offs, size):
        #await self._reqUserAllowed(self.liftperm)
        #async for item in self.layr.splices(offs, size):
            #yield item

    #async def hasTagProp(self, name):
        #return await self.layr.hasTagProp(name)

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

#STOR_TYPE_FIXED     = ??
#STOR_TYPE_TOMB      = ??

STOR_FLAG_ARRAY = 0x8000

# Splices - (<type>, <buid>, <edit>, {meta})
# The meta dict is desiged to encapuslate the things that make the splice
# specific to one cortex, allowing them to be optionally stripped when replicating
# to a downstream (but non-mirror) cortex.

# splice types...
SPLICE_NODE_ADD = 0     # (<type>, <buid>, (<form>, <valu>), {})
SPLICE_NODE_DEL = 1     # (<type>, <buid>, (<form>, <valu>), {})
SPLICE_PROP_SET = 2     # (<type>, <buid>, (<form>, <prop>, <valu>, <oldv>), {})
SPLICE_PROP_DEL = 3     # (<type>, <buid>, (<form>, <prop>, <oldv>), {})
SPLICE_TAG_SET = 4      # (<type>, <buid>, (<form>, <tag>, <valu>, <oldv>), {})
SPLICE_TAG_DEL = 5      # (<type>, <buid>, (<form>, <tag>, <oldv>), {})
SPLICE_TAGPROP_SET = 6  # (<type>, <buid>, (<form>, <tag>, <prop>, <valu>, <oldv>), {})
SPLICE_TAGPROP_DEL = 7  # (<type>, <buid>, (<form>, <tag>, <prop>, <oldv>), {})

class StorType:

    def __init__(self, layr, stortype):
        self.layr = layr
        self.stortype = stortype

        self.lifters = {}

    def lift(self, form, prop, cmpr, valu):

        func = self.lifters.get(cmpr)

        if func is None:
            raise s_exc.NoSuchCmpr()

        for buid in func(form, prop, valu):
            yield buid

    def indx(self, valu):
        raise NotImplemented

class StorTypeUtf8(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_UTF8)
        self.lifters.update({
            '=': self._liftUtf8Eq,
            '~=': self._liftUtf8Regx,
            '^=': self._liftUtf8Prefix,
        })

    def _liftUtf8Eq(self, form, prop, valu):
        indx = self._getIndxByts(valu)
        abrv = self.layr.getPropAbrv(form, prop)
        for lkey, buid in self.layr.layrslab.scanByDups(abrv + indx, db=self.layr.byprop):
            yield buid

    def _liftUtf8Regx(self, form, prop, valu):

        regx = regex.compile(valu)
        abrv = self.layr.getPropAbrv(form, prop)
        for lkey, buid in self.layr.layrslab.scanByPref(abrv, db=self.layr.byprop):
            valu = self.layr.getNodeValu(buid, prop=prop)
            if regx.search(valu) is None:
                continue
            yield buid

    def _liftUtf8Prefix(self, form, prop, valu):
        indx = self._getIndxByts(valu)
        abrv = self.layr.getPropAbrv(form, prop)
        for lkey, buid in self.layr.layrslab.scanByPref(abrv + indx, db=self.layr.byprop):
            yield buid

    def _getIndxByts(self, valu, indxtype=b'\x00'):

        # include a byte as a "type" of string index value
        # ( to allow sub-types to have special indexing )

        indx = indxtype + valu.encode('utf8', 'surrogatepass')
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

    def _liftHierEq(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        indx = self.getHierIndx(valu)
        for lkey, buid in self.layr.layrslab.scanByDups(abrv + indx, db=self.layr.byprop):
            yield buid

    def _liftHierPref(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        indx = self.getHierIndx(valu)
        for lkey, buid in self.layr.layrslab.scanByPref(abrv + indx, db=self.layr.byprop):
            yield buid

class StorTypeLoc(StorTypeHier):
    def __init__(self, layr):
        StorTypeHier.__init__(self, layr, STOR_TYPE_LOC)

class StorTypeTag(StorTypeHier):

    def __init__(self, layr):
        StorTypeHier.__init__(self, layr, STOR_TYPE_TAG)

    @staticmethod
    def getTagFilt(cmpr, valu):

        if cmpr == '=':
            def filt(x):
                return x == valu
            return filt

        if cmpr == '@=':

            def filt(item):

                if item is None:
                    return False

                if item == (None, None):
                    return False

                if item[0] >= valu[1]:
                    return False

                if item[1] <= valu[0]:
                    return False

                return True

class StorTypeFqdn(StorTypeUtf8):

    def indx(self, norm):
        return (
            self._getIndxByts(norm[::-1]),
        )

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_UTF8)
        self.lifters.update({
            '=': self._liftUtf8Eq,
        })

    def _liftUtf8Eq(self, form, prop, valu):

        abrv = self.layr.getPropAbrv(form, prop)
        if valu[0] == '*':
            indx = self._getIndxByts(valu[1:][::-1], indxtype=b'\x01')
            for lkey, buid in self.layr.layrslab.scanByPref(abrv + indx, db=self.layr.byprop):
                yield buid

        for buid in StorTypeUtf8._liftUtf8Eq(self, prop, valu):
            yield buid

class StorTypeIpv6(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IPV6)
        self.lifters.update({
            '=': self._liftIPv6Eq,
            'range=': self._liftIPv6Range,
        })

    def getIPv6Indx(self, valu):
        return ipaddress.IPv6Address(norm).packed

    def indx(self, valu):
        return (
            self.getIPv6Indx(valu),
        )

    def _liftIPv6Eq(self, form, prop, valu):
        indx = self.getIPv6Indx(valu)
        abrv = self.layr.getPropAbrv(form, prop)
        for lkey, buid in self.layr.layrslab.scanByDups(abrv + indx, db=self.layr.byprop):
            yield buid

    def _liftIPv6Range(self, form, prop, valu):
        minindx = self.getIPv6Indx(valu[0])
        maxindx = self.getIPv6Indx(valu[1])
        abrv = self.layr.getPropAbrv(form, prop)
        for lkey, buid in self.layr.layrslab.scanByRange(abrv + minindx, abrv + maxindx, db=self.layr.byprop):
            yield buid

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

    def _liftIntEq(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        indx = (valu + self.offset).to_bytes(self.size, 'big')
        for lkey, buid in self.layr.layrslab.scanByDups(abrv + indx, db=self.layr.byprop):
            yield buid

    def _liftIntGt(self, form, prop, valu):
        for buid in self._liftIntGe(form, prop, valu + 1):
            yield buid

    def _liftIntGe(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        pkeymin = abrv + (valu + self.offset).to_bytes(self.size, 'big')
        pkeymax = abrv + self.fullbyts
        for lkey, buid in self.layr.layrslab.scanByRange(pkeymin, pkeymax, db=self.layr.byprop):
            yield buid

    def _liftIntLt(self, form, prop, valu):
        for buid in self._liftIntLe(form, prop, valu - 1):
            yield buid

    def _liftIntLe(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        pkeymin = abrv + self.zerobyts
        pkeymax = abrv + (valu + self.offset).to_bytes(self.size, 'big')
        for lkey, buid in self.layr.layrslab.scanByRange(pkeymin, pkeymax, db=self.layr.byprop):
            yield buid

    def _liftIntRange(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        pkeymin = abrv + (valu[0] + self.offset).to_bytes(self.size, 'big')
        pkeymax = abrv + (valu[1] + self.offset).to_bytes(self.size, 'big')
        for lkey, buid in self.layr.layrslab.scanByRange(pkeymin, pkeymax, db=self.layr.byprop):
            yield buid

class StorTypeGuid(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_GUID)
        self.lifters.update({
            '=': self._liftGuidEq,
        })

    def _liftGuidEq(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        indx = s_common.uhex(valu)
        for lkey, buid in self.layr.layrslab.scanByDups(abrv + indx, db=self.layr.byprop):
            yield buid

    def indx(self, valu):
        return (s_common.uhex(valu),)

class StorTypeTime(StorTypeInt):
    def __init__(self, layr):
        StorTypeInt.__init__(self, layr, STOR_TYPE_TIME, 8, True)

class StorTypeIval(StorType):

    def __init__(self, layr):
        StorType.__init__(self, layr, STOR_TYPE_IVAL)
        self.timetype = StorTypeTime(layr)
        self.lifters.update({
            '=': self._liftIvalEq,
            #'<': self._liftIvalLt,
            #'>': self._liftIvalGt,
            #'>=': self._liftIvalGe,
            #'<=': self._liftIvalLe,
            '@=': self._liftIvalAt,
        })

    def _liftIvalEq(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        indx = self.timetype.getIntIndx(valu[0]) + self.timetype.getIntIndx(valu[1])
        for lkey, buid in self.layr.layrslab.scanByDups(abrv + indx, db=self.layr.byprop):
            yield buid

    def _liftIvalAt(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        indx = self.timetype.getIntIndx(valu[0])

        for lkey, buid in self.layr.layrslab.scanByPrefix(abrv + indx, db=self.layr.byprop):
            tick = s_common.int64un(lkey[32:40])
            tock = s_common.int64un(lkey[40:48])

            if tick > valu[1]:
                continue

            if tock < valu[0]:
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

    def _liftMsgpEq(self, form, prop, valu):
        indx = s_common.buid(valu)
        abrv = self.layr.getPropAbrv(form, prop)
        for lkey, buid in self.layr.layrslab.scanByDups(abrv + indx, db=self.layr.byprop):
            yield buid

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

    def _liftLatLonEq(self, form, prop, valu):
        abrv = self.layr.getPropAbrv(form, prop)
        indx = self._getLatLonIndx(valu)
        for lkey, buid in self.layr.layrslab.scanByDups(abrv + indx, db=self.layr.byprop):
            yield buid

    def _liftLatLonNear(self, form, prop, valu):

        abrv = self.layr.getPropAbrv(form, prop)

        (lat, lon), dist = valu

        latscale = (lat * self.scale) + self.latspace
        lonscale = (lon * self.scale) + self.lonspace

        latmin, latmax, lonmin, lonmax = s_gis.bbox(lat, lon, dist)

        lonminindx = int(((lonmin * self.scale) + self.lonspace)).to_bytes(5, 'big')
        lonmaxindx = int(((lonmax * self.scale) + self.lonspace)).to_bytes(5, 'big')

        latminindx = int(((latmin * self.scale) + self.latspace)).to_bytes(5, 'big')
        latmaxindx = int(((latmax * self.scale) + self.latspace)).to_bytes(5, 'big')

        # scan by lon range and down-select the results to matches.
        for lkey, buid in self.layr.layrslab.scanByRange(abrv + lonminindx, abrv + lonmaxindx, db=self.layr.byprop):

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
        # yield index bytes in lon/lat order to allow cheap optimial indexing
        latindx = int(((latlong[0] * self.scale) + self.latspace)).to_bytes(5, 'big')
        lonindx = int(((latlong[1] * self.scale) + self.lonspace)).to_bytes(5, 'big')
        return lonindx + latindx

    def indx(self, valu):
        # yield index bytes in lon/lat order to allow cheap optimial indexing
        return (self._getLatLonIndx(valu),)

class Layer(s_base.Base):
    '''
    The base class for a cortex layer.
    '''
    confdefs = ()

    def __repr__(self):
        return f'Layer ({self.__class__.__name__}): {self.iden}'

    async def __anit__(self, layrinfo, conf=None):

        await s_base.Base.__anit__(self)

        self.dirn = layrinfo.get('dirn')
        self.iden = layrinfo.get('iden')
        self.readonly = layrinfo.get('readonly')

        if conf is None:
            conf = {}

        confpath = s_common.genpath(self.dirn, 'layer.yaml')
        if os.path.isfile(confpath):
            [conf.setdefault(k, v) for (k, v) in s_common.yamlload(confpath).items()]

        self.conf = s_common.config(conf, self.confdefs)

        path = s_common.genpath(self.dirn, 'layer_v2.lmdb')

        self.fresh = not os.path.exists(path)

        self.layrslab = await s_lmdbslab.Slab.anit(path)
        self.formcounts = await self.layrslab.getHotCount('count:forms')

        path = s_common.genpath(self.dirn, 'splices_v2.lmdb')
        self.spliceslab = await s_lmdbslab.Slab.anit(path)

        self.tagabrv = self.layrslab.getNameAbrv('tagabrv')
        self.propabrv = self.layrslab.getNameAbrv('propabrv')

        self.onfini(self.layrslab)
        self.onfini(self.spliceslab)

        self.bybuid = self.layrslab.initdb('bybuid')

        self.bytag = self.layrslab.initdb('bytag', dupsort=True)
        self.byprop = self.layrslab.initdb('byprop', dupsort=True)
        self.byarray = self.layrslab.initdb('byarray', dupsort=True)

        self.countdb = self.layrslab.initdb('counters')

        self.splicelog = s_slabseqn.SlabSeqn(self.spliceslab, 'splices')

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

        ]

        self.canrev = True

    async def getFormCounts(self):
        return self.formcounts.pack()

    @s_cache.memoize(size=10000)
    def getPropAbrv(self, form, prop):
        return self.propabrv.bytsToAbrv(s_msgpack.en((form, prop)))

    async def getAbrvProp(self, abrv):
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

            logger.warning(f'unrecognized storage row: {flag}')

        info = {}

        if ndef:
            info['ndef'] = ndef

        if props:
            info['props'] = props

        if tags:
            info['tags'] = tags

        return info

    async def liftByTag(self, tag, form=None):

        abrv = self.tagabrv.bytsToAbrv(tag.encode())
        if form is not None:
            abrv += self.getPropAbrv(form, None)

        for lkey, buid in self.layrslab.scanByPref(abrv, db=self.bytag):
            yield buid, await self.getStorNode(buid)

    async def liftByTagValu(self, tag, cmpr, valu, form=None):

        abrv = self.tagabrv.bytsToAbrv(tag.encode())
        if form is not None:
            abrv += self.getPropAbrv(form, None)

        filt = StorTypeTag.getTagFilt(cmpr, valu)

        for lkey, buid in self.layrslab.scanByPref(abrv, db=self.bytag):
            # filter based on the ival value before lifting the node...
            valu = self.getNodeTag(buid, tag)
            if filt(valu):
                yield buid, await self.getStorNode(buid)

    #async def liftByTagProp(self, form, tag, prop):
    #async def liftByTagPropValu(self, form, tag, prop, cmprvals):

    async def liftByProp(self, form, prop):
        abrv = self.getPropAbrv(form, prop)
        for lkey, buid in self.layrslab.scanByPref(abrv, db=self.byprop):
            yield buid, await self.getStorNode(buid)

    # NOTE: form vs prop valu lifting is differentiated to allow merge sort
    async def liftByFormValu(self, form, cmprvals):
        abrv = self.getPropAbrv(form, None)
        for cmpr, valu, kind in cmprvals:
            for buid in self.stortypes[kind].lift(form, None, cmpr, valu):
                yield buid, await self.getStorNode(buid)

    async def liftByPropValu(self, form, prop, cmprvals):
        for cmpr, valu, kind in cmprvals:
            for buid in self.stortypes[kind].lift(form, prop, cmpr, valu):
                yield buid, await self.getStorNode(buid)

    async def liftByUnivValu(self, univ, cmprvals):
        for cmpr, valu, kind in cmprvals:
            for buid in self.stortypes[kind].lift(None, univ, cmpr, valu):
                yield buid, await self.getStorNode(buid)

    async def storNodeEdits(self, edits, meta):
        return [await self.storNodeEdit(e, meta) for e in edits]

    async def storNodeEdit(self, edit, meta):
        '''
        Execute a series of storage operations for the given node.
        '''
        buid, info = edit

        form = info.get('form')

        isnew = False

        storvalu = info.get('valu')
        if storvalu is not None:
            valu, stortype = storvalu
            isnew = await self._setNodeForm(buid, form, valu, stortype)

        onnew = info.get('onadd')

        propstodo = list(info.get('setprops', ()))

        if isnew and onnew is not None:
            propstodo.extend(onnew.get('setprops', ()))

        props = {}
        for propname, propvalu, stortype in propstodo:
            await self._setNodeProp(buid, form, propname, propvalu, stortype)
            props[propname] = propvalu

        for tagname, tagvalu in info.get('settags', ()):
            await self._setNodeTag(buid, form, tagname, tagvalu)

        delprops = info.get('delprops')
        if delprops is not None:
            for propname in delprops:
                await self._delNodeProp(buid, form, propname)

        # delete operations...
        if info.get('delnode'):
            await self._delNodeForm(buid, form)

        return buid, await self.getStorNode(buid)

    async def _setNodeForm(self, buid, form, valu, stortype):

        fenc = form.encode()

        byts = s_msgpack.en((form, valu, stortype))
        if not self.layrslab.put(buid + b'\x00', byts, db=self.bybuid, overwrite=False):
            return False

        abrv = self.getPropAbrv(form, None)
        for indx in self.getStorIndx(stortype, valu):
            self.layrslab.put(abrv + indx, buid, db=self.byprop)

        self.formcounts.inc(fenc)
        self.splicelog.append((SPLICE_NODE_ADD, buid, (form, valu, stortype), {}))
        return True

    async def _delNodeForm(self, buid, form):

        byts = self.layrslab.pop(buid + b'\x00', db=self.bybuid)
        if byts is None:
            return False

        form, valu, stortype = s_msgpack.un(byts)

        fenc = form.encode()

        abrv = self.getPropAbrv(form, None)
        for indx in self.getStorIndx(stortype, valu):
            self.layrslab.delete(abrv + indx, buid, db=self.byprop)

        self.formcounts.inc(fenc, valu=-1)
        self.splicelog.append((SPLICE_NODE_DEL, buid, (form, valu, stortype), {}))
        return True

    async def _setNodeProp(self, buid, form, prop, valu, stortype):

        oldv = None
        penc = prop.encode()
        bkey = buid + b'\x01' + penc

        abrv = self.getPropAbrv(form, prop)
        univabrv = None

        if penc[0] == 46: # '.' to detect universal props (as quickly as possible)
            univabrv = self.getPropAbrv(None, prop)

        oldb = self.layrslab.replace(bkey, s_msgpack.en((valu, stortype)), db=self.bybuid)
        if oldb is not None:
            oldv, oldt = s_msgpack.un(oldb)
            for oldi in self.getStorIndx(oldt, oldv):
                self.layrslab.delete(abrv + oldi, buid, db=self.byprop)
                if univabrv is not None:
                    self.layrslab.delete(univabrv + indx, buid, db=self.byprop)

        if stortype & STOR_FLAG_ARRAY:

            realtype = stortype & 0x7fff
            for aval in valu:
                for indx in self.getStorIndx(realtype, aval):
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

        self.splicelog.append((SPLICE_PROP_SET, buid, (form, prop, valu, oldv, stortype), {}))

    async def _delNodeProp(self, buid, form, prop):

        penc = prop.encode()
        bkey = buid + b'\x01' + penc

        abrv = self.getPropAbrv(form, prop)
        univabrv = None

        if penc[0] == 46: # '.' to detect universal props (as quickly as possible)
            univabrv = self.propabrv.bytsToAbrv(penc)

        byts = self.layrslab.pop(bkey, db=self.bybuid)
        if byts is None:
            return False

        valu, stortype = s_msgpack.un(byts)

        if stortype & STOR_FLAG_ARRAY:

            realtype = stortype & 0xefff

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

        self.splicelog.append((SPLICE_PROP_DEL, buid, (form, prop, valu, stortype), {}))

    async def _setNodeTag(self, buid, form, tag, valu):

        oldv = None
        tenc = tag.encode()

        tagabrv = self.tagabrv.bytsToAbrv(tenc)
        formabrv = self.getPropAbrv(form, None)

        self.layrslab.put(tagabrv + formabrv, buid, db=self.bytag)

        oldb = self.layrslab.replace(buid + b'\x02' + tenc, s_msgpack.en(valu), db=self.bybuid)
        if oldb is not None:
            oldv = s_msgpack.un(oldb)

        self.splicelog.append((SPLICE_TAG_SET, buid, (form, tag, valu, oldv), {}))

        # TODO counters / metrics / splices

    def getStorIndx(self, stortype, valu):

        pref = stortype.to_bytes(1, 'big')

        if stortype & 0x8000:

            realtype = stortype & 0xefff
            realpref = stortype.to_bytes(1, 'big')

            retn = []
            [retn.extend(self.getStorIndx(realtype, aval)) for aval in valu]
            return retn

        return self.stortypes[stortype].indx(valu)

    async def iterPropRows(self, form, prop):

        fenc = form.encode()
        penc = prop.encode()

        abrv = self.getPropAbrv(form, prop)

        for lval, buid in self.layrslab.scanByPref(abrv, db=self.byprop):
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

        for lval, buid in self.layrslab.scanByPref(abrv, db=self.byprop):
            bkey = buid + b'\x01' + penc
            byts = self.layrslab.get(bkey, db=self.bybuid)

            await asyncio.sleep(0)

            if byts is None:
                continue

            valu, stortype = s_msgpack.un(byts)
            yield buid, valu

    #async def _storFireSplices(self, splices):
        #'''
        #Fire events, windows, etc for splices.
        #'''
        #indx = await self._storSplices(splices)

        #self.spliced.set()
        #self.spliced.clear()

        #items = [(indx + i, s) for (i, s) in enumerate(splices)]

        # go fast and protect against edit-while-iter issues
        #[(await wind.puts(items)) for wind in tuple(self.windows)]

        #[(await self.dist(s)) for s in splices]

    #async def _storSplices(self, splices):  # pragma: no cover
        #'''
        #Store the splices into a sequentially accessible storage structure.
        #Returns the indx of the first splice stored.
        #'''
        #raise NotImplementedError

    #async def _liftByFormRe(self, oper):

        #form, query, info = oper[1]

        #regx = regex.compile(query)

        #count = 0

        #async for buid, valu in self.iterFormRows(form):

            #count += 1
            #if not count % FAIR_ITERS:
                #await asyncio.sleep(0)  # give other tasks a chance

            # for now... but maybe repr eventually?
            #if not isinstance(valu, str):
                #valu = str(valu)

            #if not regx.search(valu):
                #continue

            #yield (buid,)

    #async def _liftByUnivRe(self, oper):

        #prop, query, info = oper[1]
#
        #regx = regex.compile(query)

        #count = 0

        #async for buid, valu in self.iterUnivRows(prop):

            #count += 1
            #if not count % FAIR_ITERS:
                #await asyncio.sleep(0)  # give other tasks a chance

            # for now... but maybe repr eventually?
            #if not isinstance(valu, str):
                #valu = str(valu)

            #if not regx.search(valu):
                #continue

            #yield (buid,)

    #async def _liftByPropRe(self, oper):
        # ('regex', (<form>, <prop>, <regex>, info))
        #form, prop, query, info = oper[1]

        #regx = regex.compile(query)

        #count = 0

        # full table scan...
        #async for buid, valu in self.iterPropRows(form, prop):

            #count += 1
            #if not count % FAIR_ITERS:
                #await asyncio.sleep(0)  # give other tasks a chance

            # for now... but maybe repr eventually?
            #if not isinstance(valu, str):
                #valu = str(valu)

            #if not regx.search(valu):
                #continue

            # yield buid, form, prop, valu
            #yield (buid,)

    # TODO: Hack until we get interval trees pushed all the way through
    def _cmprIval(self, item, othr):

        if othr[0] >= item[1]:
            return False

        if othr[1] <= item[0]:
            return False

        return True

    #async def _liftByPropIval(self, oper):
        #form, prop, ival = oper[1]
        #count = 0
        #async for buid, valu in self.iterPropRows(form, prop):
            #count += 1

            #if not count % FAIR_ITERS:
                #await asyncio.sleep(0)

            #if type(valu) not in (list, tuple):
                #continue

            #if len(valu) != 2:
                #continue

            #if not self._cmprIval(ival, valu):
                #continue

            #yield (buid,)

    #async def _liftByUnivIval(self, oper):
        #_, prop, ival = oper[1]
        #count = 0
        #async for buid, valu in self.iterUnivRows(prop):
            #count += 1

            #if not count % FAIR_ITERS:
                #await asyncio.sleep(0)

            #if type(valu) not in (list, tuple):
                #continue

            #if len(valu) != 2:
                #continue

            #if not self._cmprIval(ival, valu):
                #continue

            #yield (buid,)

    #async def _liftByFormIval(self, oper):
        #_, form, ival = oper[1]
        #count = 0
        #async for buid, valu in self.iterFormRows(form):
            #count += 1

            #if not count % FAIR_ITERS:
                #await asyncio.sleep(0)

            #if type(valu) not in (list, tuple):
                #continue

            #if len(valu) != 2:
                #continue

            #if not self._cmprIval(ival, valu):
                #continue

            #yield (buid,)

    # The following functions are abstract methods that must be implemented by a subclass

    #async def getModelVers(self):  # pragma: no cover
        #raise NotImplementedError

    async def getModelVers(self):

        byts = self.layrslab.get(b'layer:model:version')
        if byts is None:
            return (-1, -1, -1)

        return s_msgpack.un(byts)

    async def setModelVers(self, vers):
        byts = s_msgpack.en(vers)
        self.layrslab.put(b'layer:model:version', byts)

    #async def setModelVers(self, vers):  # pragma: no cover
        #raise NotImplementedError

    #async def setOffset(self, iden, offs):  # pragma: no cover
        #raise NotImplementedError

    #async def getOffset(self, iden):  # pragma: no cover
        #raise NotImplementedError

    #async def abort(self):  # pragma: no cover
        #raise NotImplementedError

    #async def getBuidProps(self, buid):  # pragma: no cover
        #raise NotImplementedError

    #async def _storPropSet(self, oper):  # pragma: no cover
        #raise NotImplementedError

    #async def _storTagPropSet(self, oper): # pragma: no cover
        #raise NotImplementedError

    #async def _storTagPropDel(self, oper): # pragma: no cover
        #raise NotImplementedError

    #async def _storBuidSet(self, oper):  # pragma: no cover
        #raise NotImplementedError

    #async def _storPropDel(self, oper):  # pragma: no cover
        #raise NotImplementedError

    #async def _liftByIndx(self, oper):  # pragma: no cover
        #raise NotImplementedError

    #async def _liftByTagProp(self, oper): # pragma: no cover
        #raise NotImplementedError

    #async def iterFormRows(self, form):  # pragma: no cover
        #'''
        #Iterate (buid, valu) rows for the given form in this layer.
        #'''
        #for x in (): yield x
        #raise NotImplementedError

    #async def hasTagProp(self, name): # pragma: no cover
        #raise NotImplementedError

    #async def iterPropRows(self, form, prop):  # pragma: no cover
        #'''
        #Iterate (buid, valu) rows for the given form:prop in this layer.
        #'''
        #for x in (): yield x
        #raise NotImplementedError

    #async def iterUnivRows(self, prop):  # pragma: no cover
        #'''
        #Iterate (buid, valu) rows for the given universal prop
        #'''
        #for x in (): yield x
        #raise NotImplementedError

    #async def stat(self):  # pragma: no cover
        #raise NotImplementedError

    #async def splices(self, offs, size):  # pragma: no cover
        #for x in (): yield x
        #raise NotImplementedError

    #async def syncSplices(self, offs):  # pragma: no cover
        #'''
        #Yield (offs, mesg) tuples from the given offset.

        #Once caught up with storage, yield them in realtime.
        #'''
        #for x in (): yield x
        #raise NotImplementedError

    #async def getNodeNdef(self, buid):  # pragma: no cover
        #raise NotImplementedError

    #def migrateProvPre010(self, slab):  # pragma: no cover
        #raise NotImplementedError

    #async def delUnivProp(self, propname, info=None): # pragma: no cover
        #'''
        #Bulk delete all instances of a universal prop.
        #'''
        #raise NotImplementedError

    #async def delFormProp(self, formname, propname, info=None): # pragma: no cover
        #'''
        #Bulk delete all instances of a form prop.
        #'''

    #async def setNodeData(self, buid, name, item): # pragma: no cover
        #raise NotImplementedError

    #async def getNodeData(self, buid, name, defv=None): # pragma: no cover
        #raise NotImplementedError

    #async def iterNodeData(self, buid): # pragma: no cover
        #for x in (): yield x
        #raise NotImplementedError

    async def trash(self):
        '''
        Delete the underlying storage
        '''
        await s_hive.AuthGater.trash(self)
        shutil.rmtree(self.dirn, ignore_errors=True)

class LayerStorage(s_base.Base):
    '''
    An LayerStorage acts as a factory instance for Layers.
    '''

    stortype = 'local'

    async def __anit__(self, info):

        await s_base.Base.__anit__(self)

        self.info = info
        self.iden = info.get('iden')
        self.name = info.get('name')
        self.conf = info.get('conf')

    async def initLayr(self, layrinfo):
        return await Layer.anit(layrinfo)

    async def reqValidLayrConf(self, conf):
        return

    @staticmethod
    async def reqValidConf(conf):
        return
