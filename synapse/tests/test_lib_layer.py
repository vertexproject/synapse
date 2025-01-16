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

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 +#foo.bar ]')
            buid = nodes[0].buid

            await core.nodes('[ ou:org=* :names=(hehe, haha) ]')

            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

            core.getLayer()._testDelTagIndx(buid, 'inet:ipv4', 'foo')
            core.getLayer()._testDelPropIndx(buid, 'inet:ipv4', 'asn')

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoTagIndex')
            self.eq(errors[1][0], 'NoPropIndex')

            errors = await core.callStorm('''
                $retn = ()
                for $mesg in $lib.layer.get().verify() {
                    $retn.append($mesg)
                }
                return($retn)
            ''')

            self.len(2, errors)
            self.eq(errors[0][0], 'NoTagIndex')
            self.eq(errors[1][0], 'NoPropIndex')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 +#foo.bar ]')
            buid = nodes[0].buid

            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

            core.getLayer()._testDelTagStor(buid, 'inet:ipv4', 'foo')

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

            core.getLayer()._testDelPropStor(buid, 'inet:ipv4', 'asn')
            errors = [e async for e in core.getLayer().verifyByProp('inet:ipv4', 'asn')]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)

            core.getLayer()._testDelFormValuStor(buid, 'inet:ipv4')
            errors = [e async for e in core.getLayer().verifyByProp('inet:ipv4', None)]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 +#foo.bar ]')
            buid = nodes[0].buid

            core.getLayer()._testAddPropIndx(buid, 'inet:ipv4', 'asn', 30)
            errors = [e async for e in core.getLayer().verify()]
            self.len(1, errors)
            self.eq(errors[0][0], 'SpurPropKeyForIndex')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 +#foo ]')
            buid = nodes[0].buid

            await core.nodes('.created | delnode --force')
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4'))

            core.getLayer()._testAddTagIndx(buid, 'inet:ipv4', 'foo')
            core.getLayer()._testAddPropIndx(buid, 'inet:ipv4', 'asn', 30)
            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoNodeForTagIndex')
            self.eq(errors[1][0], 'NoNodeForPropIndex')

        # Smash in a bad stortype into a sode.
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 +#foo ]')
            buid = nodes[0].buid

            layr = core.getLayer()
            sode = await layr.getStorNode(buid)
            asn = sode['props']['asn']
            sode['props']['asn'] = (asn[0], 8675309)
            layr.setSodeDirty(buid, sode, sode.get('form'))

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoStorTypeForProp')
            self.eq(errors[1][0], 'NoStorTypeForProp')

            sode['props'] = None
            layr.setSodeDirty(buid, sode, sode.get('form'))
            errors = [e async for e in core.getLayer().verify()]
            self.len(4, errors)
            for err in errors:
                self.eq(err[0], 'NoValuForPropIndex')

        # Check arrays
        async with self.getTestCore() as core:

            layr = core.getLayer()

            nodes = await core.nodes('[ ps:contact=* :names=(foo, bar)]')
            buid = nodes[0].buid

            core.getLayer()._testAddPropArrayIndx(buid, 'ps:contact', 'names', ('baz',))

            scanconf = {'autofix': 'index'}
            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(1, errors)
            self.eq(errors[0][0], 'SpurPropArrayKeyForIndex')

            errors = [e async for e in layr.verifyAllProps()]
            self.len(0, errors)

            sode = await layr.getStorNode(buid)
            names = sode['props']['names']
            sode['props']['names'] = (names[0], 8675309)
            layr.setSodeDirty(buid, sode, sode.get('form'))

            scanconf = {'include': [('ps:contact', 'names')]}
            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoStorTypeForProp')
            self.eq(errors[1][0], 'NoStorTypeForPropArray')
            self.eq(errors[2][0], 'NoStorTypeForPropArray')

            sode = await layr.getStorNode(buid)
            names = sode['props']['names']
            sode['props'] = {}
            layr.setSodeDirty(buid, sode, sode.get('form'))

            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')
            self.eq(errors[1][0], 'NoValuForPropArrayIndex')
            self.eq(errors[2][0], 'NoValuForPropArrayIndex')

            sode['props'] = None
            layr.setSodeDirty(buid, sode, sode.get('form'))
            errors = [e async for e in core.getLayer().verify()]
            self.len(5, errors)
            self.eq(errors[0][0], 'NoValuForPropIndex')
            self.eq(errors[1][0], 'NoValuForPropArrayIndex')
            self.eq(errors[2][0], 'NoValuForPropArrayIndex')
            self.eq(errors[3][0], 'NoValuForPropIndex')
            self.eq(errors[4][0], 'NoValuForPropIndex')

            await core.nodes('ps:contact | delnode --force')

            core.getLayer()._testAddPropArrayIndx(buid, 'ps:contact', 'names', ('foo',))

            errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]
            self.len(3, errors)
            self.eq(errors[0][0], 'NoNodeForPropIndex')
            self.eq(errors[1][0], 'NoNodeForPropArrayIndex')
            self.eq(errors[2][0], 'NoNodeForPropArrayIndex')

            q = "$lib.model.ext.addForm('_test:array', array, ({'type': 'int'}), ({}))"
            await core.nodes(q)
            nodes = await core.nodes('[ _test:array=(1, 2, 3) ]')
            buid = nodes[0].buid
            core.getLayer()._testDelFormValuStor(buid, '_test:array')

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

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 +#foo ]')
            buid = nodes[0].buid

            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

            # test autofix=node
            core.getLayer()._testDelTagStor(buid, 'inet:ipv4', 'foo')
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +#foo'))

            config = {'scans': {'tagindex': {'autofix': 'node'}}}
            errors = [e async for e in core.getLayer().verify(config=config)]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +#foo'))
            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

            # test autofix=index
            core.getLayer()._testDelTagStor(buid, 'inet:ipv4', 'foo')
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +#foo'))

            config = {'scans': {'tagindex': {'autofix': 'index'}}}
            errors = [e async for e in core.getLayer().verify(config=config)]
            self.len(1, errors)
            self.eq(errors[0][0], 'NoTagForTagIndex')
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +#foo'))
            errors = [e async for e in core.getLayer().verify()]
            self.len(0, errors)

        async with self.getTestCore() as core:
            await core.addTagProp('score', ('int', {}), {})

            layr = core.getLayer()
            errors = [e async for e in layr.verifyAllBuids()]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllProps()]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(0, errors)

            layr._testAddTagPropIndx(buid, 'inet:ipv4', 'foo', 'score', 5)

            scanconf = {'include': ['newp']}
            errors = [e async for e in layr.verifyAllTagProps(scanconf=scanconf)]
            self.len(0, errors)

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoNodeForTagPropIndex')
            self.eq(errors[1][0], 'NoNodeForTagPropIndex')

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 +#foo:score=5 ]')
            buid = nodes[0].buid

            layr._testAddTagPropIndx(buid, 'inet:ipv4', 'foo', 'score', 6)

            scanconf = {'autofix': 'index'}
            errors = [e async for e in layr.verifyAllTagProps(scanconf=scanconf)]
            self.len(2, errors)
            self.eq(errors[0][0], 'SpurTagPropKeyForIndex')
            self.eq(errors[1][0], 'SpurTagPropKeyForIndex')

            errors = [e async for e in layr.verifyAllTagProps()]
            self.len(0, errors)

            sode = await layr.getStorNode(buid)
            score = sode['tagprops']['foo']['score']
            sode['tagprops']['foo']['score'] = (score[0], 8675309)
            layr.setSodeDirty(buid, sode, sode.get('form'))

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoStorTypeForTagProp')
            self.eq(errors[1][0], 'NoStorTypeForTagProp')

            sode = await layr.getStorNode(buid)
            sode['tagprops']['foo'] = {}
            layr.setSodeDirty(buid, sode, sode.get('form'))

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoValuForTagPropIndex')
            self.eq(errors[1][0], 'NoValuForTagPropIndex')

            sode = await layr.getStorNode(buid)
            sode['tagprops'] = {}
            layr.setSodeDirty(buid, sode, sode.get('form'))

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoPropForTagPropIndex')
            self.eq(errors[1][0], 'NoPropForTagPropIndex')

            sode = await layr.getStorNode(buid)
            sode['tagprops'] = None
            layr.setSodeDirty(buid, sode, sode.get('form'))

            errors = [e async for e in core.getLayer().verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoPropForTagPropIndex')
            self.eq(errors[1][0], 'NoPropForTagPropIndex')

            scanconf = {'autofix': 'newp'}

            with self.raises(s_exc.BadArg):
                errors = [e async for e in layr.verifyAllTags(scanconf=scanconf)]

            with self.raises(s_exc.BadArg):
                errors = [e async for e in layr.verifyAllProps(scanconf=scanconf)]

            with self.raises(s_exc.BadArg):
                errors = [e async for e in layr.verifyAllTagProps(scanconf=scanconf)]

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
                await core00.addTagProp('score', ('int', {}), {})

                layriden = core00.view.layers[0].iden

                await core00.nodes('[test:str=foobar +#hehe.haha]')
                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')
                await core00.nodes('[test:str=foo :tick=(12345) +#bar:score=10] $node.data.set(baz, nodedataiscool)')
                await core00.nodes('[test:str=bar :tick=(12345)] $node.data.set(baz, nodedataiscool)')
                await core00.nodes('test:str=foo [ +(refs)> { test:str=bar }]')

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

                    nodes = await core01.nodes('test:str=foo')
                    self.len(1, nodes)
                    node = nodes[0]
                    self.nn(node)
                    self.eq(node.props.get('tick'), 12345)
                    self.eq(node.getTagProp('bar', 'score'), 10)
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

                    # make sure time and user are set on the downstream changes
                    root = await core01.auth.getUserByName('root')

                    nedits = await alist(layr.syncNodeEdits2(0, wait=False))
                    last_edit = nedits[-1]
                    offs, edit, meta = last_edit
                    self.gt(meta.get('time'), 0)
                    self.eq(meta.get('user'), root.iden)
                    self.notin('prov', meta)

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
                        self.true(len(layr.activetasks))

                        layr = core02.getLayer(ldef.get('iden'))
                        self.false(len(layr.activetasks))

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
            self.raises(s_exc.NoSuchImpl, indxby.getNodeValu, s_common.guid())

            for key, val in ((stor.indx(v), s_msgpack.en(v)) for v in vals):
                layr.layrslab.put(key[0], val, db=tmpdb)
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

            await core.addTagProp('tval', ('ival', {}), {})
            await core.addTagProp('mintime', ('time', {'ismin': True}), {})
            await core.addTagProp('maxtime', ('time', {'ismax': True}), {})

            await core.nodes('[test:str=tagprop +#foo:tval=2021]')
            await core.nodes('test:str=tagprop [+#foo:tval=2023]')

            self.eq(1, await core.count('#foo:tval@=2022'))

            await core.nodes('test:str=tagprop [+#foo:mintime=2021 +#foo:maxtime=2013]')
            await core.nodes('test:str=tagprop [+#foo:mintime=2023 +#foo:maxtime=2011]')

            self.eq(1, await core.count('#foo:mintime=2021'))
            self.eq(1, await core.count('#foo:maxtime=2013'))

            await core.nodes('test:str=tagprop [+#foo:mintime=2020 +#foo:maxtime=2015]')

            self.eq(1, await core.count('#foo:mintime=2020'))
            self.eq(1, await core.count('#foo:maxtime=2015'))

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
                        self.nn(await layrprox.storNodeEdits(nodeedits))

                    nodelist1 = []
                    nodelist1.extend(await core1.nodes('test:str'))
                    nodelist1.extend(await core1.nodes('inet:ipv4'))

                    nodelist1 = [node.pack() for node in nodelist1]
                    self.eq(nodelist0, nodelist1)

                layr = core1.view.layers[0]  # type: s_layer.Layer

                ############################################################################
                # TEST ONLY - Force the layer nexus handler to consume a truncate event.
                # This is for backwards compatibility for a mirror that consumes a truncate
                # event.
                # This can be removed in 3.0.0.

                await layr._push('layer:truncate')

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

                    await layr._push('layer:truncate')

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

                ############################################################################

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
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            self.eq(events, [
                (strnode.buid, 'test:str', s_layer.EDIT_NODE_ADD, ('foo', s_layer.STOR_TYPE_UTF8), ()),
                (strnode.buid, 'test:str', s_layer.EDIT_NODE_DEL, ('foo', s_layer.STOR_TYPE_UTF8), ()),
            ])

            mdef = {'props': ['.seen']}
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            ival = tuple([s_time.parse(x) for x in ('2012', '2014')])
            self.eq(events, [
                (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_PROP_SET, ('.seen', ival, None, s_layer.STOR_TYPE_IVAL), ()),
                (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_PROP_DEL, ('.seen', ival, s_layer.STOR_TYPE_IVAL), ()),
            ])

            mdef = {'props': ['inet:ipv4:asn']}
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            self.len(2, events)
            self.eq(events, [
                (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_PROP_SET, ('asn', 42, None, s_layer.STOR_TYPE_I64), ()),
                (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_PROP_DEL, ('asn', 42, s_layer.STOR_TYPE_I64), ()),
            ])

            mdef = {'tags': ['foo.bar']}
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            self.eq(events, [
                (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_TAG_SET, ('foo.bar', ival, None), ()),
                (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_TAG_DEL, ('foo.bar', ival), ()),
            ])

            mdefs = ({'tagprops': ['score']}, {'tagprops': ['mytag:score']})
            events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
            for mdef in mdefs:
                events = [e[1] for e in await alist(layr.syncIndexEvents(baseoff, mdef, wait=False))]
                self.eq(events, [
                    (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_TAGPROP_SET,
                        ('mytag', 'score', 99, None, s_layer.STOR_TYPE_I64), ()),
                    (ipv4node.buid, 'inet:ipv4', s_layer.EDIT_TAGPROP_DEL,
                        ('mytag', 'score', 99, s_layer.STOR_TYPE_I64), ()),
                ])

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

            iden = s_common.guid()
            with self.raises(ValueError) as cm:
                with layr.getIdenFutu(iden=iden):
                    raise ValueError('oops')
            self.none(layr.futures.get(iden))

            await core.nodes('[ test:str=data ] $node.data.set(foodata, bar)')

            abrv = layr.getPropAbrv('foodata', None)
            self.len(1, list(layr.dataslab.scanByDups(abrv, db=layr.dataname)))

            await core.nodes('test:str=data | delnode')

            self.len(0, list(layr.dataslab.scanByDups(abrv, db=layr.dataname)))

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
            lbefore = len(await alist(layr.syncNodeEdits2(0, wait=False)))
            await core.nodes('[test:str=foo .seen=(2015, 2016)]')
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

            self.checkLayrvers(core)

    async def test_layer_v7(self):
        async with self.getRegrCore('2.78.0-tagprop-missing-indx') as core:
            nodes = await core.nodes('inet:ipv4=1.2.3.4')
            # Our malformed node was migrated properly.
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[0].get('asn'), 20)
            self.eq(nodes[0].getTag('foo'), (None, None))
            self.eq(nodes[0].getTagProp('foo', 'comment'), 'words')

            nodes = await core.nodes('inet:ipv4=1.2.3.3')
            # Our partially malformed node was migrated properly.
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020303))
            self.eq(nodes[0].get('asn'), 20)
            self.eq(nodes[0].getTag('foo'), (None, None))
            self.eq(nodes[0].getTagProp('foo', 'comment'), 'bar')

            nodes = await core.nodes('inet:ipv4=1.2.3.2')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020302))
            self.eq(nodes[0].get('asn'), 10)
            self.eq(nodes[0].getTag('foo'), (None, None))
            self.eq(nodes[0].getTagProp('foo', 'comment'), 'foo')

            nodes = await core.nodes('inet:ipv4=1.2.3.1')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020301))
            self.eq(nodes[0].get('asn'), 10)
            self.eq(nodes[0].getTag('bar'), (None, None))
            self.none(nodes[0].getTagProp('foo', 'comment'))

            self.checkLayrvers(core)

    async def test_layer_v8(self):
        async with self.getRegrCore('2.85.1-hugenum-indx') as core:

            nodes = await core.nodes('inet:fqdn:_huge=1.23')
            self.len(1, nodes)

            nodes = await core.nodes('inet:fqdn:_huge:array=(1.23, 2.34)')
            self.len(1, nodes)

            nodes = await core.nodes('inet:fqdn:_huge:array*[=1.23]')
            self.len(2, nodes)

            nodes = await core.nodes('inet:fqdn:_huge:array*[=2.34]')
            self.len(2, nodes)

            nodes = await core.nodes('inet:fqdn._univhuge=2.34')
            self.len(1, nodes)

            nodes = await core.nodes('._univhuge=2.34')
            self.len(1, nodes)

            nodes = await core.nodes('inet:fqdn._hugearray=(3.45, 4.56)')
            self.len(1, nodes)

            nodes = await core.nodes('inet:fqdn._hugearray*[=3.45]')
            self.len(2, nodes)

            nodes = await core.nodes('inet:fqdn._hugearray*[=4.56]')
            self.len(2, nodes)

            nodes = await core.nodes('._hugearray=(3.45, 4.56)')
            self.len(1, nodes)

            nodes = await core.nodes('._hugearray*[=3.45]')
            self.len(2, nodes)

            nodes = await core.nodes('._hugearray*[=4.56]')
            self.len(2, nodes)

            nodes = await core.nodes('inet:fqdn#bar:cool:huge=1.23')
            self.len(1, nodes)

            nodes = await core.nodes('#bar:cool:huge=1.23')
            self.len(1, nodes)

            nodes = await core.nodes('inet:fqdn:_huge:array = (1.23, 10E-21)')
            self.len(1, nodes)
            self.eq(nodes[0].props['_huge:array'], ('1.23', '0.00000000000000000001'))

            nodes = await core.nodes('inet:fqdn._hugearray = (3.45, 10E-21)')
            self.len(1, nodes)
            self.eq(nodes[0].props['._hugearray'], ('3.45', '0.00000000000000000001'))

            nodes = await core.nodes('inet:fqdn:_huge:array*[=10E-21]')
            self.len(1, nodes)
            self.eq(nodes[0].props['_huge:array'], ('1.23', '0.00000000000000000001'))

            nodes = await core.nodes('inet:fqdn._hugearray*[=10E-21]')
            self.len(1, nodes)
            self.eq(nodes[0].props['._hugearray'], ('3.45', '0.00000000000000000001'))

            nodes = await core.nodes('inet:fqdn:_huge=0.00000000000000000001')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.props.get('_huge'), '0.00000000000000000001')
            self.eq(node.props.get('._univhuge'), '0.00000000000000000001')
            self.eq(node.props.get('._hugearray'), ('3.45', '0.00000000000000000001'))
            self.eq(node.props.get('._hugearray'), ('3.45', '0.00000000000000000001'))

            self.checkLayrvers(core)

    async def test_layer_v10(self):

        async with self.getRegrCore('layer-v10') as core:

            nodes = await core.nodes('file:bytes inet:user')
            verbs = [verb async for verb in nodes[0].iterEdgeVerbs(nodes[1].buid)]
            self.eq(('refs',), verbs)

            nodes0 = await core.nodes('[ ps:contact=* :name=visi +(has)> {[ mat:item=* :name=laptop ]} ]')
            self.len(1, nodes0)
            buid1 = nodes0[0].buid

            nodes1 = await core.nodes('mat:item')
            self.len(1, nodes1)
            buid2 = nodes1[0].buid

            layr = core.getView().layers[0]
            self.true(layr.layrslab.hasdup(buid1 + buid2, b'has', db=layr.edgesn1n2))
            verbs = [verb async for verb in nodes0[0].iterEdgeVerbs(buid2)]
            self.eq(('has',), verbs)

            await core.nodes('ps:contact:name=visi [ -(has)> { mat:item:name=laptop } ]')

            self.false(layr.layrslab.hasdup(buid1 + buid2, b'has', db=layr.edgesn1n2))
            verbs = [verb async for verb in nodes0[0].iterEdgeVerbs(buid2)]
            self.len(0, verbs)

            await core.nodes('ps:contact:name=visi [ +(has)> { mat:item:name=laptop } ]')

            self.true(layr.layrslab.hasdup(buid1 + buid2, b'has', db=layr.edgesn1n2))
            verbs = [verb async for verb in nodes0[0].iterEdgeVerbs(buid2)]
            self.eq(('has',), verbs)

            await core.nodes('ps:contact:name=visi | delnode --force')

            self.false(layr.layrslab.hasdup(buid1 + buid2, b'has', db=layr.edgesn1n2))
            verbs = [verb async for verb in nodes0[0].iterEdgeVerbs(buid2)]
            self.len(0, verbs)

    async def test_layer_v11(self):

        try:

            oldv = s_layer.MIGR_COMMIT_SIZE
            s_layer.MIGR_COMMIT_SIZE = 1

            async with self.getRegrCore('layer-v11') as core:

                wlyrs_byview = await core.callStorm('''
                    $wlyrs = ({})
                    for $view in $lib.view.list() {
                        $wlyrs.($view.get(name)) = $view.layers.0.iden
                    }
                    return($wlyrs)
                ''')
                self.len(8, wlyrs_byview)

                layr = core.getLayer(iden=wlyrs_byview['default'])
                await self.agenlen(2, layr.getStorNodesByForm('test:str'))
                await self.agenlen(1, layr.getStorNodesByForm('syn:tag'))

                layr = core.getLayer(iden=wlyrs_byview['prop'])
                await self.agenlen(1, layr.getStorNodesByForm('test:str'))

                layr = core.getLayer(iden=wlyrs_byview['tags'])
                await self.agenlen(1, layr.getStorNodesByForm('test:str'))
                await self.agenlen(1, layr.getStorNodesByForm('syn:tag'))

                layr = core.getLayer(iden=wlyrs_byview['tagp'])
                await self.agenlen(1, layr.getStorNodesByForm('test:str'))
                await self.agenlen(0, layr.getStorNodesByForm('syn:tag'))

                layr = core.getLayer(iden=wlyrs_byview['n1eg'])
                await self.agenlen(1, layr.getStorNodesByForm('test:str'))
                await self.agenlen(1, layr.getStorNodesByForm('test:int'))

                layr = core.getLayer(iden=wlyrs_byview['n2eg'])
                await self.agenlen(0, layr.getStorNodesByForm('test:str'))
                await self.agenlen(1, layr.getStorNodesByForm('test:int'))

                layr = core.getLayer(iden=wlyrs_byview['data'])
                await self.agenlen(1, layr.getStorNodesByForm('test:str'))

                layr = core.getLayer(iden=wlyrs_byview['noop'])
                await self.agenlen(0, layr.getStorNodes())
                await self.agenlen(0, layr.getStorNodesByForm('test:str'))

        finally:
            s_layer.MIGR_COMMIT_SIZE = oldv

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

            nodes = await core.nodes('[inet:ipv4=1 :asn=10 .seen=(2016, 2017) +#foo=(2020, 2021) +#foo:score=42]')
            self.len(1, nodes)
            buid1 = nodes[0].buid

            nodes = await core.nodes('[inet:ipv4=2 :asn=20 .seen=(2015, 2016) +#foo=(2019, 2020) +#foo:score=41]')
            self.len(1, nodes)
            buid2 = nodes[0].buid

            nodes = await core.nodes('[inet:ipv4=3 :asn=30 .seen=(2015, 2016) +#foo=(2018, 2020) +#foo:score=99]')
            self.len(1, nodes)
            buid3 = nodes[0].buid

            nodes = await core.nodes('[test:str=yolo]')
            self.len(1, nodes)
            strbuid = nodes[0].buid

            nodes = await core.nodes('[test:str=$valu]', opts={'vars': {'valu': 'z' * 500}})
            self.len(1, nodes)
            strbuid2 = nodes[0].buid

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

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

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

                self.true(await core.callStorm('$layer=$lib.layer.get() $layer.set(readonly, $lib.true) return($layer.get(readonly))'))
                await self.asyncraises(s_exc.IsReadOnly, core.nodes('[inet:ipv4=7.7.7.7]'))
                await self.asyncraises(s_exc.IsReadOnly, core.nodes('$lib.layer.get().set(logedits, $lib.false)'))

                self.false(await core.callStorm('$layer=$lib.layer.get() $layer.set(readonly, $lib.false) return($layer.get(readonly))'))
                self.len(1, await core.nodes('[inet:ipv4=7.7.7.7]'))

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

                info00 = await core.callStorm('return($lib.layer.get().pack())')
                self.eq('foo', info00['name'])
                self.eq('foodesc', info00['desc'])
                self.false(info00['logedits'])
                self.true(info00['readonly'])

            async with self.getTestCore(dirn=dirn) as core:

                self.eq(info00, await core.callStorm('return($lib.layer.get().pack())'))

    async def test_reindex_byarray(self):

        async with self.getRegrCore('reindex-byarray2') as core:

            layr = core.getView().layers[0]

            nodes = await core.nodes('transport:air:flightnum:stops*[=stop1]')
            self.len(1, nodes)

            nodes = await core.nodes('transport:air:flightnum:stops*[=stop4]')
            self.len(1, nodes)

            prop = core.model.prop('transport:air:flightnum:stops')
            cmprvals = prop.type.arraytype.getStorCmprs('=', 'stop1')
            nodes = await alist(layr.liftByPropArray(prop.form.name, prop.name, cmprvals))
            self.len(1, nodes)

            prop = core.model.prop('transport:air:flightnum:stops')
            cmprvals = prop.type.arraytype.getStorCmprs('=', 'stop4')
            nodes = await alist(layr.liftByPropArray(prop.form.name, prop.name, cmprvals))
            self.len(1, nodes)

            nodes = await core.nodes('inet:http:request:headers*[=(header1, valu1)]')
            self.len(1, nodes)

            nodes = await core.nodes('inet:http:request:headers*[=(header3, valu3)]')
            self.len(1, nodes)

            prop = core.model.prop('inet:http:request:headers')
            cmprvals = prop.type.arraytype.getStorCmprs('=', ('header1', 'valu1'))
            nodes = await alist(layr.liftByPropArray(prop.form.name, prop.name, cmprvals))
            self.len(1, nodes)

            prop = core.model.prop('inet:http:request:headers')
            cmprvals = prop.type.arraytype.getStorCmprs('=', ('header3', 'valu3'))
            nodes = await alist(layr.liftByPropArray(prop.form.name, prop.name, cmprvals))
            self.len(1, nodes)

            opts = {'vars': {
                'longfqdn': '.'.join(('a' * 63,) * 5),
                'longname': 'a' * 256,
            }}

            nodes = await core.nodes('crypto:x509:cert:identities:fqdns*[=vertex.link]')
            self.len(1, nodes)

            nodes = await core.nodes('crypto:x509:cert:identities:fqdns*[=$longfqdn]', opts=opts)
            self.len(1, nodes)

            nodes = await core.nodes('ps:person:names*[=foo]')
            self.len(1, nodes)

            nodes = await core.nodes('ps:person:names*[=$longname]', opts=opts)
            self.len(1, nodes)

            self.checkLayrvers(core)

    async def test_rebuild_byarray(self):

        async with self.getRegrCore('reindex-byarray3') as core:

            layr = core.getView().layers[0]

            nodes = await core.nodes('transport:air:flightnum:stops*[=stop1]')
            self.len(1, nodes)

            nodes = await core.nodes('transport:air:flightnum:stops*[=stop4]')
            self.len(1, nodes)

            prop = core.model.prop('transport:air:flightnum:stops')
            cmprvals = prop.type.arraytype.getStorCmprs('=', 'stop1')
            nodes = await alist(layr.liftByPropArray(prop.form.name, prop.name, cmprvals))
            self.len(1, nodes)

            prop = core.model.prop('transport:air:flightnum:stops')
            cmprvals = prop.type.arraytype.getStorCmprs('=', 'stop4')
            nodes = await alist(layr.liftByPropArray(prop.form.name, prop.name, cmprvals))
            self.len(1, nodes)

            nodes = await core.nodes('inet:http:request:headers*[=(header1, valu1)]')
            self.len(1, nodes)

            nodes = await core.nodes('inet:http:request:headers*[=(header3, valu3)]')
            self.len(1, nodes)

            prop = core.model.prop('inet:http:request:headers')
            cmprvals = prop.type.arraytype.getStorCmprs('=', ('header1', 'valu1'))
            nodes = await alist(layr.liftByPropArray(prop.form.name, prop.name, cmprvals))
            self.len(1, nodes)

            prop = core.model.prop('inet:http:request:headers')
            cmprvals = prop.type.arraytype.getStorCmprs('=', ('header3', 'valu3'))
            nodes = await alist(layr.liftByPropArray(prop.form.name, prop.name, cmprvals))
            self.len(1, nodes)

            opts = {'vars': {
                'longfqdn': '.'.join(('a' * 63,) * 5),
                'longname': 'a' * 256,
            }}

            nodes = await core.nodes('crypto:x509:cert:identities:fqdns*[=vertex.link]')
            self.len(1, nodes)

            nodes = await core.nodes('crypto:x509:cert:identities:fqdns*[=$longfqdn]', opts=opts)
            self.len(1, nodes)

            nodes = await core.nodes('ps:person:names*[=foo]')
            self.len(1, nodes)

            nodes = await core.nodes('ps:person:names*[=$longname]', opts=opts)
            self.len(1, nodes)

            self.checkLayrvers(core)

    async def test_migr_tagprop_keys(self):

        async with self.getRegrCore('tagprop-keymigr') as core:

            nodes = await core.nodes('ps:person#bar:score=10')
            self.len(4003, nodes)

            nodes = await core.nodes('ou:org#foo:score=20')
            self.len(4000, nodes)

            nodes = await core.nodes('ou:contract#foo:score=30')
            self.len(2000, nodes)

            nodes = await core.nodes('ou:industry#foo:score=40')
            self.len(2, nodes)

            self.checkLayrvers(core)

    async def test_layer_edit_perms(self):

        class Dict(s_spooled.Dict):
            async def __anit__(self, dirn=None, size=1, cell=None):
                await super().__anit__(dirn=dirn, size=size, cell=cell)

        seen = set()
        def confirm(self, perm, default=None, gateiden=None):
            seen.add(perm)
            return True

        def confirmPropSet(self, user, prop, layriden):
            seen.add(prop.setperms[0])
            seen.add(prop.setperms[1])

        def confirmPropDel(self, user, prop, layriden):
            seen.add(prop.delperms[0])
            seen.add(prop.delperms[1])

        with mock.patch('synapse.lib.spooled.Dict', Dict):
            async with self.getTestCore() as core:

                user = await core.auth.addUser('blackout@vertex.link')

                viewiden = await core.callStorm('''
                    $lyr = $lib.layer.add()
                    $view = $lib.view.add(($lyr.iden,))
                    return($view.iden)
                ''')

                layr = core.views[viewiden].layers[0]

                opts = {'view': viewiden}

                await core.addTagProp('score', ('int', {}), {})

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
                    with mock.patch.object(s_cortex.Cortex, 'confirmPropSet', confirmPropSet):
                        with mock.patch.object(s_cortex.Cortex, 'confirmPropDel', confirmPropDel):
                            await layr.confirmLayerEditPerms(user, parent.iden)

                self.eq(seen, {
                    # Node add
                    ('node', 'add', 'syn:tag'),
                    ('node', 'add', 'test:str'),

                    # Old style prop set
                    ('node', 'prop', 'set', 'test:str:hehe'),
                    ('node', 'prop', 'set', 'test:str.created'),

                    ('node', 'prop', 'set', 'syn:tag:up'),
                    ('node', 'prop', 'set', 'syn:tag:base'),
                    ('node', 'prop', 'set', 'syn:tag:depth'),
                    ('node', 'prop', 'set', 'syn:tag.created'),

                    # New style prop set
                    ('node', 'prop', 'set', 'test:str', 'hehe'),
                    ('node', 'prop', 'set', 'test:str', '.created'),

                    ('node', 'prop', 'set', 'syn:tag', 'up'),
                    ('node', 'prop', 'set', 'syn:tag', 'base'),
                    ('node', 'prop', 'set', 'syn:tag', 'depth'),
                    ('node', 'prop', 'set', 'syn:tag', '.created'),

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

                seen.clear()
                with mock.patch.object(s_auth.User, 'confirm', confirm):
                    with mock.patch.object(s_cortex.Cortex, 'confirmPropSet', confirmPropSet):
                        with mock.patch.object(s_cortex.Cortex, 'confirmPropDel', confirmPropDel):
                            await layr.confirmLayerEditPerms(user, parent.iden)

                self.eq(seen, {
                    # Node add
                    ('node', 'add', 'syn:tag'),
                    ('node', 'add', 'test:str'),

                    # Old style prop set
                    ('node', 'prop', 'set', 'test:str.created'),

                    ('node', 'prop', 'set', 'syn:tag:up'),
                    ('node', 'prop', 'set', 'syn:tag:base'),
                    ('node', 'prop', 'set', 'syn:tag:depth'),
                    ('node', 'prop', 'set', 'syn:tag.created'),

                    # New style prop set
                    ('node', 'prop', 'set', 'test:str', '.created'),

                    ('node', 'prop', 'set', 'syn:tag', 'up'),
                    ('node', 'prop', 'set', 'syn:tag', 'base'),
                    ('node', 'prop', 'set', 'syn:tag', 'depth'),
                    ('node', 'prop', 'set', 'syn:tag', '.created'),

                    # Tag/tagprop add
                    ('node', 'tag', 'add', 'foo', 'bar'),
                })

                seen.clear()
                with mock.patch.object(s_auth.User, 'confirm', confirm):
                    with mock.patch.object(s_cortex.Cortex, 'confirmPropSet', confirmPropSet):
                        with mock.patch.object(s_cortex.Cortex, 'confirmPropDel', confirmPropDel):
                            await layr.confirmLayerEditPerms(user, layr.iden, delete=True)

                self.eq(seen, {
                    # Node del
                    ('node', 'del', 'syn:tag'),
                    ('node', 'del', 'test:str'),

                    # Old style prop del
                    ('node', 'prop', 'del', 'test:str.created'),

                    ('node', 'prop', 'del', 'syn:tag:up'),
                    ('node', 'prop', 'del', 'syn:tag:base'),
                    ('node', 'prop', 'del', 'syn:tag:depth'),
                    ('node', 'prop', 'del', 'syn:tag.created'),

                    # New style prop del
                    ('node', 'prop', 'del', 'test:str', '.created'),

                    ('node', 'prop', 'del', 'syn:tag', 'up'),
                    ('node', 'prop', 'del', 'syn:tag', 'base'),
                    ('node', 'prop', 'del', 'syn:tag', 'depth'),
                    ('node', 'prop', 'del', 'syn:tag', '.created'),

                    # Tag/tagprop del
                    ('node', 'tag', 'del', 'foo', 'bar'),
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
                with mock.patch.object(s_cortex.Cortex, 'confirmPropSet', confirmPropSet):
                    with mock.patch.object(s_cortex.Cortex, 'confirmPropDel', confirmPropDel):
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
                with mock.patch.object(s_cortex.Cortex, 'confirmPropSet', confirmPropSet):
                    with mock.patch.object(s_cortex.Cortex, 'confirmPropDel', confirmPropDel):
                        await layr.confirmLayerEditPerms(user, parent.iden)

            self.eq(seen, set())

    async def test_layer_v9(self):
        async with self.getRegrCore('2.101.1-hugenum-indxprec') as core:

            huge1 = '730750818665451459101841.000000000000000000000001'
            huge2 = '730750818665451459101841.000000000000000000000002'
            huge3 = '730750818665451459101841.000000000000000000000003'

            nodes = await core.nodes(f'econ:purchase:price={huge1}')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('econ:purchase', '99a453112c45570ac2ccc6b941b09035'))

            nodes = await core.nodes(f'econ:purchase:price={huge2}')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('econ:purchase', '95afaf2b258160e0845f899ffff5115c'))

            nodes = await core.nodes(f'inet:fqdn:_hugearray*[={huge1}]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:fqdn', 'test1.com'))

            nodes = await core.nodes(f'inet:fqdn:_hugearray*[={huge3}]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:fqdn', 'test2.com'))

            nodes = await core.nodes(f'inet:fqdn#test:hugetp={huge1}')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:fqdn', 'test3.com'))

            nodes = await core.nodes(f'inet:fqdn#test:hugetp={huge2}')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:fqdn', 'test4.com'))

            self.len(1, await core.nodes(f'_test:huge={huge1}'))
            self.len(1, await core.nodes(f'_test:huge={huge2}'))
            self.len(1, await core.nodes(f'_test:hugearray*[={huge1}]'))
            self.len(1, await core.nodes(f'_test:hugearray*[={huge2}]'))
            self.len(1, await core.nodes(f'_test:hugearray*[={huge3}]'))

    async def test_layer_fromfuture(self):
        with self.raises(s_exc.BadStorageVersion):
            async with self.getRegrCore('future-layrvers') as core:
                pass

    async def test_layer_readonly_new(self):
        with self.getLoggerStream('synapse.cortex') as stream:
            async with self.getRegrCore('readonly-newlayer') as core:
                ldefs = await core.callStorm('return($lib.layer.list())')
                self.len(2, ldefs)

                readidens = [ldef['iden'] for ldef in ldefs if ldef.get('readonly')]
                self.len(1, readidens)

                writeidens = [ldef['iden'] for ldef in ldefs if not ldef.get('readonly')]

                readlayr = core.getLayer(readidens[0])
                writelayr = core.getLayer(writeidens[0])

                self.eq(readlayr.meta.get('version'), writelayr.meta.get('version'))

    async def test_push_pull_default_migration(self):
        async with self.getRegrCore('2.159.0-layr-pdefs') as core:
            def_tree = core.getLayer('507ebf7e6ec7aadc47ace6f1f8f77954').layrinfo
            dst_tree = core.getLayer('9bf7a3adbf69bd16832529ab1fcd1c83').layrinfo

            epulls = {'28cb757e9e390a234822f55b922f3295':
                           {'chunk:size': 1000,
                            'iden': '28cb757e9e390a234822f55b922f3295',
                            'offs': 0,
                            'queue:size': 10000,
                            'time': 1703781215891,
                            'url': 'cell://./cells/pdefmigr00:*/layer/9bf7a3adbf69bd16832529ab1fcd1c83',
                            'user': '1d8e6e87a2931f8d27690ff408debdab'}}
            epushs = {'e112f93f09e43f3a10ae945b84721778':
                           {'chunk:size': 1000,
                            'iden': 'e112f93f09e43f3a10ae945b84721778',
                            'offs': 0,
                            'queue:size': 10000,
                            'time': 1703781208684,
                            'url': 'cell://./cells/pdefmigr00:*/layer/9bf7a3adbf69bd16832529ab1fcd1c83',
                            'user': '1d8e6e87a2931f8d27690ff408debdab'}}

            self.eq(def_tree.get('pulls'), epulls)
            self.eq(def_tree.get('pushs'), epushs)

            self.notin('pulls', dst_tree)
            self.notin('pushs', dst_tree)

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

            iden = await core.callStorm('[ inet:ipv4=1.2.3.4 ] return($node.iden())')

            sodes = await s_t_utils.alist(layr00.getStorNodesByForm('inet:ipv4'))
            self.len(0, sodes)

            q = '''
                inet:ipv4=1.2.3.4
                $node.data.set("key", "valu")
            '''
            await core.callStorm(q, opts=infork00)

            sodes = await s_t_utils.alist(layr00.getStorNodesByForm('inet:ipv4'))
            self.len(1, sodes)

            q = '''
                view.exec $fork00 {
                    yield $iden
                    $lib.print($node)
                    delnode --deledges --force
                }
            '''
            opts = {'vars': {'iden': iden, 'fork00': fork00['iden']}}
            await core.callStorm(q, opts=opts)

            sodes = await s_t_utils.alist(layr00.getStorNodesByForm('inet:ipv4'))
            self.len(0, sodes)
