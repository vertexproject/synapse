import os
import math
import asyncio
import contextlib

import synapse.exc as s_exc
import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.auth as s_auth
import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.nexus as s_nexus
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.spooled as s_spooled

import synapse.tools.service.backup as s_tools_backup

import synapse.tests.utils as s_t_utils

from synapse.tests.utils import alist

from unittest import mock

async def iterPropForm(self, form=None, prop=None):
    bad_valu = [(b'foo', "bar"), (b'bar', ('bar',)), (b'biz', 4965), (b'baz', (0, 56))]
    bad_valu += [(b'boz', 'boz')] * 10
    for buid, valu in bad_valu:
        yield buid, valu

class LayerTest(s_t_utils.SynTest):

    async def test_layer_sodeenvl_sortneutral(self):
        '''
        SodeEnvl must be sort neutral, so a row tuple which ends in one still sorts by whatever key
        follows it. Without __eq__ the tuples are neither equal nor ordered, which silently strips
        the sort of that following key rather than raising.
        '''
        envl0 = s_layer.SodeEnvl('layr00', {})
        envl1 = s_layer.SodeEnvl('layr01', {})

        self.eq(envl0, envl1)
        self.false(envl0 < envl1)
        self.false(envl1 < envl0)

        # a tuple ending in an envl must compare on the earlier elements only
        self.eq((10, b'nid', envl0), (10, b'nid', envl1))
        self.lt((10, b'nid', envl0), (11, b'nid', envl1))

        # so merggenr2( withordr=True ) still resolves a tie by generator order, in both
        # directions. this is what keeps the topmost layer winning a tie in a multi layer lift.
        for reverse in (False, True):
            genrs = [s_common.agen((10, b'nid', envl0)), s_common.agen((10, b'nid', envl1))]
            retn = await s_t_utils.alist(s_common.merggenr2(genrs, reverse=reverse, withordr=True))
            self.eq([0, 1], [ordr for _, ordr in retn])

        # envls stay usable as dict keys, since __hash__ is not dropped by defining __eq__
        self.len(2, {envl0: 'a', envl1: 'b'})

    async def test_layer_verify(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 +#foo.bar ]')

            nid = nodes[0].nid

            await core.nodes('[ ou:org=* :names=(hehe, haha) ]')

            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

            core.getLayer()._testDelTagIndx(nid, 'inet:ip', 'foo')
            core.getLayer()._testDelPropIndx(nid, 'inet:ip', 'asn')

            errors = [e async for e in core.getLayer().verify()]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoTagIndex')
            self.eq(errors[1][0], 'NoTagIndex')
            self.eq(errors[2][0], 'NoPropIndex')

            errors = await core.callStorm('''
                $retn = ()
                for $mesg in $lib.layer.get().verify() {
                    $retn.append($mesg)
                }
                return($retn)
            ''')

            self.len(3, errors)
            self.eq(errors[0][0], 'NoTagIndex')
            self.eq(errors[1][0], 'NoTagIndex')
            self.eq(errors[2][0], 'NoPropIndex')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 +#foo.bar ]')
            nid = nodes[0].nid

            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

            core.getLayer()._testDelTagStor(nid, 'inet:ip', 'foo')

            config = {'scanall': False, 'scans': {'tagindex': {'include': ('foo',)}}}
            errors = [e async for e in core.getLayer().verify(config=config)]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')
            self.eq(errors[1][0], 'NoTagForTagIndex')

            config = {'scanall': False, 'scans': {'tagindex': {'include': ('baz',)}}}
            errors = [e async for e in core.getLayer().verify(config=config)]
            self.len(0, errors)

            errors = [e async for e in core.getLayer().verifyAllTags()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')
            self.eq(errors[1][0], 'NoTagForTagIndex')

            core.getLayer()._testDelPropStor(nid, 'inet:ip', 'asn')
            errors = [e async for e in core.getLayer().verifyByProp('inet:ip', 'asn')]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')

            errors = [e async for e in core.getLayer().verify()]
            self.len(3, errors)

            core.getLayer()._testDelFormValuStor(nid, 'inet:ip')
            errors = [e async for e in core.getLayer().verifyByProp('inet:ip', None)]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 +#foo.bar ]')
            nid = nodes[0].nid

            core.getLayer()._testAddPropIndx(nid, 'inet:ip', 'asn', ('inet:asn', 30))
            errors = [e async for e in core.getLayer().verify()]
            self.len(1, errors)
            self.eq(errors[0][0], 'SpurPropKeyForIndex')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 +#foo ]')
            nid = nodes[0].nid

            await core.nodes('.created | delnode --force')
            self.len(0, await core.nodes('inet:ip=1.2.3.4'))

            core.getLayer()._testAddTagIndx(nid, 'inet:ip', 'foo')
            core.getLayer()._testAddPropIndx(nid, 'inet:ip', 'asn', ('inet:asn', 30))
            errors = [e async for e in core.getLayer().verify()]
            self.eq(errors[0][0], 'NoNodeForTagIndex')
            self.eq(errors[1][0], 'NoNodeForTagIndex')
            self.eq(errors[2][0], 'NoNodeForPropIndex')

        # Smash in a bad stortype into a sode.
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 +#foo ]')
            nid = nodes[0].nid

            layr = core.getLayer()
            sode = layr.getStorNode(nid)
            asn = sode['props']['asn']
            sode['props']['asn'] = (asn[0], 8675309, None)

            layr.dirty[nid] = sode

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoStorTypeForProp')
            self.eq(errors[1][0], 'NoStorTypeForProp')

            sode['props'] = None
            layr.dirty[nid] = sode
            errors = [e async for e in core.getLayer().verify()]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')
            self.eq(errors[1][0], 'NoValuForPropIndex')
            self.eq(errors[2][0], 'NoValuForPropIndex')

        # Check arrays
        async with self.getTestCore() as core:

            layr = core.getLayer()

            nodes = await core.nodes('[ entity:contact=* :names=(foo, bar)]')
            nid = nodes[0].nid

            core.getLayer()._testAddPropArrayIndx(nid, 'entity:contact', 'names', (('entity:name', 'baz'),))

            scanconf = {'autofix': 'index'}
            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(1, errors)
            self.eq(errors[0][0], 'SpurPropArrayKeyForIndex')

            errors = [e async for e in layr.verifyAllProps()]
            self.len(0, errors)

            sode = layr._getStorNode(nid)
            names = sode['props']['names']
            sode['props']['names'] = (names[0], 8675309, None)
            layr.dirty[nid] = sode

            scanconf = {'include': [('entity:contact', 'names')]}
            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoStorTypeForProp')
            self.eq(errors[1][0], 'NoStorTypeForPropArray')
            self.eq(errors[2][0], 'NoStorTypeForPropArray')

            sode = layr._getStorNode(nid)
            names = sode['props']['names']
            sode['props'] = {}
            layr.dirty[nid] = sode

            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')
            self.eq(errors[1][0], 'NoValuForPropArrayIndex')
            self.eq(errors[2][0], 'NoValuForPropArrayIndex')

            sode['props'] = None
            layr.dirty[nid] = sode
            errors = [e async for e in core.getLayer().verify()]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')
            self.eq(errors[1][0], 'NoValuForPropArrayIndex')
            self.eq(errors[2][0], 'NoValuForPropArrayIndex')

            await core.nodes('entity:contact | delnode --force')

            core.getLayer()._testAddPropArrayIndx(nid, 'entity:contact', 'names', (('entity:name', 'foo'),))

            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoNodeForPropIndex')
            self.eq(errors[1][0], 'NoNodeForPropArrayIndex')
            self.eq(errors[2][0], 'NoNodeForPropArrayIndex')

        # test autofix for tagindex verify
        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 +#foo ]')
            nid = nodes[0].nid

            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

            # test autofix=node
            core.getLayer()._testDelTagStor(nid, 'inet:ip', 'foo')
            self.len(0, await core.nodes('inet:ip=1.2.3.4 +#foo'))

            config = {'scans': {'tagindex': {'autofix': 'node'}}}
            errors = [e async for e in core.getLayer().verify(config=config)]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')

            self.len(1, await core.nodes('inet:ip=1.2.3.4 +#foo'))
            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

            # test autofix=index
            core.getLayer()._testDelTagStor(nid, 'inet:ip', 'foo')
            self.len(0, await core.nodes('inet:ip=1.2.3.4 +#foo'))

            config = {'scans': {'tagindex': {'autofix': 'index'}}}
            errors = [e async for e in core.getLayer().verify(config=config)]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')
            self.eq(errors[1][0], 'NoTagForTagIndex')
            self.len(0, await core.nodes('inet:ip=1.2.3.4 +#foo'))
            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

        async with self.getTestCore() as core:
            await core.addTagProp('_score', ('int', {}), {})

            layr = core.getLayer()
            errors = [e async for e in layr.verifyAllNids()]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllProps()]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(0, errors)

            layr._testAddTagPropIndx(nid, 'inet:ip', 'foo', '_score', 5)

            scanconf = {'include': ['newp']}
            errors = [e async for e in layr.verifyAllTagProps(scanconf=scanconf)]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoNodeForTagPropIndex')
            self.eq(errors[1][0], 'NoNodeForTagPropIndex')
            self.eq(errors[2][0], 'NoNodeForTagPropIndex')

            nodes = await core.nodes('[ inet:ip=1.2.3.4 +#foo:_score=5 ]')
            nid = nodes[0].nid

            layr._testAddTagPropIndx(nid, 'inet:ip', 'foo', '_score', 6)

            scanconf = {'autofix': 'index'}
            errors = [e async for e in layr.verifyAllTagProps(scanconf=scanconf)]
            self.len(4, errors)
            self.eq(errors[0][0], 'SpurTagPropKeyForIndex')
            self.eq(errors[1][0], 'SpurTagPropKeyForIndex')
            self.eq(errors[2][0], 'SpurTagPropKeyForIndex')
            self.eq(errors[3][0], 'SpurTagPropKeyForIndex')

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(0, errors)

            sode = layr._getStorNode(nid)
            score = sode['tagprops']['foo']['_score']
            sode['tagprops']['foo']['_score'] = (score[0], 8675309, None)
            layr.dirty[nid] = sode

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoStorTypeForTagProp')
            self.eq(errors[1][0], 'NoStorTypeForTagProp')

            sode = layr._getStorNode(nid)
            sode['tagprops']['foo'] = {}
            layr.dirty[nid] = sode

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoValuForTagPropIndex')
            self.eq(errors[1][0], 'NoValuForTagPropIndex')

            sode = layr._getStorNode(nid)
            sode['tagprops'] = {}
            layr.dirty[nid] = sode

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoPropForTagPropIndex')
            self.eq(errors[1][0], 'NoPropForTagPropIndex')

            sode = layr._getStorNode(nid)
            sode['tagprops'] = None
            layr.dirty[nid] = sode

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoPropForTagPropIndex')
            self.eq(errors[1][0], 'NoPropForTagPropIndex')

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            await core.nodes('[ test:str=foo +#foo:_score=5 ]')
            await core.nodes('test:str=foo [ -#foo:_score ]', opts={'view': viewiden2})
            await core.nodes('''
            $layr = $lib.layer.get()
            for ($iden, $type, $info) in $layr.getTombstones() {
                $layr.delTombstone($iden, $type, $info)
            }''', opts={'view': viewiden2})

            errors = [e async for e in core.getView(viewiden2).wlyr.verify()]
            self.len(0, errors)

            scanconf = {'autofix': 'newp'}

            with self.raises(s_exc.BadArg):
                errors = [e async for e in layr.verifyAllTags(scanconf=scanconf)]

            with self.raises(s_exc.BadArg):
                errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]

            with self.raises(s_exc.BadArg):
                errors = [e async for e in layr.verifyAllTagProps(scanconf=scanconf)]

    async def test_layer_stortype_hier(self):
        stor = s_layer.StorTypeHier(None, None)

        vals = ['', 'foo', 'foo.bar']

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

    async def test_layer_stortype_ip(self):
        stor = s_layer.StorTypeIpv6(None)

        vals = ('::1', 'fe80::431c:39b2:888:974')

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

        stor = s_layer.StorTypeIPAddr(None)
        with self.raises(s_exc.BadTypeValu):
            stor._getIndxByts((7, 1))

    async def test_layer_stortype_fqdn(self):
        stor = s_layer.StorTypeFqdn(None)

        vals = ('vertex.link', 'www.vertex.link')

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

        longfqdn = '.'.join(('a' * 63,) * 5)
        indx = stor.indx(longfqdn)
        self.eq(s_common.novalu, stor.decodeIndx(indx[0]))

    async def test_layer_stortype_utf8(self):
        size = s_layer.LAYER_UTF8_INDEX_SIZE

        stor = s_layer.StorTypeUtf8(None)
        for valu in ('', 'foo', 'a' * (size - 1)):
            self.eq(valu, stor.decodeIndx(stor.indx(valu)[0]))

        # values longer than the index size retain size bytes plus an 8 byte
        # appended hash and can no longer be decoded from the index
        longval = 'a' * (size + 10)
        indx = stor.indx(longval)[0]
        self.len(size + 8, indx)
        self.eq(s_common.novalu, stor.decodeIndx(indx))

        # distinct values sharing a prefix get distinct indexes via the hash
        self.ne(stor.indx('a' * size + 'x')[0], stor.indx('a' * size + 'y')[0])

        # the text stortype lower-cases its index value
        stor = s_layer.StorTypeText(None)
        self.eq(b'foo', stor.indx('FoO')[0])

    async def test_layer_stortype_hugenum(self):
        stor = s_layer.StorTypeHugeNum(self, None)

        vals = ['-99999.9', '-0.00000000000000000001', '-42.1', '0', '0.000001', '42.1',
                '99999.9', '730750818665451459101842', '-730750818665451459101842',
                '730750818665451459101841.000000000000000000000001']

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

    async def test_layer_stortype_ival(self):
        stor = s_layer.StorTypeIval(self)

        vals = [(2000, 2020, 20), (1960, 1970, 10),
                (stor.timetype.unksize, 2020, stor.unkdura),
                (2020, stor.timetype.futsize, stor.futdura)]

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

    async def test_layer_stortype_latlon(self):
        stor = s_layer.StorTypeLatLon(self)

        vals = [(0.0, 0.0), (89.2, -140.2)]

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

    async def test_layer_stortype_int(self):
        async with self.getTestCore() as core:

            layr = core.view.layers[0]
            tmpdb = layr.layrslab.initdb('temp', dupsort=True)

            stor = s_layer.StorTypeInt(layr, s_layer.STOR_TYPE_I32, 8, True)
            minv = -2 ** 63 + 1
            maxv = 2 ** 63
            vals = [minv, 0, 1, maxv]

            indxby = s_layer.IndxBy(layr, b'', tmpdb)

            for key, val in ((stor.indx(v), s_msgpack.en(v)) for v in vals):
                await layr.layrslab.put(key[0], val, db=tmpdb)

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '=', minv)]
            self.eq(retn, [minv])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '=', maxv)]
            self.eq(retn, [maxv])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<', minv + 1)]
            self.eq(retn, [minv])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>', maxv - 1)]
            self.eq(retn, [maxv])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<=', minv)]
            self.eq(retn, [minv])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>=', maxv)]
            self.eq(retn, [maxv])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, 'range=', (minv, maxv))]
            self.eq(retn, vals)

            # Should get no results instead of overflowing
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '=', minv - 1)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '=', maxv + 1)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<', minv)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>', maxv)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<=', minv - 1)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>=', maxv + 1)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, 'range=', (minv - 2, minv - 1))]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, 'range=', (maxv + 1, maxv + 2))]
            self.eq(retn, [])

            # Value is out of range but there are still valid results
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<', maxv + 2)]
            self.eq(retn, vals)

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>', minv - 2)]
            self.eq(retn, vals)

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<=', maxv + 1)]
            self.eq(retn, vals)

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>=', minv - 1)]
            self.eq(retn, vals)

            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, 'range=', (minv - 1, maxv + 1))]
            self.eq(retn, vals)

    async def test_layer_stortype_float(self):
        async with self.getTestCore() as core:

            layr = core.view.layers[0]
            tmpdb = layr.layrslab.initdb('temp', dupsort=True)

            stor = s_layer.StorTypeFloat(layr, s_layer.STOR_TYPE_FLOAT64, 8)
            vals = [math.nan, -math.inf, -99999.9, -0.0000000001, -42.1, -0.0, 0.0, 0.000001, 42.1, 99999.9, math.inf]

            indxby = s_layer.IndxBy(layr, b'', tmpdb)

            for key, val in ((stor.indx(v), s_msgpack.en(v)) for v in vals):
                await layr.layrslab.put(key[0], val, db=tmpdb)
                self.eqOrNan(s_msgpack.un(val), stor.decodeIndx(key[0]))

            # = -99999.9
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '=', -99999.9)]
            self.eq(retn, [-99999.9])

            # <= -99999.9
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<=', -99999.9)]
            self.eq(retn, [-math.inf, -99999.9])

            # < -99999.9
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<', -99999.9)]
            self.eq(retn, [-math.inf])

            # > 99999.9
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>', 99999.9)]
            self.eq(retn, [math.inf])

            # >= 99999.9
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>=', 99999.9)]
            self.eq(retn, [99999.9, math.inf])

            # <= 0.0
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<=', 0.0)]
            self.eq(retn, [-math.inf, -99999.9, -42.1, -0.0000000001, -0.0, 0.0])

            # >= -0.0
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>=', -0.0)]
            self.eq(retn, [-0.0, 0.0, 0.000001, 42.1, 99999.9, math.inf])

            # >= -42.1
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>=', -42.1)]
            self.eq(retn, [-42.1, -0.0000000001, -0.0, 0.0, 0.000001, 42.1, 99999.9, math.inf])

            # > -42.1
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '>', -42.1)]
            self.eq(retn, [-0.0000000001, -0.0, 0.0, 0.000001, 42.1, 99999.9, math.inf])

            # < 42.1
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<', 42.1)]
            self.eq(retn, [-math.inf, -99999.9, -42.1, -0.0000000001, -0.0, 0.0, 0.000001])

            # <= 42.1
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, '<=', 42.1)]
            self.eq(retn, [-math.inf, -99999.9, -42.1, -0.0000000001, -0.0, 0.0, 0.000001, 42.1])

            # -42.1 to 42.1
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, 'range=', (-42.1, 42.1))]
            self.eq(retn, [-42.1, -0.0000000001, -0.0, 0.0, 0.000001, 42.1])

            # 1 to 42.1
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, 'range=', (1.0, 42.1))]
            self.eq(retn, [42.1])

            # -99999.9 to -0.1
            retn = [s_msgpack.un(valu[1]) async for valu in stor.indxBy(indxby, 'range=', (-99999.9, -0.1))]
            self.eq(retn, [-99999.9, -42.1])

            # <= NaN
            await self.agenraises(s_exc.NotANumberCompared, stor.indxBy(indxby, '<=', math.nan))

            # >= NaN
            await self.agenraises(s_exc.NotANumberCompared, stor.indxBy(indxby, '>=', math.nan))

            # 1.0 to NaN
            await self.agenraises(s_exc.NotANumberCompared, stor.indxBy(indxby, 'range=', (1.0, math.nan)))

    async def test_layer_stortype_guid(self):
        stor = s_layer.StorTypeGuid(None)

        vals = (s_common.guid(valu=42), '0' * 32, 'f' * 32)

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

    async def test_layer_nodeedits_created(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:int=1 :loc=us ]')
            created00 = nodes[0].get('.created')
            self.nn(created00)

            layr = core.getLayer()

            editlist00 = [nes async for nes in layr.iterLayerNodeEdits()]
            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # meta used for .created
            await asyncio.sleep(0.01)
            await layr.saveNodeEdits(editlist00, {'time': created00})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            self.propeq(nodes[0], '.created', created00)

            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # If meta is not specified .created gets populated to now
            await asyncio.sleep(0.01)
            await layr.saveNodeEdits(editlist00, {})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            created01 = nodes[0].get('.created')
            self.gt(created01, created00)

            # edits with the same node has the same .created
            await asyncio.sleep(0.01)
            nodes = await core.nodes('[ test:int=1 ]')
            self.propeq(nodes[0], '.created', created01)

            nodes = await core.nodes('[ test:int=1 :loc=us +#foo]')
            self.propeq(nodes[0], '.created', created01)

            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # Tests for behavior of storing nodeedits directly prior to using meta (i.e. meta['time'] != .created)
            # .created is a MINTIME therefore earlier value wins, which is typically meta
            created02 = s_time.parse('1990-10-10 12:30')
            await layr.saveNodeEdits(editlist00, {'time': created02})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            self.propeq(nodes[0], '.created', created02)

            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # meta could be after .created for manual store operations
            created03 = s_time.parse('2050-10-10 12:30')
            await layr.saveNodeEdits(editlist00, {'time': created03})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            self.propeq(nodes[0], '.created', created03)

    async def test_layer_nodeedits(self):

        async with self.getTestCoreAndProxy() as (core0, prox0):

            etime = await core0.callStorm('return($lib.layer.get().edited())')
            self.none(etime)

            nodelist0 = []
            nodes = await core0.nodes('[ test:str=foo ]')
            nodelist0.extend(nodes)
            nodes = await core0.nodes('[ test:int=1 :seen=(2012,2014) +#foo.bar=(2012, 2014) ]')
            nodelist0.extend(nodes)

            nodelist0 = [node.pack() for node in nodelist0]

            editlist = []
            async for offs, nodeedits, meta in core0.getLayer().syncNodeEdits(0, wait=False, compat=True):
                editlist.append(nodeedits)

            etime = await core0.callStorm('return($lib.layer.get().edited())')
            self.nn(etime)
            self.gt(etime, s_time.parse('2020-01-01'))

            async with self.getTestCore() as core1:

                url = core1.getLocalUrl('*/layer')
                offs = await core1.getNexsIndx()

                async with await s_telepath.openurl(url) as layrprox:
                    for nodeedits in editlist:
                        self.nn(await layrprox.saveNodeEdits(nodeedits, {}, compat=True))

                    nodelist1 = []
                    nodelist1.extend(await core1.nodes('test:str'))
                    nodelist1.extend(await core1.nodes('test:int'))

                    nodelist1 = [node.pack() for node in nodelist1]

                    # metadata is cortex local and won't match
                    for node in nodelist0:
                        node[1].pop('meta')

                    for node in nodelist1:
                        node[1].pop('meta')

                    self.eq(nodelist0, nodelist1)

                    self.len(4, await alist(layrprox.syncNodeEdits(0, wait=False)))

                layr = core1.view.layers[0]

            # Force an edit to be added while constructing a Window
            orig = s_layer.Layer.getNodeEditWindow

            @contextlib.asynccontextmanager
            async def slowwindow(self):
                await core0.nodes('[ test:str=bar ]')
                async with orig(self) as wind:
                    await core0.nodes('[ test:str=baz ]')
                    yield wind

            with mock.patch('synapse.lib.layer.Layer.getNodeEditWindow', slowwindow):
                genr = core0.getLayer().syncNodeEdits(0, wait=True, compat=True, withmeta=True)
                for edit in editlist:
                    offs, nodeedits, meta = await anext(genr)

                    self.eq(edit, nodeedits)
                    self.eq(core0.auth.rootuser.iden, meta.get('user'))

                offs, nodeedits, meta = await anext(genr)
                self.eq(6, offs)
                self.eq(['test:str', 'bar'], nodeedits[0][:2])

                offs, nodeedits, meta = await anext(genr)
                self.eq(7, offs)
                self.eq(['test:str', 'baz'], nodeedits[0][:2])

                # Once we've caught back up to the end of the nexus log, we shouldn't get a duplicate from the window
                task = core0.schedCoro(anext(genr))
                await core0.nodes('[ test:str=faz ]')

                offs, nodeedits, meta = await task
                self.eq(8, offs)
                self.eq(['test:str', 'faz'], nodeedits[0][:2])

                await genr.aclose()

            await core0.addTagProp('_score', ('int', {}), {})

            q = '[ test:int=1 +#tp:_score=5 +(refs)> { test:str=foo } ] $node.data.set(foo, bar)'
            nodes = await core0.nodes(q)
            intnid = s_common.int64un(nodes[0].nid)
            tstrnid = s_common.int64un((await core0.nodes('test:str=foo'))[0].nid)

            layr = core0.getLayer()

            noedit = [(None, 'test:int', [(s_layer.EDIT_PROP_SET, ('newp', 5, None))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_TAG_DEL, ('newp',))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_TAGPROP_SET, ('tp', '_score', 5, s_layer.STOR_TYPE_I64, None))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_TAGPROP_DEL, ('newp', 'newp'))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_TAGPROP_DEL, ('tp', 'newp'))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_NODEDATA_SET, ('foo', 'bar'))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_EDGE_ADD, ('refs', tstrnid))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            await core0.trimNexsLog()
            etime = await core0.callStorm('return($lib.layer.get().edited())')
            self.nn(etime)
            self.gt(etime, s_time.parse('2020-01-01'))

            # test remoteToLocalEdits with a non-node-add first edit for an unknown node
            rnodeedits = [
                ('test:str', 'remotenewp', [(s_layer.EDIT_PROP_SET, ('tick', 0, s_layer.STOR_TYPE_I64, None))]),
            ]
            ledits = await layr.remoteToLocalEdits(rnodeedits)
            self.len(1, ledits)
            self.nn(ledits[0][0])

            # test remoteToLocalEdits with an edge edit referencing an existing n2 node
            rnodeedits = [
                ('test:str', 'remotenewp2', [
                    (s_layer.EDIT_NODE_ADD, (1, s_layer.STOR_TYPE_UTF8, None)),
                    (s_layer.EDIT_EDGE_ADD, ('refs', ('test:str', 'foo'))),
                ]),
            ]
            ledits = await layr.remoteToLocalEdits(rnodeedits)
            self.len(1, ledits)
            self.len(2, ledits[0][2])

            # test localToRemoteEdits skips nodeedits whose n1 nid has no ndef mapping
            fakenid = 0xdeadbeefcafe
            lnodeedits = [(fakenid, 'test:str', [(s_layer.EDIT_NODE_ADD, ('newp', s_layer.STOR_TYPE_UTF8, None))])]
            self.eq([], await layr.localToRemoteEdits(lnodeedits))

            # test localToRemoteEdits skips edge edits whose n2 nid has no ndef mapping
            lnodeedits = [(intnid, 'test:int', [(s_layer.EDIT_EDGE_ADD, ('refs', fakenid))])]
            self.eq([], await layr.localToRemoteEdits(lnodeedits))

            lnodeedits = [(intnid, 'test:int', [(s_layer.EDIT_EDGE_DEL, ('refs', fakenid))])]
            self.eq([], await layr.localToRemoteEdits(lnodeedits))

            # test localToRemoteEdits resolves edge edits with valid n2 nids to ndef
            lnodeedits = [(intnid, 'test:int', [(s_layer.EDIT_EDGE_ADD, ('refs', tstrnid))])]
            redits = await layr.localToRemoteEdits(lnodeedits)
            self.len(1, redits)
            self.eq(redits[0][:2], ('test:int', 1))
            self.eq(redits[0][2], [(s_layer.EDIT_EDGE_ADD, ('refs', ('test:str', 'foo')))])

    async def test_layer_stornodeedits_nonexus(self):
        # test for migration methods that store nodeedits bypassing nexus

        async with self.getTestCore() as core0:

            layer0 = core0.getLayer()

            await core0.nodes('[ test:str=foo ]')
            self.len(1, await core0.nodes('.created'))

            nodeedits = [ne async for ne in layer0.iterLayerNodeEdits()]
            self.len(1, nodeedits)

            await core0.nodes('.created | delnode --force')

            flatedits = await layer0._storNodeEdits(nodeedits, {'time': s_common.now()}, None)
            self.len(1, flatedits)

            self.len(1, await core0.nodes('.created'))

            url = core0.getLocalUrl('*/layer')
            async with await s_telepath.openurl(url) as layrprox:
                async for nedit in layrprox.iterLayerNodeEdits(meta=True):
                    break

                metaedit = [edit for edit in nedit[2] if edit[0] == s_layer.EDIT_META_SET]
                self.len(1, metaedit)

                # Force replaying a meta edit for coverage
                nid = nedit[0]
                sode = layer0.getStorNode(s_common.int64en(nid))
                self.eq((), await layer0._editMetaSet(nid, None, metaedit[0], sode, None))

            user = await core0.auth.addUser('lowuser')
            url = core0.getLocalUrl(user='lowuser', share='*/layer')
            async with await s_telepath.openurl(url) as layrprox:

                with self.raises(s_exc.AuthDeny):
                    await layrprox.storNodeEdits(nodeedits)

                await user.addRule((True, ('layer', 'write')), gateiden=layer0.iden)

                await layrprox.storNodeEdits(nodeedits)

            # _saveNodeEditsFollower (the non-leader edit-forward path) returns
            # the leader's result directly when the forwarded saveLayerNodeEdits
            # answers non-None, rather than waiting on the response future.
            class Proxy:
                async def saveLayerNodeEdits(self, iden, edits, meta, waitiden=None):
                    return ('offs', ['appliededit'])

            retn = await layer0._saveNodeEditsFollower(Proxy(), (), {})
            self.eq(('offs', ['appliededit']), retn)

    async def test_layer_tombstone(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'verbs': ('_foo', '_bar')}}
            await core.nodes('for $verb in $verbs { $lib.model.ext.addEdge(*, $verb, *, ({})) }', opts=opts)

            async def checkempty(opts=None):
                nodes = await core.nodes('inet:ip=1.2.3.4', opts=opts)
                self.len(1, nodes)
                self.none(nodes[0].get('asn'))
                self.none(nodes[0].get('#foo.tag'))
                self.none(nodes[0].getTagProp('bar.tag', '_score'))

                self.len(0, await core.nodes('inet:ip=1.2.3.4 -(_bar)> *', opts=opts))
                self.len(0, await core.nodes('inet:ip=1.2.3.4 <(_foo)- *', opts=opts))

                self.none(await core.callStorm('inet:ip=1.2.3.4 return($node.data.get(foodata))', opts=opts))
                self.len(0, await core.nodes('yield $lib.lift.byNodeData(foodata)', opts=opts))

            async def hastombs(opts=None):
                q = 'for $tomb in $lib.layer.get().getTombstones() { $lib.print($tomb) }'
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint("('inet:ip', 'asn')", msgs)
                self.stormIsInPrint("foo.tag", msgs)
                self.stormIsInPrint("'bar.tag', '_score'", msgs)
                self.stormIsInPrint("'_bar'", msgs)
                self.stormIsInPrint("'_foo'", msgs)
                self.stormIsInPrint("'foodata'", msgs)

            async def notombs(opts=None):
                q = 'for $tomb in $lib.layer.get().getTombstones() { $lib.print($tomb) }'
                msgs = await core.stormlist(q, opts=opts)
                self.len(0, [m for m in msgs if m[0] == 'print'])

            await core.addTagProp('_score', ('int', {}), {})

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            addq = '''[
            inet:ip=1.2.3.4
                :asn=4
                +#foo.tag=2024
                +#bar.tag:_score=5
                +(_bar)> {[ it:dev:str=n1 ]}
                <(_foo)+ {[ it:dev:str=n2 ]}
            ]
            $node.data.set(foodata, bar)
            '''

            delq = '''
            inet:ip=1.2.3.4
            [   -:asn
                -#foo.tag
                -#bar.tag:_score
                -(_bar)> {[ it:dev:str=n1 ]}
                <(_foo)- {[ it:dev:str=n2 ]}
            ]
            $node.data.pop(foodata)
            '''

            nodes = await core.nodes(addq)
            self.len(1, nodes)
            nodeiden = s_common.ehex(nodes[0].nid)

            self.false(await core.callStorm('[ test:str=newp ] return($node.data.has(foodata))'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -:asn ]', opts=viewopts2)
            self.none(nodes[0].get('asn'))

            nodes = await core.nodes('inet:ip=1.2.3.4')
            self.propeq(nodes[0], 'asn', 4)

            nodes = await core.nodes('inet:ip=1.2.3.4 [ :asn=5 ]', opts=viewopts2)
            self.propeq(nodes[0], 'asn', 5)

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -:asn ]', opts=viewopts2)
            self.none(nodes[0].get('asn'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -#foo.tag ]', opts=viewopts2)
            self.none(nodes[0].get('#foo.tag'))

            nodes = await core.nodes('inet:ip=1.2.3.4')
            self.nn(nodes[0].get('#foo.tag'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ +#foo.tag=2020 ]', opts=viewopts2)
            self.nn(nodes[0].get('#foo.tag'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -#foo.tag ]', opts=viewopts2)
            self.none(nodes[0].get('#foo.tag'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -#bar.tag:_score ]', opts=viewopts2)
            self.none(nodes[0].getTagProp('bar.tag', '_score'))

            nodes = await core.nodes('inet:ip=1.2.3.4')
            self.eq(5, nodes[0].getTagProp('bar.tag', '_score'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ +#bar.tag:_score=6 ]', opts=viewopts2)
            self.eq(6, nodes[0].getTagProp('bar.tag', '_score'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -#bar.tag:_score ]', opts=viewopts2)
            self.none(nodes[0].getTagProp('bar.tag', '_score'))

            await core.nodes('inet:ip=1.2.3.4 $node.data.pop(foodata)', opts=viewopts2)

            self.none(await core.callStorm('inet:ip=1.2.3.4 return($node.data.get(foodata))', opts=viewopts2))

            self.len(0, await core.nodes('yield $lib.lift.byNodeData(foodata)', opts=viewopts2))
            self.len(1, await core.nodes('yield $lib.lift.byNodeData(foodata)'))

            await core.nodes('inet:ip=1.2.3.4 $node.data.set(foodata, baz)', opts=viewopts2)
            self.eq('baz', await core.callStorm('inet:ip=1.2.3.4 return($node.data.get(foodata))', opts=viewopts2))

            self.len(1, await core.nodes('yield $lib.lift.byNodeData(foodata)', opts=viewopts2))

            await core.nodes('inet:ip=1.2.3.4 $node.data.pop(foodata)', opts=viewopts2)

            self.none(await core.callStorm('inet:ip=1.2.3.4 return($node.data.get(foodata))', opts=viewopts2))
            self.len(0, await core.nodes('yield $lib.lift.byNodeData(foodata)', opts=viewopts2))

            await core.nodes('inet:ip=1.2.3.4 $node.data.pop(foodata)', opts=viewopts2)

            await core.nodes('inet:ip=1.2.3.4 [ -(_bar)> { it:dev:str=n1 } ]', opts=viewopts2)
            self.len(0, await core.nodes('inet:ip=1.2.3.4 -(_bar)> *', opts=viewopts2))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 -(_bar)> *'))

            await core.nodes('inet:ip=1.2.3.4 [ +(_bar)> { it:dev:str=n1 } ]', opts=viewopts2)
            self.len(1, await core.nodes('inet:ip=1.2.3.4 -(_bar)> *', opts=viewopts2))

            await core.nodes('inet:ip=1.2.3.4 [ -(_bar)> { it:dev:str=n1 } ]', opts=viewopts2)
            self.len(0, await core.nodes('inet:ip=1.2.3.4 -(_bar)> *', opts=viewopts2))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 -(_bar)> *'))

            await core.nodes('inet:ip=1.2.3.4 [ <(_foo)- { it:dev:str=n2 } ]', opts=viewopts2)
            self.len(0, await core.nodes('inet:ip=1.2.3.4 <(_foo)- *', opts=viewopts2))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 <(_foo)- *'))

            await core.nodes('inet:ip=1.2.3.4 [ <(_foo)+ { it:dev:str=n2 } ]', opts=viewopts2)
            self.len(1, await core.nodes('inet:ip=1.2.3.4 <(_foo)- *', opts=viewopts2))

            await core.addTagProp('_score2', ('int', {}), {})
            nodes = await core.nodes('[test:str=multi +#foo:_score=5 +#foo:_score2=6]')
            self.sorteq(('_score', '_score2'), nodes[0].getTagProps('foo'))

            nodes = await core.nodes('test:str=multi [-#foo:_score]')
            self.eq(('_score2',), nodes[0].getTagProps('foo'))

            nodes = await core.nodes('test:str=multi')
            self.eq(('_score2',), nodes[0].getTagProps('foo'))

            await core.nodes('inet:ip=1.2.3.4 [ <(_foo)- { it:dev:str=n2 } ]', opts=viewopts2)
            self.len(0, await core.nodes('inet:ip=1.2.3.4 <(_foo)- *', opts=viewopts2))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 <(_foo)- *'))

            await hastombs(opts=viewopts2)

            q = 'for $edge in $lib.layer.get().getEdgeTombstones() { $lib.print($edge) }'
            msgs = await core.stormlist(q, opts=viewopts2)
            self.stormIsInPrint("(0, '_bar', 6)", msgs)
            self.stormIsInPrint("(7, '_foo', 0)", msgs)

            q = 'for $edge in $lib.layer.get().getEdgeTombstones(_bar) { $lib.print($edge) }'
            msgs = await core.stormlist(q, opts=viewopts2)
            self.stormIsInPrint("(0, '_bar', 6)", msgs)
            self.stormNotInPrint("(7, '_foo', 0)", msgs)

            await view2.merge()
            self.true(await view2.waitfini(timeout=5))
            await checkempty()
            await notombs()
            self.none(core.getView(viewiden2))

            # re-fork: merge consumes the previous view
            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}
            await notombs(opts=viewopts2)

            self.len(1, await core.nodes(addq))

            await core.nodes(delq, opts=viewopts2)
            await hastombs(opts=viewopts2)

            await core.nodes('''
            $layr = $lib.layer.get()
            for ($iden, $type, $info) in $layr.getTombstones() {
                $layr.delTombstone($iden, $type, $info)
            }''', opts=viewopts2)

            await notombs(opts=viewopts2)

            await core.nodes(delq, opts=viewopts2)
            await hastombs(opts=viewopts2)

            await core.nodes('inet:ip=1.2.3.4 | delnode', opts=viewopts2)
            self.len(0, await core.nodes('inet:ip=1.2.3.4', opts=viewopts2))

            await core.nodes('[ inet:ip=1.2.3.4 ] | delnode', opts=viewopts2)
            self.len(0, await core.nodes('inet:ip=1.2.3.4', opts=viewopts2))

            await core.nodes('''
            $layr = $lib.layer.get()
            for ($iden, $type, $info) in $layr.getTombstones() {
                $layr.delTombstone($iden, $type, $info)
            }''', opts=viewopts2)

            await notombs(opts=viewopts2)
            self.len(1, await core.nodes('inet:ip=1.2.3.4', opts=viewopts2))

            await core.nodes(delq, opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 | delnode', opts=viewopts2)
            self.len(0, await core.nodes('inet:ip=1.2.3.4', opts=viewopts2))

            # deleting a node clears its other tombstones
            msgs = await core.stormlist('for $tomb in $lib.layer.get().getTombstones() { $lib.print($tomb) }', opts=viewopts2)

            self.stormIsInPrint("('inet:ip', None)", msgs)
            self.stormNotInPrint("('inet:ip', 'asn')", msgs)
            self.stormNotInPrint("foo.tag", msgs)
            self.stormNotInPrint("'bar.tag', '_score'", msgs)
            self.stormNotInPrint("'_bar'", msgs)
            self.stormNotInPrint("'foodata'", msgs)

            self.len(0, await core.nodes('yield $lib.lift.byNodeData(foodata)', opts=viewopts2))

            await view2.merge()
            self.true(await view2.waitfini(timeout=5))
            await notombs()

            self.len(0, await core.nodes('inet:ip=1.2.3.4'))

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}
            await notombs(opts=viewopts2)

            # use command to merge
            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)

            self.len(3, await core.nodes('diff', opts=viewopts2))
            self.len(1, await core.nodes('diff --prop inet:ip:asn', opts=viewopts2))

            msgs = await core.stormlist('merge --diff', opts=viewopts2)
            self.stormIsInPrint('delete inet:ip:asn', msgs)
            self.stormIsInPrint('delete inet:ip#foo.tag', msgs)
            self.stormIsInPrint('delete inet:ip#bar.tag:_score', msgs)
            self.stormIsInPrint('delete inet:ip DATA foodata', msgs)
            self.stormIsInPrint('delete inet:ip -(_bar)> ', msgs)

            msgs = await core.stormlist('merge --diff --exclude-tags foo.*', opts=viewopts2)
            self.stormNotInPrint('delete inet:ip#foo.tag', msgs)

            msgs = await core.stormlist('merge --diff --exclude-tags bar.*', opts=viewopts2)
            self.stormNotInPrint('delete inet:ip#bar.tag:_score', msgs)

            await core.nodes('for $verb in $lib.range(1001) { $lib.model.ext.addEdge(*, `_a{$verb}`, *, ({})) }')

            await core.nodes('inet:ip for $x in $lib.range(1001) { $node.data.set($x, foo) }')
            await core.nodes('inet:ip for $x in $lib.range(1001) { $node.data.pop($x) }', opts=viewopts2)

            await core.nodes('inet:ip for $x in $lib.range(1001) {[ +(`_a{$x}`)> { it:dev:str=n1 }]}')
            await core.nodes('inet:ip for $x in $lib.range(1001) {[ -(`_a{$x}`)> { it:dev:str=n1 }]}', opts=viewopts2)
            await core.nodes('inet:ip for $x in $lib.range(1001) {[ +(`_a{$x}`)> { it:dev:str=n2 }]}', opts=viewopts2)

            await core.nodes('merge --diff --apply', opts=viewopts2)

            await checkempty()
            await notombs(opts=viewopts2)

            await core.nodes(addq)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force', opts=viewopts2)
            self.len(1, await core.nodes('diff', opts=viewopts2))
            await core.nodes('merge --diff --apply', opts=viewopts2)

            self.len(0, await core.nodes('diff', opts=viewopts2))
            self.len(0, await core.nodes('inet:ip=1.2.3.4'))
            await notombs(opts=viewopts2)

            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force')

            await view2.merge()
            self.true(await view2.waitfini(timeout=5))
            await notombs()

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force', opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force')

            await view2.merge()
            self.true(await view2.waitfini(timeout=5))
            await notombs()

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            # use quorum to merge
            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)

            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('view', 'read')))
            visiopts = {'view': viewiden2, 'user': visi.iden}

            setq = '$lib.view.get().set(quorum, ({"count": 1, "roles": [$lib.auth.roles.byname(all).iden]}))'
            await core.nodes(setq)
            await core.nodes('$lib.view.get().setMergeRequest()', opts=viewopts2)
            await core.nodes('$lib.view.get().setMergeVote()', opts=visiopts)

            self.true(await view2.waitfini(timeout=5))

            await checkempty()

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}
            visiopts = {'view': viewiden2, 'user': visi.iden}

            await core.nodes('inet:ip=1.2.3.4 [ :asn=4 ]')
            await core.nodes('inet:ip=1.2.3.4 [ :place:loc=us -:asn ]', opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 [ -:asn ]')

            await core.nodes('$lib.view.get().setMergeRequest()', opts=viewopts2)
            await core.nodes('$lib.view.get().setMergeVote()', opts=visiopts)

            self.true(await view2.waitfini(timeout=5))

            nodes = await core.nodes('inet:ip=1.2.3.4')
            self.propeq(nodes[0], 'place:loc', 'us')
            self.none(nodes[0].get('asn'))
            await notombs()

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}
            visiopts = {'view': viewiden2, 'user': visi.iden}

            await core.nodes(addq)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force', opts=viewopts2)

            await core.nodes('$lib.view.get().setMergeRequest()', opts=viewopts2)
            await core.nodes('$lib.view.get().setMergeVote()', opts=visiopts)

            self.true(await view2.waitfini(timeout=5))

            self.len(0, await core.nodes('inet:ip=1.2.3.4'))

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}
            visiopts = {'view': viewiden2, 'user': visi.iden}

            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force')

            await core.nodes('$lib.view.get().setMergeRequest()', opts=viewopts2)
            await core.nodes('$lib.view.get().setMergeVote()', opts=visiopts)

            self.true(await view2.waitfini(timeout=5))

            self.len(0, await core.nodes('inet:ip=1.2.3.4'))
            await notombs()

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}
            visiopts = {'view': viewiden2, 'user': visi.iden}

            await core.nodes(addq)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force', opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force')

            await core.nodes('$lib.view.get().setMergeRequest()', opts=viewopts2)
            await core.nodes('$lib.view.get().setMergeVote()', opts=visiopts)

            self.true(await view2.waitfini(timeout=5))

            self.len(0, await core.nodes('inet:ip=1.2.3.4'))
            await notombs()

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            viewiden3 = await core.callStorm('return($lib.view.get().fork().iden)', opts=viewopts2)
            view3 = core.getView(viewiden3)
            viewopts3 = {'view': viewiden3}

            # use movenodes with tombstones
            destlayr = view3.layers[0].iden

            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)
            msgs = await core.stormlist('inet:ip=1.2.3.4 | movenodes', opts=viewopts3)
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip:asn', msgs)
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip#foo.tag', msgs)
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip#bar.tag:_score', msgs)
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip DATA foodata', msgs)
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip -(_bar)>', msgs)

            msgs = await core.stormlist('inet:ip=1.2.3.4 | movenodes --preserve-tombstones', opts=viewopts3)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip:asn', msgs)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip#foo.tag', msgs)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip#bar.tag:_score', msgs)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip DATA foodata', msgs)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip -(_bar)>', msgs)

            await core.nodes('inet:ip=1.2.3.4 it:dev:str=n2 | movenodes --apply', opts=viewopts3)
            await notombs(opts=viewopts2)
            await notombs(opts=viewopts3)
            await checkempty(opts=viewopts3)

            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)

            await core.nodes('inet:ip=1.2.3.4 it:dev:str=n2 | movenodes --apply --preserve-tombstones', opts=viewopts3)
            await notombs(opts=viewopts2)
            await hastombs(opts=viewopts3)

            layr1 = core.getView().layers[0].iden
            layr2 = view2.layers[0].iden

            # moving a full node tomb should clear individual tombstones
            await core.nodes('[ inet:ip=1.2.3.4 it:dev:str=n2 ]')
            await core.nodes('inet:ip=1.2.3.4 it:dev:str=n2 | delnode --force', opts=viewopts2)
            q = f'''
            inet:ip=1.2.3.4 it:dev:str=n2
            | movenodes --precedence {layr2} {layr1} {destlayr} --apply --preserve-tombstones
            '''
            await core.nodes(q, opts=viewopts3)
            await notombs(opts=viewopts2)

            q = 'for $tomb in $lib.layer.get().getTombstones() { $lib.print($tomb) }'
            msgs = await core.stormlist(q, opts=viewopts3)
            self.len(2, [m for m in msgs if m[0] == 'print'])
            self.stormIsInPrint("('inet:ip', None)", msgs)
            self.stormIsInPrint("('it:dev:str', None)", msgs)

            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)
            await core.nodes(addq, opts=viewopts3)

            q = f'''
            inet:ip=1.2.3.4 it:dev:str=n2
            | movenodes --precedence {layr2} {layr1} {destlayr}
            '''
            msgs = await core.stormlist(q, opts=viewopts3)
            self.stormIsInPrint(f'{destlayr} delete {nodeiden} inet:ip:asn', msgs)
            self.stormIsInPrint(f'{destlayr} delete {nodeiden} inet:ip#foo', msgs)
            self.stormIsInPrint(f'{destlayr} delete {nodeiden} inet:ip#bar.tag:_score', msgs)
            self.stormIsInPrint(f'{destlayr} delete {nodeiden} inet:ip DATA foodata', msgs)
            self.stormIsInPrint(f'{destlayr} delete {nodeiden} inet:ip -(_bar)>', msgs)

            q = f'''
            inet:ip=1.2.3.4 it:dev:str=n2
            | movenodes --precedence {layr2} {layr1} {destlayr} --apply
            '''
            await core.nodes(q, opts=viewopts3)
            await notombs(opts=viewopts2)
            await notombs(opts=viewopts3)
            await checkempty(opts=viewopts3)

            await core.nodes(addq)
            await core.nodes('inet:ip=1.2.3.4 it:dev:str=n2 | delnode --force', opts=viewopts2)
            await core.nodes(addq, opts=viewopts3)

            q = f'''
            inet:ip=1.2.3.4 it:dev:str=n2
            | movenodes --precedence {layr2} {layr1} {destlayr}
            '''
            msgs = await core.stormlist(q, opts=viewopts3)
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip', msgs)

            q = f'''
            inet:ip=1.2.3.4 it:dev:str=n2
            | movenodes --preserve-tombstones --precedence {layr2} {layr1} {destlayr}
            '''
            msgs = await core.stormlist(q, opts=viewopts3)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip', msgs)

            q = f'''
            inet:ip=1.2.3.4 it:dev:str=n2
            | movenodes --apply --precedence {layr2} {layr1} {destlayr}
            '''
            await core.nodes(q, opts=viewopts3)
            await notombs(opts=viewopts2)
            await notombs(opts=viewopts3)
            self.len(0, await core.nodes('inet:ip=1.2.3.4', opts=viewopts3))

            await core.nodes(addq)
            await core.nodes('inet:ip=1.2.3.4 it:dev:str=n2 | delnode --force', opts=viewopts2)
            await core.nodes(addq, opts=viewopts3)

            q = f'''
            inet:ip=1.2.3.4 it:dev:str=n2
            | movenodes --apply --preserve-tombstones --precedence {layr2} {layr1} {destlayr}
            '''
            await core.nodes(q, opts=viewopts3)
            await notombs(opts=viewopts2)
            self.len(0, await core.nodes('inet:ip=1.2.3.4', opts=viewopts3))

            q = 'for $tomb in $lib.layer.get().getTombstones() { $lib.print($tomb) }'
            msgs = await core.stormlist(q, opts=viewopts3)
            self.len(2, [m for m in msgs if m[0] == 'print'])
            self.stormIsInPrint("('inet:ip', None)", msgs)
            self.stormIsInPrint("('it:dev:str', None)", msgs)

            await view2.wipeLayer()
            await view3.wipeLayer()

            await core.nodes(addq)

            await core.nodes('inet:ip=1.2.3.4 | delnode --force', opts=viewopts3)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force', opts=viewopts2)
            await core.nodes('merge --diff --apply', opts=viewopts3)
            msgs = await core.stormlist('merge --diff', opts=viewopts3)
            self.stormIsInPrint('delete inet:ip = 1.2.3.4', msgs)

            await core.nodes('syn:tag=foo.tag | delnode', opts=viewopts3)
            msgs = await core.stormlist('merge --diff --exclude-tags foo.*', opts=viewopts3)
            self.stormNotInPrint('delete syn:tag = foo.tag', msgs)

            await view2.wipeLayer()
            await view3.wipeLayer()

            q = '''
            inet:ip=1.2.3.4
            for $edge in $node.edges(reverse=(true)) {
                $lib.print($edge)
            }
            '''
            msgs = await core.stormlist(q, opts=viewopts3)
            self.len(1, [m for m in msgs if m[0] == 'print'])

            await core.nodes('it:dev:str=n2 | delnode', opts=viewopts2)

            msgs = await core.stormlist(q, opts=viewopts3)
            self.len(0, [m for m in msgs if m[0] == 'print'])

            await view2.wipeLayer()
            await core.nodes(delq, opts=viewopts3)

            await checkempty(opts=viewopts3)
            await hastombs(opts=viewopts3)

            q = 'for ($n1, $v, $n2, $tomb) in $lib.layer.get().getEdges() { $lib.print($tomb) }'
            msgs = await core.stormlist(q, opts=viewopts3)
            self.eq(['true', 'true'], [m[1]['mesg'] for m in msgs if m[0] == 'print'])

            q = 'inet:ip for $edge in $lib.layer.get().getEdgesByN1($node.nid) { $lib.print($edge."-1") }'
            msgs = await core.stormlist(q, opts=viewopts3)
            self.eq(['true'], [m[1]['mesg'] for m in msgs if m[0] == 'print'])

            q = 'inet:ip for $edge in $lib.layer.get().getEdgesByN2($node.nid) { $lib.print($edge."-1") }'
            msgs = await core.stormlist(q, opts=viewopts3)
            self.eq(['true'], [m[1]['mesg'] for m in msgs if m[0] == 'print'])

            await view3.merge()
            self.true(await view3.waitfini(timeout=5))

            # tombstones should merge down since they still have values to cover
            await checkempty(opts=viewopts2)
            await hastombs(opts=viewopts2)

            viewiden3 = await core.callStorm('return($lib.view.get().fork().iden)', opts=viewopts2)
            view3 = core.getView(viewiden3)
            viewopts3 = {'view': viewiden3}

            nodes = await core.nodes('inet:ip=1.2.3.4', opts=viewopts3)
            self.false(nodes[0].has('asn'))

            bylayer = await core.callStorm('inet:ip=1.2.3.4 return($node.getByLayer())', opts=viewopts3)

            layr = view2.layers[0].iden
            self.eq(bylayer['props']['asn'], layr)
            self.eq(bylayer['tags']['foo.tag'], layr)
            self.eq(bylayer['tagprops']['bar.tag']['_score'], layr)

            await core.nodes('inet:ip=1.2.3.4 [ <(_foo)- { it:dev:str=n2 } ] | delnode')

            await core.nodes(addq, opts=viewopts2)
            await notombs(opts=viewopts2)

            await core.nodes(delq, opts=viewopts3)
            await checkempty(opts=viewopts3)
            await hastombs(opts=viewopts3)

            await view3.merge()
            self.true(await view3.waitfini(timeout=5))

            # no tombstones should merge since the base layer has no values
            await checkempty(opts=viewopts2)
            await notombs(opts=viewopts2)

            viewiden3 = await core.callStorm('return($lib.view.get().fork().iden)', opts=viewopts2)
            view3 = core.getView(viewiden3)
            viewopts3 = {'view': viewiden3}

            # node re-added above a tombstone is empty
            await core.nodes(addq)
            await core.nodes('[ inet:ip=1.2.3.4 :place:loc=uk ]', opts=viewopts3)
            await core.nodes('inet:ip=1.2.3.4 [ <(_foo)- { it:dev:str=n2 } ] | delnode', opts=viewopts2)

            self.len(0, await core.nodes('inet:ip:place:loc=uk', opts=viewopts3))

            nodes = await core.nodes('[ inet:ip=1.2.3.4 -:place:loc ]', opts=viewopts3)
            await checkempty(opts=viewopts3)

            bylayer = await core.callStorm('inet:ip=1.2.3.4 return($node.getByLayer())', opts=viewopts3)

            layr = view3.layers[0].iden
            self.eq(bylayer, {'ndef': layr, 'props': {'type': layr, 'version': layr}})

            await core.nodes('inet:ip=1.2.3.4 [ +#nomerge ]', opts=viewopts3)
            await core.nodes('merge --diff --apply --only-tags', opts=viewopts3)
            self.len(1, await core.nodes('#nomerge', opts=viewopts3))

            await core.nodes('inet:ip=1.2.3.4 | delnode', opts=viewopts3)
            nodes = await core.nodes('[ inet:ip=1.2.3.4 ]', opts=viewopts3)
            await checkempty(opts=viewopts3)

            # test helpers above a node tombstone
            node = nodes[0]

            self.false(node.has('asn'))
            self.false(node.hasInLayers('asn'))
            self.eq((None, None), node.getWithLayer('asn'))
            self.none(node.getFromLayers('asn'))
            self.none(node.getFromLayers('place:loc', strt=2))

            self.none(node.getTag('foo.tag'))
            self.none(node.getTagFromLayers('foo.tag'))
            self.none(node.getTagFromLayers('newp', strt=2))
            self.false(node.hasTag('foo.tag'))
            self.false(node.hasTagInLayers('foo.tag'))

            self.eq([], node.getTagProps('bar.tag'))
            self.eq([], node.getTagPropsWithLayer('bar.tag'))
            self.false(node.hasTagProp('bar.tag', '_score'))
            self.false(node.hasTagPropInLayers('bar.tag', '_score'))
            self.eq((None, None), node.getTagPropWithLayer('bar.tag', '_score'))

            self.eq(['version', 'type'], list(nodes[0].getProps().keys()))
            self.eq({}, node._getTagsDict())
            self.eq({}, node._getTagPropsDict())

            self.len(0, await core.nodes('#bar.tag:_score', opts=viewopts3))
            self.len(0, await core.nodes('#bar.tag:_score=5', opts=viewopts3))

            await view2.wipeLayer()
            await core.nodes(delq, opts=viewopts2)
            await checkempty(opts=viewopts3)

            await core.nodes('inet:ip [ -(_bar)> {[ it:dev:str=n1 ]} ]', opts=viewopts3)
            nodes = await core.nodes('inet:ip=1.2.3.4', opts=viewopts3)

            # test helpers above individual tombstones
            node = nodes[0]

            self.false(node.hasInLayers('asn'))
            self.none(node.getFromLayers('asn'))
            self.eq((None, None), node.getWithLayer('asn'))

            self.false(node.hasTag('foo.tag'))
            self.false(node.hasTagInLayers('foo.tag'))
            self.none(node.getTagFromLayers('foo.tag'))

            self.eq([], node.getTagProps('bar.tag'))
            self.eq([], node.getTagPropsWithLayer('bar.tag'))
            self.false(node.hasTagProp('bar.tag', '_score'))
            self.false(node.hasTagPropInLayers('bar.tag', '_score'))
            self.false(node.hasTagPropInLayers('foo.tag', '_score'))
            self.eq((None, None), node.getTagPropWithLayer('bar.tag', '_score'))
            self.eq((None, None), node.getTagPropWithLayer('foo.tag', '_score'))

            self.eq(['version', 'type'], list(nodes[0].getProps().keys()))
            self.sorteq(['bar', 'bar.tag', 'foo'], list(node._getTagsDict().keys()))
            self.eq({}, node._getTagPropsDict())

            self.len(0, await alist(node.iterData()))
            self.len(0, await alist(node.iterDataKeys()))
            self.false(0, await node.hasData('foodata'))
            self.none(await core.callStorm('inet:ip=1.2.3.4 return($node.data.pop(foodata))', opts=viewopts3))

            randnid = s_common.int64en(0xdeadbeefcafe)
            self.false((await view3.layers[0].hasNodeData(randnid, 'foodata')))
            self.false((await view3.layers[0].getNodeData(randnid, 'foodata'))[0])

            self.len(0, await alist(view3.getEdges()))
            self.len(0, await alist(view3.layers[1].getEdgeVerbs()))
            self.len(2, await alist(view3.layers[2].getEdgeVerbs()))

            self.len(0, await core.nodes('inet:ip:asn', opts=viewopts3))
            self.len(0, await core.nodes('inet:ip:asn=4', opts=viewopts3))
            self.len(0, await core.nodes('#foo.tag', opts=viewopts3))
            self.len(0, await core.nodes('#foo.tag@=2024', opts=viewopts3))
            self.len(0, await core.nodes('#bar.tag:_score', opts=viewopts3))
            self.len(0, await core.nodes('#bar.tag:_score=5', opts=viewopts3))

            await core.nodes('[ entity:goal=(foo,) :names=(foo, bar) ]')
            await core.nodes('entity:goal=(foo,) [ -:names ]', opts=viewopts2)
            self.len(0, await core.nodes('entity:goal:names*[=foo]', opts=viewopts2))

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.layer.get().delTombstone(newp, newp, newp)')

            with self.raises(s_exc.BadArg):
                opts = {'vars': {'nid': b'\x00'}}
                await core.nodes('$lib.layer.get().delTombstone($nid, newp, newp)', opts=opts)

            with self.raises(s_exc.BadArg):
                opts = {'vars': {'nid': b'\x01' * 8}}
                await core.nodes('$lib.layer.get().delTombstone($nid, newp, newp)', opts=opts)

            await core.nodes('[ test:str=foo +(refs)> {[ test:int=1 test:int=2 test:int=3 ]} ]')
            nodes = await core.nodes('test:str=foo $n=$node -(refs)> * [ <(refs)- { yield $n } ]', opts=viewopts2)
            for node in nodes:
                self.eq(node.pack()[1]['n2verbs'], {})

            self.len(3, await core.nodes('test:str=foo -(refs)> *'))
            self.len(0, await core.nodes('test:str=foo -(refs)> *', opts=viewopts2))

    # async def test_layer_form_by_buid(self):

    #     async with self.getTestCore() as core:

    #         layr00 = core.view.layers[0]

    #         # add node - buid:form exists
    #         nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :loc=us ]')
    #         buid0 = nodes[0].buid
    #         self.eq('inet:ipv4', await layr00.getNodeForm(buid0))

    #         # add edge and nodedata
    #         nodes = await core.nodes('[ inet:ipv4=2.3.4.5 ]')
    #         buid1 = nodes[0].buid
    #         self.eq('inet:ipv4', await layr00.getNodeForm(buid1))

    #         await core.nodes('inet:ipv4=1.2.3.4 [ +(refs)> {inet:ipv4=2.3.4.5} ] $node.data.set(spam, ham)')
    #         self.eq('inet:ipv4', await layr00.getNodeForm(buid0))

    #         # remove edge, map still exists
    #         await core.nodes('inet:ipv4=1.2.3.4 [ -(refs)> {inet:ipv4=2.3.4.5} ]')
    #         self.eq('inet:ipv4', await layr00.getNodeForm(buid0))

    #         # remove nodedata, map still exists
    #         await core.nodes('inet:ipv4=1.2.3.4 $node.data.pop(spam)')
    #         self.eq('inet:ipv4', await layr00.getNodeForm(buid0))

    #         # delete node - buid:form removed
    #         await core.nodes('inet:ipv4=1.2.3.4 | delnode')
    #         self.none(await layr00.getNodeForm(buid0))

    #         await core.nodes('[ inet:ipv4=5.6.7.8 ]')

    #         # fork a view
    #         info = await core.view.fork()
    #         layr01 = core.getLayer(info['layers'][0]['iden'])
    #         view01 = core.getView(info['iden'])

    #         await alist(view01.eval('[ inet:ipv4=6.7.8.9 ]'))

    #         # buid:form for a node in child doesn't exist
    #         self.none(await layr01.getNodeForm(buid1))

    #         # add prop, buid:form map exists
    #         nodes = await alist(view01.eval('inet:ipv4=2.3.4.5 [ :loc=ru ]'))
    #         self.len(1, nodes)
    #         self.eq('inet:ipv4', await layr01.getNodeForm(buid1))

    #         # add nodedata and edge
    #         await alist(view01.eval('inet:ipv4=2.3.4.5 [ +(refs)> {inet:ipv4=6.7.8.9} ] $node.data.set(faz, baz)'))

    #         # remove prop, map still exists due to nodedata
    #         await alist(view01.eval('inet:ipv4=2.3.4.5 [ -:loc ]'))
    #         self.eq('inet:ipv4', await layr01.getNodeForm(buid1))

    #         # remove nodedata, map still exists due to edge
    #         await alist(view01.eval('inet:ipv4=2.3.4.5 $node.data.pop(faz)'))
    #         self.eq('inet:ipv4', await layr01.getNodeForm(buid1))

    #         # remove edge, map is deleted
    #         await alist(view01.eval('inet:ipv4=2.3.4.5 [ -(refs)> {inet:ipv4=6.7.8.9} ]'))
    #         self.none(await layr01.getNodeForm(buid1))

    #         # edges between two nodes in parent
    #         await alist(view01.eval('inet:ipv4=2.3.4.5 [ +(refs)> {inet:ipv4=5.6.7.8} ]'))
    #         self.eq('inet:ipv4', await layr01.getNodeForm(buid1))

    #         await alist(view01.eval('inet:ipv4=2.3.4.5 [ -(refs)> {inet:ipv4=5.6.7.8} ]'))
    #         self.none(await layr01.getNodeForm(buid1))

    async def test_layer(self):

        async with self.getTestCore() as core:

            await core.addTagProp('_score', ('int', {}), {})

            layr = core.getLayer()
            self.isin(f'Layer (Layer): {layr.iden}', str(layr))

            nodes = await core.nodes('[test:str=foo :seen=(2015, 2016)]')

            self.false(await layr.hasTagProp('_score'))
            nodes = await core.nodes('[test:str=bar +#test:_score=100]')
            self.true(await layr.hasTagProp('_score'))

    async def test_layer_no_extra_logging(self):

        async with self.getTestCore() as core:
            '''
            For a do-nothing write, don't write new log entries
            '''
            await core.nodes('[test:str=foo :seen=(2015, 2016)]')
            layr = core.getLayer(None)
            offs = layr.getEditIndx()
            await core.nodes('[test:str=foo :seen=(2015, 2016)]')
            self.eq(offs, layr.getEditIndx())

    async def test_layer_tomb_over_live(self):
        '''
        A tombstone edit applied to a layer which still holds the live row must
        remove it, so that point lookups and index scans agree.
        '''
        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:str=foo +(refs)> {[ test:int=1 ]} ] $node.data.set(hehe, haha)')
            nid = s_common.int64un(nodes[0].nid)

            nodes = await core.nodes('test:int=1')
            n2nid = s_common.int64un(nodes[0].nid)

            layr = core.getLayer()

            # a raw tombstone replay, such as a layer push or a mirror, must not
            # leave the live rows behind.
            edits = (
                (s_layer.EDIT_NODEDATA_TOMB, ('hehe',)),
                (s_layer.EDIT_EDGE_TOMB, ('refs', n2nid)),
            )
            self.len(1, await layr.saveNodeEdits([(nid, 'test:str', edits)], {}))

            # the point lookups and the scans must agree
            self.none(await core.callStorm('test:str=foo return($node.data.get(hehe))'))
            self.eq((), await core.callStorm('test:str=foo return($node.data.list())'))
            self.len(0, await core.nodes('yield $lib.lift.byNodeData(hehe)'))

            self.len(0, await core.nodes('test:str=foo -(refs)> *'))
            self.len(0, await core.nodes('test:int=1 <(refs)- *'))
            self.eq(0, core.getView().getEdgeCount(nodes[0].nid, n2=True))

            # and the edit is idempotent
            self.len(0, await layr.saveNodeEdits([(nid, 'test:str', edits)], {}))

    async def test_layer_tomb_over_live_parts(self):
        '''
        The prop, tag and tagprop tombstones must also remove the live row they mask,
        the same way the nodedata and light edge tombstones do.
        '''
        async with self.getTestCore() as core:

            await core.addTagProp('_score', ('int', {}), {})

            nodes = await core.nodes('[ test:str=foo :hehe=haha +#a.b=2024 +#c.d:_score=7 ]')
            nid = s_common.int64un(nodes[0].nid)

            layr = core.getLayer()

            edits = (
                (s_layer.EDIT_PROP_TOMB, ('hehe',)),
                (s_layer.EDIT_TAG_TOMB, ('a.b',)),
                (s_layer.EDIT_TAGPROP_TOMB, ('c.d', '_score')),
            )
            self.len(1, await layr.saveNodeEdits([(nid, 'test:str', edits)], {}))

            # the live values are gone from the storage node...
            sode = layr._getStorNode(nodes[0].nid)
            self.notin('hehe', sode.get('props', {}))
            self.notin('a.b', sode.get('tags', {}))
            self.notin('c.d', sode.get('tagprops', {}))

            # ...and the tombstones remain
            self.true(sode['antiprops'].get('hehe'))
            self.true(sode['antitags'].get('a.b'))
            self.true(sode['antitagprops']['c.d'].get('_score'))

            # the point lookups and the index scans agree
            nodes = await core.nodes('test:str=foo')
            self.len(1, nodes)
            self.none(nodes[0].get('hehe'))
            self.none(nodes[0].getTag('a.b'))
            self.none(nodes[0].getTagProp('c.d', '_score'))

            self.len(0, await core.nodes('test:str:hehe=haha'))
            self.len(0, await core.nodes('test:str:hehe'))
            self.len(0, await core.nodes('#a.b'))
            self.len(0, await core.nodes('#a.b@=2024'))
            self.len(0, await core.nodes('#c.d:_score'))
            self.len(0, await core.nodes('#c.d:_score=7'))

            # and the edits are idempotent
            self.len(0, await layr.saveNodeEdits([(nid, 'test:str', edits)], {}))

    async def test_layer_node_tomb_over_live(self):
        '''
        A whole node tombstone must remove every live value the layer holds for the node,
        and supersede any part-of-node tombstones it was carrying.
        '''
        async with self.getTestCore() as core:

            await core.addTagProp('_score', ('int', {}), {})

            nodes = await core.nodes('''
                [ test:str=foo :hehe=haha +#a.b +#c.d:_score=7
                  +(refs)> {[ test:int=1 ]} ] $node.data.set(hehe, haha)
            ''')
            node = nodes[0]
            nid = s_common.int64un(node.nid)

            layr = core.getLayer()

            # give the node a part-of-node tombstone which the node tombstone supersedes
            self.len(1, await layr.saveNodeEdits([(nid, 'test:str', (
                (s_layer.EDIT_PROP_TOMB, ('newp',)),
            ))], {}))
            self.true(layr._getStorNode(node.nid)['antiprops'].get('newp'))

            self.len(1, await layr.saveNodeEdits([(nid, 'test:str', (
                (s_layer.EDIT_NODE_TOMB, ()),
            ))], {}))

            sode = layr._getStorNode(node.nid)

            # the tombstone is all that is left of the node in this layer
            self.true(sode.get('antivalu'))
            self.eq({}, sode.get('props', {}))
            self.eq({}, sode.get('tags', {}))
            self.eq({}, sode.get('tagprops', {}))
            self.eq({}, sode.get('antiprops', {}))
            self.eq({}, sode.get('antitags', {}))
            self.eq({}, sode.get('antitagprops', {}))
            self.eq({}, sode.get('n1verbs', {}))

            # so iterLayerNodeEdits() replays exactly the tombstone, losing nothing
            edits = [e async for e in layr.iterLayerNodeEdits()]
            self.eq([(nid, 'test:str', [(s_layer.EDIT_NODE_TOMB, ())])],
                    [e for e in edits if e[0] == nid])

            # the node is no longer lifted by any index
            self.len(0, await core.nodes('test:str=foo'))
            self.len(0, await core.nodes('test:str'))
            self.len(0, await core.nodes('test:str:hehe=haha'))
            self.len(0, await core.nodes('#a.b'))
            self.len(0, await core.nodes('#c.d:_score=7'))
            self.len(0, await core.nodes('yield $lib.lift.byNodeData(hehe)'))
            self.len(0, await core.nodes('test:int=1 <(refs)- *'))

            # and the edit is idempotent
            self.len(0, await layr.saveNodeEdits([(nid, 'test:str', (
                (s_layer.EDIT_NODE_TOMB, ()),
            ))], {}))

    async def test_layer_del_tombstone_perms(self):
        '''
        delTombstone() removes a mask over a lower layer value, so it requires the "add"
        permission for that value, and may only target the write layer of the view.
        '''
        async with self.getTestCore() as core:

            await core.addTagProp('_score', ('int', {}), {})
            await core.nodes('[ test:str=foo :hehe=haha +#a.b +#c.d:_score=7 ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            await core.nodes('test:str=foo [ -:hehe -#a.b -#c.d:_score ]', opts=opts)
            self.len(0, await core.nodes('test:str:hehe=haha', opts=opts))

            layriden = core.getView(viewiden).wlyr.iden

            user = await core.auth.addUser('lowly')
            await user.addRule((True, ('view', 'read')), gateiden=viewiden)

            useropts = {'view': viewiden, 'user': user.iden}

            q = '''
                $layr = $lib.layer.get()
                for ($nid, $type, $info) in $layr.getTombstones() {
                    $lib.print($layr.delTombstone($nid, $type, $info))
                }
            '''

            # without the add perms the user may not remove a tombstone
            with self.raises(s_exc.AuthDeny):
                await core.nodes(q, opts=useropts)

            await user.addRule((True, ('node', 'prop', 'set')), gateiden=layriden)
            await user.addRule((True, ('node', 'tag', 'add')), gateiden=layriden)

            msgs = await core.stormlist(q, opts=useropts)
            self.stormHasNoWarnErr(msgs)

            # the values from the parent layer are visible in the fork again
            self.len(1, await core.nodes('test:str:hehe=haha', opts=opts))
            self.len(1, await core.nodes('#a.b', opts=opts))
            self.len(1, await core.nodes('#c.d:_score=7', opts=opts))

            # delTombstone() returns True when it removed one and False when it did not
            nid = await core.callStorm('test:str=foo return($node.nid)', opts=opts)
            tombinfo = ('test:str', 'hehe')
            valu = await core.callStorm('''
                return($lib.layer.get().delTombstone($nid, $type, $info))
            ''', opts={'view': viewiden, 'vars': {
                'nid': nid, 'type': s_layer.INDX_PROP, 'info': tombinfo}})
            self.false(valu)

            # an unknown tombstone type is rejected rather than silently ignored
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    return($lib.layer.get().delTombstone($nid, $type, $info))
                ''', opts={'view': viewiden, 'vars': {
                    'nid': nid, 'type': b'\x99\x99', 'info': tombinfo}})

            # as is a property which does not exist on the node's form
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    return($lib.layer.get().delTombstone($nid, $type, $info))
                ''', opts={'view': viewiden, 'vars': {
                    'nid': nid, 'type': s_layer.INDX_PROP, 'info': ('test:str', 'newp')}})

            # and it may only be called on the write layer of the current view
            parentlayr = core.getView().layers[0].iden
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    return($lib.layer.get($layr).delTombstone($nid, $type, $info))
                ''', opts={'view': viewiden, 'vars': {
                    'layr': parentlayr, 'nid': nid,
                    'type': s_layer.INDX_PROP, 'info': tombinfo}})

    async def test_layer_del_stor_node_valuless(self):
        '''
        delStorNode() on a storage node with no valu of its own, which is what a fork
        looks like once it edits a node that lives in the parent. Such a sode carries
        the live and tombstoned node data and light edges, or a whole node tombstone.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:int=1 ]')
            await core.nodes('[ test:int=2 ]')
            await core.nodes('[ test:str=foo +(refs)> { test:int=1 } ] $node.data.set(pdata, x)')
            await core.nodes('[ test:str=bar ]')

            meta = {'time': s_common.now(), 'user': core.auth.rootuser.iden}

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}
            layr = core.getView(viewiden).wlyr

            # the fork masks the inherited edge and node data, and adds its own of each
            nodes = await core.nodes('''
                test:str=foo
                [ -(refs)> { test:int=1 } +(refs)> { test:int=2 } ]
                $node.data.pop(pdata) $node.data.set(fdata, y)
            ''', opts=opts)
            nid = nodes[0].nid

            sode = layr._getStorNode(nid)
            self.none(sode.get('valu'))
            self.none(sode.get('antivalu'))
            self.nn(sode.get('n1verbs'))
            self.nn(sode.get('n1antiverbs'))

            self.true(await layr.delStorNode(nid, meta=meta))
            self.eq({}, layr._getStorNode(nid))

            # dropping the fork's storage node restores the inherited view of the node
            self.eq([('test:int', 1)], [n.ndef for n in
                    await core.nodes('test:str=foo -(refs)> *', opts=opts)])
            self.eq('x', await core.callStorm('test:str=foo return($node.data.get(pdata))', opts=opts))
            self.none(await core.callStorm('test:str=foo return($node.data.get(fdata))', opts=opts))

            # a whole node tombstone is the other shape a valu-less sode takes
            nodes = await core.nodes('test:str=bar | delnode', opts=opts)
            barnid = core.getNidByNdef(('test:str', 'bar'))
            self.true(layr._getStorNode(barnid).get('antivalu'))
            self.len(0, await core.nodes('test:str=bar', opts=opts))

            self.true(await layr.delStorNode(barnid, meta=meta))
            self.eq({}, layr._getStorNode(barnid))
            self.len(1, await core.nodes('test:str=bar', opts=opts))

            # and the ordinary case, a sode which does hold the valu
            rootlayr = core.getLayer()
            self.true(await rootlayr.delStorNode(barnid, meta=meta))
            self.len(0, await core.nodes('test:str=bar'))

            # the parent is otherwise untouched
            self.len(1, await core.nodes('test:str=foo'))

    async def test_layer_diff_tag_tombstone(self):
        '''
        diff --tag must surface tags removed in the fork, the way diff --prop does for
        props, so that the removal can be merged down.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#cno.mal ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            await core.nodes('inet:fqdn=evil.com [ -#cno.mal ]', opts=opts)
            self.len(0, await core.nodes('#cno.mal', opts=opts))

            layr = core.getView(viewiden).wlyr

            # the tag lift cannot see the removal, the tombstone walk can
            self.len(0, [nid async for nid, sode in layr.liftByTags(['cno.mal'])])
            self.len(1, [nid async for nid in layr.iterTagTombstones('cno.mal')])

            nodes = await core.nodes('diff --tag cno.mal', opts=opts)
            self.len(1, nodes)
            self.eq(('inet:fqdn', 'evil.com'), nodes[0].ndef)

            # and the removal merges down to the parent
            await core.nodes('diff --tag cno.mal | merge --apply', opts=opts)
            self.len(0, await core.nodes('#cno.mal'))

    async def test_layer_tag_form_indx_new_sode(self):
        '''
        A tag set which is the first edit to materialize a nid in the layer must write
        the per-form tag index rows under the tag abbreviation.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=foo ]')

            vdef = await core.view.fork()
            view = core.getView(vdef.get('iden'))
            opts = {'view': view.iden}

            layr = view.layers[0]

            # the node lives in the layer below, so the tag set creates the sode
            await core.nodes('test:str=foo [ +#hehe=2020 ]', opts=opts)

            self.len(1, await core.nodes('test:str#hehe', opts=opts))
            self.len(1, await core.nodes('test:str#hehe@=2020', opts=opts))
            self.len(1, await alist(layr.liftByTag('hehe', form='test:str')))

            # the count and the index rows must agree
            self.eq(1, await layr.getTagCount('hehe', formname='test:str'))

            # and the form row is the only row under the form abbreviation
            formabrv = core.getIndxAbrv(s_layer.INDX_FORM, 'test:str')
            rows = list(layr.layrslab.scanByPref(formabrv, db=layr.indxdb))
            self.len(1, rows)
            self.eq(formabrv, rows[0][0])

            # removing the tag removes every row it added
            await core.nodes('test:str=foo [ -#hehe ]', opts=opts)

            self.len(0, await core.nodes('test:str#hehe', opts=opts))
            self.eq(0, await layr.getTagCount('hehe', formname='test:str'))
            self.len(0, list(layr.layrslab.scanByPref(formabrv, db=layr.indxdb)))

    async def test_layer_delnode_edge_tomb_counts(self):
        '''
        Deleting a node which carries edge tombstones must adjust the tombstone verb
        count rather than the live edge counts.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=foo +(refs)> {[ test:int=1 ]} ]')

            vdef = await core.view.fork()
            view = core.getView(vdef.get('iden'))
            opts = {'view': view.iden}

            layr = view.layers[0]
            vabrv = core.getIndxAbrv(s_layer.INDX_EDGE_VERB, 'refs')
            tombabrv = s_layer.INDX_TOMB + vabrv

            # the edge lives in the layer below, so deleting it writes a tombstone
            await core.nodes('test:str=foo [ -(refs)> { test:int=1 } ]', opts=opts)

            self.eq(0, layr.getEdgeVerbCount('refs'))
            self.eq(1, layr.indxcounts.get(tombabrv))

            await core.nodes('test:str=foo | delnode', opts=opts)

            self.eq(0, layr.getEdgeVerbCount('refs'))
            self.eq(0, layr.getEdgeVerbCount('refs', n1form='test:str'))
            self.eq(0, layr.getEdgeVerbCount('refs', n2form='test:int'))
            self.eq(0, layr.getEdgeVerbCount('refs', n1form='test:str', n2form='test:int'))
            self.eq(0, layr.indxcounts.get(tombabrv))

    async def test_layer_node_add_dedup(self):
        '''
        A node add which matches the storage node must be dropped by calcEdits(), and
        one which differs only by the folding of nidNorm() must update the storage
        node without disturbing the index.
        '''
        async with self.getTestCore() as core:

            layr = core.getLayer()

            nodes = await core.nodes('[ test:str=foo ]')
            nid = s_common.int64un(nodes[0].nid)

            sode = layr.getStorNode(nodes[0].nid)
            edit = (s_layer.EDIT_NODE_ADD, sode['valu'])

            self.none(layr._calcNodeAdd(nodes[0].nid, edit, sode))
            self.eq((), await layr.saveNodeEdits([(nid, 'test:str', (edit,))], {}))

            # the text type folds case for nid deconfliction, so a raw node add such as
            # a layer push may carry a different value for a nid we already hold
            nodes = await core.nodes('[ it:hostname="HayStack" ]')
            nid = s_common.int64un(nodes[0].nid)

            abrv = core.getIndxAbrv(s_layer.INDX_PROP, 'it:hostname', None)
            rows = list(layr.layrslab.scanByPref(abrv, db=layr.indxdb))
            self.len(1, rows)

            edit = (s_layer.EDIT_NODE_ADD, ('haystack', s_layer.STOR_TYPE_TEXT, None))
            self.len(1, await layr.saveNodeEdits([(nid, 'it:hostname', (edit,))], {}))

            self.eq(('haystack', s_layer.STOR_TYPE_TEXT, None), layr.getStorNode(nodes[0].nid)['valu'])

            # the index rows and counts are built from the folded value, so they stand
            self.eq(rows, list(layr.layrslab.scanByPref(abrv, db=layr.indxdb)))
            self.eq(1, layr.indxcounts.get(abrv))

            self.len(1, await core.nodes('it:hostname="HayStack"'))
            self.len(1, await core.nodes('it:hostname=haystack'))

    async def test_layer_prop_set_virts_no_prop(self):
        '''
        A prop set with no value and virts, for a prop the node does not have, must not
        raise from the virts comparison.
        '''
        async with self.getTestCore() as core:

            layr = core.getLayer()

            nodes = await core.nodes('[ test:str=foo ]')
            nid = s_common.int64un(nodes[0].nid)

            virts = {'newp': ('bar', s_layer.STOR_TYPE_UTF8)}
            edits = ((s_layer.EDIT_PROP_SET, ('hehe', None, s_layer.STOR_TYPE_UTF8, virts)),)

            self.len(1, await layr.saveNodeEdits([(nid, 'test:str', edits)], {}))

    async def test_layer_mapfull_mid_edit(self):
        '''
        A map growth part way through a nexus edit must not commit the layer slab: the
        index rows are written as the edits are applied but the storage nodes are only
        flushed at the end, so a commit here would make a partial edit durable ahead of
        both the storage nodes and the nexus log entry describing it.
        '''
        async with self.getTestCore() as core:

            layr = core.getLayer()
            slab = layr.layrslab

            grown = []
            realedit = layr._editPropSet

            async def wrap(nid, form, edit, sode, meta):
                retn = await realedit(nid, form, edit, sode, meta)

                # the map fills part way through the edit and has to grow
                if not grown:
                    commits = len(slab.commitstats)
                    slab._handle_mapfull()
                    grown.append((commits, len(slab.commitstats)))

                return retn

            layr.editors[s_layer.EDIT_PROP_SET] = wrap
            try:
                await core.nodes('[ test:str=foo :hehe=lol :tick=2020 ]')
            finally:
                layr.editors[s_layer.EDIT_PROP_SET] = realedit

            # the growth happened and committed nothing
            self.len(1, grown)
            self.eq(grown[0][0], grown[0][1])

            # and the edit survived the abort and replay intact
            nodes = await core.nodes('test:str=foo')
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 'lol')
            self.propeq(nodes[0], 'tick', 1577836800000000)

            self.len(1, await core.nodes('test:str:hehe=lol'))
            self.len(1, await core.nodes('test:str:tick=2020'))

    async def test_layer_del_then_lift(self):
        '''
        Regression test
        '''
        async with self.getTestCore() as core:
            await core.nodes('$x = 0 while $($x < 2000) { [file:bytes="*"] [ou:org="*"] $x = $($x + 1)}')
            await core.nodes('.created | delnode --force')
            nodes = await core.nodes('.created')
            self.len(0, nodes)

    async def test_layer_clone(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            layr = core.getLayer()
            self.isin(f'Layer (Layer): {layr.iden}', str(layr))

            nodes = await core.nodes('[test:str=foo :seen=(2015, 2016)]')

            nid = nodes[0].nid

            sode = layr.getStorNode(nid)
            self.eq('foo', sode['valu'][0])
            self.eq((1420070400000000, 1451606400000000, 31536000000000), sode['props']['seen'][0][1])

            s_common.gendir(layr.dirn, 'adir')

            copylayrinfo = await core.cloneLayer(layr.iden)
            self.len(2, core.layers)

            copylayr = core.getLayer(copylayrinfo.get('iden'))
            self.isin(f'Layer (Layer): {copylayr.iden}', str(copylayr))
            self.ne(layr.iden, copylayr.iden)

            sode = copylayr.getStorNode(nid)
            self.eq('foo', sode['valu'][0])
            self.eq((1420070400000000, 1451606400000000, 31536000000000), sode['props']['seen'][0][1])

            cdir = s_common.gendir(copylayr.dirn, 'adir')
            self.true(os.path.exists(cdir))

            await self.asyncraises(s_exc.NoSuchLayer, prox.cloneLayer('newp'))

            self.false(layr.readonly)

            # Test overriding layer config values
            ldef = {'readonly': True}
            readlayrinfo = await core.cloneLayer(layr.iden, ldef)
            self.len(3, core.layers)

            readlayr = core.getLayer(readlayrinfo.get('iden'))
            self.true(readlayr.readonly)

            self.none(await core._cloneLayer(readlayrinfo['iden'], readlayrinfo, None))

    async def test_layer_ro(self):
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                msgs = await core.stormlist('$lib.layer.add(({"readonly": true}))')
                self.stormHasNoWarnErr(msgs)

                ldefs = await core.callStorm('return($lib.layer.list())')
                self.len(2, ldefs)

                readonly = [ldef for ldef in ldefs if ldef.get('readonly')]
                self.len(1, readonly)

                layriden = readonly[0].get('iden')
                layr = core.getLayer(layriden)

                view = await core.callStorm(f'return($lib.view.add(layers=({layriden},)))')

                with self.raises(s_exc.IsReadOnly):
                    await core.nodes('[inet:fqdn=vertex.link]', opts={'view': view['iden']})

                # a node in the default (writable) layer to read back after the
                # whole-Cortex readonly reopen below
                await core.nodes('[ inet:ip=1.2.3.4 ]')

            # reopening the whole Cortex readonly opens every layer's storage
            # read-only (slabopts readonly); reads still work against the shared
            # files, and deleting such a layer fini's it but skips the durable
            # rmtree of the shared files (the writer owns them).
            async with await s_cortex.Cortex.anit(dirn, readonly=True) as core:

                layr = core.getLayer()
                self.true(layr.layrslab.readonly)

                self.eq(1, await core.count('inet:ip=1.2.3.4'))

                layrdirn = layr.dirn
                await layr.delete()
                self.true(layr.isdeleted)
                self.true(os.path.isdir(layrdirn))

    async def test_layer_iter_props(self):

        async with self.getTestCore() as core:
            await core.addTagProp('_score', ('int', {}), {})

            nodes = await core.nodes('[inet:ip=([4, 1]) :asn=10 +#foo=(2020, 2021) +#foo:_score=42]')
            self.len(1, nodes)
            nid1 = nodes[0].nid

            nodes = await core.nodes('[inet:ip=([4, 2]) :asn=20 +#foo=(2019, 2020) +#foo:_score=41]')
            self.len(1, nodes)
            nid2 = nodes[0].nid

            nodes = await core.nodes('[inet:ip=([4, 3]) :asn=30 +#foo +#foo:_score=99]')
            self.len(1, nodes)
            nid3 = nodes[0].nid

            nodes = await core.nodes('[test:str=yolo]')
            self.len(1, nodes)
            strnid = nodes[0].nid

            nodes = await core.nodes('[test:str=$valu]', opts={'vars': {'valu': 'z' * 500}})
            self.len(1, nodes)
            strnid2 = nodes[0].nid

            # rows are (nid, valu) tuples
            layr = core.view.layers[0]
            rows = await alist(layr.iterPropRows('inet:ip', 'asn'))

            self.eq((10, 20, 30), tuple(sorted([row[1][1] for row in rows])))

            styp = core.model.form('inet:ip').prop('asn').type.stortype
            rows = await alist(layr.iterPropRows('inet:ip', 'asn', styp))
            self.eq((10, 20, 30), tuple(sorted([row[1][1] for row in rows])))

            # for poly rows, providing a specific poly flagged stortype will filter by the requested stortype
            styp = core.model.type('inet:asn').stortype | s_layer.STOR_FLAG_POLY
            rows = await alist(layr.iterPropRows('inet:ip', 'asn', styp))
            self.eq((10, 20, 30), tuple(sorted([row[1][1] for row in rows])))

            rows = await alist(layr.iterPropRows('inet:ip', 'asn', styp, startvalu=('inet:asn', 20)))
            self.eq((20, 30), tuple(sorted([row[1][1] for row in rows])))

            rows = await alist(layr.iterPropRows('inet:ip', 'asn', s_layer.STOR_TYPE_IVAL | s_layer.STOR_FLAG_POLY))
            self.eq((), tuple(sorted([row[1][1] for row in rows])))

            tm = lambda x, y: (s_time.parse(x), s_time.parse(y), s_time.parse(y) - s_time.parse(x))  # NOQA

            # iterFormRows
            rows = await alist(layr.iterFormRows('inet:ip'))
            self.eq([(nid1, (4, 1)), (nid2, (4, 2)), (nid3, (4, 3))], rows)

            rows = await alist(layr.iterFormRows('inet:ip', stortype=s_layer.STOR_TYPE_IPADDR, startvalu=(4, 2)))
            self.eq([(nid2, (4, 2)), (nid3, (4, 3))], rows)

            rows = await alist(layr.iterFormRows('test:str', stortype=s_layer.STOR_TYPE_UTF8, startvalu='yola'))
            self.eq([(strnid, 'yolo'), (strnid2, 'z' * 500)], rows)

            # iterTagRows
            expect = (
                (nid3, (None, None, None)),
                (nid2, tm('2019', '2020')),
                (nid1, tm('2020', '2021')),
            )

            rows = await alist(layr.iterTagRows('foo'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagRows('foo', form='inet:ip'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagRows('foo', form='newpform'))
            self.eq([], rows)

            rows = await alist(layr.iterTagRows('foo', form='newpform', starttupl=expect[1]))
            self.eq([], rows)

            rows = await alist(layr.iterTagRows('foo', starttupl=expect[0]))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagRows('foo', starttupl=expect[1]))
            self.eq(expect[1:], rows)

            rows = await alist(layr.iterTagRows('foo', form='inet:ip', starttupl=expect[1]))
            self.eq(expect[1:], rows)

            rows = await alist(layr.iterTagRows('nosuchtag'))
            self.eq([], rows)

            expect = [
                (nid2, 41,),
                (nid1, 42,),
                (nid3, 99,),
            ]

            rows = await alist(layr.iterTagPropRows('foo', 'newp'))
            self.eq([], rows)

            rows = await alist(layr.iterTagPropRows('foo', '_score'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagPropRows('foo', '_score', form='inet:ip'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagPropRows('foo', '_score', form='inet:ip', stortype=s_layer.STOR_TYPE_I64,
                                                    startvalu=42))
            self.eq(expect[1:], rows)

            rows = await alist(layr.iterTagPropRows('foo', '_score', stortype=s_layer.STOR_TYPE_I64, startvalu=42))
            self.eq(expect[1:], rows)

    async def test_layer_setinfo(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                layer = core.getView().layers[0]

                self.eq('hehe', await core.callStorm('$layer = $lib.layer.get() $layer.set(name, hehe) return($layer.get(name))'))

                self.true(await core.callStorm('$layer=$lib.layer.get() $layer.set(readonly, (true)) return($layer.get(readonly))'))
                await self.asyncraises(s_exc.IsReadOnly, core.nodes('[inet:ip=7.7.7.7]'))
                await self.asyncraises(s_exc.IsReadOnly, core.nodes('$lib.layer.get().set(desc, foo)'))

                self.false(await core.callStorm('$layer=$lib.layer.get() $layer.set(readonly, (false)) return($layer.get(readonly))'))
                self.len(1, await core.nodes('[inet:ip=7.7.7.7]'))

                msgs = []
                didset = False
                async for mesg in core.storm('[( test:guid=(rotest00,) )] $lib.time.sleep(1) [( test:guid=(rotest01,) )]'):
                    msgs.append(mesg)
                    if mesg[0] == 'edits' and not didset:
                        self.true(await core.callStorm('$layer=$lib.layer.get() $layer.set(readonly, (true)) return($layer.get(readonly))'))
                        didset = True

                self.stormIsInErr(f'Layer {layer.iden} is read only!', msgs)
                self.len(1, [mesg for mesg in msgs if mesg[0] == 'node'])

                with self.raises(s_exc.BadOptValu):
                    await core.callStorm('$layer = $lib.layer.get() $layer.set(newp, hehe)')

                await core.nodes('''
                    $layer = $lib.layer.get()
                    $layer.set(readonly, (false))  // so we can set everything else
                    $layer.set(name, foo)
                    $layer.set(desc, foodesc)
                    $layer.set(readonly, (true))
                ''')

                info00 = await core.callStorm('return($lib.layer.get())')
                self.eq('foo', info00['name'])
                self.eq('foodesc', info00['desc'])
                self.true(info00['readonly'])

            async with self.getTestCore(dirn=dirn) as core:

                self.eq(info00, await core.callStorm('return($lib.layer.get())'))

    async def test_layer_cachesize(self):

        # Test default cache size
        async with self.getTestCore() as core:
            layr = core.getView().layers[0]
            self.eq(layr.nidcache.maxsize, s_layer.NID_CACHE_SIZE)

        # Verify the env var name maps correctly
        envar = s_config.make_envar_name('layers:cache:size', prefix='SYN_CORTEX')
        self.eq(envar, 'SYN_CORTEX_LAYERS_CACHE_SIZE')

        # Test Cortex conf override
        async with self.getTestCore(conf={'layers:cache:size': 15000}) as core:
            layr = core.getView().layers[0]
            self.eq(layr.nidcache.maxsize, 15000)

        # Test layer config override (takes priority over Cortex conf)
        async with self.getTestCore(conf={'layers:cache:size': 20000}) as core:
            ldef = await core.addLayer({'cache:size': 5000})
            layr = core.getLayer(ldef['iden'])
            self.eq(layr.nidcache.maxsize, 5000)

        # Test Storm set/get for cache:size
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                layr = core.getView().layers[0]

                # Set cache:size via Storm
                self.eq(50000, await core.callStorm('''
                    $layer = $lib.layer.get()
                    $layer.set(cache:size, 50000)
                    return($layer.get(cache:size))
                '''))

                # Verify the nidcache was resized
                self.eq(layr.nidcache.maxsize, 50000)

                # Verify it persists in pack
                info = await core.callStorm('return($lib.layer.get())')
                self.eq(info['cache:size'], 50000)

            # Verify persistence across restart
            async with self.getTestCore(dirn=dirn) as core:

                layr = core.getView().layers[0]
                self.eq(layr.nidcache.maxsize, 50000)

                info = await core.callStorm('return($lib.layer.get())')
                self.eq(info['cache:size'], 50000)

        # Test cache:size via layer.add Storm command
        async with self.getTestCore() as core:
            msgs = await core.stormlist('layer.add --cache-size 30000')
            self.stormHasNoWarnErr(msgs)

            ldef = [m[1] for m in msgs if m[0] == 'print'][0]
            # Get the layer and verify the cache:size
            layers = await core.callStorm('return($lib.layer.list())')
            newlayr = [lyr for lyr in layers if lyr.get('cache:size') == 30000]
            self.len(1, newlayr)

        # Test invalid cache:size
        async with self.getTestCore() as core:
            with self.raises(s_exc.BadOptValu):
                await core.callStorm('$layer = $lib.layer.get() $layer.set(cache:size, 0)')

        # Test that view forks use default cache size
        async with self.getTestCore(conf={'layers:cache:size': 25000}) as core:
            fork = await core.view.fork()
            forklayr = core.getLayer(fork['layers'][0]['iden'])
            self.eq(forklayr.nidcache.maxsize, 25000)

            view01 = core.getView(fork['iden'])
            fork01 = await view01.insertParentFork(core.auth.rootuser.iden)
            fork01layr = core.getLayer(fork01['layers'][0]['iden'])
            self.eq(fork01layr.nidcache.maxsize, 25000)

        # Test that cortex conf is resolved at runtime (restart with different value)
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn, conf={'layers:cache:size': 15000}) as core:
                layr = core.getView().layers[0]
                self.eq(layr.nidcache.maxsize, 15000)

            async with self.getTestCore(dirn=dirn, conf={'layers:cache:size': 25000}) as core:
                layr = core.getView().layers[0]
                self.eq(layr.nidcache.maxsize, 25000)

    async def test_layer_edit_perms(self):

        class Dict(s_spooled.Dict):
            async def __anit__(self, dirn=None, size=1, cell=None):
                await super().__anit__(dirn=dirn, size=size, cell=cell)

        seen = set()
        def confirm(self, perm, default=None, gateiden=None):
            seen.add(perm)
            return True

        with mock.patch('synapse.lib.spooled.Dict', Dict):
            async with self.getTestCore() as core:

                user = await core.auth.addUser('blackout@vertex.link')

                await core.addTagProp('_score', ('int', {}), {})

                nodes = await core.nodes('''
                    [
                        (meta:topic=marty
                            :desc=marty
                            +#performance:_score=10
                            +#role.protagonist
                        )
                        (meta:topic=emmett :desc=emmett)
                        (meta:topic=biff :desc=biff)
                        (meta:topic=george :desc=george)
                        (meta:topic=loraine :desc=loraine)
                        <(seen)+ {[ meta:source=(movie, "Back to the Future") :name=BTTF :type=movie ]}
                    ]
                    $node.data.set(movie, "Back to the Future")
                ''')
                self.len(5, nodes)

                viewiden = await core.callStorm('''
                    $view = $lib.view.get().fork()
                    return($view.iden)
                ''')

                layr = core.views[viewiden].layers[0]

                opts = {'view': viewiden}

                await core.nodes('[ test:str=bar +#foo.bar ]', opts=opts)

                await core.nodes('''
                    [ test:str=foo
                        :hehe=bar
                        +#foo:_score=2
                        +#foo.bar.baz
                        +#bar:_score=2
                        <(refs)+ { test:str=bar }
                    ]
                    $node.data.set(foo, bar)
                ''', opts=opts)

                parent = core.view.layers[0]

                seen.clear()
                with mock.patch.object(s_auth.User, 'confirm', confirm):
                    await layr.confirmLayerEditPerms(user, parent.iden)

                self.eq(seen, {
                    # Node add
                    ('node', 'add', 'syn:tag'),
                    ('node', 'add', 'test:str'),

                    # New style prop set
                    ('node', 'prop', 'set', 'test:str', 'hehe'),

                    ('node', 'prop', 'set', 'syn:tag', 'up'),
                    ('node', 'prop', 'set', 'syn:tag', 'base'),
                    ('node', 'prop', 'set', 'syn:tag', 'depth'),

                    # Tag/tagprop add
                    ('node', 'tag', 'add', 'foo'),
                    ('node', 'tag', 'add', 'bar'),
                    ('node', 'tag', 'add', 'foo', 'bar'),
                    ('node', 'tag', 'add', 'foo', 'bar', 'baz'),

                    # Nodedata set
                    ('node', 'data', 'set', 'foo'),

                    # Edge add
                    ('node', 'edge', 'add', 'refs'),
                })

                await core.nodes('''
                    test:str=foo
                    [ <(refs)- { test:str=bar } ]
                    $node.data.pop(foo)
                    | delnode
                ''', opts=opts)

                await core.nodes('''
                    meta:topic:desc=biff
                    [ <(seen)- { meta:source:type=movie } ]
                    | delnode |

                    meta:topic=emmett [ -:desc ]
                    meta:topic=marty [ -#performance:_score -#role.protagonist ]
                    $node.data.pop(movie)
                ''', opts=opts)

                seen.clear()
                with mock.patch.object(s_auth.User, 'confirm', confirm):
                    await layr.confirmLayerEditPerms(user, parent.iden)

                self.eq(seen, {
                    # Node add
                    ('node', 'add', 'syn:tag'),
                    ('node', 'add', 'test:str'),

                    # New style prop set
                    ('node', 'prop', 'set', 'syn:tag', 'up'),
                    ('node', 'prop', 'set', 'syn:tag', 'base'),
                    ('node', 'prop', 'set', 'syn:tag', 'depth'),

                    # Tag/tagprop add
                    ('node', 'tag', 'add', 'foo', 'bar'),

                    # Node del (tombstone)
                    ('node', 'del', 'meta:topic'),

                    # Prop del (tombstone)
                    ('node', 'prop', 'del', 'meta:topic', 'desc'),

                    # Tag del (tombstone)
                    ('node', 'tag', 'del', 'role', 'protagonist'),

                    # Tagprop del (tombstone)
                    ('node', 'tag', 'del', 'performance', '_score'),

                    # Nodedata del (tombstone)
                    ('node', 'data', 'del', 'movie'),

                    # Edge del (tombstone)
                    ('node', 'edge', 'del', 'seen'),
                })

                seen.clear()
                with mock.patch.object(s_auth.User, 'confirm', confirm):
                    await layr.confirmLayerEditPerms(user, layr.iden, delete=True)

                self.eq(seen, {
                    # Node del
                    ('node', 'del', 'syn:tag'),
                    ('node', 'del', 'test:str'),

                    # New style prop del
                    ('node', 'prop', 'del', 'syn:tag', 'up'),
                    ('node', 'prop', 'del', 'syn:tag', 'base'),
                    ('node', 'prop', 'del', 'syn:tag', 'depth'),

                    # Tag/tagprop del
                    ('node', 'tag', 'del', 'foo', 'bar'),

                    # Node add (restore tombstone)
                    ('node', 'add', 'meta:topic'),

                    # Prop set (restore tombstone)
                    ('node', 'prop', 'set', 'meta:topic', 'desc'),

                    # Tag/tagprop add (restore tombstone)
                    ('node', 'tag', 'add', 'role', 'protagonist'),
                    ('node', 'tag', 'add', 'performance', '_score'),

                    # Nodedata set (tombstone restore)
                    ('node', 'data', 'set', 'movie'),

                    # Edge add (tombstone restor)
                    ('node', 'edge', 'add', 'seen'),

                })

                # Unknown tombstone type -> else branch logs and continues.
                # Patch abrvToByts to return bytes with an unrecognised tombtype
                # so every tombstone decoded hits the else branch.
                badbyts = b'\xff\xff' + s_msgpack.en(('foo',))
                with mock.patch.object(core.indxabrv, 'abrvToByts', return_value=badbyts):
                    with self.getLoggerStream('synapse.lib.layer') as stream:
                        with mock.patch.object(s_auth.User, 'confirm', confirm):
                            await layr.confirmLayerEditPerms(user, parent.iden)
                        await stream.expect('Encountered unknown tombstone type', timeout=1)

        async with self.getTestCore() as core:

            user = await core.auth.addUser('blackout@vertex.link')
            await user.addRule((False, ('node', 'edge', 'add', 'haha')))
            await user.addRule((False, ('node', 'data', 'set', 'hehe')))
            await user.addRule((True, ('node',)))

            viewiden = await core.callStorm('''
                $lyr = $lib.layer.add()
                $view = $lib.view.add(($lyr.iden,))
                return($view.iden)
            ''')

            layr = core.views[viewiden].layers[0]

            opts = {'view': viewiden}

            await core.nodes('[ test:str=bar +#foo.bar ]', opts=opts)

            await core.nodes('''
                [ test:str=foo
                    :hehe=bar
                    +#foo.bar.baz
                    <(refs)+ { test:str=bar }
                ]
                $node.data.set(foo, bar)
            ''', opts=opts)

            parent = core.view.layers[0]

            seen.clear()
            with mock.patch.object(s_auth.User, 'confirm', confirm):
                await layr.confirmLayerEditPerms(user, parent.iden)

            self.eq(seen, {
                # node.edge.add.* and node.data.set.* because of the deny rules
                ('node', 'edge', 'add', 'refs'),
                ('node', 'data', 'set', 'foo'),
            })

            await user.delRule((False, ('node', 'edge', 'add', 'haha')))
            await user.delRule((False, ('node', 'data', 'set', 'hehe')))

            seen.clear()
            with mock.patch.object(s_auth.User, 'confirm', confirm):
                await layr.confirmLayerEditPerms(user, parent.iden)

            self.eq(seen, set())

    async def test_layer_ival_indexes(self):

        async with self.getTestCore() as core:

            await core.addTagProp('_footime', ('ival', {}), {})

            self.len(0, await core.nodes('entity:campaign#bar:_footime.min=2020-01-01'))

            await core.nodes('''[
                entity:campaign=(foo,)
                    :period=(2019-01-01, ?)
                    +#foo=(2019-01-01, ?)
                    +#bar:_footime=(2019-01-01, ?)
            ]''')

            await core.nodes('''[
                (entity:campaign=* :period=(2020-01-01, 2020-01-02))
                (entity:campaign=* :period=(2021-01-01, 2021-02-01))
                (entity:campaign=* :period=(2022-01-01, 2022-05-01))
                (entity:campaign=* :period=(2023-01-01, 2024-01-01))
                (entity:campaign=* :period=(2024-01-01, 2026-01-01))
            ]''')

            self.len(1, await core.nodes('entity:campaign:period.began=2020-01-01'))
            self.len(3, await core.nodes('entity:campaign:period.began<2022-01-01'))
            self.len(4, await core.nodes('entity:campaign:period.began<=2022-01-01'))
            self.len(3, await core.nodes('entity:campaign:period.began>=2022-01-01'))
            self.len(2, await core.nodes('entity:campaign:period.began>2022-01-01'))
            self.len(1, await core.nodes('entity:campaign:period.began@=2020'))
            self.len(2, await core.nodes('entity:campaign:period.began@=(2020-01-01, 2022-01-01)'))

            self.len(1, await core.nodes('reverse(entity:campaign:period.began=2020-01-01)'))
            self.len(3, await core.nodes('reverse(entity:campaign:period.began<2022-01-01)'))
            self.len(4, await core.nodes('reverse(entity:campaign:period.began<=2022-01-01)'))
            self.len(3, await core.nodes('reverse(entity:campaign:period.began>=2022-01-01)'))
            self.len(2, await core.nodes('reverse(entity:campaign:period.began>2022-01-01)'))
            self.len(1, await core.nodes('reverse(entity:campaign:period.began@=2020)'))
            self.len(2, await core.nodes('reverse(entity:campaign:period.began@=(2020-01-01, 2022-01-01))'))

            self.len(1, await core.nodes('entity:campaign:period.ended=2020-01-02'))
            self.len(2, await core.nodes('entity:campaign:period.ended<2022-05-01'))
            self.len(3, await core.nodes('entity:campaign:period.ended<=2022-05-01'))
            self.len(3, await core.nodes('entity:campaign:period.ended>=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign:period.ended>2022-05-01'))
            self.len(2, await core.nodes('entity:campaign:period.ended@=(2020-01-02, 2022-05-01)'))
            self.len(1, await core.nodes('entity:campaign:period.ended=?'))

            self.len(1, await core.nodes('entity:campaign:period.duration=1D'))
            self.len(1, await core.nodes('entity:campaign:period.duration<31D'))
            self.len(2, await core.nodes('entity:campaign:period.duration<=31D'))
            self.len(4, await core.nodes('entity:campaign:period.duration>=31D'))
            self.len(3, await core.nodes('entity:campaign:period.duration>31D'))
            self.len(1, await core.nodes('entity:campaign:period.duration=?'))

            await core.nodes('''[
                (entity:campaign=* +#foo=(2020-01-01, 2020-01-02))
                (entity:campaign=* +#foo=(2021-01-01, 2021-02-01))
                (entity:campaign=* +#foo=(2022-01-01, 2022-05-01))
                (entity:campaign=* +#foo=(2023-01-01, 2024-01-01))
                (entity:campaign=* +#foo=(2024-01-01, 2026-01-01))
            ]''')

            self.len(1, await core.nodes('entity:campaign#(foo).min=2020-01-01'))
            self.len(3, await core.nodes('entity:campaign#(foo).min<2022-01-01'))
            self.len(4, await core.nodes('entity:campaign#(foo).min<=2022-01-01'))
            self.len(3, await core.nodes('entity:campaign#(foo).min>=2022-01-01'))
            self.len(2, await core.nodes('entity:campaign#(foo).min>2022-01-01'))
            self.len(2, await core.nodes('entity:campaign#(foo).min@=(2020-01-01, 2022-01-01)'))
            self.len(2, await core.nodes('reverse(entity:campaign#(foo).min@=(2020-01-01, 2022-01-01))'))

            self.len(1, await core.nodes('entity:campaign#(foo).max=2020-01-02'))
            self.len(2, await core.nodes('entity:campaign#(foo).max<2022-05-01'))
            self.len(3, await core.nodes('entity:campaign#(foo).max<=2022-05-01'))
            self.len(3, await core.nodes('entity:campaign#(foo).max>=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign#(foo).max>2022-05-01'))
            self.len(2, await core.nodes('entity:campaign#(foo).max@=(2020-01-02, 2022-05-01)'))
            self.len(1, await core.nodes('entity:campaign#(foo).max=?'))

            self.len(1, await core.nodes('entity:campaign#(foo).duration=1D'))
            self.len(1, await core.nodes('entity:campaign#(foo).duration<31D'))
            self.len(2, await core.nodes('entity:campaign#(foo).duration<=31D'))
            self.len(4, await core.nodes('entity:campaign#(foo).duration>=31D'))
            self.len(3, await core.nodes('entity:campaign#(foo).duration>31D'))
            self.len(1, await core.nodes('entity:campaign#(foo).duration=?'))

            await core.nodes('''[
                (entity:campaign=* +#bar:_footime=(2020-01-01, 2020-01-02))
                (entity:campaign=* +#bar:_footime=(2021-01-01, 2021-02-01))
                (entity:campaign=* +#bar:_footime=(2022-01-01, 2022-05-01))
                (entity:campaign=* +#bar:_footime=(2023-01-01, 2024-01-01))
                (entity:campaign=* +#bar:_footime=(2024-01-01, 2026-01-01))
            ]''')

            self.len(1, await core.nodes('entity:campaign#bar:_footime.min=2020-01-01'))
            self.len(3, await core.nodes('entity:campaign#bar:_footime.min<2022-01-01'))
            self.len(4, await core.nodes('entity:campaign#bar:_footime.min<=2022-01-01'))
            self.len(3, await core.nodes('entity:campaign#bar:_footime.min>=2022-01-01'))
            self.len(2, await core.nodes('entity:campaign#bar:_footime.min>2022-01-01'))
            self.len(2, await core.nodes('entity:campaign#bar:_footime.min@=(2020-01-01, 2022-01-01)'))
            self.len(2, await core.nodes('reverse(entity:campaign#bar:_footime.min@=(2020-01-01, 2022-01-01))'))

            self.len(1, await core.nodes('entity:campaign#bar:_footime.max=2020-01-02'))
            self.len(2, await core.nodes('entity:campaign#bar:_footime.max<2022-05-01'))
            self.len(3, await core.nodes('entity:campaign#bar:_footime.max<=2022-05-01'))
            self.len(3, await core.nodes('entity:campaign#bar:_footime.max>=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign#bar:_footime.max>2022-05-01'))
            self.len(2, await core.nodes('entity:campaign#bar:_footime.max@=(2020-01-02, 2022-05-01)'))
            self.len(1, await core.nodes('entity:campaign#bar:_footime.max=?'))

            self.len(1, await core.nodes('entity:campaign#bar:_footime.duration=1D'))
            self.len(1, await core.nodes('entity:campaign#bar:_footime.duration<31D'))
            self.len(2, await core.nodes('entity:campaign#bar:_footime.duration<=31D'))
            self.len(4, await core.nodes('entity:campaign#bar:_footime.duration>=31D'))
            self.len(3, await core.nodes('entity:campaign#bar:_footime.duration>31D'))
            self.len(1, await core.nodes('entity:campaign#bar:_footime.duration=?'))

            await core.nodes('[ entity:campaign=(foo,) +#bar:_footime=(2018, 2022) ]')
            self.len(0, await core.nodes('entity:campaign#bar:_footime.max=?'))
            self.len(0, await core.nodes('entity:campaign#bar:_footime.min=2019-01-01'))

            await core.nodes('[ entity:campaign=(foo,) -:period -#foo -#bar:_footime ]')

            def staticnow():
                # 2021-01-01
                return 1609459200000000

            with mock.patch('synapse.common.now', staticnow):
                await core.callStorm('[ou:asset=* :period=(2020, *)] return(:period.duration)')
                await core.callStorm('[ou:asset=* :period=(2020, ?)] return(:period.duration)')
                await core.callStorm('[ou:asset=* :period=(2020, 2021)] return(:period.duration)')
                await core.callStorm('[ou:asset=* :period=(2020, 2022)] return(:period.duration)')

                self.len(1, await core.nodes('ou:asset:period.duration=*'))
                self.len(1, await core.nodes('ou:asset:period.duration=?'))

                nodes = await core.nodes('ou:asset:period.duration=366D')
                rnodes = await core.nodes('reverse(ou:asset:period.duration=366D)')
                self.len(2, nodes)
                self.eq(nodes[::-1], rnodes)

                self.len(2, await core.nodes('ou:asset:period.duration<367D'))
                self.len(0, await core.nodes('ou:asset:period.duration<365D'))
                self.len(1, await core.nodes('ou:asset:period.duration<=?'))
                self.len(0, await core.nodes('ou:asset:period.duration<?'))
                self.len(1, await core.nodes('ou:asset:period.duration<=*'))
                self.len(0, await core.nodes('ou:asset:period.duration<*'))

                nodes = await core.nodes('ou:asset:period.duration<367D')
                rnodes = await core.nodes('reverse(ou:asset:period.duration<367D)')
                self.len(2, nodes)
                self.eq(nodes[::-1], rnodes)

                self.len(1, await core.nodes('ou:asset:period.duration>366D'))
                self.len(1, await core.nodes('ou:asset:period.duration>=?'))
                self.len(0, await core.nodes('ou:asset:period.duration>?'))
                self.len(1, await core.nodes('ou:asset:period.duration>=*'))
                self.len(0, await core.nodes('ou:asset:period.duration>*'))

                nodes = await core.nodes('ou:asset:period.duration>365D')
                rnodes = await core.nodes('reverse(ou:asset:period.duration>365D)')
                self.len(3, nodes)
                self.eq(nodes[::-1], rnodes)

    async def test_layer_prop_virt_overrides(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()

            # A time precision virt is stored on the node but not indexed:
            # StorTypeTime opts out of the generic virtual index.
            await core.nodes('[ biz:deal=(d,) :updated=2020 ]')
            await core.nodes('biz:deal=(d,) [ :updated.precision=year ]')

            nid = (await core.nodes('biz:deal=(d,)'))[0].nid
            valu, stortype, virts = layr._getStorNode(nid)['props']['updated']

            self.isin('precision', virts)
            with self.raises(s_exc.NoSuchAbrv):
                core.getIndxAbrv(s_layer.INDX_VIRTUAL, 'biz:deal', 'updated', 'precision')

            # an ival precision virt is likewise not indexed (StorTypeIval opts
            # out; ival ordering is served by dedicated side indexes).
            await core.nodes('[ entity:campaign=(foo,) :period=(2020, 2021) ]')
            await core.nodes('entity:campaign=(foo,) [ :period.precision=year ]')

            nid = (await core.nodes('entity:campaign=(foo,)'))[0].nid
            valu, stortype, virts = layr._getStorNode(nid)['props']['period']

            self.isin('precision', virts)
            with self.raises(s_exc.NoSuchAbrv):
                core.getIndxAbrv(s_layer.INDX_VIRTUAL, 'entity:campaign', 'period', 'precision')

            # ival ordering virts are lifted via their side indexes
            self.len(1, await core.nodes('entity:campaign:period.began=2020'))

            # a pricechange currency virt is liftable, so it is indexed in the
            # generic virtual index.
            await core.nodes('[ econ:balance=(b,) :change=(100, 200) :change.currency=usd ]')
            self.len(1, await core.nodes('econ:balance:change.currency=usd'))

            # deleting the property removes its currency virt index
            await core.nodes('econ:balance=(b,) [ -:change ]')
            self.len(0, await core.nodes('econ:balance:change.currency=usd'))

            # a tagprop virt added on a value-unchanged edit is indexed
            await core.addTagProp('_cur', ('econ:pricechange', {}), {})
            await core.nodes('[ econ:balance=(b2,) :amount=100 +#foo:_cur=(1, 2) ]')

            await core.nodes('econ:balance=(b2,) [ +#foo:_cur.currency=usd ]')
            self.len(1, await core.nodes('econ:balance#foo:_cur.currency=usd'))

            # changing the currency re-indexes: only the new value matches
            await core.nodes('econ:balance=(b2,) [ +#foo:_cur.currency=eur ]')
            self.len(0, await core.nodes('econ:balance#foo:_cur.currency=usd'))
            self.len(1, await core.nodes('econ:balance#foo:_cur.currency=eur'))

            # a poly property's virts are indexed with a 2-byte member stortype prefix
            await core.nodes('[ test:str=serv :poly={[ inet:server=1.2.3.4:80 ]} ]')

            self.len(1, await core.nodes('test:str:poly.port=80'))

            abrv = core.getIndxAbrv(s_layer.INDX_VIRTUAL, 'test:str', 'poly', 'port')
            rows = list(layr.layrslab.scanByPref(abrv, db=layr.indxdb))
            self.len(1, rows)

            # the key carries the member stortype prefix (STOR_TYPE_I64 for port)
            self.eq(rows[0][0][len(abrv):len(abrv) + 2], s_layer.STOR_TYPE_I64.to_bytes(2, 'big'))
            self.eq(1, layr.indxcounts.get(abrv))

            # poly-array virts are also prefixed and remain liftable
            await core.nodes('[ test:arrayprop=(3,) :vers=(v1.2.3, v4.5.6) ]')
            self.len(1, await core.nodes('test:arrayprop:vers*[.semver=4.5.6]'))

            # deleting the poly property removes the virtual index row and its count
            await core.nodes('test:str=serv [ -:poly ]')
            self.len(0, list(layr.layrslab.scanByPref(abrv, db=layr.indxdb)))
            self.eq(0, layr.indxcounts.get(abrv))
            self.len(0, await core.nodes('test:str:poly.port=80'))

    async def test_layer_vers_index(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()

            # an ordered/range lift against a form:prop that has never had a
            # parseable it:version value indexed hits NoSuchAbrv (the side
            # index abrv doesn't exist yet) and returns nothing rather than
            # erroring.
            self.len(0, await core.nodes('it:hardware:version >= "1.0.0"'))

            await core.nodes('[ it:hardware=(hw,) :version=1.0.0 ]')
            other = (await core.nodes('[ it:hardware=(hw2,) ]'))[0]

            self.eq(['1.0.0'], [n.get('version')[1] for n in await core.nodes('it:hardware:version >= "1.0.0"')])

            # simulate a stale/orphaned side-index row (index present but the
            # target node has no :version prop) -- this can't happen via
            # normal edits, since delVirtIndxVals always removes the row
            # alongside the prop, so inject one directly to exercise the
            # defensive skip in StorTypeVers._liftVers / IndxByPropVersIndex's
            # getSodeValu (getNodeValu falls back to novalu, and the lifter
            # skips it rather than erroring).
            abrv = core.getIndxAbrv(s_layer.INDX_VERS_INDEX, 'it:hardware', 'version')
            lkey, _ = next(layr.layrslab.scanByPref(abrv, db=layr.indxdb))
            indx = lkey[len(abrv):]
            await layr.layrslab.put(abrv + indx, other.nid, db=layr.indxdb)

            # the stale row is silently skipped; the real match still returns
            self.eq(['1.0.0'], [n.get('version')[1] for n in await core.nodes('it:hardware:version >= "1.0.0"')])

    def getPropIndxRows(self, core, layr, form, prop):
        '''
        Return the (rows, ckeys) of every index which belongs to a single (form, prop):
        the prop and array value indexes, their side indexes, and the virtual property
        indexes. ckeys are the index count keys those rows are counted under, including
        the per-member-type key a poly value rides on the first 10 bytes of its index.
        '''
        rows = set()
        ckeys = set()

        for byts, abrv in core.indxabrv.items():

            args = s_msgpack.un(byts[2:])
            if len(args) < 2 or args[0] != form or args[1] != prop:
                continue

            ckeys.add(abrv)

            for lkey, nid in layr.layrslab.scanByPref(abrv, db=layr.indxdb):
                rows.add((lkey, nid))
                ckeys.add(abrv + lkey[len(abrv):len(abrv) + 10])

        return rows, ckeys

    async def reqPolyIndxRoundTrip(self, core, form, prop, setq, delq, opts=None):
        '''
        Require that setting and then deleting a poly property leaves the index exactly
        as it was found, and that what it stores in between describes itself: the layer
        de-indexes a value using only the stortype and virts held alongside it, so a
        triple which is not a Type.getStorInfo() fixpoint leaves rows no lift can find.
        '''
        layr = core.getLayer()
        ptyp = core.model.reqProp(f'{form}:{prop}').type

        rows, ckeys = self.getPropIndxRows(core, layr, form, prop)
        counts = {ckey: layr.indxcounts.get(ckey) for ckey in ckeys}

        nodes = await core.nodes(setq, opts=opts)
        self.len(1, nodes)

        valt = layr.getStorNode(nodes[0].nid).get('props', {}).get(prop)
        self.nn(valt)
        self.eq((valt[1], valt[2]), ptyp.getStorInfo(valt[0], virts=valt[2]))

        await core.nodes(delq, opts=opts)

        newrows, newckeys = self.getPropIndxRows(core, layr, form, prop)
        self.eq(rows, newrows)

        for ckey in ckeys | newckeys:
            self.eq(counts.get(ckey, 0), layr.indxcounts.get(ckey))

    async def test_layer_poly_index_roundtrip(self):

        polyvals = (
            'test:int=1',
            'inet:fqdn=foo.com',
            'inet:server=1.2.3.4:80',       # a comp member, which carries _stortypes
            'test:lowstr=HeHe',             # a folding member
        )

        async with self.getTestCore() as core:

            for valu in polyvals:
                setq = f'[ test:str=poly :poly={{[ {valu} ]}} ]'
                await self.reqPolyIndxRoundTrip(core, 'test:str', 'poly', setq, 'test:str=poly [ -:poly ]')

            # guid and comp members, which are keyed by their folded buid
            for valu in ('ps:person=*', 'test:comp=(1, foo)'):
                setq = f'[ test:str=poly :bar={{[ {valu} ]}} ]'
                await self.reqPolyIndxRoundTrip(core, 'test:str', 'bar', setq, 'test:str=poly [ -:bar ]')

            # an ival poly, which maintains the max and duration side indexes
            setq = '[ test:str=poly :seen=(2020, 2021) ]'
            await self.reqPolyIndxRoundTrip(core, 'test:str', 'seen', setq, 'test:str=poly [ -:seen ]')

            # poly arrays, including comp elements (_elemvirts) and duplicate elements
            setq = '[ test:str=poly :polyarry=(1, 2) ] [ :polyarry += {[ inet:server=1.2.3.4:80 ]} ]'
            await self.reqPolyIndxRoundTrip(core, 'test:str', 'polyarry', setq, 'test:str=poly [ -:polyarry ]')

            setq = '[ test:str=poly :polynonuniq=(foo, foo, bar, foo) ]'
            await self.reqPolyIndxRoundTrip(core, 'test:str', 'polynonuniq', setq, 'test:str=poly [ -:polynonuniq ]')

            # setStorNodeProp() builds the edit itself rather than going through the editor
            await core.nodes('[ test:str=stor ]')

            setq = 'test:str=stor $lib.layer.get().setStorNodeProp($node.nid, test:str:poly, foo.com)'
            await self.reqPolyIndxRoundTrip(core, 'test:str', 'poly', setq, 'test:str=stor [ -:poly ]')

            setq = 'test:str=stor $lib.layer.get().setStorNodeProp($node.nid, test:str:seen, (2020, 2021))'
            await self.reqPolyIndxRoundTrip(core, 'test:str', 'seen', setq, 'test:str=stor [ -:seen ]')

            setq = 'test:str=stor $lib.layer.get().setStorNodeProp($node.nid, test:str:polyarry, (foo, bar))'
            await self.reqPolyIndxRoundTrip(core, 'test:str', 'polyarry', setq, 'test:str=stor [ -:polyarry ]')

            # the poly member type count is maintained for every producer
            self.eq(0, await core.count('test:str:poly'))

            await core.nodes('[ test:str=c1 :poly={[ inet:fqdn=count.com ]} ]')
            await core.nodes('test:str=stor $lib.layer.get().setStorNodeProp($node.nid, test:str:poly, hehe)')

            view = core.getView()
            self.eq(1, await view.getPropCount('test:str:poly', type='inet:fqdn'))
            self.eq(1, await view.getPropCount('test:str:poly', type='test:str'))
            self.eq(0, await view.getPropCount('test:str:poly', type='test:int'))

            await core.nodes('test:str=c1 [ -:poly ]')
            await core.nodes('test:str=stor [ -:poly ]')

            self.eq(0, await view.getPropCount('test:str:poly', type='inet:fqdn'))
            self.eq(0, await view.getPropCount('test:str:poly', type='test:str'))

    async def test_layer_poly_index_movenodes(self):
        '''
        movenodes() merges a prop value across layers, so the stortype and virts it
        stores must describe the merged value rather than whichever layer was walked
        last, or the row it writes is one no lift can find.
        '''
        async with self.getTestCore() as core:

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            viewopts = {'view': viewiden}

            view = core.getView(viewiden)
            layr = core.getLayer(view.layers[0].iden)

            # the member types differ between the layers, as do the array lengths
            await core.nodes('[ test:str=move :poly={[ inet:server=1.2.3.4:80 ]} :polyarry=(1, 2) ]')
            await core.nodes('test:str=move [ :poly=hehe :polyarry=(3, 4, 5) ]', opts=viewopts)

            msgs = await core.stormlist('test:str=move | movenodes --apply', opts=viewopts)
            self.stormHasNoWarnErr(msgs)

            props = layr.getStorNode((await core.nodes('test:str=move', opts=viewopts))[0].nid).get('props')

            for prop in ('poly', 'polyarry'):
                valt = props.get(prop)
                self.nn(valt)

                ptyp = core.model.reqProp(f'test:str:{prop}').type
                self.eq((valt[1], valt[2]), ptyp.getStorInfo(valt[0], virts=valt[2]))

            # the moved values are still liftable from the layer they landed in
            self.len(1, await core.nodes('test:str:poly=hehe', opts=viewopts))
            self.len(1, await core.nodes('test:str:poly.type=test:str', opts=viewopts))

            for valu in (3, 4, 5):
                self.len(1, await core.nodes(f'test:str:polyarry*[={valu}]', opts=viewopts))

    async def reqMergeRoundTrip(self, core, setq, lift, prop=None, tagprop=None):
        '''
        Require that merging a node moves its property or tag property down intact: the
        parent layer must end up holding the same (valu, stortype, virts) triple the fork
        held. merge() re-norms through the editor, so a value which cannot be re-read from
        its stored form -- or which drops the virts stored with it -- shows up here.
        '''
        viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
        viewopts = {'view': viewiden}

        forklayr = core.getLayer(core.getView(viewiden).layers[0].iden)

        nodes = await core.nodes(setq, opts=viewopts)
        self.len(1, nodes)

        nid = nodes[0].nid

        def gettriple(layr):
            sode = layr.getStorNode(nid)
            if tagprop is not None:
                return sode.get('tagprops', {}).get(tagprop[0], {}).get(tagprop[1])
            return sode.get('props', {}).get(prop)

        before = gettriple(forklayr)
        self.nn(before)

        msgs = await core.stormlist(f'{lift} | merge --apply', opts=viewopts)
        self.stormHasNoWarnErr(msgs)

        self.eq(before, gettriple(core.getLayer()))

    async def test_layer_merge_roundtrip(self):

        async with self.getTestCore() as core:

            await core.addTagProp('_cur', ('econ:pricechange', {}), {})
            await core.addTagProp('_seen', ('ival', {}), {})

            # an array property: its members are typed tuples, so the stored value can only
            # be re-read as a typed value
            setq = '[ ou:conference=(c,) :names=(foo, bar) ]'
            await self.reqMergeRoundTrip(core, setq, 'ou:conference=(c,)', prop='names')

            setq = '[ test:str=arr :polyarry=(1, 2) ] [ :polyarry += {[ inet:server=1.2.3.4:80 ]} ]'
            await self.reqMergeRoundTrip(core, setq, 'test:str=arr', prop='polyarry')

            # a scalar property whose stored virt has to survive the re-norm
            setq = '[ test:str=pv :seen=(2020, 2021) ] [ :seen.precision=year ]'
            await self.reqMergeRoundTrip(core, setq, 'test:str=pv', prop='seen')

            # a tag property, both a plain one and one whose stored norm has more fields
            # than its constructor takes
            setq = '[ test:str=tp +#foo:_seen=(2020, 2021) ] [ +#foo:_seen.precision=year ]'
            await self.reqMergeRoundTrip(core, setq, 'test:str=tp', tagprop=('foo', '_seen'))

            setq = '[ econ:balance=(b,) +#foo:_cur=(1, 2) ] [ +#foo:_cur.currency=usd ]'
            await self.reqMergeRoundTrip(core, setq, 'econ:balance=(b,)', tagprop=('foo', '_cur'))

    async def test_layer_copyto_roundtrip(self):
        '''
        copyto() rebuilds each node in the destination view through the editor, so what it
        hands the setters has to be re-normable back into the value it read: an array whose
        members are typed values, and a property or tag property carrying its virts.
        '''
        async with self.getTestCore() as core:

            await core.addTagProp('_cur', ('econ:pricechange', {}), {})
            await core.addTagProp('_seen', ('ival', {}), {})

            q = '$l = $lib.layer.add() return($lib.view.add(layers=($l.iden,)).iden)'
            viewiden = await core.callStorm(q)

            destlayr = core.getLayer(core.getView(viewiden).layers[0].iden)
            srclayr = core.getLayer()

            cases = (
                ('[ ou:conference=(c,) :names=(foo, bar) ]', 'ou:conference=(c,)', ('props', 'names')),
                ('[ test:str=arr :polyarry=(1, 2) ] [ :polyarry += {[ inet:server=1.2.3.4:80 ]} ]',
                 'test:str=arr', ('props', 'polyarry')),
                ('[ test:str=pv :seen=(2020, 2021) ] [ :seen.precision=year ]',
                 'test:str=pv', ('props', 'seen')),
                ('[ test:str=tp +#foo:_seen=(2020, 2021) ] [ +#foo:_seen.precision=year ]',
                 'test:str=tp', ('tagprops', 'foo', '_seen')),
                ('[ econ:balance=(b,) +#foo:_cur=(1, 2) ] [ +#foo:_cur.currency=usd ]',
                 'econ:balance=(b,)', ('tagprops', 'foo', '_cur')),
            )

            for setq, lift, path in cases:

                nodes = await core.nodes(setq)
                self.len(1, nodes)

                nid = nodes[0].nid

                def gettriple(layr):
                    sode = layr.getStorNode(nid)
                    if path[0] == 'props':
                        return sode.get('props', {}).get(path[1])
                    return sode.get('tagprops', {}).get(path[1], {}).get(path[2])

                before = gettriple(srclayr)
                self.nn(before)

                msgs = await core.stormlist(f'{lift} | copyto {viewiden}')
                self.stormHasNoWarnErr(msgs)

                self.eq(before, gettriple(destlayr))

    async def test_layer_tagprop_hidden_virts(self):
        '''
        A hidden ("_" prefixed) virt carries index metadata rather than a value to index.
        No tagprop type produces one today, since a tagprop is never poly or array, but
        the tagprop virt indexers skip them the way the property path does rather than
        unpacking the metadata as a (valu, vtyp) pair.
        '''
        async with self.getTestCore() as core:

            layr = core.getLayer()

            await core.addTagProp('_cur', ('econ:pricechange', {}), {})
            nodes = await core.nodes('[ econ:balance=(b,) +#foo:_cur=(1, 2) ]')

            nid = nodes[0].nid
            stor = layr.stortypes[core.model.tagprop('_cur').type.stortype]
            tagabrv = core.getIndxAbrv(s_layer.INDX_TAG, None, 'foo')

            virts = {'currency': ('USD', s_layer.STOR_TYPE_UTF8)}
            hidden = virts | {'_stortypes': ((s_layer.STOR_TYPE_UTF8,), s_layer.STOR_TYPE_MSGP)}

            rows = stor.getTagPropVirtIndxVals(nid, 'econ:balance', 'foo', tagabrv, '_cur', virts)
            self.len(3, rows)
            self.eq(rows, stor.getTagPropVirtIndxVals(nid, 'econ:balance', 'foo', tagabrv, '_cur', hidden))

            # and the delete side skips it too, so the two stay symmetric
            self.none(stor.delTagPropVirtIndxVals(nid, 'econ:balance', 'foo', tagabrv, '_cur', hidden))

    async def test_layer_tagprop_index_movenodes(self):
        '''
        movenodes() merges a tagprop value across layers, so the virts it stores must
        be the ones belonging to the value it kept. A tagprop is never poly or array
        (TagProp clones a named type), but a virt which the layer indexes -- an
        econ:price currency, say -- still has to describe the value it rides with.
        '''
        async with self.getTestCore() as core:

            await core.addTagProp('_cur', ('econ:pricechange', {}), {})

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            viewopts = {'view': viewiden}

            view = core.getView(viewiden)
            layr = core.getLayer(view.layers[0].iden)

            await core.nodes('[ econ:balance=(b,) +#foo:_cur=(1, 2) ]')
            await core.nodes('econ:balance=(b,) [ +#foo:_cur.currency=eur ]')

            await core.nodes('econ:balance=(b,) [ +#foo:_cur=(1, 2) ]', opts=viewopts)
            await core.nodes('econ:balance=(b,) [ +#foo:_cur.currency=usd ]', opts=viewopts)

            msgs = await core.stormlist('econ:balance | movenodes --apply', opts=viewopts)
            self.stormHasNoWarnErr(msgs)

            # the write layer value wins, so its currency virt is the one which moves
            nodes = await core.nodes('econ:balance', opts=viewopts)
            self.len(1, nodes)

            sode = layr.getStorNode(nodes[0].nid)
            self.eq('USD', sode['tagprops']['foo']['_cur'][2]['currency'][0])

            self.len(1, await core.nodes('econ:balance#foo:_cur.currency=usd', opts=viewopts))
            self.len(0, await core.nodes('econ:balance#foo:_cur.currency=eur', opts=viewopts))

    async def test_layer_poly_indexes(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=polyarry :polyarry=(1, 2) ]')
            await core.nodes('test:str=polyarry [ :polyarry += {[inet:fqdn=woot.com]} ]')
            await core.nodes('[ test:str=p1 :poly={[test:int=1]} ]')
            await core.nodes('[ test:str=p2 :poly={[inet:fqdn=foo.com]} ]')
            await core.nodes('[ test:str=p3 ]')

            self.len(0, await core.nodes('test:str:poly={[test:str=newp]}'))

            self.len(1, await core.nodes('test:str:poly.type=test:int'))
            self.len(1, await core.nodes('test:str:poly.type=inet:fqdn'))
            self.len(0, await core.nodes('test:str:poly.type=test:str'))

            self.len(2, await core.nodes('test:str.created +:poly.type'))
            self.len(1, await core.nodes('test:str.created +:poly.type=inet:fqdn'))

            self.len(2, await core.nodes('test:str:polyarry*[.type=test:int]'))
            self.len(1, await core.nodes('test:str:polyarry*[.type=inet:fqdn]'))
            self.len(0, await core.nodes('test:str:polyarry*[.type=test:str]'))

            self.len(1, await core.nodes('test:str.created +:polyarry*[.type=inet:fqdn]'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:poly.type=newp')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('test:str:poly.newp=newp')

            await core.nodes('test:str [ -:poly ]')

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            await core.nodes('[ test:str=foo :poly=4 ]', opts=viewopts2)
            await core.nodes('[ test:str=foo :poly=4 ]')

            nodes = await core.nodes('test:int=4 <- *', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'foo'))

            await core.nodes('[ test:str=foo :poly=5 ]', opts=viewopts2)
            self.len(0, await core.nodes('test:int=4 <- *', opts=viewopts2))

            await core.nodes('[ test:str=foo -:poly ]', opts=viewopts2)
            self.len(0, await core.nodes('test:int=4 <- *', opts=viewopts2))

            await core.nodes('[ test:str=bar :poly=4 ]')
            nodes = await core.nodes('test:int=4 <- *', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'bar'))

            self.len(1, await core.nodes('test:int=4 <- *', opts=viewopts2))

            await core.nodes('test:str=polyarry [ :polyarry={test:str=foo} ]', opts=viewopts2)
            self.len(0, await core.nodes('test:int=1 <- *', opts=viewopts2))

            await core.nodes('test:str=polyarry [ -:polyarry ]', opts=viewopts2)
            self.len(0, await core.nodes('test:str=foo <- *', opts=viewopts2))

            q = '[ test:str=polyarry :polynonuniq=(foo, foo, bar, foo) ]'
            await core.nodes(q, opts=viewopts2)

            self.len(3, await core.nodes('test:str=foo <- *', opts=viewopts2))
            self.len(4, await core.nodes('test:str=polyarry -> *', opts=viewopts2))
            self.len(4, await core.nodes('test:str=polyarry :polynonuniq -> *', opts=viewopts2))

            q = '[ test:str=polyarry :polynonuniq=(foo, bar) ]'
            await core.nodes(q, opts=viewopts2)

            self.len(2, await core.nodes('test:str=polyarry -> *', opts=viewopts2))
            self.len(2, await core.nodes('test:str=polyarry :polynonuniq -> *', opts=viewopts2))

            layr = core.getLayer()
            indxby = s_layer.IndxByPoly(layr, 'test:str', 'poly', s_layer.STOR_TYPE_UTF8)
            self.eq(str(indxby), 'IndxByPoly: test:str:poly')

            nodes = await core.nodes('[ test:str=newp ]')
            self.eq(s_common.novalu, indxby.getSodeValu(nodes[0].sodes[0]))
            self.eq(s_common.novalu, indxby.getNodeValu(s_common.int64en(1337)))

            indxby = s_layer.IndxByPolyArray(layr, 'test:str', 'polyarry', s_layer.STOR_TYPE_UTF8)
            self.eq(str(indxby), 'IndxByPolyArray: test:str:polyarry')

            abrv = core.getIndxAbrv(s_layer.INDX_PROP, 'test:str', 'poly')
            indx = layr.polytype.indx(('test:str', 'a' * 500))[0]
            self.eq(s_common.novalu, indxby.getNodeValu(nodes[0].nid, lkey=abrv + indx))
            self.eq(s_common.novalu, indxby.getNodeValu(s_common.int64en(1337), lkey=abrv + indx))

            indxby = s_layer.IndxByPolyArrayKeys(layr, 'test:str', 'polyarry', s_layer.STOR_TYPE_UTF8)
            self.eq(str(indxby), 'IndxByPolyArrayKeys: test:str:polyarry')

            await core.nodes('[ test:str=serv :poly={[ inet:server=1.2.3.4:80 ]} ]')

            indxby = s_layer.IndxByPolyVirt(layr, 'test:str', 'poly', 'port', s_layer.STOR_TYPE_I64)
            self.eq(str(indxby), 'IndxByPolyVirt: test:str:poly.port')

    async def test_layer_virt_indexes(self):

        async with self.getTestCore() as core:

            await core.nodes('''[
                inet:server=tcp://127.0.0.1:12341
                inet:server=tcp://127.0.0.3:12343
                inet:server=tcp://127.0.0.2:12342
                inet:server="tcp://[::3]:12343"
                inet:server="tcp://[::1]:12341"
                inet:server="tcp://[::2]:12342"
                (inet:http:request=* :server=tcp://127.0.0.4:12344)
                (inet:http:request=* :server=tcp://127.0.0.5:12345)
                (inet:http:request=* :server=tcp://127.0.0.6:12346)
                (inet:http:request=* :server="tcp://[::4]:12344")
                (inet:http:request=* :server="tcp://[::5]:12345")
                (inet:http:request=* :server="tcp://[::6]:12346")
                (test:guid=* :server=tcp://127.0.0.4:12344)
                (test:guid=* :server=tcp://127.0.0.5:12345)
                (test:guid=* :server=tcp://127.0.0.6:12346)
                (test:guid=* :server="tcp://[::4]:12344")
                (test:guid=* :server="tcp://[::5]:12345")
                (test:guid=* :server="tcp://[::6]:12346")
                (inet:http:request=* :flow={[ inet:flow=* :client=tcp://127.0.0.1:12341 ]})
                (inet:http:request=* :flow={[ inet:flow=* :client=tcp://127.0.0.2:12342 ]})
                (inet:http:request=* :flow={[ inet:flow=* :client=tcp://127.0.0.3:12343 ]})
                (inet:http:request=* :flow={[ inet:flow=* :client="tcp://[::4]:12344" ]})
                (inet:http:request=* :flow={[ inet:flow=* :client="tcp://[::5]:12345" ]})
                (inet:http:request=* :flow={[ inet:flow=* :client="tcp://[::6]:12346" ]})
                (test:virtiface=(if1,) :servers=(tcp://127.0.0.1:12341, tcp://127.0.0.2:12342))
                (test:virtiface=(if2,) :servers=("tcp://[::1]:12341", "tcp://[::2]:12342"))
                (test:virtiface=(if3,) :servers=("tcp://127.0.0.1:12341", "tcp://[::2]:12342"))
                (test:str=piv1 :pivvirt=(if1,) as test:virtiface)
                (test:str=piv2 :pivvirt=(if2,) as test:virtiface)
            ]''')

            self.len(12, await core.nodes('inet:server.ip'))
            self.len(12, await core.nodes('inet:server.port'))
            self.len(1, await core.nodes('inet:server.ip=127.0.0.1'))
            self.len(2, await core.nodes('inet:server.ip*range=(127.0.0.2, 127.0.0.3)'))
            nodes = await core.nodes('inet:server.ip="::1"')
            self.len(1, nodes)
            self.eq(nodes[0].valu(), 'tcp://[::1]:12341')

            self.eq((4, 2130706433), await core.callStorm('inet:server.ip return(.ip)'))
            self.propeq((await core.nodes('inet:server.ip'))[0], '.ip', (4, 2130706433))

            self.len(6, await core.nodes('inet:ip -> inet:http:request:server.ip'))

            self.len(6, await core.nodes('inet:http:request :server.ip -> *'))
            self.len(6, await core.nodes('inet:http:request :server.ip -> inet:ip'))
            self.len(3, await core.nodes('inet:http:request :server.ip -> inet:flow:client.ip'))
            self.len(6, await core.nodes('$foo=inet:ip inet:http:request :server.ip -> $foo'))

            q = 'inet:http:request :server.ip -> (inet:flow:client.ip, test:guid:server.ip)'
            self.len(9, await core.nodes(q))
            q = '$foo=test:guid:server inet:http:request :server.ip -> ($foo).ip'
            self.len(6, await core.nodes(q))
            q = '$foo=test:guid:server $bar=ip inet:http:request :server.$bar -> ($foo).$bar'
            self.len(6, await core.nodes(q))
            q = '$foo=test:guid:server inet:http:request :server.ip -> (($foo).ip, inet:flow:client.ip)'
            self.len(9, await core.nodes(q))
            q = '$foo=test:guid:server $bar=ip inet:http:request :server.ip -> (($foo).$bar, inet:flow:client.$bar)'
            self.len(9, await core.nodes(q))
            q = '$foo=(test:guid:server, inet:flow:client) inet:http:request :server.ip -> ($foo).ip'
            self.len(9, await core.nodes(q))

            self.len(12, await core.nodes('.created +inet:server.ip'))
            self.len(12, await core.nodes('inet:server.created +inet:server.ip'))
            self.len(12, await core.nodes('inet:server.created +inet:server.port'))
            self.len(1, await core.nodes('inet:server.created +inet:server.ip=127.0.0.2'))
            self.len(2, await core.nodes('inet:server.created +inet:server.ip*range=(127.0.0.2, 127.0.0.3)'))
            self.len(12, await core.nodes('inet:server.created +.ip'))
            self.len(12, await core.nodes('inet:server.created +.port'))
            self.len(1, await core.nodes('inet:server.created +.ip=127.0.0.2'))
            self.len(2, await core.nodes('inet:server.created +.ip*range=(127.0.0.2, 127.0.0.3)'))

            self.len(6, await core.nodes('inet:http:request:server.ip'))
            self.len(6, await core.nodes('inet:http:request:server.port'))
            self.len(1, await core.nodes('inet:http:request:server.ip=127.0.0.5'))
            self.len(1, await core.nodes('inet:http:request:server.ip="::5"'))
            self.len(2, await core.nodes('inet:http:request:server.ip*range=(127.0.0.5, 127.0.0.6)'))

            self.len(6, await core.nodes('inet:http:request.created +:server.ip'))
            self.len(1, await core.nodes('inet:http:request.created +:server.ip=127.0.0.4'))
            self.len(2, await core.nodes('inet:http:request.created +:server.ip*range=(127.0.0.4, 127.0.0.5)'))

            self.len(6, await core.nodes('inet:proto:request:server.ip'))
            self.len(6, await core.nodes('inet:proto:request:server.port'))
            self.len(1, await core.nodes('inet:proto:request:server.ip=127.0.0.5'))
            self.len(1, await core.nodes('inet:proto:request:server.ip="::5"'))
            self.len(2, await core.nodes('inet:proto:request:server.ip*range=(127.0.0.5, 127.0.0.6)'))

            self.len(6, await core.nodes('inet:proto:request +inet:proto:request:server.ip'))
            self.len(1, await core.nodes('inet:proto:request +inet:proto:request:server.ip=127.0.0.4'))
            self.len(2, await core.nodes('inet:proto:request +inet:proto:request:server.ip*range=(127.0.0.4, 127.0.0.5)'))

            self.len(6, await core.nodes('test:guid:server.ip'))
            self.len(6, await core.nodes('test:guid:server.port'))
            self.len(1, await core.nodes('test:guid:server.ip=127.0.0.5'))
            self.len(1, await core.nodes('test:guid:server.ip="::5"'))
            self.len(2, await core.nodes('test:guid:server.ip*range=(127.0.0.5, 127.0.0.6)'))

            self.len(6, await core.nodes('test:guid.created +:server.ip'))
            self.len(1, await core.nodes('test:guid.created +:server.ip=127.0.0.4'))
            self.len(2, await core.nodes('test:guid.created +:server.ip*range=(127.0.0.4, 127.0.0.5)'))

            self.len(1, await core.nodes('inet:http:request.created +:flow::client.ip=127.0.0.2'))
            self.len(2, await core.nodes('inet:http:request.created +:flow::client.ip*range=(127.0.0.2, 127.0.0.3)'))
            self.len(2, await core.nodes('inet:http:request.created +:flow::client.ip>"::4"'))
            self.len(2, await core.nodes('inet:http:request.created +:flow::client.ip*range=("::5", "::6")'))

            self.len(2, await core.nodes('test:virtiface.created +:servers*[.ip=127.0.0.1]'))
            self.len(2, await core.nodes('test:virtiface.created +:servers*[.ip="::2"]'))
            self.len(2, await core.nodes('test:virtiface.created +:servers*[.ip*range=(127.0.0.1, 127.0.0.2)]'))

            self.len(2, await core.nodes('test:virtiface:servers*[.ip=127.0.0.1]'))
            self.len(2, await core.nodes('test:virtiface:servers*[.ip="::2"]'))
            self.len(3, await core.nodes('test:virtiface:servers*[.ip*range=(127.0.0.1, 127.0.0.2)]'))

            self.len(2, await core.nodes('test:virtarray:servers*[.ip=127.0.0.1]'))
            self.len(2, await core.nodes('test:virtarray:servers*[.ip="::2"]'))
            self.len(3, await core.nodes('test:virtarray:servers*[.ip*range=(127.0.0.1, 127.0.0.2)]'))

            self.len(3, await core.nodes('test:virtiface.created +:servers.size=2'))
            self.len(3, await core.nodes('test:virtiface.created +:servers.size>1'))
            self.len(0, await core.nodes('test:virtiface.created +:servers.size>2'))

            self.len(3, await core.nodes('test:virtiface:servers.size=2'))
            self.len(0, await core.nodes('test:virtiface:servers.size=3'))
            self.len(3, await core.nodes('test:virtiface:servers.size>1'))
            self.len(0, await core.nodes('test:virtiface:servers.size>2'))
            self.len(3, await core.nodes('test:virtiface:servers.size<3'))
            self.len(0, await core.nodes('test:virtiface:servers.size<2'))
            self.len(3, await core.nodes('test:virtiface:servers.size*range=(1, 3)'))
            self.len(0, await core.nodes('test:virtiface:servers.size*range=(3, 4)'))

            self.len(1, await core.nodes('test:str:pivvirt::servers*[.ip=127.0.0.1]'))

            nodes = await core.nodes('test:virtarray:servers.size=2')
            self.len(3, nodes)
            self.eq(nodes[::-1], await core.nodes('reverse(test:virtarray:servers.size=2)'))

            nodes = await core.nodes('test:virtarray:servers.size*range=(2, 3)')
            self.len(3, nodes)
            self.eq(nodes[::-1], await core.nodes('reverse(test:virtarray:servers.size*range=(2, 3))'))

            self.len(1, await core.nodes('test:virtiface:servers=("tcp://[::1]:12341", "tcp://[::2]:12342")'))
            self.len(1, await core.nodes('reverse(test:virtiface:servers=("tcp://[::1]:12341", "tcp://[::2]:12342"))'))

            # repr with poly prop virt where prop is not set returns None
            nodes = await core.nodes('[ test:guid=* ]')
            self.none(nodes[0].repr('server.ip'))

            # getWithLayer with getr
            nodes = await core.nodes('inet:http:request:server.ip=127.0.0.4')
            prop = core.model.prop('inet:http:request:server')
            getr = prop.type.getVirtGetr('ip')
            valu, layr = nodes[0].getWithLayer('server', getr=getr)
            self.nn(valu)

            await core.nodes('inet:http:request:server.ip | [ -:server ]')
            self.len(0, await core.nodes('inet:http:request:server.ip'))

            await core.nodes('test:guid:server.ip | [ -:server ]')
            self.len(0, await core.nodes('test:guid:server.ip'))

            await core.nodes('test:virtiface:servers | [ -:servers ]')
            self.len(0, await core.nodes('test:virtiface:servers*[.ip=127.0.0.1]'))

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            nodes = await core.nodes('inet:server=tcp://127.0.0.4:12344', opts=viewopts2)
            self.len(1, nodes)

            await core.nodes('inet:server=tcp://127.0.0.4:12344 | delnode', opts=viewopts2)
            self.len(0, await core.nodes('inet:server=tcp://127.0.0.4:12344', opts=viewopts2))
            self.len(0, await core.nodes('inet:server.ip=127.0.0.4', opts=viewopts2))
            self.len(1, await core.nodes('inet:server.ip=127.0.0.4'))

            node = await view2.getNodeByNdef(nodes[0].ndef, tombs=True)
            self.none(node.valu(getr='foo'))
            self.none(node.valuvirts())

            await core.nodes('[ inet:server=tcp://127.0.0.4:12344 +(refs)> { inet:server=tcp://127.0.0.4:12344 }]', opts=viewopts2)
            await core.nodes('inet:server=tcp://127.0.0.4:12344 [+(refs)> { inet:server=tcp://127.0.0.4:12344 }]', opts=viewopts2)
            self.len(1, await core.nodes('inet:server.ip=127.0.0.4', opts=viewopts2))

            nodes = await core.nodes('[ test:str=foo ]')
            await core.nodes('[ test:str=foo :seen=now ]', opts=viewopts2)
            await core.nodes('test:str=foo | delnode')

            node = await view2.getNodeByNdef(nodes[0].ndef, tombs=True)
            self.none(node.valu(getr='foo'))

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('inet:server +.ip*newp=newp')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('inet:server.newp.ip')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('inet:server.ip.newp')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('inet:server.newp.ip=127.0.0.1')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('inet:server +.ip.newp=127.0.0.1')

            await core.nodes('inet:server.ip | delnode')
            self.len(0, await core.nodes('inet:server.ip'))

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:virtiface:servers*[newp=127.0.0.1]')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('test:virtiface:servers*[.newp*newp=127.0.0.1]')

            # TODO check possible types and their virts to raise
            # with self.raises(s_exc.NoSuchVirt):
            #    await core.nodes('test:virtiface +:servers*[.newp*newp=127.0.0.1]')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:virtiface +:servers*[@=127.0.0.1]')

            # TODO check possible types and their virts to raise
            # with self.raises(s_exc.NoSuchVirt):
            #    await core.nodes('inet:proto:request +inet:proto:request:server.newp*newp=newp')

            with self.raises(s_exc.BadCmprType):
                await core.nodes('inet:proto:request +:server*[newp=newp]')

            # TODO check possible types and their virts to raise
            # with self.raises(s_exc.NoSuchVirt):
            #    await core.nodes('test:guid +test:guid:server.newp*newp=newp')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:guid +.created.newp*newp=newp')

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('test:guid.created +:newp.ip=newp')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:guid +test:guid.created*newp=newp')

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('test:virtiface +:newp*[.ip=127.0.0.1]')

            with self.raises(s_exc.BadCmprType) as exc:
                await core.nodes('test:virtiface:server*[.ip=127.0.0.1]')
            self.isin('Array syntax is invalid on non array type', exc.exception.get('mesg'))

            # TODO check possible types and their virts to raise
            # with self.raises(s_exc.NoSuchCmpr):
            #    await core.nodes('test:virtiface:server +test:virtiface:server.ip*newp=newp')

            self.len(0, await core.nodes('$val = (null) test:guid.created +:server.ip=$val'))
            self.len(0, await core.nodes('test:guid.created +:newp::servers.ip=127.0.0.1'))
            self.len(0, await core.nodes('test:virtiface +:newp::servers*[.ip=127.0.0.1]'))
            self.len(0, await core.nodes('test:guid.created +:server.newp'))
            self.len(0, await core.nodes('test:guid +test:str.created<now'))
            self.len(0, await core.nodes('test:guid +inet:server.ip=1.2.3.4'))
            self.len(0, await core.nodes('test:guid +inet:http:request:server.ip=1.2.3.4'))

            self.none(await core.callStorm('test:guid.created return(:newp::servers)'))

            # getVirtIndx with invalid virt name
            ival = core.model.type('ival')
            with self.raises(s_exc.NoSuchVirt):
                ival.getVirtIndx('newp')

            # RuntNode.valu with getr
            nodes = await core.nodes('syn:form=inet:server')
            runtnode = nodes[0]
            self.eq(runtnode.valu(getr=lambda x: x[0]), 'inet:server')

            layr = core.getLayer()
            indxby = s_layer.IndxByVirt(layr, 'inet:http:request', 'server', 'ip')
            self.eq(str(indxby), 'IndxByVirt: inet:http:request:server.ip')

            indxby = s_layer.IndxByVirt(layr, 'test:guid', 'server', 'ip')
            self.eq(str(indxby), 'IndxByVirt: test:guid:server.ip')

            indxby = s_layer.IndxByVirt(layr, 'test:virtiface', 'servers', 'ip')
            self.eq(str(indxby), 'IndxByVirt: test:virtiface:servers.ip')

            indxby = s_layer.IndxByProp(layr, 'test:guid', 'server')
            self.eq(str(indxby), 'IndxByProp: test:guid:server')

            indxby = s_layer.IndxByPropKeys(layr, 'test:guid', 'server')
            self.eq(str(indxby), 'IndxByPropKeys: test:guid:server')

            indxby = s_layer.IndxByPropArray(layr, 'test:virtiface', 'servers')
            self.eq(str(indxby), 'IndxByPropArray: test:virtiface:servers')

            indxby = s_layer.IndxByPropArrayKeys(layr, 'test:virtiface', 'servers')
            self.eq(str(indxby), 'IndxByPropArrayKeys: test:virtiface:servers')

            indxby = s_layer.IndxByPropArrayValu(layr, 'test:virtiface', 'servers')
            self.eq(str(indxby), 'IndxByPropArrayValu: test:virtiface:servers')

            indxby = s_layer.IndxByPropArraySize(layr, 'test:virtiface', 'servers')
            self.eq(str(indxby), 'IndxByPropArraySize: test:virtiface:servers')

    async def test_layer_readahead(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()
            self.true(layr.layrslab.readahead)
            self.true(layr.layrslab.lenv.flags()['readahead'])
            self.false(layr.dataslab.readahead)
            self.false(layr.dataslab.lenv.flags()['readahead'])

            with self.setTstEnvars(SYNDEV_CORTEX_LAYER_READAHEAD='false'):
                iden = await core.callStorm('return($lib.layer.add().iden)')
                layr = core.getLayer(iden)
                self.false(layr.layrslab.readahead)
                self.false(layr.layrslab.lenv.flags()['readahead'])
                self.false(layr.dataslab.readahead)
                self.false(layr.dataslab.lenv.flags()['readahead'])

    async def test_layer_delete_with_nodedata(self):

        async with self.getTestCore() as core:

            fork00 = await core.view.fork()
            infork00 = {'view': fork00['iden']}
            layr00 = core.getLayer(fork00['layers'][0]['iden'])

            iden = await core.callStorm('[ inet:ip=1.2.3.4 ] return($node.nid)')

            sodes = await s_t_utils.alist(layr00.getStorNodesByForm('inet:ip'))
            self.len(0, sodes)

            q = '''
                inet:ip=1.2.3.4
                $node.data.set("key", "valu")
            '''
            await core.callStorm(q, opts=infork00)

            nodes = await core.nodes('inet:ip=1.2.3.4')
            nid = nodes[0].nid

            sodes = await s_t_utils.alist(layr00.getStorNodesByForm('inet:ip'))
            self.len(1, sodes)
            self.len(1, await alist(layr00.iterNodeData(nid)))

            q = '''
                view.exec $fork00 {
                    yield $iden
                    $lib.print($node)
                    delnode --deledges --force
                }
            '''
            opts = {'vars': {'iden': iden, 'fork00': fork00['iden']}}
            await core.callStorm(q, opts=opts)

            sodes = await s_t_utils.alist(layr00.getStorNodesByForm('inet:ip'))
            self.len(1, sodes)
            self.true(sodes[0][1].get('antivalu'))

            self.len(0, await alist(layr00.iterNodeData(nid)))

    async def test_layer_deleted_fork_edits(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:

                vdef2 = await core00.view.fork()
                opts2 = {'view': vdef2.get('iden')}

                await core00.nodes('[ test:str=foo ]', opts=opts2)

                vdef3 = await core00.view.fork()
                opts3 = {'view': vdef3.get('iden')}

                await core00.nodes('[ test:str=bar ]', opts=opts3)

            s_tools_backup.backup(path00, path01)

            async with self.getTestCore(dirn=path00) as core00:

                url = core00.getLocalUrl()

                core01conf = {'parent': url}

                async with self.getTestCore(dirn=path01, conf=core01conf) as core01:

                    await core01.sync()

                    indx = await core00.getNexsIndx()

                    # attempt to edit a node in a deleted layer from the leader
                    with self.raises(s_exc.NoSuchLayer):
                        await core00.nodes('''
                            test:str=foo
                            $lib.view.del($lib.view.get().iden)
                            $lib.layer.del($lib.layer.get().iden)
                            [ :seen=2020 ]''', opts=opts2)

                    await core01.sync()

                    evnts = [n[1][1] for n in await alist(core00.nexsroot.nexslog.iter(indx))]
                    self.eq(['view:del', 'layer:del', 'sync'], evnts)

                await core00.nodes('''
                    $lib.view.del($lib.view.get().iden)
                    $lib.layer.del($lib.layer.get().iden)
                    ''', opts=opts3)

            # attempt to edit a node on the mirror in a layer that has been deleted on the leader.
            # It is important that we patch out the mirror loop to delay its startup, so that the
            # loop on the follower does not race against the storm query execution on the mirror.
            evnt = asyncio.Event()
            original_loop = s_nexus.NexsRoot.runMirrorLoop
            async def delayedMirrorLoop(nexsroot, proxy):
                await asyncio.wait_for(evnt.wait(), timeout=12)
                return await original_loop(nexsroot, proxy)

            with mock.patch('synapse.lib.nexus.NexsRoot.runMirrorLoop', delayedMirrorLoop):
                async with self.getTestCore(dirn=path01, conf=core01conf) as core01:

                    indx = await core01.getNexsIndx()

                    async def doEdit():
                        with self.raises(s_exc.NoSuchLayer) as cm:
                            await core01.nodes('test:str=bar [ :seen=2020 ]', opts=opts3)
                        evnt.set()

                    task = core01.schedCoro(doEdit())

                    async with self.getTestCore(dirn=path00) as core00:

                        await asyncio.wait_for(task, timeout=6)

                        await core01.sync()

                        # Ensure that the mirror eventually catches up and does not have the failed edits.
                        evnts = [n[1][1] for n in await alist(core01.nexsroot.nexslog.iter(indx))]
                        self.eq(['view:del', 'layer:del', 'sync'], evnts)

    async def test_layer_migrate_props_fork(self):

        async with self.getTestCore() as core:

            fork00 = await core.view.fork()
            layr00 = core.getLayer(fork00['layers'][0]['iden'])
            infork = {'view': fork00['iden']}

            await core.nodes('''
                $typeopts = ({'enums': [[10, "low"], [20, "medium"], [30, "high"]]})
                $lib.model.ext.addType('_custom:risk:level', 'int', $typeopts, ({}))

                for $prop in (_custom:risk:level, _custom:risk:severity) {
                    $lib.model.ext.addFormProp(
                        test:guid,
                        $prop,
                        (["_custom:risk:level", {}]),
                        ({"doc": "hey now"}),
                    )
                }

            ''')
            self.len(1, await core.nodes('syn:prop=test:guid:_custom:risk:level'))
            self.len(1, await core.nodes('syn:prop=test:guid:_custom:risk:severity'))

            # Full node in the default layer
            nodes = await core.nodes('[ test:guid=* :name=test0 :_custom:risk:level=high ]')
            self.len(1, nodes)
            testnode00 = nodes[0].pack()

            # Make some edits in the fork layer
            q = '''
                test:guid
                [
                    :_custom:risk:level=medium
                    <(seen)+ {[ meta:source=* ]}
                    +(refs)> {[ test:str=foobar ]}
                ]
                $node.data.set(foo, foo)
                $node.data.set(bar, bar)
                $node.data.set(baz, baz)
            '''
            msgs = await core.stormlist(q, opts=infork)
            self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes('test:str=foobar', opts=infork)
            self.len(1, nodes)
            refs = nodes[0]

            # Edit a prop on the node in the default layer
            await core.nodes('test:guid [ :_custom:risk:level=medium ]', opts=infork)

            # Full node in the fork layer
            nodes = await core.nodes('[ test:guid=* :name=test1 :_custom:risk:level=low ]', opts=infork)
            self.len(1, nodes)

            await core.getView(fork00['iden']).delete()

            # Can't delete prop because we iterated through the views and there's a _custom:risk:level prop in an
            # orphaned layer
            with self.raises(s_exc.CantDelProp) as cm:
                await core.callStorm('''
                    $fullprop = "test:guid:_custom:risk:level"
                    for $view in $lib.view.list(deporder=(true)) {
                        view.exec $view.iden {
                            yield $lib.layer.get().liftByProp($fullprop)
                            $repr = $node.repr("_custom:risk:level")
                            [ :_custom:risk:severity=$repr -:_custom:risk:level ]
                        }
                    }
                    $lib.model.ext.delFormProp("test:guid", "_custom:risk:level")
                ''')
            self.eq(cm.exception.get('mesg'), f'Nodes still exist with prop: test:guid:_custom:risk:level in layer {layr00.iden}')
            self.len(1, await core.nodes('syn:prop=test:guid:_custom:risk:level'))

            # Migrate layer
            await core.callStorm('''
                $fullprop = "test:guid:_custom:risk:level"
                for $layer in $lib.layer.list() {
                    for ($nid, $sode) in $layer.getStorNodesByProp($fullprop) {
                        $oldv = $sode.props."_custom:risk:level"
                        $layer.setStorNodeProp($nid, "test:guid:_custom:risk:severity", $oldv.0.1)
                        $layer.delStorNodeProp($nid, $fullprop)

                        $layer.delNodeData($nid, foo)
                        $layer.delNodeData($nid, bar)

                        for ($verb, $n2nid, $tomb) in $layer.getEdgesByN2($nid) {
                            $layer.delEdge($n2nid, $verb, $nid)
                        }
                    }
                }
                $lib.model.ext.delFormProp("test:guid", "_custom:risk:level")
            ''')

            nodes = await core.nodes('syn:prop=test:guid:_custom:risk:level')
            self.len(0, nodes)

            nodes = await core.nodes('test:guid:_custom:risk:severity')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, testnode00[0])
            self.propeq(nodes[0], 'name', testnode00[1]['props']['name'][0])
            self.propeq(nodes[0], '_custom:risk:severity', testnode00[1]['props']['_custom:risk:level'][0])

            view00 = (await core.addView(vdef={'layers': [layr00.iden, core.view.layers[0].iden]}))['iden']
            inview = {'view': view00}

            nodes = await core.nodes('test:guid:name=test1', opts=inview)
            self.len(1, nodes)
            self.none(nodes[0].get('_custom:risk:level'))
            self.propeq(nodes[0], '_custom:risk:severity', 10)

            nodes = await core.nodes('test:guid:name=test0', opts=inview)
            self.len(1, nodes)
            self.none(nodes[0].get('_custom:risk:level'))
            self.propeq(nodes[0], '_custom:risk:severity', 20)
            self.eq(await s_t_utils.alist(nodes[0].iterData()), [('baz', 'baz')])
            self.eq(await s_t_utils.alist(nodes[0].iterEdgesN1()), [('refs', refs.nid)])
            self.len(0, await s_t_utils.alist(nodes[0].iterEdgesN2()))

            msgs = await core.stormlist('test:guid:name=test0 $lib.layer.get().delStorNode($node.nid)', opts=inview)

            nodes = await core.nodes('test:guid:name=test0', opts=inview)
            self.len(1, nodes)
            self.none(nodes[0].get('_custom:risk:level'))
            self.propeq(nodes[0], '_custom:risk:severity', 30)
            self.len(0, await s_t_utils.alist(nodes[0].iterData()))
            self.len(0, await s_t_utils.alist(nodes[0].iterEdgesN1()))
            self.len(0, await s_t_utils.alist(nodes[0].iterEdgesN2()))

    async def test_layer_nonuniq_arrays(self):

        async with self.getTestCore() as core:

            # Non-uniq arrays should yield nodes for each instance of a matching value
            self.len(1, await core.nodes('[ test:arrayprop=(0,) :strs=(foo, bar, baz, foobar, foobar) ]'))
            self.len(2, await core.nodes('test:arrayprop:strs*[=foobar]'))
            self.len(3, await core.nodes('test:arrayprop:strs*[~=foo]'))

            self.len(1, await core.nodes('[test:str=virts :polyarry={[test:str=foo1 test:int=3]}]'))
            self.len(1, await core.nodes('test:str:polyarry*[.type=test:str]'))

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            viewopts2 = {'view': viewiden2, 'vars': {'long': 'a' * 500}}

            await core.nodes('[ test:arrayprop=(foo,) :ints=(1, 2, 3, 3) ]', opts=viewopts2)
            await core.nodes('[ test:arrayprop=(foo,) :ints=(1, 2, 3, 3) ]')

            self.len(2, await core.nodes('test:arrayprop:ints*[=3]', opts=viewopts2))
            self.len(3, await core.nodes('test:arrayprop:ints*[>1]', opts=viewopts2))

            await core.nodes('test:arrayprop=(foo,) | delnode', opts=viewopts2)
            self.len(0, await core.nodes('test:arrayprop:ints*[=3]', opts=viewopts2))
            self.len(0, await core.nodes('test:arrayprop:ints*[>1]', opts=viewopts2))

            # Bad data test coverage
            nodes = await core.nodes('test:str=virts')
            sode = nodes[0].sodes[0]
            sode['props']['polyarry'] = ((('test:int', 3),), *sode['props']['polyarry'][1:])
            self.len(0, await core.nodes('test:str:polyarry*[.type=test:str]'))
            self.len(1, await core.nodes('test:str:polyarry*[.type=test:int]'))

            forkview = core.getView(viewiden2)
            await core.nodes('[ test:arrayprop=(0,) :strs=($long, $long) ]', opts=viewopts2)
            self.len(2, await core.nodes('test:arrayprop:strs*[={[test:str=$long]}]', opts=viewopts2))

            nodes = await core.nodes('[ test:arrayprop=(0,) :strs=(bar,) ]', opts=viewopts2)
            forkview.wlyr._testAddPropArrayIndx(nodes[0].nid, 'test:arrayprop', 'strs', (('test:str', 'a' * 500),))

            self.len(0, await core.nodes('test:arrayprop:strs*[=$long]', opts=viewopts2))
            self.len(0, await core.nodes('test:arrayprop:strs*[^=$long]', opts=viewopts2))
            self.len(1, await core.nodes('test:arrayprop:strs*[=bar]', opts=viewopts2))
            self.len(0, await core.nodes('test:arrayprop:strs*[={[test:str=$long]}]', opts=viewopts2))

            # Non-poly prop handling
            await core.nodes('[ test:arrayprop=(1,) :plainstr=(v1, v2, v1, v1) ]', opts=viewopts2)
            await core.nodes('[ test:arrayprop=(1,) :plainstr=(v1, v2, v1, v1) ]')

            self.len(3, await core.nodes('test:arrayprop:plainstr*[=v1]', opts=viewopts2))

            await core.nodes('test:arrayprop=(1,) | delnode', opts=viewopts2)
            self.len(0, await core.nodes('test:arrayprop:plainstr*[=v1]', opts=viewopts2))

            await core.nodes('[ test:arrayprop=(2,) :plainstr=(v3, v4) ]')
            nodes = await core.nodes('[ test:arrayprop=(2,) :plainstr=(v4,) ]', opts=viewopts2)

            # Invalid array index coverage
            forkview.wlyr._testAddPropArrayIndx(nodes[0].nid, 'test:arrayprop', 'plainstr', (('str', 'a' * 500),))

            self.len(0, await core.nodes('test:arrayprop:plainstr*[=$long]', opts=viewopts2))
            self.len(0, await core.nodes('test:arrayprop:plainstr*[=v3]', opts=viewopts2))
            self.len(1, await core.nodes('test:arrayprop:plainstr*[=v4]', opts=viewopts2))

            q = '''[
            test:str=iparry
                :polyarry={[
                    inet:server=tcp://1.2.3.4:80
                    inet:server=tcp://1.2.3.4:90
                    inet:server=tcp://1.2.3.5:80
                ]}
            ]'''
            await core.nodes(q, opts=viewopts2)
            await core.nodes(q)

            self.len(2, await core.nodes('test:str:polyarry*[.port=80]', opts=viewopts2))
            self.len(3, await core.nodes('test:str:polyarry*[.type=inet:server]', opts=viewopts2))

            await core.nodes('test:str=iparry [ :polyarry={ inet:server=tcp://1.2.3.4:90 } ]', opts=viewopts2)
            self.len(0, await core.nodes('test:str:polyarry*[.port=80]', opts=viewopts2))
            self.len(1, await core.nodes('test:str:polyarry*[.port=90]', opts=viewopts2))
            self.len(1, await core.nodes('test:str:polyarry*[.type=inet:server]', opts=viewopts2))

            await core.nodes('test:str=iparry [ -:polyarry ]', opts=viewopts2)
            self.len(0, await core.nodes('test:str:polyarry*[.port=80]', opts=viewopts2))
            self.len(0, await core.nodes('test:str:polyarry*[.port=90]', opts=viewopts2))
            self.len(0, await core.nodes('test:str:polyarry*[.type=inet:server]', opts=viewopts2))

            await core.nodes('test:str=iparry | delnode', opts=viewopts2)
            self.len(0, await core.nodes('test:str:polyarry*[.port=80]', opts=viewopts2))
            self.len(0, await core.nodes('test:str:polyarry*[.port=90]', opts=viewopts2))
            self.len(0, await core.nodes('test:str:polyarry*[.type=inet:server]', opts=viewopts2))

            viewiden3 = await core.callStorm('return($lib.view.get().fork().iden)', opts=viewopts2)
            viewopts3 = {'view': viewiden3}

            await core.nodes('[ test:str=iparry ]', opts=viewopts3)
            self.len(0, await core.nodes('test:str:polyarry*[.port=80]', opts=viewopts3))

            # Multiple virt types
            q = '''[
                test:arrayprop=(3,)
                    :multivirt={[
                        file:path=`/foo/{$long}`
                        file:path=`/foo/{$long}`
                        inet:server=tcp://1.2.3.4:80
                        inet:server=tcp://1.2.3.4:80
                ]}
            ]'''
            await core.nodes(q, opts=viewopts2)

            self.len(2, await core.nodes('test:arrayprop:multivirt*[.port=80]', opts=viewopts2))
            self.len(2, await core.nodes('test:arrayprop:multivirt*[.base=$long]', opts=viewopts2))

            # Non-poly virts
            await core.nodes('[ test:arrayprop=(4,) :vers=(v1.2.3, v1.2.3, foo1.2.3, 4.5.6) ]')
            await core.nodes('[ test:arrayprop=(4,) :vers=(4.5.6,) ]', opts=viewopts2)

            self.len(1, await core.nodes('test:arrayprop:vers*[.semver=4.5.6]', opts=viewopts2))
            self.len(0, await core.nodes('test:arrayprop:vers*[.semver=1.2.3]', opts=viewopts2))

            await core.nodes('test:arrayprop=(4,) | delnode', opts=viewopts2)
            self.len(0, await core.nodes('test:arrayprop:vers*[.semver=4.5.6]', opts=viewopts2))
            self.len(0, await core.nodes('test:arrayprop:vers*[.semver=1.2.3]', opts=viewopts2))

            # A reverse array lift over more than one layer must merge the layers into one
            # descending sequence rather than returning each layer's rows back to back. The layer
            # index stays out of the merge comparison ( merggenr2 withordr, plus SodeEnvl being
            # sort neutral ) so a tie resolves to the topmost layer in either direction.
            await core.nodes('''[
                (test:arrayprop=(low0,) :ints=(10,) :vers=(v1.0.0,))
                (test:arrayprop=(low1,) :ints=(30,) :vers=(v3.0.0,))
            ]''')

            await core.nodes('''[
                (test:arrayprop=(top0,) :ints=(20,) :vers=(v2.0.0,))
                (test:arrayprop=(top1,) :ints=(40,) :vers=(v4.0.0,))
            ]''', opts=viewopts2)

            async def arryvals(name, text, opts=viewopts2):
                return [node.get(name)[0][1] for node in await core.nodes(text, opts=opts)]

            self.eq([10, 20, 30, 40], await arryvals('ints', 'test:arrayprop:ints*[>=10]'))
            self.eq([40, 30, 20, 10], await arryvals('ints', 'reverse(test:arrayprop:ints*[>=10])'))

            # the virt lift branch merges the same way
            self.eq(['v1.0.0', 'v2.0.0', 'v3.0.0', 'v4.0.0'],
                    await arryvals('vers', 'test:arrayprop:vers*[.semver>=1.0.0]'))
            self.eq(['v4.0.0', 'v3.0.0', 'v2.0.0', 'v1.0.0'],
                    await arryvals('vers', 'reverse(test:arrayprop:vers*[.semver>=1.0.0])'))

            # a value in both layers is lifted once, from the topmost layer, either direction
            await core.nodes('test:arrayprop=(low0,) [ :ints=(10,) ]', opts=viewopts2)

            self.eq([10, 20, 30, 40], await arryvals('ints', 'test:arrayprop:ints*[>=10]'))
            self.eq([40, 30, 20, 10], await arryvals('ints', 'reverse(test:arrayprop:ints*[>=10])'))

            # the single layer view keeps only the rows written to it
            self.eq([10, 30], await arryvals('ints', 'test:arrayprop:ints*[>=10]', opts=None))
            self.eq([30, 10], await arryvals('ints', 'reverse(test:arrayprop:ints*[>=10])', opts=None))

            await core.nodes('test:arrayprop=(low0,) test:arrayprop=(low1,) | delnode', opts=viewopts2)
            await core.nodes('test:arrayprop=(top0,) test:arrayprop=(top1,) | delnode', opts=viewopts2)

            # Bad virt data coverage
            nodes = await core.nodes('[test:str=iparry :polyarry={ inet:server=tcp://1.2.3.4:90 } ]', opts=viewopts2)
            self.len(1, await core.nodes('test:str:polyarry*[.port=90]', opts=viewopts2))

            nodes[0].sodes[0]['props']['polyarry'][2].pop('port')
            self.len(0, await core.nodes('test:str:polyarry*[.port=90]', opts=viewopts2))

            nodes = await core.nodes('test:arrayprop=(3,)', opts=viewopts2)
            nodes[0].sodes[0]['props']['multivirt'][2]['base'] = {('newp', 9): 2}
            self.len(0, await core.nodes('test:arrayprop:multivirt*[.base=$long]', opts=viewopts2))

            nodes[0].sodes[0]['props']['multivirt'][2]['port'] = {(90, 9): 2}
            self.len(0, await core.nodes('test:arrayprop:multivirt*[.port=80]', opts=viewopts2))

            nodes = await core.nodes('[ test:arrayprop=(4,) :vers=(4.5.6,) ]', opts=viewopts2)
            nodes[0].sodes[0]['props']['vers'][2]['semver'] = {('newp', 9): 1}
            self.len(0, await core.nodes('test:arrayprop:vers*[.semver=4.5.6]', opts=viewopts2))

            nodes[0].sodes[0]['props']['vers'][2].pop('semver')
            self.len(0, await core.nodes('test:arrayprop:vers*[.semver=4.5.6]', opts=viewopts2))

            nodes = await core.nodes('[ test:str=empty ]')
            self.eq(((None, None, None), None), nodes[0].getRawWithLayer('polyarry'))
