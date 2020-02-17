import asyncio
import contextlib

import synapse.common as s_common
import synapse.tests.utils as s_t_utils


async def iterPropForm(self, form=None, prop=None):
    bad_valu = [(b'foo', "bar"), (b'bar', ('bar',)), (b'biz', 4965), (b'baz', (0, 56))]
    bad_valu += [(b'boz', 'boz')] * 10
    for buid, valu in bad_valu:
        yield buid, valu


@contextlib.contextmanager
def patch_snap(snap):
    old_layr = []
    for layr in snap.layers:
        old_layr.append((layr.iterPropRows, layr.iterUnivRows))
        layr.iterPropRows, layr.iterUnivRows = (iterPropForm,) * 2

    yield

    for layr_idx, layr in enumerate(snap.layers):
        layr.iterPropRows, layr.iterUnivRows = old_layr[layr_idx]


class LayerTest(s_t_utils.SynTest):

    async def test_ival_failure(self):
        self.skip('this is completely different now. FIXME')

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                await snap.addNode('test:str', 'a', {'tick': '1970'})
                await snap.addNode('test:str', 'b', {'tick': '19700101'})
                await snap.addNode('test:str', 'c', {'tick': '1972'})
                oper = ('test:str', 'tick', (0, 24 * 60 * 60 * 366))

                async def liftByHandler(lopf, expt):
                    count = 0
                    lops = ((lopf, oper),)
                    async for node in snap.getLiftRows(lops):
                        count += 1
                    self.assertTrue(count == expt)

                with patch_snap(snap):
                    await liftByHandler('prop:ival', 1)
                    await liftByHandler('univ:ival', 1)
                    await liftByHandler('form:ival', 1)

    async def test_layer_buidcache(self):
        '''
        Make sure the layer buidcache isn't caching incorrectly
        '''
        self.skip('No layer buidcache anymore. Delete? FIXME')

        async with self.getTestCore() as core:
            buidcache = core.view.layers[0].buidcache

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'a', {'tick': '2001'})
                await node.addTag('foo')
                testbuid = node.buid

            self.isin(testbuid, buidcache)
            propbag = buidcache.get(testbuid)
            self.eq(propbag.get('*test:str'), 'a')
            self.eq(propbag.get('tick'), 978307200000)
            self.eq(propbag.get('#foo'), (None, None))
            self.isin('.created', propbag)

            async with await core.snap() as snap:
                nodes = await snap.nodes('test:str')
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.props['tick'], 978307200000)
                await node.set('tick', '2002')

            self.eq(buidcache.get(testbuid).get('tick'), 1009843200000)

            # new snap -> no cached buids in snap
            async with await core.snap() as snap:
                nodes = snap.nodes('test:str')
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.props['tick'], 1009843200000,)
                self.eq(node.tags, {'foo': (None, None)})
                await node.delete()

            self.notin(testbuid, buidcache)

            async with await core.snap() as snap:
                nodes = await snap.nodes('test:str')
                self.len(0, nodes)

            self.notin(testbuid, buidcache)

    async def test_layer_abrv(self):

        async with self.getTestCore() as core:

            layr = core.view.layers[0]
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x04', layr.getPropAbrv('visi', 'foo'))
            # another to check the cache...
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x04', layr.getPropAbrv('visi', 'foo'))
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x05', layr.getPropAbrv('whip', None))
            self.eq(('visi', 'foo'), await layr.getAbrvProp(b'\x00\x00\x00\x00\x00\x00\x00\x04'))
            self.eq(('whip', None), await layr.getAbrvProp(b'\x00\x00\x00\x00\x00\x00\x00\x05'))

            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x00', layr.getTagPropAbrv('visi', 'foo'))
            # another to check the cache...
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x00', layr.getTagPropAbrv('visi', 'foo'))
            self.eq(b'\x00\x00\x00\x00\x00\x00\x00\x01', layr.getTagPropAbrv('whip', None))

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
                    node = await snap.addNode('test:str', 'foo', props=props)
                    await node.setTagProp('bar', 'score', 10)
                    await node.setData('baz', 'nodedataiscool')

                async with self.getTestCore(dirn=path01) as core01:

                    url = core00.getLocalUrl('*/layer')
                    conf = {'upstream': url}
                    layr = await core01.addLayer(ldef=conf)
                    await core01.view.addLayer(layr.iden)

                    # test initial sync
                    offs = core00.getView().layers[0].getNodeEditOffset()
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

                    # make sure updates show up
                    await core00.nodes('[ inet:fqdn=vertex.link ]')

                    offs = core00.getView().layers[0].getNodeEditOffset()
                    evnt = await layr.waitUpstreamOffs(layriden, offs)
                    await asyncio.wait_for(evnt.wait(), timeout=2.0)

                    self.len(1, await core01.nodes('inet:fqdn=vertex.link'))

                await core00.nodes('[ inet:ipv4=5.5.5.5 ]')
                offs = core00.getView().layers[0].getNodeEditOffset()

                # test what happens when we go down and come up again...
                async with self.getTestCore(dirn=path01) as core01:

                    layr = core01.getView().layers[-1]

                    evnt = await layr.waitUpstreamOffs(layriden, offs)
                    await asyncio.wait_for(evnt.wait(), timeout=2.0)

                    self.len(1, await core01.nodes('inet:ipv4=5.5.5.5'))

                    await core00.nodes('[ inet:ipv4=5.6.7.8 ]')

                    offs = core00.getView().layers[0].getNodeEditOffset()
                    evnt = await layr.waitUpstreamOffs(layriden, offs)
                    await asyncio.wait_for(evnt.wait(), timeout=2.0)

                    self.len(1, await core01.nodes('inet:ipv4=5.6.7.8'))

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

                        layr = await core02.addLayer(ldef=conf)
                        await core02.view.addLayer(layr.iden)

                        # core00 is synced
                        offs = core00.getView().layers[0].getNodeEditOffset()
                        evnt = await layr.waitUpstreamOffs(iden00, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=1.2.3.4'))
                        nodes = await core02.nodes('test:str=foobar')
                        self.len(1, nodes)
                        self.nn(nodes[0].tags.get('hehe.haha'))

                        # core01 is synced
                        offs = core01.getView().layers[0].getNodeEditOffset()
                        evnt = await layr.waitUpstreamOffs(iden01, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=4.3.2.1'))
                        nodes = await core02.nodes('test:str=barfoo')
                        self.len(1, nodes)
                        self.nn(nodes[0].tags.get('haha.hehe'))

                        # updates from core00 show up
                        await core00.nodes('[ inet:fqdn=vertex.link ]')

                        offs = core00.getView().layers[0].getNodeEditOffset()
                        evnt = await layr.waitUpstreamOffs(iden00, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:fqdn=vertex.link'))

                        # updates from core01 show up
                        await core01.nodes('[ inet:fqdn=google.com ]')

                        offs = core01.getView().layers[0].getNodeEditOffset()
                        evnt = await layr.waitUpstreamOffs(iden01, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:fqdn=google.com'))

                    await core00.nodes('[ inet:ipv4=5.5.5.5 ]')
                    await core01.nodes('[ inet:ipv4=6.6.6.6 ]')

                    # test what happens when we go down and come up again...
                    async with self.getTestCore(dirn=path02) as core02:

                        layr = core02.getView().layers[-1]

                        # test we catch up to core00
                        offs = core00.getView().layers[0].getNodeEditOffset()
                        evnt = await layr.waitUpstreamOffs(iden00, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=5.5.5.5'))

                        # test we catch up to core01
                        offs = core01.getView().layers[0].getNodeEditOffset()
                        evnt = await layr.waitUpstreamOffs(iden01, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=6.6.6.6'))

                        # test we get updates from core00
                        await core00.nodes('[ inet:ipv4=5.6.7.8 ]')

                        offs = core00.getView().layers[0].getNodeEditOffset()
                        evnt = await layr.waitUpstreamOffs(iden00, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=5.6.7.8'))

                        # test we get updates from core01
                        await core01.nodes('[ inet:ipv4=8.7.6.5 ]')

                        offs = core01.getView().layers[0].getNodeEditOffset()
                        evnt = await layr.waitUpstreamOffs(iden01, offs)
                        await asyncio.wait_for(evnt.wait(), timeout=2.0)

                        self.len(1, await core02.nodes('inet:ipv4=8.7.6.5'))

    async def test_layer_splices(self):

        async with self.getTestCore() as core:

            layr = core.view.layers[0]
            root = await core.auth.getUserByName('root')

            splices = await alist(layr.splices(0, 10))
            spliceoffs = splices[-1][0][0] + 1

            await core.addTagProp('risk', ('int', {'minval': 0, 'maxval': 100}), {'doc': 'risk score'})

            # Convert a node:add splice
            await core.nodes('[ test:str=foo ]')

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[0][1]
            self.eq(splice[0], 'node:add')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

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

            spliceoffs = splices[-1][0][0] + 1

            # Convert a node:del splice
            await core.nodes('test:str=foo | delnode')

            splices = await alist(layr.splices(spliceoffs, 10))

            splice = splices[2][1]
            self.eq(splice[0], 'node:del')
            self.eq(splice[1]['ndef'], ('test:str', 'foo'))
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))

    async def test_layer_fallback_splices(self):

        conf = {'splice:fallback': True}
        async with self.getTestCore(conf=conf) as core:

            root = await core.auth.getUserByName('root')

            layr = core.view.layers[0]

            splice =  layr.splicelog.get(0)
            self.eq(splice[0], 'node:add')
            self.eq(splice[1]['ndef'][0], 'meta:source')
            self.eq(splice[1]['user'], root.iden)
            self.nn(splice[1].get('time'))
