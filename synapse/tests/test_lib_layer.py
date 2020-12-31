import os
import math
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack

import synapse.tools.backup as s_tools_backup

import synapse.tests.utils as s_t_utils

from synapse.tests.utils import alist

async def iterPropForm(self, form=None, prop=None):
    bad_valu = [(b'foo', "bar"), (b'bar', ('bar',)), (b'biz', 4965), (b'baz', (0, 56))]
    bad_valu += [(b'boz', 'boz')] * 10
    for buid, valu in bad_valu:
        yield buid, valu

class LayerTest(s_t_utils.SynTest):

    async def test_layer_abrv(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x04', layr.setPropAbrv('visi', 'foo'))
            # another to check the cache...
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x04', layr.getPropAbrv('visi', 'foo'))
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x05', layr.setPropAbrv('whip', None))
            self.eq(('visi', 'foo'), layr.getAbrvProp(b'\x00\x00\x00\x00\x00\x00\x00\x04'))
            self.eq(('whip', None), layr.getAbrvProp(b'\x00\x00\x00\x00\x00\x00\x00\x05'))
            self.raises(s_exc.NoSuchAbrv, layr.getAbrvProp, b'\x00\x00\x00\x00\x00\x00\x00\x06')

            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x00', layr.setTagPropAbrv('visi', 'foo'))
            # another to check the cache...
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x00', layr.getTagPropAbrv('visi', 'foo'))
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x01', layr.setTagPropAbrv('whip', None))

    async def test_layer_upstream(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:

                layriden = core00.view.layers[0].iden

                await core00.nodes('[test:str=foobar +#hehe.haha]')
                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')
                await core00.addTagProp('score', ('int', {}), {})

                async with await core00.snap() as snap:

                    props = {'tick': 12345}
                    node1 = await snap.addNode('test:str', 'foo', props=props)
                    await node1.setTagProp('bar', 'score', 10)
                    await node1.setData('baz', 'nodedataiscool')

                    node2 = await snap.addNode('test:str', 'bar', props=props)
                    await node2.setData('baz', 'nodedataiscool')

                    await node1.addEdge('refs', node2.iden())

                async with self.getTestCore(dirn=path01) as core01:

                    # test layer/<iden> mapping
                    async with core00.getLocalProxy(f'*/layer/{layriden}') as layrprox:
                        self.eq(layriden, await layrprox.getIden())

                    url = core00.getLocalUrl('*/layer')
                    conf = {'upstream': url}
                    ldef = await core01.addLayer(ldef=conf)
                    layr = core01.getLayer(ldef.get('iden'))
                    await core01.view.addLayer(layr.iden)

                    # test initial sync
                    offs = await core00.getView().layers[0].getEditIndx()
                    evnt = await layr.waitUpstreamOffs(layriden, offs)
                    await asyncio.wait_for(evnt.wait(), timeout=2.0)

                    self.len(1, await core01.nodes('inet:ipv4=1.2.3.4'))
                    nodes = await core01.nodes('test:str=foobar')
                    self.len(1, nodes)
                    self.nn(nodes[0].tags.get('hehe.haha'))

                    async with await core01.snap() as snap:
                        node = await snap.getNodeByNdef(('test:str', 'foo'))
                        self.nn(node)
                        self.eq(node.props.get('tick'), 12345)
                        self.eq(node.tagprops.get(('bar', 'score')), 10)
                        self.eq(await node.getData('baz'), 'nodedataiscool')
                        self.len(1, await alist(node.iterEdgesN1()))

                    # make sure updates show up
                    await core00.nodes('[ inet:fqdn=vertex.link ]')

                    offs = await core00.getView().layers[0].getEditIndx()
                    evnt = await layr.waitUpstreamOffs(layriden, offs)
                    await asyncio.wait_for(evnt.wait(), timeout=2.0)

                    self.len(1, await core01.nodes('inet:fqdn=vertex.link'))

                await core00.nodes('[ inet:ipv4=5.5.5.5 ]')
                offs = await core00.getView().layers[0].getEditIndx()

                # test what happens when we go down and come up again...
                async with self.getTestCore(dirn=path01) as core01:

                    layr = core01.getView().layers[-1]

                    evnt = await layr.waitUpstreamOffs(layriden, offs)
                    await asyncio.wait_for(evnt.wait(), timeout=2.0)

                    self.len(1, await core01.nodes('inet:ipv4=5.5.5.5'))

                    await core00.nodes('[ inet:ipv4=5.6.7.8 ]')

                    offs = await core00.getView().layers[0].getEditIndx()
                    evnt = await layr.waitUpstreamOffs(layriden, offs)
                    await asyncio.wait_for(evnt.wait(), timeout=2.0)

                    self.len(1, await core01.nodes('inet:ipv4=5.6.7.8'))

                    # make sure time and user are set on the downstream splices
                    root = await core01.auth.getUserByName('root')

                    splices = await alist(layr.splicesBack(size=1))
                    self.len(1, splices)

                    splice = splices[0][1][1]
                    self.nn(splice.get('time'))
                    self.eq(splice.get('user'), root.iden)
                    self.none(splice.get('prov'))

    async def test_layer_upstream_with_mirror(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')  # layer upstream
            path01 = s_common.gendir(dirn, 'core01')  # layer downstream, mirror leader
            path02 = s_common.gendir(dirn, 'core02')  # layer downstream, mirror follower

            async with self.getTestCore(dirn=path00) as core00:

                layriden = core00.view.layers[0].iden

                await core00.nodes('[test:str=foobar +#hehe.haha]')
                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')
                await core00.addTagProp('score', ('int', {}), {})

                async with self.getTestCore(dirn=path01) as core01:
                    url = core00.getLocalUrl('*/layer')
                    conf = {'upstream': url}
                    ldef = await core01.addLayer(ldef=conf)
                    layr = core01.getLayer(ldef.get('iden'))
                    await core01.view.addLayer(layr.iden)

                s_tools_backup.backup(path01, path02)

                async with self.getTestCore(dirn=path01) as core01:
                    layr = core01.getLayer(ldef.get('iden'))

                    # Sync core01 with core00
                    offs = await core00.getView().layers[0].getEditIndx()
                    evnt = await layr.waitUpstreamOffs(layriden, offs)
                    await asyncio.wait_for(evnt.wait(), timeout=8.0)

                    self.len(1, await core01.nodes('inet:ipv4=1.2.3.4'))

                    url = core01.getLocalUrl()

                    async with self.getTestCore(dirn=path02, conf={'mirror': url}) as core02:
                        await core02.sync()

                        layr = core01.getLayer(ldef.get('iden'))
                        self.true(layr.allow_upstream)

                        layr = core02.getLayer(ldef.get('iden'))
                        self.false(layr.allow_upstream)

                        self.len(1, await core02.nodes('inet:ipv4=1.2.3.4'))

    async def test_layer_multi_upstream(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')
            path02 = s_common.gendir(dirn, 'core02')

            async with self.getTestCore(dirn=path00) as core00:

                iden00 = core00.view.layers[0].iden

                await core00.nodes('[test:str=foobar +#hehe.haha]')
                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')

                async with self.getTestCore(dirn=path01) as core01:

                    iden01 = core01.view.layers[0].iden

                    await core01.nodes('[test:str=barfoo +#haha.hehe]')
                    await core01.nodes('[ inet:ipv4=4.3.2.1 ]')

                    async with self.getTestCore(dirn=path02) as core02:

                        url00 = core00.getLocalUrl('*/layer')
                        url01 = core01.getLocalUrl('*/layer')

                        conf = {'upstream': [url00, url01]}

                        ldef = await core02.addLayer(ldef=conf)
                        layr = core02.getLayer(ldef.get('iden'))
                        await core02.view.addLayer(layr.iden)

                        # core00 is synced
                        offs = await core00.getView().layers[0].getEditIndx()
                        evnt = await layr.waitUpstreamOffs(iden00, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=1.2.3.4'))
                        nodes = await core02.nodes('test:str=foobar')
                        self.len(1, nodes)
                        self.nn(nodes[0].tags.get('hehe.haha'))

                        # core01 is synced
                        offs = await core01.getView().layers[0].getEditIndx()
                        evnt = await layr.waitUpstreamOffs(iden01, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=4.3.2.1'))
                        nodes = await core02.nodes('test:str=barfoo')
                        self.len(1, nodes)
                        self.nn(nodes[0].tags.get('haha.hehe'))

                        # updates from core00 show up
                        await core00.nodes('[ inet:fqdn=vertex.link ]')

                        offs = await core00.getView().layers[0].getEditIndx()
                        evnt = await layr.waitUpstreamOffs(iden00, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:fqdn=vertex.link'))

                        # updates from core01 show up
                        await core01.nodes('[ inet:fqdn=google.com ]')

                        offs = await core01.getView().layers[0].getEditIndx()
                        evnt = await layr.waitUpstreamOffs(iden01, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:fqdn=google.com'))

                    await core00.nodes('[ inet:ipv4=5.5.5.5 ]')
                    await core01.nodes('[ inet:ipv4=6.6.6.6 ]')

                    # test what happens when we go down and come up again...
                    async with self.getTestCore(dirn=path02) as core02:

                        layr = core02.getView().layers[-1]

                        # test we catch up to core00
                        offs = await core00.getView().layers[0].getEditIndx()
                        evnt = await layr.waitUpstreamOffs(iden00, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=5.5.5.5'))

                        # test we catch up to core01
                        offs = await core01.getView().layers[0].getEditIndx()
                        evnt = await layr.waitUpstreamOffs(iden01, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=6.6.6.6'))

                        # test we get updates from core00
                        await core00.nodes('[ inet:ipv4=5.6.7.8 ]')

                        offs = await core00.getView().layers[0].getEditIndx()
                        evnt = await layr.waitUpstreamOffs(iden00, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=5.6.7.8'))

                        # test we get updates from core01
                        await core01.nodes('[ inet:ipv4=8.7.6.5 ]')

                        offs = await core01.getView().layers[0].getEditIndx()
                        evnt = await layr.waitUpstreamOffs(iden01, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=8.7.6.5'))

    async def test_layer_splices(self):

        async with self.getTestCore() as core:

            layr = core.view.layers[0]
            root = await core.auth.getUserByName('root')

            splices = await alist(layr.splices(None, 10))
            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            await core.addTagProp('risk', ('int', {'min': 0, 'max': 100}), {'doc': 'risk score'})

            # Convert a node:add splice
            await core.nodes('[ test:str=foo ]')

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'node:add')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a prop:set splice with no oldv
            await core.nodes("test:str=foo [ :tick=2000 ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'prop:set')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['prop'], 'tick')
            self.eq(splice[1]['valu'], 946684800000)
            self.eq(splice[1]['oldv'], None)
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a prop:set splice with an oldv
            await core.nodes("test:str=foo [ :tick=2001 ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'prop:set')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['prop'], 'tick')
            self.eq(splice[1]['valu'], 978307200000)
            self.eq(splice[1]['oldv'], 946684800000)
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a prop:del splice
            await core.nodes("test:str=foo [ -:tick ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'prop:del')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['prop'], 'tick')
            self.eq(splice[1]['valu'], 978307200000)
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a tag:add splice with no oldv
            await core.nodes("test:str=foo [ +#haha=2000 ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[4][1]
            self.eq(splice[0], 'tag:add')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['tag'], 'haha')
            self.eq(splice[1]['valu'], (946684800000, 946684800001))
            self.eq(splice[1]['oldv'], None)
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a tag:add splice with an oldv
            await core.nodes("test:str=foo [ +#haha=2001 ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'tag:add')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['tag'], 'haha')
            self.eq(splice[1]['valu'], (946684800000, 978307200001))
            self.eq(splice[1]['oldv'], (946684800000, 946684800001))
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a tag:del splice
            await core.nodes("test:str=foo [ -#haha ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'tag:del')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['tag'], 'haha')
            self.eq(splice[1]['valu'], (946684800000, 978307200001))
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a tag:prop:add splice with no oldv
            await core.nodes("test:str=foo [ +#rep:risk=50 ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[5][1]
            self.eq(splice[0], 'tag:prop:set')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['tag'], 'rep')
            self.eq(splice[1]['prop'], 'risk')
            self.eq(splice[1]['valu'], 50)
            self.eq(splice[1]['oldv'], None)
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a tag:prop:add splice with an oldv
            await core.nodes("test:str=foo [ +#rep:risk=0 ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'tag:prop:set')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['tag'], 'rep')
            self.eq(splice[1]['prop'], 'risk')
            self.eq(splice[1]['valu'], 0)
            self.eq(splice[1]['oldv'], 50)
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Convert a tag:prop:del splice
            await core.nodes("test:str=foo [ -#rep:risk ]")

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'tag:prop:del')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['tag'], 'rep')
            self.eq(splice[1]['prop'], 'risk')
            self.eq(splice[1]['valu'], 0)
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = (splices[-1][0][0] + 1, 0, 0)

            # Nodedata edits don't make splices
            nodes = await core.nodes('test:str=foo')
            await nodes[0].setData('baz', 'nodedataiscool')

            splices = await alist(layr.splices(spliceoffs, 10))
            self.len(0, splices)

            # Make sure nodedata edits have oldv set
            nedit = await layr.iterNodeEditLog(spliceoffs[0]).__anext__()
            self.eq(nedit[1][0][2][0][1], ('baz', 'nodedataiscool', None))

            spliceoffs = (spliceoffs[0] + 1, 0, 0)

            await nodes[0].setData('baz', 'stillcool')
            nedit = await layr.iterNodeEditLog(spliceoffs[0]).__anext__()
            self.eq(nedit[1][0][2][0][1], ('baz', 'stillcool', 'nodedataiscool'))

            # Convert a node:del splice
            await core.nodes('test:str=foo | delnode')

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[2][1]
            self.eq(splice[0], 'node:del')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            # Get all the splices
            splices = [x async for x in layr.splices()]
            self.len(26, splices)

            # Get all but the first splice
            await self.agenlen(25, layr.splices(splices[1][0]))

            await self.agenlen(4, layr.splicesBack(splices[3][0]))

            # Make sure we still get two splices when
            # offset is not at the beginning of a nodeedit
            await self.agenlen(2, layr.splices((1, 0, 200), 2))
            await self.agenlen(2, layr.splicesBack((3, 0, -1), 2))

            # Use the layer api to get the splices
            url = core.getLocalUrl('*/layer')
            async with await s_telepath.openurl(url) as layrprox:
                await self.agenlen(26, layrprox.splices())

    async def test_layer_stortype_hier(self):
        stor = s_layer.StorTypeHier(None, None)

        vals = ['', 'foo', 'foo.bar']

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

    async def test_layer_stortype_ipv6(self):
        stor = s_layer.StorTypeIpv6(None)

        vals = ('::1', 'fe80::431c:39b2:888:974')

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eq(valu, stor.decodeIndx(indx[0]))

    async def test_layer_stortype_hugenum(self):
        stor = s_layer.StorTypeHugeNum(self, None)

        vals = [-99999.9, -0.0000000001, -42.1, -0.0, 0.0, 0.000001, 42.1, 99999.9, 2**63 + 1.1]

        for valu, indx in ((v, stor.indx(v)) for v in vals):
            self.eqish(valu, stor.decodeIndx(indx[0]), places=3)

    async def test_layer_stortype_ival(self):
        stor = s_layer.StorTypeIval(self)

        vals = [(2000, 2020), (1960, 1970)]

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
                layr.layrslab.put(key[0], val, db=tmpdb)

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '=', minv)]
            self.eq(retn, [minv])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '=', maxv)]
            self.eq(retn, [maxv])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<', minv + 1)]
            self.eq(retn, [minv])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>', maxv - 1)]
            self.eq(retn, [maxv])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<=', minv)]
            self.eq(retn, [minv])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>=', maxv)]
            self.eq(retn, [maxv])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, 'range=', (minv, maxv))]
            self.eq(retn, vals)

            # Should get no results instead of overflowing
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '=', minv - 1)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '=', maxv + 1)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<', minv)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>', maxv)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<=', minv - 1)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>=', maxv + 1)]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, 'range=', (minv - 2, minv - 1))]
            self.eq(retn, [])

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, 'range=', (maxv + 1, maxv + 2))]
            self.eq(retn, [])

            # Value is out of range but there are still valid results
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<', maxv + 2)]
            self.eq(retn, vals)

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>', minv - 2)]
            self.eq(retn, vals)

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<=', maxv + 1)]
            self.eq(retn, vals)

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>=', minv - 1)]
            self.eq(retn, vals)

            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, 'range=', (minv - 1, maxv + 1))]
            self.eq(retn, vals)

    async def test_layer_stortype_float(self):
        async with self.getTestCore() as core:

            layr = core.view.layers[0]
            tmpdb = layr.layrslab.initdb('temp', dupsort=True)

            stor = s_layer.StorTypeFloat(layr, s_layer.STOR_TYPE_FLOAT64, 8)
            vals = [math.nan, -math.inf, -99999.9, -0.0000000001, -42.1, -0.0, 0.0, 0.000001, 42.1, 99999.9, math.inf]

            indxby = s_layer.IndxBy(layr, b'', tmpdb)
            self.raises(s_exc.NoSuchImpl, indxby.getNodeValu, s_common.guid())

            for key, val in ((stor.indx(v), s_msgpack.en(v)) for v in vals):
                layr.layrslab.put(key[0], val, db=tmpdb)
                self.eqOrNan(s_msgpack.un(val), stor.decodeIndx(key[0]))

            # = -99999.9
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '=', -99999.9)]
            self.eq(retn, [-99999.9])

            # <= -99999.9
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<=', -99999.9)]
            self.eq(retn, [-math.inf, -99999.9])

            # < -99999.9
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<', -99999.9)]
            self.eq(retn, [-math.inf])

            # > 99999.9
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>', 99999.9)]
            self.eq(retn, [math.inf])

            # >= 99999.9
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>=', 99999.9)]
            self.eq(retn, [99999.9, math.inf])

            # <= 0.0
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<=', 0.0)]
            self.eq(retn, [-math.inf, -99999.9, -42.1, -0.0000000001, -0.0, 0.0])

            # >= -0.0
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>=', -0.0)]
            self.eq(retn, [-0.0, 0.0, 0.000001, 42.1, 99999.9, math.inf])

            # >= -42.1
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>=', -42.1)]
            self.eq(retn, [-42.1, -0.0000000001, -0.0, 0.0, 0.000001, 42.1, 99999.9, math.inf])

            # > -42.1
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '>', -42.1)]
            self.eq(retn, [-0.0000000001, -0.0, 0.0, 0.000001, 42.1, 99999.9, math.inf])

            # < 42.1
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<', 42.1)]
            self.eq(retn, [-math.inf, -99999.9, -42.1, -0.0000000001, -0.0, 0.0, 0.000001])

            # <= 42.1
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, '<=', 42.1)]
            self.eq(retn, [-math.inf, -99999.9, -42.1, -0.0000000001, -0.0, 0.0, 0.000001, 42.1])

            # -42.1 to 42.1
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, 'range=', (-42.1, 42.1))]
            self.eq(retn, [-42.1, -0.0000000001, -0.0, 0.0, 0.000001, 42.1])

            # 1 to 42.1
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, 'range=', (1.0, 42.1))]
            self.eq(retn, [42.1])

            # -99999.9 to -0.1
            retn = [s_msgpack.un(valu) async for valu in stor.indxBy(indxby, 'range=', (-99999.9, -0.1))]
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

    async def test_layer_stortype_merge(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()
            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 .seen=(2012,2014) +#foo.bar=(2012, 2014) ]')

            buid = nodes[0].buid
            ival = nodes[0].get('.seen')
            tick = nodes[0].get('.created')
            tagv = nodes[0].getTag('foo.bar')

            newival = (ival[0] + 100, ival[1] - 100)
            newtagv = (tagv[0] + 100, tagv[1] - 100)

            nodeedits = [
                (buid, 'inet:ipv4', (
                    (s_layer.EDIT_PROP_SET, ('.seen', newival, ival, s_layer.STOR_TYPE_IVAL), ()),
                )),
            ]

            await layr.storNodeEdits(nodeedits, {})

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +.seen=(2012,2014)'))

            nodeedits = [
                (buid, 'inet:ipv4', (
                    (s_layer.EDIT_PROP_SET, ('.created', tick + 200, tick, s_layer.STOR_TYPE_MINTIME), ()),
                )),
            ]

            await layr.storNodeEdits(nodeedits, {})

            nodes = await core.nodes('inet:ipv4=1.2.3.4')
            self.eq(tick, nodes[0].get('.created'))

            nodeedits = [
                (buid, 'inet:ipv4', (
                    (s_layer.EDIT_PROP_SET, ('.created', tick - 200, tick, s_layer.STOR_TYPE_MINTIME), ()),
                )),
            ]

            await layr.storNodeEdits(nodeedits, {})

            nodes = await core.nodes('inet:ipv4=1.2.3.4')
            self.eq(tick - 200, nodes[0].get('.created'))

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]')
            self.eq(tick - 200, nodes[0].get('.created'))

            nodeedits = [
                (buid, 'inet:ipv4', (
                    (s_layer.EDIT_TAG_SET, ('foo.bar', newtagv, tagv), ()),
                )),
            ]

            await layr.storNodeEdits(nodeedits, {})

            nodes = await core.nodes('inet:ipv4=1.2.3.4')
            self.eq(tagv, nodes[0].getTag('foo.bar'))

            nodes = await core.nodes('inet:ipv4=1.2.3.4 [ +#foo.bar=2015 ]')
            self.eq((1325376000000, 1420070400001), nodes[0].getTag('foo.bar'))

    async def test_layer_nodeedits_created(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:int=1 :loc=us ]')
            created00 = nodes[0].get('.created')
            self.nn(created00)

            layr = core.getLayer()

            editlist00 = [nes async for nes in layr.iterLayerNodeEdits()]
            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # Simulate a nexus edit list (no .created)
            nexslist00 = [(ne[0], ne[1], [e for e in ne[2] if e[1][0] != '.created']) for ne in editlist00]

            # meta used for .created
            await asyncio.sleep(0.01)
            await layr.storNodeEdits(nexslist00, {'time': created00})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            self.eq(created00, nodes[0].get('.created'))

            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # If meta is not specified .created gets populated to now
            await asyncio.sleep(0.01)
            await layr.storNodeEdits(nexslist00, {})

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
            await layr.storNodeEdits(editlist00, {'time': created02})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            self.eq(created02, nodes[0].get('.created'))

            await core.nodes('test:int=1 | delnode')
            self.len(0, await core.nodes('test:int'))

            # meta could be after .created for manual store operations
            created03 = s_time.parse('2050-10-10 12:30')
            await layr.storNodeEdits(editlist00, {'time': created03})

            nodes = await core.nodes('test:int')
            self.len(1, nodes)

            self.eq(created00, nodes[0].get('.created'))

    async def test_layer_nodeedits(self):

        async with self.getTestCoreAndProxy() as (core0, prox0):

            nodelist0 = []
            nodes = await core0.nodes('[ test:str=foo ]')
            nodelist0.extend(nodes)
            nodes = await core0.nodes('[ inet:ipv4=1.2.3.4 .seen=(2012,2014) +#foo.bar=(2012, 2014) ]')
            nodelist0.extend(nodes)

            nodelist0 = [node.pack() for node in nodelist0]

            editlist = []

            layr = core0.getLayer()
            async for offs, nodeedits in prox0.syncLayerNodeEdits(0):
                editlist.append(nodeedits)
                if offs == layr.nodeeditlog.index() - 1:
                    break

            async with self.getTestCore() as core1:

                url = core1.getLocalUrl('*/layer')

                async with await s_telepath.openurl(url) as layrprox:

                    for nodeedits in editlist:
                        self.nn(await layrprox.storNodeEdits(nodeedits))

                    nodelist1 = []
                    nodelist1.extend(await core1.nodes('test:str'))
                    nodelist1.extend(await core1.nodes('inet:ipv4'))

                    nodelist1 = [node.pack() for node in nodelist1]
                    self.eq(nodelist0, nodelist1)

                layr = core1.view.layers[0]

                # Empty the layer to try again

                await layr.truncate()

                async with await s_telepath.openurl(url) as layrprox:

                    for nodeedits in editlist:
                        self.none(await layrprox.storNodeEditsNoLift(nodeedits))

                    nodelist1 = []
                    nodelist1.extend(await core1.nodes('test:str'))
                    nodelist1.extend(await core1.nodes('inet:ipv4'))

                    nodelist1 = [node.pack() for node in nodelist1]
                    self.eq(nodelist0, nodelist1)

                    meta = {'user': s_common.guid(),
                            'time': 0,
                            }

                    await layr.truncate()

                    for nodeedits in editlist:
                        self.none(await layrprox.storNodeEditsNoLift(nodeedits, meta=meta))

                    lastoffs = layr.nodeeditlog.index()
                    for nodeedit in layr.nodeeditlog.sliceBack(lastoffs, 2):
                        self.eq(meta, nodeedit[1][1])

                    async def waitForEdit():
                        edit = (0, ('endofquery', 1), ())
                        async for item in layr.syncNodeEdits(lastoffs):
                            if item[1][0][1] == 'test:str' and edit in item[1][0][2]:
                                return
                            await asyncio.sleep(0)

                    async def doEdit():
                        await core1.nodes('sleep 1 | [ test:str=endofquery ]')

                    core1.schedCoro(doEdit())
                    await asyncio.wait_for(waitForEdit(), timeout=6)

    async def test_layer_stornodeedits_nonexus(self):
        # test for migration methods that store nodeedits bypassing nexus

        async with self.getTestCore() as core0:

            layer0 = core0.getLayer()

            await core0.nodes('[ test:str=foo ]')
            self.len(2, await core0.nodes('.created'))

            nodeedits = [ne async for ne in layer0.iterLayerNodeEdits()]
            self.len(2, nodeedits)

            await core0.nodes('.created | delnode --force')

            flatedits = await layer0._storNodeEdits(nodeedits, {}, None)
            self.len(2, flatedits)

            self.len(2, await core0.nodes('.created'))

    async def test_layer_syncindexevents(self):

        async with self.getTestCore() as core:
            layr = core.getLayer()
            await core.addTagProp('score', ('int', {}), {})
            baseoff = await core.getNexsIndx()

            nodes = await core.nodes('[ test:str=foo ]')
            strnode = nodes[0]
            q = '[ inet:ipv4=1.2.3.4 :asn=42 .seen=(2012,2014) +#mytag:score=99 +#foo.bar=(2012, 2014) ]'
            nodes = await core.nodes(q)
            ipv4node = nodes[0]

            await core.nodes('inet:ipv4=1.2.3.4 test:str=foo | delnode')

            mdef = {'forms': ['test:str']}
            events = await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))
            self.len(2, events)
            expectadd = (baseoff, (strnode.buid, 'test:str', s_layer.EDIT_NODE_ADD,
                                   ('foo', s_layer.STOR_TYPE_UTF8), ()))
            expectdel = (baseoff + 19, (strnode.buid, 'test:str', s_layer.EDIT_NODE_DEL,
                                        ('foo', s_layer.STOR_TYPE_UTF8), ()))
            self.eq(events, [expectadd, expectdel])

            mdef = {'props': ['.seen']}
            events = await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))
            self.len(2, events)
            ival = tuple([s_time.parse(x) for x in ('2012', '2014')])
            expectadd = (baseoff + 3, (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_PROP_SET,
                                       ('.seen', ival, None, s_layer.STOR_TYPE_IVAL), ()))
            expectdel = (baseoff + 16, (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_PROP_DEL,
                                        ('.seen', ival, s_layer.STOR_TYPE_IVAL), ()))
            self.eq(events, [expectadd, expectdel])

            mdef = {'props': ['inet:ipv4:asn']}
            events = await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))
            self.len(2, events)
            expectadd = (baseoff + 2, (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_PROP_SET,
                                       ('asn', 42, None, s_layer.STOR_TYPE_I64), ()))
            expectdel = (baseoff + 15, (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_PROP_DEL,
                                        ('asn', 42, s_layer.STOR_TYPE_I64), ()))
            self.eq(events, [expectadd, expectdel])

            mdef = {'tags': ['foo.bar']}
            events = await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))
            self.len(2, events)
            expectadd = (baseoff + 9, (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_TAG_SET,
                                       ('foo.bar', ival, None), ()))
            expectdel = (baseoff + 10, (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_TAG_DEL,
                                        ('foo.bar', ival), ()))
            self.eq(events, [expectadd, expectdel])

            mdefs = ({'tagprops': ['score']}, {'tagprops': ['mytag:score']})
            for mdef in mdefs:
                events = await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))
                self.len(2, events)
                expectadd = (baseoff + 6, (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_TAGPROP_SET,
                                           ('mytag', 'score', 99, None, s_layer.STOR_TYPE_I64), ()))
                expectdel = (baseoff + 11, (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_TAGPROP_DEL,
                                            ('mytag', 'score', 99, s_layer.STOR_TYPE_I64), ()))
                self.eq(events, [expectadd, expectdel])

            mdef = {'forms': ['test:str', 'inet:ipv4'], 'tags': ['foo', ]}
            count = 0
            async for item in layr.syncIndexEvents(baseoff, mdef):
                count += 1
                if count == 4:
                    await core.nodes('test:str=bar')
                if count == 5:
                    break

            self.eq(count, 5)

    async def test_layer_form_by_buid(self):

        async with self.getTestCore() as core:

            layr00 = core.view.layers[0]

            # add node - buid:form exists
            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :loc=us ]')
            buid0 = nodes[0].buid
            self.eq('inet:ipv4', await layr00.getNodeForm(buid0))

            # add edge and nodedata
            nodes = await core.nodes('[ inet:ipv4=2.3.4.5 ]')
            buid1 = nodes[0].buid
            self.eq('inet:ipv4', await layr00.getNodeForm(buid1))

            await core.nodes('inet:ipv4=1.2.3.4 [ +(refs)> {inet:ipv4=2.3.4.5} ] $node.data.set(spam, ham)')
            self.eq('inet:ipv4', await layr00.getNodeForm(buid0))

            # remove edge, map still exists
            await core.nodes('inet:ipv4=1.2.3.4 [ -(refs)> {inet:ipv4=2.3.4.5} ]')
            self.eq('inet:ipv4', await layr00.getNodeForm(buid0))

            # remove nodedata, map still exists
            await core.nodes('inet:ipv4=1.2.3.4 $node.data.pop(spam)')
            self.eq('inet:ipv4', await layr00.getNodeForm(buid0))

            # delete node - buid:form removed
            await core.nodes('inet:ipv4=1.2.3.4 | delnode')
            self.none(await layr00.getNodeForm(buid0))

            await core.nodes('[ inet:ipv4=5.6.7.8 ]')

            # fork a view
            info = await core.view.fork()
            layr01 = core.getLayer(info['layers'][0]['iden'])
            view01 = core.getView(info['iden'])

            await alist(view01.eval('[ inet:ipv4=6.7.8.9 ]'))

            # buid:form for a node in child doesn't exist
            self.none(await layr01.getNodeForm(buid1))

            # add prop, buid:form map exists
            nodes = await alist(view01.eval('inet:ipv4=2.3.4.5 [ :loc=ru ]'))
            self.len(1, nodes)
            self.eq('inet:ipv4', await layr01.getNodeForm(buid1))

            # add nodedata and edge
            await alist(view01.eval('inet:ipv4=2.3.4.5 [ +(refs)> {inet:ipv4=6.7.8.9} ] $node.data.set(faz, baz)'))

            # remove prop, map still exists due to nodedata
            await alist(view01.eval('inet:ipv4=2.3.4.5 [ -:loc ]'))
            self.eq('inet:ipv4', await layr01.getNodeForm(buid1))

            # remove nodedata, map still exists due to edge
            await alist(view01.eval('inet:ipv4=2.3.4.5 $node.data.pop(faz)'))
            self.eq('inet:ipv4', await layr01.getNodeForm(buid1))

            # remove edge, map is deleted
            await alist(view01.eval('inet:ipv4=2.3.4.5 [ -(refs)> {inet:ipv4=6.7.8.9} ]'))
            self.none(await layr01.getNodeForm(buid1))

            # edges between two nodes in parent
            await alist(view01.eval('inet:ipv4=2.3.4.5 [ +(refs)> {inet:ipv4=5.6.7.8} ]'))
            self.eq('inet:ipv4', await layr01.getNodeForm(buid1))

            await alist(view01.eval('inet:ipv4=2.3.4.5 [ -(refs)> {inet:ipv4=5.6.7.8} ]'))
            self.none(await layr01.getNodeForm(buid1))

    async def test_layer(self):

        async with self.getTestCore() as core:

            await core.addTagProp('score', ('int', {}), {})

            layr = core.getLayer()
            self.isin(f'Layer (Layer): {layr.iden}', str(layr))

            nodes = await core.nodes('[test:str=foo .seen=(2015, 2016)]')
            buid = nodes[0].buid

            self.eq('foo', await layr.getNodeValu(buid))
            self.eq((1420070400000, 1451606400000), await layr.getNodeValu(buid, '.seen'))
            self.none(await layr.getNodeValu(buid, 'noprop'))
            self.none(await layr.getNodeTag(buid, 'faketag'))

            self.false(await layr.hasTagProp('score'))
            nodes = await core.nodes('[test:str=bar +#test:score=100]')
            self.true(await layr.hasTagProp('score'))

    async def test_layer_waitForHot(self):
        self.thisHostMust(hasmemlocking=True)

        async with self.getTestCore() as core:
            layr = core.getLayer()

            await asyncio.wait_for(layr.waitForHot(), timeout=1.0)

        conf = {'layers:lockmemory': True}
        async with self.getTestCore(conf=conf) as core:
            layr = core.getLayer()
            await asyncio.wait_for(layr.waitForHot(), timeout=1.0)

    async def test_layer_no_extra_logging(self):

        async with self.getTestCore() as core:
            '''
            For a do-nothing write, don't write new log entries
            '''
            await core.nodes('[test:str=foo .seen=(2015, 2016)]')
            layr = core.getLayer(None)
            lbefore = len(await alist(layr.splices()))
            await core.nodes('[test:str=foo .seen=(2015, 2016)]')
            lafter = len(await alist(layr.splices()))
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

    async def test_layer_flat_edits(self):
        nodeedits = (
            (b'asdf', 'test:junk', (
                (s_layer.EDIT_NODE_ADD, (10, s_layer.STOR_TYPE_U64), (
                    (b'qwer', 'test:junk', (
                        (s_layer.EDIT_NODE_ADD, (11, s_layer.STOR_TYPE_U64), ()),
                    )),
                )),
            )),
        )
        self.len(2, s_layer.getFlatEdits(nodeedits))

    async def test_layer_clone(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            layr = core.getLayer()
            self.isin(f'Layer (Layer): {layr.iden}', str(layr))

            nodes = await core.nodes('[test:str=foo .seen=(2015, 2016)]')
            buid = nodes[0].buid

            self.eq('foo', await layr.getNodeValu(buid))
            self.eq((1420070400000, 1451606400000), await layr.getNodeValu(buid, '.seen'))

            s_common.gendir(layr.dirn, 'adir')

            copylayrinfo = await core.cloneLayer(layr.iden)
            self.len(2, core.layers)

            copylayr = core.getLayer(copylayrinfo.get('iden'))
            self.isin(f'Layer (Layer): {copylayr.iden}', str(copylayr))
            self.ne(layr.iden, copylayr.iden)

            self.eq('foo', await copylayr.getNodeValu(buid))
            self.eq((1420070400000, 1451606400000), await copylayr.getNodeValu(buid, '.seen'))

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

    async def test_layer_v3(self):

        async with self.getRegrCore('2.0-layerv2tov3') as core:

            nodes = await core.nodes('inet:ipv4=1.2.3.4')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[0].get('asn'), 33)
            self.true(nodes[0].getTag('foo.bar'), (None, None))
            self.true(nodes[0].getTagProp('foo.bar', 'confidence'), 22)

            self.eq(10004, await core.count('.created'))
            self.len(2, await core.nodes('syn:tag~=foo'))

            for layr in core.layers.values():
                self.eq(layr.layrvers, 3)

    async def test_layer_logedits_default(self):

        with self.getTestDir() as dirn:

            layrinfo = {
                'iden': s_common.guid(),
                'creator': s_common.guid(),
                'lockmemory': False,
            }
            s_layer.reqValidLdef(layrinfo)
            layr = await s_layer.Layer.anit(layrinfo, dirn)
            self.true(layr.logedits)

    async def test_layer_no_logedits(self):

        with self.getTestDir() as dirn:

            layrinfo = {
                'logedits': False
            }
            layr = await s_layer.Layer.anit(layrinfo, dirn)
            self.false(layr.logedits)

            self.eq(-1, await layr.getEditOffs())

    async def test_layer_iter_props(self):

        async with self.getTestCore() as core:
            await core.addTagProp('score', ('int', {}), {})

            async with await core.snap() as snap:

                props = {'asn': 10, '.seen': ('2016', '2017')}
                node = await snap.addNode('inet:ipv4', 1, props=props)
                buid1 = node.buid
                await node.addTag('foo', ('2020', '2021'))
                await node.setTagProp('foo', 'score', 42)

                props = {'asn': 20, '.seen': ('2015', '2016')}
                node = await snap.addNode('inet:ipv4', 2, props=props)
                buid2 = node.buid
                await node.addTag('foo', ("2019", "2020"))
                await node.setTagProp('foo', 'score', 41)

                props = {'asn': 30, '.seen': ('2015', '2016')}
                node = await snap.addNode('inet:ipv4', 3, props=props)
                buid3 = node.buid
                await node.addTag('foo', ("2018", "2020"))
                await node.setTagProp('foo', 'score', 99)

                node = await snap.addNode('test:str', 'yolo')
                strbuid = node.buid

                node = await snap.addNode('test:str', 'z' * 500)
                strbuid2 = node.buid

            # rows are (buid, valu) tuples
            layr = core.view.layers[0]
            rows = await alist(layr.iterPropRows('inet:ipv4', 'asn'))

            self.eq((10, 20, 30), tuple(sorted([row[1] for row in rows])))

            styp = core.model.form('inet:ipv4').prop('asn').type.stortype
            rows = await alist(layr.iterPropRows('inet:ipv4', 'asn', styp))
            self.eq((10, 20, 30), tuple(sorted([row[1] for row in rows])))

            rows = await alist(layr.iterPropRows('inet:ipv4', 'asn', styp))
            self.eq((10, 20, 30), tuple(sorted([row[1] for row in rows])))

            # rows are (buid, valu) tuples
            rows = await alist(layr.iterUnivRows('.seen'))

            tm = lambda x, y: (s_time.parse(x), s_time.parse(y))  # NOQA
            ivals = (tm('2015', '2016'), tm('2015', '2016'), tm('2016', '2017'))
            self.eq(ivals, tuple(sorted([row[1] for row in rows])))

            # iterFormRows
            rows = await alist(layr.iterFormRows('inet:ipv4'))
            self.eq([(buid1, 1), (buid2, 2), (buid3, 3)], rows)

            rows = await alist(layr.iterFormRows('inet:ipv4', stortype=s_layer.STOR_TYPE_U32, startvalu=2))
            self.eq([(buid2, 2), (buid3, 3)], rows)

            rows = await alist(layr.iterFormRows('test:str', stortype=s_layer.STOR_TYPE_UTF8, startvalu='yola'))
            self.eq([(strbuid, 'yolo'), (strbuid2, 'z' * 500)], rows)

            # iterTagRows
            expect = sorted(
                [
                    (buid1, (tm('2020', '2021'), 'inet:ipv4')),
                    (buid2, (tm('2019', '2020'), 'inet:ipv4')),
                    (buid3, (tm('2018', '2020'), 'inet:ipv4')),
                ], key=lambda x: x[0])

            rows = await alist(layr.iterTagRows('foo'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagRows('foo', form='inet:ipv4'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagRows('foo', form='newpform'))
            self.eq([], rows)

            rows = await alist(layr.iterTagRows('foo', form='newpform', starttupl=(expect[1][0], 'newpform')))
            self.eq([], rows)

            rows = await alist(layr.iterTagRows('foo', starttupl=(expect[1][0], 'inet:ipv4')))
            self.eq(expect[1:], rows)

            rows = await alist(layr.iterTagRows('foo', form='inet:ipv4', starttupl=(expect[1][0], 'inet:ipv4')))
            self.eq(expect[1:], rows)

            rows = await alist(layr.iterTagRows('foo', form='inet:ipv4', starttupl=(expect[1][0], 'newpform')))
            self.eq([], rows)

            rows = await alist(layr.iterTagRows('nosuchtag'))
            self.eq([], rows)

            expect = [
                (buid2, 41,),
                (buid1, 42,),
                (buid3, 99,),
            ]

            rows = await alist(layr.iterTagPropRows('foo', 'newp'))
            self.eq([], rows)

            rows = await alist(layr.iterTagPropRows('foo', 'score'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagPropRows('foo', 'score', form='inet:ipv4'))
            self.eq(expect, rows)

            rows = await alist(layr.iterTagPropRows('foo', 'score', form='inet:ipv4', stortype=s_layer.STOR_TYPE_I64,
                                                    startvalu=42))
            self.eq(expect[1:], rows)

            rows = await alist(layr.iterTagPropRows('foo', 'score', stortype=s_layer.STOR_TYPE_I64, startvalu=42))
            self.eq(expect[1:], rows)

    async def test_layer_setinfo(self):

        async with self.getTestCore() as core:

            layer = core.getView().layers[0]

            self.eq('hehe', await core.callStorm('$layer = $lib.layer.get() $layer.set(name, hehe) return($layer.get(name))'))

            self.eq(False, await core.callStorm('$layer = $lib.layer.get() $layer.set(logedits, $lib.false) return($layer.get(logedits))'))
            edits0 = [e async for e in layer.syncNodeEdits(0, wait=False)]
            await core.callStorm('[inet:ipv4=1.2.3.4]')
            edits1 = [e async for e in layer.syncNodeEdits(0, wait=False)]
            self.eq(len(edits0), len(edits1))

            self.eq(True, await core.callStorm('$layer = $lib.layer.get() $layer.set(logedits, $lib.true) return($layer.get(logedits))'))
            await core.callStorm('[inet:ipv4=5.5.5.5]')
            edits2 = [e async for e in layer.syncNodeEdits(0, wait=False)]
            self.gt(len(edits2), len(edits1))

            with self.raises(s_exc.BadOptValu):
                await core.callStorm('$layer = $lib.layer.get() $layer.set(newp, hehe)')
