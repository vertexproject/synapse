import os
import math
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.auth as s_auth
import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack
import synapse.lib.spooled as s_spooled

import synapse.tools.backup as s_tools_backup

import synapse.tests.utils as s_t_utils

from synapse.tests.utils import alist

from unittest import mock

async def iterPropForm(self, form=None, prop=None):
    bad_valu = [(b'foo', "bar"), (b'bar', ('bar',)), (b'biz', 4965), (b'baz', (0, 56))]
    bad_valu += [(b'boz', 'boz')] * 10
    for buid, valu in bad_valu:
        yield buid, valu

class LayerTest(s_t_utils.SynTest):

    def checkLayrvers(self, core):
        for layr in core.layers.values():
            self.eq(layr.layrvers, 11)

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
            self.len(1, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')

            config = {'scanall': False, 'scans': {'tagindex': {'include': ('baz',)}}}
            errors = [e async for e in core.getLayer().verify(config=config)]
            self.len(0, errors)

            errors = [e async for e in core.getLayer().verifyAllTags()]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')

            core.getLayer()._testDelPropStor(nid, 'inet:ip', 'asn')
            errors = [e async for e in core.getLayer().verifyByProp('inet:ip', 'asn')]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)

            core.getLayer()._testDelFormValuStor(nid, 'inet:ip')
            errors = [e async for e in core.getLayer().verifyByProp('inet:ip', None)]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 +#foo.bar ]')
            nid = nodes[0].nid

            core.getLayer()._testAddPropIndx(nid, 'inet:ip', 'asn', 30)
            errors = [e async for e in core.getLayer().verify()]
            self.len(1, errors)
            self.eq(errors[0][0], 'SpurPropKeyForIndex')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ip=1.2.3.4 :asn=20 +#foo ]')
            nid = nodes[0].nid

            await core.nodes('.created | delnode --force')
            self.len(0, await core.nodes('inet:ip=1.2.3.4'))

            core.getLayer()._testAddTagIndx(nid, 'inet:ip', 'foo')
            core.getLayer()._testAddPropIndx(nid, 'inet:ip', 'asn', 30)
            errors = [e async for e in core.getLayer().verify()]
            self.eq(errors[0][0], 'NoNodeForTagIndex')
            self.eq(errors[1][0], 'NoNodeForPropIndex')

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

            core.getLayer()._testAddPropArrayIndx(nid, 'entity:contact', 'names', ('baz',))

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

            core.getLayer()._testAddPropArrayIndx(nid, 'entity:contact', 'names', ('foo',))

            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoNodeForPropIndex')
            self.eq(errors[1][0], 'NoNodeForPropArrayIndex')
            self.eq(errors[2][0], 'NoNodeForPropArrayIndex')

            q = "$lib.model.ext.addForm('_test:array', array, ({'type': 'int'}), ({}))"
            await core.nodes(q)
            nodes = await core.nodes('[ _test:array=(1, 2, 3) ]')
            nid = nodes[0].nid
            core.getLayer()._testDelFormValuStor(nid, '_test:array')

            scanconf = {'include': [('_test:array', None)]}
            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(4, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')
            self.eq(errors[1][0], 'NoValuForPropArrayIndex')
            self.eq(errors[2][0], 'NoValuForPropArrayIndex')
            self.eq(errors[3][0], 'NoValuForPropArrayIndex')

            scanconf = {'include': [('_test:array', None)], 'autofix': 'index'}
            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(4, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')
            self.eq(errors[1][0], 'NoValuForPropArrayIndex')
            self.eq(errors[2][0], 'NoValuForPropArrayIndex')
            self.eq(errors[3][0], 'NoValuForPropArrayIndex')

            scanconf = {'include': [('_test:array', None)]}
            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(0, errors)

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
            self.len(1, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')
            self.len(0, await core.nodes('inet:ip=1.2.3.4 +#foo'))
            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

        async with self.getTestCore() as core:
            await core.addTagProp('score', ('int', {}), {})

            layr = core.getLayer()
            errors = [e async for e in layr.verifyAllNids()]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllProps()]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(0, errors)

            layr._testAddTagPropIndx(nid, 'inet:ip', 'foo', 'score', 5)

            scanconf = {'include': ['newp']}
            errors = [e async for e in layr.verifyAllTagProps(scanconf=scanconf)]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoNodeForTagPropIndex')
            self.eq(errors[1][0], 'NoNodeForTagPropIndex')

            nodes = await core.nodes('[ inet:ip=1.2.3.4 +#foo:score=5 ]')
            nid = nodes[0].nid

            layr._testAddTagPropIndx(nid, 'inet:ip', 'foo', 'score', 6)

            scanconf = {'autofix': 'index'}
            errors = [e async for e in layr.verifyAllTagProps(scanconf=scanconf)]
            self.len(2, errors)
            self.eq(errors[0][0], 'SpurTagPropKeyForIndex')
            self.eq(errors[1][0], 'SpurTagPropKeyForIndex')

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(0, errors)

            sode = layr._getStorNode(nid)
            score = sode['tagprops']['foo']['score']
            sode['tagprops']['foo']['score'] = (score[0], 8675309)
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
            await core.nodes('[ test:str=foo +#foo:score=5 ]')
            await core.nodes('test:str=foo [ -#foo:score ]', opts={'view': viewiden2})
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
            # TODO self.raises(s_exc.NoSuchImpl, indxby.getNodeValu, s_common.guid())

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

            self.eq(created00, nodes[0].get('.created'))

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
            self.eq(created01, nodes[0].get('.created'))

            nodes = await core.nodes('[ test:int=1 :loc=us +#foo]')
            self.eq(created01, nodes[0].get('.created'))

            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # Tests for behavior of storing nodeedits directly prior to using meta (i.e. meta['time'] != .created)
            # .created is a MINTIME therefore earlier value wins, which is typically meta
            created02 = s_time.parse('1990-10-10 12:30')
            await layr.saveNodeEdits(editlist00, {'time': created02})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            self.eq(created02, nodes[0].get('.created'))

            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # meta could be after .created for manual store operations
            created03 = s_time.parse('2050-10-10 12:30')
            await layr.saveNodeEdits(editlist00, {'time': created03})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            self.eq(created03, nodes[0].get('.created'))

    async def test_layer_nodeedits(self):

        async with self.getTestCoreAndProxy() as (core0, prox0):

            nodelist0 = []
            nodes = await core0.nodes('[ test:str=foo ]')
            nodelist0.extend(nodes)
            nodes = await core0.nodes('[ test:int=1 :seen=(2012,2014) +#foo.bar=(2012, 2014) ]')
            nodelist0.extend(nodes)

            nodelist0 = [node.pack() for node in nodelist0]

            editlist = []

            layr = core0.getLayer()
            async for offs, nodeedits in prox0.syncLayerNodeEdits(0):
                editlist.append(nodeedits)
                if offs == layr.nodeeditlog.index() - 1:
                    break

            fwdedits = [item async for item in core0.getLayer().syncNodeEdits(0, wait=False)]
            revedits = [item async for item in core0.getLayer().syncNodeEdits(0xffffffff, wait=False, reverse=True)]

            self.eq(fwdedits, list(reversed(revedits)))

            fwdedit = await core0.callStorm('for $item in $lib.layer.get().edits() { return($item) }')
            revedit = await core0.callStorm('for $item in $lib.layer.get().edits(reverse=(true)) { return($item) }')

            self.nn(await core0.callStorm('return($lib.layer.get().edited())'))

            self.ne(fwdedit, revedit)
            self.eq(fwdedits[0], fwdedit)
            self.eq(revedits[0], revedit)

            async with self.getTestCore() as core1:

                url = core1.getLocalUrl('*/layer')

                async with await s_telepath.openurl(url) as layrprox:

                    for nodeedits in editlist:
                        self.nn(await layrprox.saveNodeEdits(nodeedits, {}))

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

                    self.len(4, await alist(layrprox.syncNodeEdits2(0, wait=False)))

                layr = core1.view.layers[0]  # type: s_layer.Layer

            await core0.addTagProp('score', ('int', {}), {})

            q = '[ test:int=1 +#tp:score=5 +(refs)> { test:str=foo } ] $node.data.set(foo, bar)'
            nodes = await core0.nodes(q)
            intnid = s_common.int64un(nodes[0].nid)
            tstrnid = s_common.int64un((await core0.nodes('test:str=foo'))[0].nid)

            layr = core0.getLayer()

            noedit = [(None, 'test:int', [(s_layer.EDIT_PROP_SET, ('newp', 5, None))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_TAG_DEL, ('newp',))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_TAGPROP_SET, ('tp', 'score', 5, s_layer.STOR_TYPE_I64))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_TAGPROP_DEL, ('newp', 'newp'))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_TAGPROP_DEL, ('tp', 'newp'))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_NODEDATA_SET, ('foo', 'bar'))])]
            self.eq([], await layr.calcEdits(noedit, {}))

            noedit = [(intnid, 'test:int', [(s_layer.EDIT_EDGE_ADD, ('refs', tstrnid))])]
            self.eq([], await layr.calcEdits(noedit, {}))

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

    async def test_layer_syncindexevents(self):

        async with self.getTestCore() as core:
            layr = core.getLayer()
            await core.addTagProp('score', ('int', {}), {})
            baseoff = await core.getNexsIndx()

            nodes = await core.nodes('[ test:str=foo ]')
            strnode = nodes[0]
            strnid = s_common.int64un(strnode.nid)
            q = '[ inet:ip=1.2.3.4 :asn=42 +#mytag:score=99 +#foo.bar=(2012, 2014) ]'
            nodes = await core.nodes(q)
            ipv4node = nodes[0]
            ipnid = s_common.int64un(ipv4node.nid)

            await core.nodes('inet:ip=1.2.3.4 test:str=foo | delnode')

            mdef = {'forms': ['test:str']}
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            self.eq(events, [
                (strnid, 'test:str', s_layer.EDIT_NODE_ADD, ('foo', s_layer.STOR_TYPE_UTF8, None)),
                (strnid, 'test:str', s_layer.EDIT_NODE_DEL, ()),
            ])

            mdef = {'props': ['inet:ip:asn']}
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            self.len(2, events)
            self.eq(events, [
                (ipnid, 'inet:ip', s_layer.EDIT_PROP_SET, ('asn', 42, s_layer.STOR_TYPE_I64, None)),
                (ipnid, 'inet:ip', s_layer.EDIT_PROP_DEL, ('asn',)),
            ])

            time = [s_time.parse(x) for x in ('2012', '2014')]
            ival = (time[0], time[1], time[1] - time[0])

            mdef = {'tags': ['foo.bar']}
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            self.eq(events, [
                (ipnid, 'inet:ip', s_layer.EDIT_TAG_SET, ('foo.bar', ival)),
                (ipnid, 'inet:ip', s_layer.EDIT_TAG_DEL, ('foo.bar',)),
            ])

            mdefs = ({'tagprops': ['score']}, {'tagprops': ['mytag:score']})
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            for mdef in mdefs:
                events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
                self.eq(events, [
                    (ipnid, 'inet:ip', s_layer.EDIT_TAGPROP_SET,
                        ('mytag', 'score', 99, s_layer.STOR_TYPE_I64)),
                    (ipnid, 'inet:ip', s_layer.EDIT_TAGPROP_DEL,
                        ('mytag', 'score')),
                ])

    async def test_layer_tombstone(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'verbs': ('_foo', '_bar')}}
            await core.nodes('for $verb in $verbs { $lib.model.ext.addEdge(*, $verb, *, ({})) }', opts=opts)

            async def checkempty(opts=None):
                nodes = await core.nodes('inet:ip=1.2.3.4', opts=opts)
                self.len(1, nodes)
                self.none(nodes[0].get('asn'))
                self.none(nodes[0].get('#foo.tag'))
                self.none(nodes[0].getTagProp('bar.tag', 'score'))

                self.len(0, await core.nodes('inet:ip=1.2.3.4 -(_bar)> *', opts=opts))
                self.len(0, await core.nodes('inet:ip=1.2.3.4 <(_foo)- *', opts=opts))

                self.none(await core.callStorm('inet:ip=1.2.3.4 return($node.data.get(foodata))', opts=opts))
                self.len(0, await core.nodes('yield $lib.lift.byNodeData(foodata)', opts=opts))

            async def hastombs(opts=None):
                q = 'for $tomb in $lib.layer.get().getTombstones() { $lib.print($tomb) }'
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint("('inet:ip', 'asn')", msgs)
                self.stormIsInPrint("foo.tag", msgs)
                self.stormIsInPrint("'bar.tag', 'score'", msgs)
                self.stormIsInPrint("'_bar'", msgs)
                self.stormIsInPrint("'_foo'", msgs)
                self.stormIsInPrint("'foodata'", msgs)

            async def notombs(opts=None):
                q = 'for $tomb in $lib.layer.get().getTombstones() { $lib.print($tomb) }'
                msgs = await core.stormlist(q, opts=opts)
                self.len(0, [m for m in msgs if m[0] == 'print'])

            await core.addTagProp('score', ('int', {}), {})

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            addq = '''[
            inet:ip=1.2.3.4
                :asn=4
                +#foo.tag=2024
                +#bar.tag:score=5
                +(_bar)> {[ it:dev:str=n1 ]}
                <(_foo)+ {[ it:dev:str=n2 ]}
            ]
            $node.data.set(foodata, bar)
            '''

            delq = '''
            inet:ip=1.2.3.4
            [   -:asn
                -#foo.tag
                -#bar.tag:score
                -(_bar)> {[ it:dev:str=n1 ]}
                <(_foo)- {[ it:dev:str=n2 ]}
            ]
            $node.data.pop(foodata)
            '''

            nodes = await core.nodes(addq)
            self.len(1, nodes)
            nodeiden = nodes[0].iden()

            self.false(await core.callStorm('[ test:str=newp ] return($node.data.has(foodata))'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -:asn ]', opts=viewopts2)
            self.none(nodes[0].get('asn'))

            nodes = await core.nodes('inet:ip=1.2.3.4')
            self.eq(4, nodes[0].get('asn'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ :asn=5 ]', opts=viewopts2)
            self.eq(5, nodes[0].get('asn'))

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

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -#bar.tag:score ]', opts=viewopts2)
            self.none(nodes[0].getTagProp('bar.tag', 'score'))

            nodes = await core.nodes('inet:ip=1.2.3.4')
            self.eq(5, nodes[0].getTagProp('bar.tag', 'score'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ +#bar.tag:score=6 ]', opts=viewopts2)
            self.eq(6, nodes[0].getTagProp('bar.tag', 'score'))

            nodes = await core.nodes('inet:ip=1.2.3.4 [ -#bar.tag:score ]', opts=viewopts2)
            self.none(nodes[0].getTagProp('bar.tag', 'score'))

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

            await core.addTagProp('score2', ('int', {}), {})
            nodes = await core.nodes('[test:str=multi +#foo:score=5 +#foo:score2=6]')
            self.sorteq(('score', 'score2'), nodes[0].getTagProps('foo'))

            nodes = await core.nodes('test:str=multi [-#foo:score]')
            self.eq(('score2',), nodes[0].getTagProps('foo'))

            nodes = await core.nodes('test:str=multi')
            self.eq(('score2',), nodes[0].getTagProps('foo'))

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
            await checkempty()
            await notombs()

            await view2.wipeLayer()
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
            self.stormNotInPrint("'bar.tag', 'score'", msgs)
            self.stormNotInPrint("'_bar'", msgs)
            self.stormNotInPrint("'foodata'", msgs)

            self.len(0, await core.nodes('yield $lib.lift.byNodeData(foodata)', opts=viewopts2))

            await view2.merge()
            await notombs()

            self.len(0, await core.nodes('inet:ip=1.2.3.4'))

            await view2.wipeLayer()
            await notombs(opts=viewopts2)

            # use command to merge
            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)

            self.len(3, await core.nodes('diff', opts=viewopts2))
            self.len(1, await core.nodes('diff --prop inet:ip:asn', opts=viewopts2))

            msgs = await core.stormlist('merge --diff', opts=viewopts2)
            self.stormIsInPrint('delete inet:ip:asn', msgs)
            self.stormIsInPrint('delete inet:ip#foo.tag', msgs)
            self.stormIsInPrint('delete inet:ip#bar.tag:score', msgs)
            self.stormIsInPrint('delete inet:ip DATA foodata', msgs)
            self.stormIsInPrint('delete inet:ip -(_bar)> ', msgs)

            msgs = await core.stormlist('merge --diff --exclude-tags foo.*', opts=viewopts2)
            self.stormNotInPrint('delete inet:ip#foo.tag', msgs)

            msgs = await core.stormlist('merge --diff --exclude-tags bar.*', opts=viewopts2)
            self.stormNotInPrint('delete inet:ip#bar.tag:score', msgs)

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
            await notombs()
            await view2.wipeLayer()

            await core.nodes(addq)
            await core.nodes(delq, opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force', opts=viewopts2)
            await core.nodes('inet:ip=1.2.3.4 | delnode --force')

            await view2.merge()
            await notombs()
            await view2.wipeLayer()

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
            self.eq(nodes[0].get('place:loc'), 'us')
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
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip#bar.tag:score', msgs)
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip DATA foodata', msgs)
            self.stormIsInPrint(f'delete tombstone {nodeiden} inet:ip -(_bar)>', msgs)

            msgs = await core.stormlist('inet:ip=1.2.3.4 | movenodes --preserve-tombstones', opts=viewopts3)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip:asn', msgs)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip#foo.tag', msgs)
            self.stormIsInPrint(f'{destlayr} tombstone {nodeiden} inet:ip#bar.tag:score', msgs)
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
            self.stormIsInPrint(f'{destlayr} delete {nodeiden} inet:ip#bar.tag:score', msgs)
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
            for $edge in $node.edges(reverse=$lib.true) {
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

            q = 'for $edge in $lib.layer.get().getEdges() { $lib.print($edge) }'
            msgs = await core.stormlist(q, opts=viewopts3)
            self.len(0, [m for m in msgs if m[0] == 'print'])

            q = 'inet:ip for $edge in $lib.layer.get().getEdgesByN1($node.iden()) { $lib.print($edge) }'
            msgs = await core.stormlist(q, opts=viewopts3)
            self.len(0, [m for m in msgs if m[0] == 'print'])

            q = 'inet:ip for $edge in $lib.layer.get().getEdgesByN2($node.iden()) { $lib.print($edge) }'
            msgs = await core.stormlist(q, opts=viewopts3)
            self.len(0, [m for m in msgs if m[0] == 'print'])

            await view3.merge()

            # tombstones should merge down since they still have values to cover
            await checkempty(opts=viewopts2)
            await hastombs(opts=viewopts2)

            await view3.wipeLayer()

            nodes = await core.nodes('inet:ip=1.2.3.4', opts=viewopts3)
            self.false(nodes[0].has('asn'))

            bylayer = await core.callStorm('inet:ip=1.2.3.4 return($node.getByLayer())', opts=viewopts3)

            layr = view2.layers[0].iden
            self.eq(bylayer['props']['asn'], layr)
            self.eq(bylayer['tags']['foo.tag'], layr)
            self.eq(bylayer['tagprops']['bar.tag']['score'], layr)

            await core.nodes('inet:ip=1.2.3.4 [ <(_foo)- { it:dev:str=n2 } ] | delnode')

            await core.nodes(addq, opts=viewopts2)
            await notombs(opts=viewopts2)

            await core.nodes(delq, opts=viewopts3)
            await checkempty(opts=viewopts3)
            await hastombs(opts=viewopts3)

            await view3.merge()

            # no tombstones should merge since the base layer has no values
            await checkempty(opts=viewopts2)
            await notombs(opts=viewopts2)

            await view3.wipeLayer()

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
            self.false(node.hasTagProp('bar.tag', 'score'))
            self.false(node.hasTagPropInLayers('bar.tag', 'score'))
            self.eq((None, None), node.getTagPropWithLayer('bar.tag', 'score'))

            self.eq(['version', 'type'], list(nodes[0].getProps().keys()))
            self.eq({}, node._getTagsDict())
            self.eq({}, node._getTagPropsDict())

            self.len(0, await core.nodes('#bar.tag:score', opts=viewopts3))
            self.len(0, await core.nodes('#bar.tag:score=5', opts=viewopts3))

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
            self.false(node.hasTagProp('bar.tag', 'score'))
            self.false(node.hasTagPropInLayers('bar.tag', 'score'))
            self.false(node.hasTagPropInLayers('foo.tag', 'score'))
            self.eq((None, None), node.getTagPropWithLayer('bar.tag', 'score'))
            self.eq((None, None), node.getTagPropWithLayer('foo.tag', 'score'))

            self.eq(['version', 'type'], list(nodes[0].getProps().keys()))
            self.sorteq(['bar', 'bar.tag', 'foo'], list(node._getTagsDict().keys()))
            self.eq({}, node._getTagPropsDict())

            self.len(0, await alist(node.iterData()))
            self.len(0, await alist(node.iterDataKeys()))
            self.false(0, await node.hasData('foodata'))
            self.none(await core.callStorm('inet:ip=1.2.3.4 return($node.data.pop(foodata))', opts=viewopts3))

            randbuid = s_common.buid('newp')
            self.false((await view3.layers[0].hasNodeData(randbuid, 'foodata')))
            self.false((await view3.layers[0].getNodeData(randbuid, 'foodata'))[0])

            self.len(0, await alist(view3.getEdges()))
            self.len(0, await alist(view3.layers[1].getEdgeVerbs()))
            self.len(2, await alist(view3.layers[2].getEdgeVerbs()))

            self.len(0, await core.nodes('inet:ip:asn', opts=viewopts3))
            self.len(0, await core.nodes('inet:ip:asn=4', opts=viewopts3))
            self.len(0, await core.nodes('#foo.tag', opts=viewopts3))
            self.len(0, await core.nodes('#foo.tag@=2024', opts=viewopts3))
            self.len(0, await core.nodes('#bar.tag:score', opts=viewopts3))
            self.len(0, await core.nodes('#bar.tag:score=5', opts=viewopts3))

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

            await core.addTagProp('score', ('int', {}), {})

            layr = core.getLayer()
            self.isin(f'Layer (Layer): {layr.iden}', str(layr))

            nodes = await core.nodes('[test:str=foo :seen=(2015, 2016)]')

            self.false(await layr.hasTagProp('score'))
            nodes = await core.nodes('[test:str=bar +#test:score=100]')
            self.true(await layr.hasTagProp('score'))

    async def test_layer_no_extra_logging(self):

        async with self.getTestCore() as core:
            '''
            For a do-nothing write, don't write new log entries
            '''
            await core.nodes('[test:str=foo :seen=(2015, 2016)]')
            layr = core.getLayer(None)
            lbefore = len(await alist(layr.syncNodeEdits2(0, wait=False)))
            await core.nodes('[test:str=foo :seen=(2015, 2016)]')
            lafter = len(await alist(layr.syncNodeEdits2(0, wait=False)))
            self.eq(lbefore, lafter)

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

            # FIXME test via sodes?
            # self.eq('foo', await layr.getNodeValu(nid))
            # self.eq((1420070400000, 1451606400000), await layr.getNodeValu(nid, ':seen'))

            s_common.gendir(layr.dirn, 'adir')

            copylayrinfo = await core.cloneLayer(layr.iden)
            self.len(2, core.layers)

            copylayr = core.getLayer(copylayrinfo.get('iden'))
            self.isin(f'Layer (Layer): {copylayr.iden}', str(copylayr))
            self.ne(layr.iden, copylayr.iden)

            # self.eq('foo', await copylayr.getNodeValu(nid))
            # self.eq((1420070400000, 1451606400000), await copylayr.getNodeValu(nid, ':seen'))

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
                msgs = await core.stormlist('$lib.layer.add(({"readonly": $lib.true}))')
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

    async def test_layer_logedits_default(self):
        async with self.getTestCore() as core:
            self.true(core.getLayer().logedits)

    async def test_layer_no_logedits(self):

        async with self.getTestCore() as core:
            info = await core.addLayer({'logedits': False})
            layr = core.getLayer(info.get('iden'))
            self.false(layr.logedits)
            self.eq(-1, await layr.getEditOffs())

    async def test_layer_iter_props(self):

        async with self.getTestCore() as core:
            await core.addTagProp('score', ('int', {}), {})

            nodes = await core.nodes('[inet:ip=([4, 1]) :asn=10 +#foo=(2020, 2021) +#foo:score=42]')
            self.len(1, nodes)
            nid1 = nodes[0].nid

            nodes = await core.nodes('[inet:ip=([4, 2]) :asn=20 +#foo=(2019, 2020) +#foo:score=41]')
            self.len(1, nodes)
            nid2 = nodes[0].nid

            nodes = await core.nodes('[inet:ip=([4, 3]) :asn=30 +#foo +#foo:score=99]')
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

            self.eq((10, 20, 30), tuple(sorted([row[1] for row in rows])))

            styp = core.model.form('inet:ip').prop('asn').type.stortype
            rows = await alist(layr.iterPropRows('inet:ip', 'asn', styp))
            self.eq((10, 20, 30), tuple(sorted([row[1] for row in rows])))

            rows = await alist(layr.iterPropRows('inet:ip', 'asn', styp))
            self.eq((10, 20, 30), tuple(sorted([row[1] for row in rows])))

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

            rows = await alist(layr.iterTagPropRows('foo', 'score'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagPropRows('foo', 'score', form='inet:ip'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagPropRows('foo', 'score', form='inet:ip', stortype=s_layer.STOR_TYPE_I64,
                                                    startvalu=42))
            self.eq(expect[1:], rows)

            rows = await alist(layr.iterTagPropRows('foo', 'score', stortype=s_layer.STOR_TYPE_I64, startvalu=42))
            self.eq(expect[1:], rows)

    async def test_layer_setinfo(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                layer = core.getView().layers[0]

                self.eq('hehe', await core.callStorm('$layer = $lib.layer.get() $layer.set(name, hehe) return($layer.get(name))'))

                self.eq(False, await core.callStorm('$layer = $lib.layer.get() $layer.set(logedits, $lib.false) return($layer.get(logedits))'))
                edits0 = [e async for e in layer.syncNodeEdits(0, wait=False)]
                await core.callStorm('[inet:ip=1.2.3.4]')
                edits1 = [e async for e in layer.syncNodeEdits(0, wait=False)]
                self.eq(len(edits0), len(edits1))

                self.eq(True, await core.callStorm('$layer = $lib.layer.get() $layer.set(logedits, $lib.true) return($layer.get(logedits))'))
                await core.callStorm('[inet:ip=5.5.5.5]')
                edits2 = [e async for e in layer.syncNodeEdits(0, wait=False)]
                self.gt(len(edits2), len(edits1))

                self.true(await core.callStorm('$layer=$lib.layer.get() $layer.set(readonly, $lib.true) return($layer.get(readonly))'))
                await self.asyncraises(s_exc.IsReadOnly, core.nodes('[inet:ip=7.7.7.7]'))
                await self.asyncraises(s_exc.IsReadOnly, core.nodes('$lib.layer.get().set(logedits, $lib.false)'))

                self.false(await core.callStorm('$layer=$lib.layer.get() $layer.set(readonly, $lib.false) return($layer.get(readonly))'))
                self.len(1, await core.nodes('[inet:ip=7.7.7.7]'))

                msgs = []
                didset = False
                async for mesg in core.storm('[( test:guid=(rotest00,) )] $lib.time.sleep(1) [( test:guid=(rotest01,) )]'):
                    msgs.append(mesg)
                    if mesg[0] == 'node:edits' and not didset:
                        self.true(await core.callStorm('$layer=$lib.layer.get() $layer.set(readonly, $lib.true) return($layer.get(readonly))'))
                        didset = True

                self.stormIsInErr(f'Layer {layer.iden} is read only!', msgs)
                self.len(1, [mesg for mesg in msgs if mesg[0] == 'node'])

                with self.raises(s_exc.BadOptValu):
                    await core.callStorm('$layer = $lib.layer.get() $layer.set(newp, hehe)')

                await core.nodes('''
                    $layer = $lib.layer.get()
                    $layer.set(readonly, $lib.false)  // so we can set everything else
                    $layer.set(name, foo)
                    $layer.set(desc, foodesc)
                    $layer.set(logedits, $lib.false)
                    $layer.set(readonly, $lib.true)
                ''')

                info00 = await core.callStorm('return($lib.layer.get())')
                self.eq('foo', info00['name'])
                self.eq('foodesc', info00['desc'])
                self.false(info00['logedits'])
                self.true(info00['readonly'])

            async with self.getTestCore(dirn=dirn) as core:

                self.eq(info00, await core.callStorm('return($lib.layer.get())'))

    async def test_layer_edit_perms(self):

        self.skip('FIXME need to pick new forms for this one')

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

                await core.addTagProp('score', ('int', {}), {})

                nodes = await core.nodes('''
                    [
                        (meta:name=marty
                            :given=marty
                            +#performance:score=10
                            +#role.protagonist
                        )
                        (meta:name=emmett :given=emmett)
                        (meta:name=biff :given=biff)
                        (meta:name=george :given=george)
                        (meta:name=loraine :given=loraine)
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
                        +#foo:score=2
                        +#foo.bar.baz
                        +#bar:score=2
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
                    meta:name:given=biff
                    [ <(seen)- { meta:source:type=movie } ]
                    | delnode |

                    meta:name=emmett [ -:given ]
                    meta:name=marty [ -#performance:score -#role.protagonist ]
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
                    ('node', 'del', 'meta:name'),

                    # Prop del (tombstone)
                    ('node', 'prop', 'del', 'meta:name', 'given'),

                    # Tag del (tombstone)
                    ('node', 'tag', 'del', 'role', 'protagonist'),

                    # Tagprop del (tombstone)
                    ('node', 'tag', 'del', 'performance', 'score'),

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
                    ('node', 'add', 'meta:name'),

                    # Prop set (restore tombstone)
                    ('node', 'prop', 'set', 'meta:name', 'given'),

                    # Tag/tagprop add (restore tombstone)
                    ('node', 'tag', 'add', 'role', 'protagonist'),
                    ('node', 'tag', 'add', 'performance', 'score'),

                    # Nodedata set (tombstone restore)
                    ('node', 'data', 'set', 'movie'),

                    # Edge add (tombstone restor)
                    ('node', 'edge', 'add', 'seen'),

                })

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

    async def test_layer_fromfuture(self):
        with self.raises(s_exc.BadStorageVersion):
            async with self.getRegrCore('future-layrvers') as core:
                pass

    async def test_layer_ival_indexes(self):

        async with self.getTestCore() as core:

            await core.addTagProp('footime', ('ival', {}), {})

            self.len(0, await core.nodes('entity:campaign#bar:footime.min=2020-01-01'))

            await core.nodes('''[
                entity:campaign=(foo,)
                    :period=(2019-01-01, ?)
                    +#foo=(2019-01-01, ?)
                    +#bar:footime=(2019-01-01, ?)
            ]''')

            await core.nodes('''[
                (entity:campaign=* :period=(2020-01-01, 2020-01-02))
                (entity:campaign=* :period=(2021-01-01, 2021-02-01))
                (entity:campaign=* :period=(2022-01-01, 2022-05-01))
                (entity:campaign=* :period=(2023-01-01, 2024-01-01))
                (entity:campaign=* :period=(2024-01-01, 2026-01-01))
            ]''')

            self.len(1, await core.nodes('entity:campaign:period.min=2020-01-01'))
            self.len(3, await core.nodes('entity:campaign:period.min<2022-01-01'))
            self.len(4, await core.nodes('entity:campaign:period.min<=2022-01-01'))
            self.len(3, await core.nodes('entity:campaign:period.min>=2022-01-01'))
            self.len(2, await core.nodes('entity:campaign:period.min>2022-01-01'))
            self.len(1, await core.nodes('entity:campaign:period.min@=2020'))
            self.len(2, await core.nodes('entity:campaign:period.min@=(2020-01-01, 2022-01-01)'))

            self.len(1, await core.nodes('reverse(entity:campaign:period.min=2020-01-01)'))
            self.len(3, await core.nodes('reverse(entity:campaign:period.min<2022-01-01)'))
            self.len(4, await core.nodes('reverse(entity:campaign:period.min<=2022-01-01)'))
            self.len(3, await core.nodes('reverse(entity:campaign:period.min>=2022-01-01)'))
            self.len(2, await core.nodes('reverse(entity:campaign:period.min>2022-01-01)'))
            self.len(1, await core.nodes('reverse(entity:campaign:period.min@=2020)'))
            self.len(2, await core.nodes('reverse(entity:campaign:period.min@=(2020-01-01, 2022-01-01))'))

            self.len(1, await core.nodes('entity:campaign:period.max=2020-01-02'))
            self.len(2, await core.nodes('entity:campaign:period.max<2022-05-01'))
            self.len(3, await core.nodes('entity:campaign:period.max<=2022-05-01'))
            self.len(3, await core.nodes('entity:campaign:period.max>=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign:period.max>2022-05-01'))
            self.len(2, await core.nodes('entity:campaign:period.max@=(2020-01-02, 2022-05-01)'))
            self.len(1, await core.nodes('entity:campaign:period.max=?'))

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
                (entity:campaign=* +#bar:footime=(2020-01-01, 2020-01-02))
                (entity:campaign=* +#bar:footime=(2021-01-01, 2021-02-01))
                (entity:campaign=* +#bar:footime=(2022-01-01, 2022-05-01))
                (entity:campaign=* +#bar:footime=(2023-01-01, 2024-01-01))
                (entity:campaign=* +#bar:footime=(2024-01-01, 2026-01-01))
            ]''')

            self.len(1, await core.nodes('entity:campaign#bar:footime.min=2020-01-01'))
            self.len(3, await core.nodes('entity:campaign#bar:footime.min<2022-01-01'))
            self.len(4, await core.nodes('entity:campaign#bar:footime.min<=2022-01-01'))
            self.len(3, await core.nodes('entity:campaign#bar:footime.min>=2022-01-01'))
            self.len(2, await core.nodes('entity:campaign#bar:footime.min>2022-01-01'))
            self.len(2, await core.nodes('entity:campaign#bar:footime.min@=(2020-01-01, 2022-01-01)'))
            self.len(2, await core.nodes('reverse(entity:campaign#bar:footime.min@=(2020-01-01, 2022-01-01))'))

            self.len(1, await core.nodes('entity:campaign#bar:footime.max=2020-01-02'))
            self.len(2, await core.nodes('entity:campaign#bar:footime.max<2022-05-01'))
            self.len(3, await core.nodes('entity:campaign#bar:footime.max<=2022-05-01'))
            self.len(3, await core.nodes('entity:campaign#bar:footime.max>=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign#bar:footime.max>2022-05-01'))
            self.len(2, await core.nodes('entity:campaign#bar:footime.max@=(2020-01-02, 2022-05-01)'))
            self.len(1, await core.nodes('entity:campaign#bar:footime.max=?'))

            self.len(1, await core.nodes('entity:campaign#bar:footime.duration=1D'))
            self.len(1, await core.nodes('entity:campaign#bar:footime.duration<31D'))
            self.len(2, await core.nodes('entity:campaign#bar:footime.duration<=31D'))
            self.len(4, await core.nodes('entity:campaign#bar:footime.duration>=31D'))
            self.len(3, await core.nodes('entity:campaign#bar:footime.duration>31D'))
            self.len(1, await core.nodes('entity:campaign#bar:footime.duration=?'))

            await core.nodes('[ entity:campaign=(foo,) +#bar:footime=(2018, 2022) ]')
            self.len(0, await core.nodes('entity:campaign#bar:footime.max=?'))
            self.len(0, await core.nodes('entity:campaign#bar:footime.min=2019-01-01'))

            await core.nodes('[ entity:campaign=(foo,) -:period -#foo -#bar:footime ]')

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

    async def test_layer_ndef_indexes(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=ndefs :ndefs=((it:dev:int, 1), (it:dev:int, 2)) ]')
            await core.nodes('test:str=ndefs [ :ndefs += (inet:fqdn, woot.com) ]')
            await core.nodes('[ risk:vulnerable=* :node=(it:dev:int, 1) ]')
            await core.nodes('[ risk:vulnerable=* :node=(inet:fqdn, foo.com) ]')
            await core.nodes('[ risk:vulnerable=* ]')

            self.len(0, await core.nodes('risk:vulnerable:node=(it:dev:str, newp)'))

            self.len(1, await core.nodes('risk:vulnerable:node.form=it:dev:int'))
            self.len(1, await core.nodes('risk:vulnerable:node.form=inet:fqdn'))
            self.len(0, await core.nodes('risk:vulnerable:node.form=it:dev:str'))

            self.len(2, await core.nodes('risk:vulnerable.created +:node.form'))
            self.len(1, await core.nodes('risk:vulnerable.created +:node.form=inet:fqdn'))

            self.len(2, await core.nodes('test:str:ndefs*[.form=it:dev:int]'))
            self.len(1, await core.nodes('test:str:ndefs*[.form=inet:fqdn]'))
            self.len(0, await core.nodes('test:str:ndefs*[.form=it:dev:str]'))

            self.len(1, await core.nodes('test:str.created +:ndefs*[.form=inet:fqdn]'))

            with self.raises(s_exc.NoSuchForm):
                await core.nodes('risk:vulnerable:node.form=newp')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('risk:vulnerable:node.newp=newp')

            await core.nodes('risk:vulnerable [ -:node ]')

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            await core.nodes('[ test:str=foo :bar=(test:int, 1) ]', opts=viewopts2)
            await core.nodes('[ test:str=foo :bar=(test:int, 1) ]')

            nodes = await core.nodes('test:int=1 <- *', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'foo'))

            await core.nodes('[ test:str=foo :bar=(test:int, 2) ]', opts=viewopts2)
            self.len(0, await core.nodes('test:int=1 <- *', opts=viewopts2))

            await core.nodes('[ test:str=foo -:bar ]', opts=viewopts2)
            self.len(0, await core.nodes('test:int=1 <- *', opts=viewopts2))

            await core.nodes('[ test:str=bar :bar=(test:int, 1) ]')
            nodes = await core.nodes('test:int=1 <- *', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'bar'))

            self.len(1, await core.nodes('it:dev:int=1 <- *', opts=viewopts2))

            await core.nodes('test:str=ndefs [ :ndefs=((test:str, foo),) ]', opts=viewopts2)
            self.len(0, await core.nodes('it:dev:int=1 <- *', opts=viewopts2))

            await core.nodes('test:str=ndefs [ -:ndefs ]', opts=viewopts2)
            self.len(0, await core.nodes('test:str=foo <- *', opts=viewopts2))

            q = '''[ test:str=ndefs :ndefs=(
                (test:str, foo),
                (test:str, foo),
                (test:str, bar),
                (test:str, foo)
            )]'''
            await core.nodes(q, opts=viewopts2)

            self.len(3, await core.nodes('test:str=foo <- *', opts=viewopts2))
            self.len(4, await core.nodes('test:str=ndefs -> *', opts=viewopts2))
            self.len(4, await core.nodes('test:str=ndefs :ndefs -> *', opts=viewopts2))

    async def test_layer_nodeprop_indexes(self):

        async with self.getTestCore() as core:

            self.len(0, await core.nodes('test:str:baz.prop=test:int:type'))
            self.len(0, await core.nodes('test:str:pdefs*[.prop=test:int:type]'))

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            await core.nodes('[ test:int=1 :type=one test:int=2 (test:str=hehe :hehe=cool) ]', opts=viewopts2)
            await core.nodes('[ test:str=foo :baz=(test:int:type, one) ]', opts=viewopts2)
            await core.nodes('[ test:str=bar :baz=(test:int:type, two) ]', opts=viewopts2)
            await core.nodes('[ test:str=baz :baz=(test:str:hehe, newp) ]', opts=viewopts2)
            await core.nodes('[ test:str=faz :pdefs=((test:int:type, one), (test:str:hehe, cool)) ]', opts=viewopts2)

            await core.nodes('[ test:str=foo :baz=(test:int:type, one) ]')

            nodes = await core.nodes('test:str:baz=(test:int:type, one)', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'foo'))

            nodes = await core.nodes('test:int=1 <- *', opts=viewopts2)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'foo'))
            self.eq(nodes[1].ndef, ('test:str', 'faz'))

            nodes = await core.nodes('test:str=foo -> *', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1))

            nodes = await core.nodes('test:str=foo :baz -> *', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1))

            nodes = await core.nodes('test:str=faz -> *', opts=viewopts2)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1))
            self.eq(nodes[1].ndef, ('test:str', 'hehe'))

            nodes = await core.nodes('test:str=faz :pdefs -> *', opts=viewopts2)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:int', 1))
            self.eq(nodes[1].ndef, ('test:str', 'hehe'))

            nodes = await core.nodes('test:str:baz.prop=test:int:type', opts=viewopts2)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'bar'))
            self.eq(nodes[1].ndef, ('test:str', 'foo'))

            nodes = await core.nodes('test:str:pdefs*[.prop=test:int:type]', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'faz'))

            self.len(0, await core.nodes('test:str:baz=(test:str:somestr, newp)'))
            self.len(0, await core.nodes('test:str:baz.prop=test:str:somestr'))

            await core.nodes('[ test:str=foo :baz=(test:int:type, three) ]', opts=viewopts2)

            self.len(0, await core.nodes('test:str:baz=(test:int:type, one)', opts=viewopts2))
            nodes = await core.nodes('test:str:baz=(test:int:type, three)', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'foo'))

            nodes = await core.nodes('test:int=1 <- *', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'faz'))

            await core.nodes('[ test:str=foo -:baz ]', opts=viewopts2)
            self.len(0, await core.nodes('test:str:baz=(test:int:type, three)', opts=viewopts2))

            await core.nodes('[ test:str=layr1 :baz=(test:int:type, one) ]')

            nodes = await core.nodes('test:int=1 <- *', opts=viewopts2)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'faz'))
            self.eq(nodes[1].ndef, ('test:str', 'layr1'))

            await core.nodes('[ test:str=layr1 :baz=(test:int:type, three) ]')
            await core.nodes('[ test:str=faz :pdefs=((test:str:hehe, cool),) ]', opts=viewopts2)
            nodes = await core.nodes('test:str=faz :pdefs -> *', opts=viewopts2)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'hehe'))
            self.len(0, await core.nodes('test:int=1 <- *', opts=viewopts2))

            await core.nodes('[ test:str=faz -:pdefs]', opts=viewopts2)
            self.len(0, await core.nodes('test:str:pdefs*[.prop=test:int:type]', opts=viewopts2))
            self.len(0, await core.nodes('test:int=1 <- *', opts=viewopts2))

            q = '''[ test:str=faz :pdefs=(
                (test:int:type, one),
                (test:int:type, one),
                (test:str:hehe, cool),
                (test:int:type, one))
            ]'''
            await core.nodes(q, opts=viewopts2)
            await core.nodes('[ test:str=faz :pdefs=((test:int:type, one),) ]')

            nodes = await core.nodes('test:int=1 <- *', opts=viewopts2)
            self.len(3, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'faz'))
            self.eq(nodes[1].ndef, ('test:str', 'faz'))
            self.eq(nodes[2].ndef, ('test:str', 'faz'))

            self.len(4, await core.nodes('test:str=faz -> *', opts=viewopts2))
            self.len(4, await core.nodes('test:str=faz :pdefs -> *', opts=viewopts2))

    async def test_layer_virt_indexes(self):

        async with self.getTestCore() as core:

            await core.nodes('''[
                inet:server=host://vertex.link:12341
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
                (test:str=piv1 :pivvirt=(if1,))
                (test:str=piv2 :pivvirt=(if2,))
            ]''')

            self.len(12, await core.nodes('inet:server.ip'))
            self.len(12, await core.nodes('inet:server.port'))
            self.len(1, await core.nodes('inet:server.ip=127.0.0.1'))
            self.len(2, await core.nodes('inet:server.ip*range=(127.0.0.2, 127.0.0.3)'))
            nodes = await core.nodes('inet:server.ip="::1"')
            self.len(1, nodes)
            self.eq(nodes[0].valu(), 'tcp://[::1]:12341')

            self.eq((4, 2130706433), await core.callStorm('inet:server.ip return(.ip)'))
            self.eq((4, 2130706433), (await core.nodes('inet:server.ip'))[0].get('.ip'))

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

            node = await view2.getNodeByBuid(nodes[0].buid, tombs=True)
            self.none(node.valu(virts='foo'))
            self.none(node.valuvirts())

            await core.nodes('[ inet:server=tcp://127.0.0.4:12344 +(refs)> { inet:server=tcp://127.0.0.4:12344 }]', opts=viewopts2)
            await core.nodes('inet:server=tcp://127.0.0.4:12344 [+(refs)> { inet:server=tcp://127.0.0.4:12344 }]', opts=viewopts2)
            self.len(1, await core.nodes('inet:server.ip=127.0.0.4', opts=viewopts2))

            nodes = await core.nodes('[ test:str=foo ]')
            await core.nodes('[ test:str=foo :seen=now ]', opts=viewopts2)
            await core.nodes('test:str=foo | delnode')

            node = await view2.getNodeByBuid(nodes[0].buid, tombs=True)
            self.none(node.valu(virts='foo'))

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('inet:server +.ip*newp=newp')

            await core.nodes('inet:server.ip | delnode')
            self.len(0, await core.nodes('inet:server.ip'))

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('inet:server.newp.ip')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('inet:server.ip.newp')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('inet:server.newp.ip=127.0.0.1')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('inet:server +.ip.newp=127.0.0.1')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:virtiface:servers*[newp=127.0.0.1]')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('test:virtiface:servers*[.newp*newp=127.0.0.1]')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('test:virtiface +:servers*[.newp*newp=127.0.0.1]')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:virtiface +:servers*[@=127.0.0.1]')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('inet:proto:request +inet:proto:request:server.newp*newp=newp')

            with self.raises(s_exc.BadCmprType):
                await core.nodes('inet:proto:request +:server*[newp=newp]')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('test:guid +test:guid:server.newp*newp=newp')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('test:guid +.created.newp*newp=newp')

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('test:guid.created +:newp.ip=newp')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:guid +test:guid.created*newp=newp')

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('test:virtiface +:newp*[.ip=127.0.0.1]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:virtiface:server*[.ip=127.0.0.1]')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:virtiface:server +test:virtiface:server.ip*newp=newp')

            self.len(0, await core.nodes('$val = (null) test:guid.created +:server.ip=$val'))
            self.len(0, await core.nodes('test:guid.created +:newp::servers.ip=127.0.0.1'))
            self.len(0, await core.nodes('test:virtiface +:newp::servers*[.ip=127.0.0.1]'))
            self.len(0, await core.nodes('test:guid.created +:server.newp'))
            self.len(0, await core.nodes('test:guid +test:str.created<now'))
            self.len(0, await core.nodes('test:guid +inet:server.ip=1.2.3.4'))
            self.len(0, await core.nodes('test:guid +inet:http:request:server.ip=1.2.3.4'))

            self.none(await core.callStorm('test:guid.created return(:newp::servers)'))

            layr = core.getLayer()
            indxby = s_layer.IndxByVirt(layr, 'inet:http:request', 'server', ['ip'])
            self.eq(str(indxby), 'IndxByVirt: inet:http:request:server.ip')

            indxby = s_layer.IndxByVirt(layr, 'test:guid', 'server', ['ip'])
            self.eq(str(indxby), 'IndxByVirt: test:guid:server.ip')

            indxby = s_layer.IndxByVirtArray(layr, 'test:virtiface', 'servers', ['ip'])
            self.eq(str(indxby), 'IndxByVirtArray: test:virtiface:servers.ip')

            self.len(0, await core.nodes('test:arrayform.size=2'))

            await core.nodes('[ test:arrayform=([1, 2]) test:arrayform=([2, 3]) test:arrayform=([4, 5, 6]) ]')

            self.len(1, await core.nodes('test:arrayform=([1, 2])'))
            self.len(1, await core.nodes('reverse(test:arrayform=([1, 2]))'))

            nodes = await core.nodes('test:arrayform.size=2')
            self.len(2, nodes)
            self.eq(nodes[::-1], await core.nodes('reverse(test:arrayform.size=2)'))

            self.len(2, await core.nodes('test:arrayform.size*range=(1, 2)'))

            nodes = await core.nodes('test:arrayform.size*range=(2, 3)')
            self.len(3, nodes)
            self.eq(nodes[::-1], await core.nodes('reverse(test:arrayform.size*range=(2, 3))'))

            indxby = s_layer.IndxByProp(layr, 'test:guid', 'server')
            self.eq(str(indxby), 'IndxByProp: test:guid:server')

            indxby = s_layer.IndxByPropKeys(layr, 'test:guid', 'server')
            self.eq(str(indxby), 'IndxByPropKeys: test:guid:server')

            indxby = s_layer.IndxByPropArray(layr, 'test:virtiface', 'servers')
            self.eq(str(indxby), 'IndxByPropArray: test:virtiface:servers')

            indxby = s_layer.IndxByPropArrayKeys(layr, 'test:virtiface', 'servers')
            self.eq(str(indxby), 'IndxByPropArrayKeys: test:virtiface:servers')

            indxby = s_layer.IndxByFormArrayValu(layr, 'test:arrayform')
            self.eq(str(indxby), 'IndxByFormArrayValu: test:arrayform')

            indxby = s_layer.IndxByFormArraySize(layr, 'test:arrayform')
            self.eq(str(indxby), 'IndxByFormArraySize: test:arrayform')

            indxby = s_layer.IndxByPropArrayValu(layr, 'test:virtiface', 'servers')
            self.eq(str(indxby), 'IndxByPropArrayValu: test:virtiface:servers')

            indxby = s_layer.IndxByPropArraySize(layr, 'test:virtiface', 'servers')
            self.eq(str(indxby), 'IndxByPropArraySize: test:virtiface:servers')

            with self.raises(s_exc.NoSuchVirt):
                await core.nodes('test:arrayform.newp*range=(2, 3)')

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:arrayform.size*newp=(2, 3)')

            self.len(1, await core.nodes('[ test:arrayvirtform=(2021?, 2022?) ]'))
            self.len(1, await core.nodes('test:arrayvirtform'))
            await core.nodes('test:arrayvirtform=(2021, 2022) | delnode')
            self.len(0, await core.nodes('test:arrayvirtform'))

    async def test_layer_readahead(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()
            self.true(layr.layrslab.readahead)
            self.true(layr.layrslab.lenv.flags()['readahead'])
            self.false(layr.nodeeditslab.readahead)
            self.false(layr.nodeeditslab.lenv.flags()['readahead'])
            self.false(layr.dataslab.readahead)
            self.false(layr.dataslab.lenv.flags()['readahead'])

            with self.setTstEnvars(SYNDEV_CORTEX_LAYER_READAHEAD='false'):
                iden = await core.callStorm('return($lib.layer.add().iden)')
                layr = core.getLayer(iden)
                self.false(layr.layrslab.readahead)
                self.false(layr.layrslab.lenv.flags()['readahead'])
                self.false(layr.nodeeditslab.readahead)
                self.false(layr.nodeeditslab.lenv.flags()['readahead'])
                self.false(layr.dataslab.readahead)
                self.false(layr.dataslab.lenv.flags()['readahead'])

    async def test_layer_delete_with_nodedata(self):

        async with self.getTestCore() as core:

            fork00 = await core.view.fork()
            infork00 = {'view': fork00['iden']}
            layr00 = core.getLayer(fork00['layers'][0]['iden'])

            iden = await core.callStorm('[ inet:ip=1.2.3.4 ] return($node.iden())')

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

                core01conf = {'mirror': url}

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

            async with self.getTestCore(dirn=path01, conf=core01conf) as core01:

                indx = await core01.getNexsIndx()

                # attempt to edit a node on the mirror in a layer that has been deleted on the leader
                async def doEdit():
                    with self.raises(s_exc.NoSuchLayer):
                        await core01.nodes('test:str=bar [ :seen=2020 ]', opts=opts3)

                task = core01.schedCoro(doEdit())

                async with self.getTestCore(dirn=path00) as core00:

                    await asyncio.wait_for(task, timeout=6)

                    await core01.sync()

                    evnts = [n[1][1] for n in await alist(core01.nexsroot.nexslog.iter(indx))]
                    self.eq(['view:del', 'layer:del', 'sync'], evnts)

    async def test_layer_migrate_props_fork(self):

        async with self.getTestCore() as core:

            iden = (await core.addUser('lowuser')).get('iden')
            lowuser = {'user': iden}

            fork00 = await core.view.fork()
            layr00 = core.getLayer(fork00['layers'][0]['iden'])

            await core.nodes('''
                for $prop in (_custom:risk:level, _custom:risk:severity) {
                    $lib.model.ext.addFormProp(
                        test:guid,
                        $prop,
                        (["int", {"enums": [[10, "low"], [20, "medium"], [30, "high"]]}]),
                        ({"doc": "hey now"}),
                    )
                }

            ''')
            self.len(1, await core.nodes('syn:prop=test:guid:_custom:risk:level'))
            self.len(1, await core.nodes('syn:prop=test:guid:_custom:risk:severity'))

            await core.nodes('[ test:guid=* :name=test1 :_custom:risk:level=low ]', opts={'view': fork00['iden']})

            await core.getView(fork00['iden']).delete()

            with self.raises(s_exc.CantDelProp) as cm:
                await core.callStorm('''
                    $fullprop = "test:guid:_custom:risk:level"
                    for $view in $lib.view.list(deporder=$lib.true) {
                        view.exec $view.iden {
                            yield $lib.layer.get().liftByProp($fullprop)
                            $repr = $node.repr("_custom:risk:level")
                            [ :severity=$repr -:_custom:risk:level ]
                        }
                    }
                    $lib.model.ext.delFormProp("test:guid", "_custom:risk:level")
                ''')
            self.isin('Nodes still exist with prop: test:guid:_custom:risk:level', str(cm.exception))
            self.len(1, await core.nodes('syn:prop=test:guid:_custom:risk:level'))

            with self.raises(s_exc.NoSuchProp) as cm:
                await core.callStorm('''
                    $layer = $lib.layer.get()
                    for $x in $layer.getStorNodesByProp("foo:bar:_custom:risk:level") {}
                ''')
            self.isin('No property named', str(cm.exception))

            with self.raises(s_exc.NoSuchProp):
                await core.callStorm('''
                    $fullprop = "test:guid:_custom:risk:level"
                    for $layer in $lib.layer.list() {
                        for ($nid, $sode) in $layer.getStorNodesByProp($fullprop) {
                            $oldv = $sode.props."_custom:risk:level"
                            $layer.setStorNodeProp($nid, "foo:bar:severity", $oldv.0)
                        }
                    }
                ''')

            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('''
                    $fullprop = "test:guid:_custom:risk:level"
                    for $layer in $lib.layer.list() {
                        for ($nid, $sode) in $layer.getStorNodesByProp($fullprop) {
                            $layer.setStorNodeProp($nid, $fullprop, "newp")
                        }
                    }
                ''')

            with self.raises(s_exc.NoSuchProp):
                await core.callStorm('''
                    $fullprop = "test:guid:_custom:risk:level"
                    for $layer in $lib.layer.list() {
                        for ($nid, $sode) in $layer.getStorNodesByProp($fullprop) {
                            $layer.delStorNodeProp($nid, "foo:bar:severity")
                        }
                    }
                ''')

            with self.raises(s_exc.AuthDeny) as cm:
                await core.callStorm('''
                    $nid = (1)
                    $layer = $lib.layer.get()
                    $layer.setStorNodeProp($nid, "foo:bar:severity", "newp")
                ''', opts=lowuser)
            self.isin('requires admin privileges', str(cm.exception))

            with self.raises(s_exc.AuthDeny) as cm:
                await core.callStorm('''
                    $nid = (1)
                    $layer = $lib.layer.get()
                    $layer.delStorNodeProp($nid, "foo:bar:severity")
                ''', opts=lowuser)
            self.isin('requires admin privileges', str(cm.exception))

            await core.callStorm('''
                $fullprop = "test:guid:_custom:risk:level"
                for $layer in $lib.layer.list() {
                    if $layer.getPropCount($fullprop) {
                        for ($nid, $sode) in $layer.getStorNodesByProp($fullprop, (10), "=") {
                            $oldv = $sode.props."_custom:risk:level"
                            $layer.setStorNodeProp($nid, "test:guid:_custom:risk:severity", $oldv.0)
                            $layer.delStorNodeProp($nid, $fullprop)
                        }
                    }
                }
                $lib.model.ext.delFormProp("test:guid", "_custom:risk:level")
            ''')
            self.len(0, await core.nodes('syn:prop=test:guid:_custom:risk:level'))
            self.len(0, await core.nodes('test:guid:_custom:risk:severity'))

            view00 = (await core.addView(vdef={'layers': [layr00.iden]}))['iden']
            nodes = await core.nodes('test:guid', opts={'view': view00})
            self.len(1, nodes)
            self.none(nodes[0].get('_custom:risk:level'))
            self.eq(nodes[0].get('_custom:risk:severity'), 10)
