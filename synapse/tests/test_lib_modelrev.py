
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.layer as s_layer
import synapse.lib.spooled as s_spooled
import synapse.lib.modelrev as s_modelrev

import synapse.tests.utils as s_tests

from unittest import mock

# The inet:url values in the model-3.2.0 regression cortex, as stored by the pre-fix
# normalizer running under python -O, grouped by what the 3.2.0 model migration does.
URL_MOVED = {
    'http:////foo.com/x': 'http://foo.com/x',
    'https:////1.2.3.4:81/x': 'https://1.2.3.4:81/x',
    'smb:////s': 'smb://s',
    'http:////exists.com/y': 'http://exists.com/y',
    'file:/foo?x=http://a': 'file:///foo?x=http://a',
    'file://1.2.3.4@0.0.0.80/t.htm': 'file://1.2.3.4@80/t.htm',
    'file://host@ssl@0.0.1.187/x': 'file://host@SSL@443/x',
    'file://u@host@0.0.0.80/x': 'file://u@host@80/x',
    'file://host@ssl/x': 'file://host@SSL/x',
}

URL_FIXPROPS = (
    'http://foo.com/r?u=https:////evil.com/x',
    'http://foo.com/r?u=https://u@evil.com/x',
    'https://login.example.net#first.last@example.com',
    'https://a.example#u:p@b.example',
)

URL_QUEUED = (
    'c:////spam////eggs',
    'dvdnav:////dev/sr1',
    'a:b:////foo.com/x',
    'smb:///.//c:////spam////eggs',
    '//www.example.com/submit?url=https://example.org/x',
    '/share?u=http://example.net/a',
    'www.example.com/submit?url=https://example.org/x',
    'mailto:visi@vertex.link?x=http://example.net',
    '1http://example.com',
    'file://user@/x',
    'http://u:pa#ss@b.example/x',
)

URL_UNTOUCHED = (
    'file://user@host.vertex.link/share/x',
    'file:////host/share/x',
    'file:////host2/share/x',
    'https://good.com/x',
    'git+ssh://vertex.link/x',
    'chrome-extension://vertex.link/x',
)

URL_SOURCE = '9e9a0e4d3e2b4b1e8f0a1c2d3e4f5a6b'


def nope(*args, **kwargs):
    raise Exception('nope was called')

class ModelRevTest(s_tests.SynTest):

    async def test_cortex_modelrev_init(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:
                layr = core.getLayer()
                self.true(layr.fresh)
                self.eq(s_modelrev.maxvers, await layr.getModelVers())

            # no longer "fresh", but lets mark a layer as read only
            # and test the bail condition for layers which we cant update
            async with self.getTestCore(dirn=dirn) as core:

                layr = core.getLayer()
                layr.canrev = False

                mrev = s_modelrev.ModelRev(core)

                mrev.revs = mrev.revs + (((9999, 9999, 9999), nope),)

                with self.raises(s_exc.CantRevLayer):
                    await mrev.revCoreLayers()

            # no longer "fresh"
            async with self.getTestCore(dirn=dirn) as core:

                layr = core.getLayer()
                self.false(layr.fresh)

                self.eq(s_modelrev.maxvers, await layr.getModelVers())

                mrev = s_modelrev.ModelRev(core)

                layr.woot = False

                async def woot(layers):
                    layr.woot = True

                mrev.revs = mrev.revs + (((9999, 9999, 9999), woot),)

                await mrev.revCoreLayers()

                self.true(layr.woot)
                self.eq((9999, 9999, 9999), await layr.getModelVers())

    async def test_modelrev_3_1_0(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                await core.addTagProp('_seen', ('bool', {}), {})
                await core.addFormProp('test:str', '_flag', ('bool', {}), {})
                await core.addFormProp('test:str', '_flags', ('bool', {}), {'array': {}})
                await core.addFormProp('test:str', '_poly', ('poly', {'types': ('inet:fqdn', 'bool')}), {})

                await core.nodes('''[
                    (test:str=a :_flag=(true) :_flags=([true, false]) :_poly=(true) +#foo:_seen=(true))
                    (test:str=b :_flag=(false) :_poly=vertex.link +#foo:_seen=(false))
                    (test:str=c :_flag=(true) +#bar:_seen=(false))
                    (test:str=d :_flag=(true) +#foo:_seen=(true))
                ]''')

                layr = core.getLayer()

                # store bools as ints, as layers written before bools normed to True/False did
                def intify(valu):
                    if valu.__class__ is bool:
                        return int(valu)

                    if valu.__class__ is tuple:
                        return tuple(intify(v) for v in valu)

                    return valu

                # an int over an equal stored bool is a no-op, so delete each value first
                deledits = []
                setedits = []
                for node in await core.nodes('test:str=a test:str=b test:str=d'):

                    sode = layr.getStorNode(node.nid)
                    nid = s_common.int64un(node.nid)

                    for name, (valu, stortype, virts) in sode['props'].items():
                        deledits.append((nid, 'test:str', ((s_layer.EDIT_PROP_DEL, (name,)),)))
                        setedits.append((nid, 'test:str', ((s_layer.EDIT_PROP_SET, (name, intify(valu), stortype, virts)),)))

                    for tag, tagprops in sode['tagprops'].items():
                        for name, (valu, stortype, virts) in tagprops.items():
                            deledits.append((nid, 'test:str', ((s_layer.EDIT_TAGPROP_DEL, (tag, name)),)))
                            setedits.append((nid, 'test:str', ((s_layer.EDIT_TAGPROP_SET, (tag, name, intify(valu), stortype, virts)),)))

                await layr.saveNodeEdits(deledits, {'user': core.auth.rootuser.iden})
                await layr.saveNodeEdits(setedits, {'user': core.auth.rootuser.iden})

                node = (await core.nodes('test:str=a'))[0]
                sode = layr.getStorNode(node.nid)
                self.true(sode['props']['_flag'][0][1].__class__ is int)
                self.true(sode['props']['_poly'][0][1].__class__ is int)
                self.eq((int, int), tuple(v[1].__class__ for v in sode['props']['_flags'][0]))
                self.true(sode['tagprops']['foo']['_seen'][0].__class__ is int)

                # the whole array index of a bool array differs between ints and bools
                self.len(0, await core.nodes('test:str:_flags=([true, false])'))

                # an ordinary set of the same bool over a stored int is a no-op
                offs = layr.getEditIndx()
                await core.nodes('test:str=d [ :_flag=(true) +#foo:_seen=(true) ]')
                self.eq(offs, layr.getEditIndx())

                node = (await core.nodes('test:str=d'))[0]
                sode = layr.getStorNode(node.nid)
                self.true(sode['props']['_flag'][0][1].__class__ is int)
                self.true(sode['tagprops']['foo']['_seen'][0].__class__ is int)

                self.len(0, [e async for e in layr.verifyAllProps()])

                await layr.setModelVers((0, 2, 36))

            async with self.getTestCore(dirn=dirn) as core:

                await self.waitForActiveMigration(core)

                layr = core.getLayer()
                self.ge(await layr.getModelVers(), (3, 1, 0))
                self.eq(s_modelrev.maxvers, await layr.getModelVers())

                node = (await core.nodes('test:str=a'))[0]
                self.true(node.get('_flag')[1] is True)
                self.true(node.get('_poly')[1] is True)
                self.true(node.get('_flags')[0][1] is False)
                self.true(node.get('_flags')[1][1] is True)
                self.true(node.getTagProp('foo', '_seen') is True)

                pode = node.pack()
                self.true(pode[1]['props']['_flag'][0] is True)
                self.true(pode[1]['props']['_poly'][0] is True)
                self.true(pode[1]['props']['_flags'][0][1][0] is True)
                self.true(pode[1]['tagprops']['foo']['_seen'][0] is True)

                node = (await core.nodes('test:str=d'))[0]
                sode = layr.getStorNode(node.nid)
                self.true(sode['props']['_flag'][0][1] is True)
                self.true(sode['tagprops']['foo']['_seen'][0] is True)

                # setting the same bool again is a no-op
                offs = layr.getEditIndx()
                await core.nodes('test:str=d [ :_flag=(true) +#foo:_seen=(true) ]')
                self.eq(offs, layr.getEditIndx())

                # a stale int over a stored bool is a no-op
                node = (await core.nodes('test:str=a'))[0]
                sode = layr.getStorNode(node.nid)

                edits = []
                for name in ('_flag', '_flags', '_poly'):
                    valu, stortype, virts = sode['props'][name]
                    edits.append((s_layer.EDIT_PROP_SET, (name, intify(valu), stortype, virts)))

                valu, stortype, virts = sode['tagprops']['foo']['_seen']
                edits.append((s_layer.EDIT_TAGPROP_SET, ('foo', '_seen', intify(valu), stortype, virts)))

                await layr.saveNodeEdits([(s_common.int64un(node.nid), 'test:str', edits)], {'user': core.auth.rootuser.iden})
                self.eq(offs, layr.getEditIndx())

                sode = layr.getStorNode(node.nid)
                self.true(sode['props']['_flag'][0][1] is True)
                self.true(sode['props']['_poly'][0][1] is True)
                self.eq((False, True), tuple(v[1] for v in sode['props']['_flags'][0]))
                self.true(all(v[1].__class__ is bool for v in sode['props']['_flags'][0]))
                self.true(sode['tagprops']['foo']['_seen'][0] is True)
                self.len(1, await core.nodes('test:str:_flags=([true, false])'))

                node = (await core.nodes('test:str=b'))[0]
                self.true(node.get('_flag')[1] is False)
                self.eq(('inet:fqdn', 'vertex.link'), node.get('_poly'))
                self.true(node.getTagProp('foo', '_seen') is False)

                # a tag prop already stored as a bool is left as is
                node = (await core.nodes('test:str=c'))[0]
                self.true(node.getTagProp('bar', '_seen') is False)

                self.len(3, await core.nodes('test:str:_flag=(true)'))
                self.len(1, await core.nodes('test:str:_flags=([true, false])'))
                self.len(1, await core.nodes('test:str:_flags*[=(false)]'))
                self.len(1, await core.nodes('test:str#foo:_seen=(false)'))

                vals = [v async for v in core.getView().iterPropValues('test:str:_flag')]
                self.eq((False, True), tuple(v[1] for v in vals))
                self.true(all(v[1].__class__ is bool for v in vals))

                self.len(0, [e async for e in layr.verifyAllProps()])

    async def test_modelrev_3_3_0(self):

        with self.getTestDir() as dirn:

            nicguid = s_common.guid()

            async with self.getTestCore(dirn=dirn) as core:

                forkiden = await core.callStorm('return($lib.view.get().fork().iden)')
                goodiden = await core.callStorm('return($lib.view.get().fork().iden)')

                await core.nodes('''[
                    (it:cloud:host=* :name=good :parent={[ it:physical:host=* ]})
                    (it:cloud:host=* :name=bad :parent={[ it:physical:host=* ]})
                ]''')
                await core.nodes('[ it:cloud:host=* :name=forkbad :parent={[ it:physical:host=* ]} ]', opts={'view': forkiden})
                await core.nodes('[ it:cloud:host=* :name=forkgood :parent={[ it:physical:host=* ]} ]', opts={'view': goodiden})

                # store an it:nic parent, which it:cloud:host:parent allowed before it narrowed to it:host
                for name, viewiden in (('bad', None), ('forkbad', forkiden)):

                    view = core.getView(viewiden)
                    layr = view.layers[0]

                    node = (await view.nodes(f'it:cloud:host:name={name}'))[0]
                    valu, stortype, virts = layr.getStorNode(node.nid)['props']['parent']

                    edits = ((s_layer.EDIT_PROP_SET, ('parent', ('it:nic', nicguid), stortype, virts)),)
                    await layr.saveNodeEdits([(s_common.int64un(node.nid), 'it:cloud:host', edits)], {'user': core.auth.rootuser.iden})

                    node = (await view.nodes(f'it:cloud:host:name={name}'))[0]
                    self.eq(('it:nic', nicguid), node.get('parent'))

                for layr in core.layers.values():
                    await layr.setModelVers((3, 2, 0))

            with self.getLoggerStream('synapse.lib.modelrev') as stream:
                async with self.getTestCore(dirn=dirn) as core:

                    await self.waitForActiveMigration(core)
                    self.isin('Removed 2 it:cloud:host:parent values of a type it no longer accepts', stream.getvalue())

                    for layr in core.layers.values():
                        self.eq(s_modelrev.maxvers, await layr.getModelVers())

                    node = (await core.nodes('it:cloud:host:name=good'))[0]
                    self.eq('it:physical:host', node.get('parent')[0])
                    self.none(await node.getData('_migrated:it:cloud:host:parent'))

                    for name, viewiden in (('bad', None), ('forkbad', forkiden)):

                        view = core.getView(viewiden)

                        node = (await view.nodes(f'it:cloud:host:name={name}'))[0]
                        self.none(node.get('parent'))
                        self.eq(('it:nic', nicguid), await node.getData('_migrated:it:cloud:host:parent'))

                    self.len(1, await core.nodes('it:cloud:host:parent'))
                    self.len(1, await core.nodes('it:cloud:host:parent', opts={'view': forkiden}))

                    node = (await core.nodes('it:cloud:host:name=forkgood', opts={'view': goodiden}))[0]
                    self.eq('it:physical:host', node.get('parent')[0])
                    self.none(await node.getData('_migrated:it:cloud:host:parent'))

                    for layr in core.layers.values():
                        self.len(0, [e async for e in layr.verifyAllProps()])

    @contextlib.asynccontextmanager
    async def _getUrlCore(self, dirn, maxvers=None):

        orig = s_modelrev.ModelRev

        class ModelRev(orig):
            def __init__(self, core):
                orig.__init__(self, core)
                if maxvers is not None:
                    self.revs = [k for k in self.revs if k[0] <= maxvers]

        with self.withNexusReplay():
            with mock.patch.object(s_modelrev, 'ModelRev', ModelRev):
                async with await s_cortex.Cortex.anit(dirn) as core:
                    await self.waitForActiveMigration(core)
                    yield core

    async def _getUrlViews(self, core):
        views = {view.info.get('name'): view.iden for view in core.views.values()}
        return {'view': views['fork00']}, {'view': views['roview']}

    async def _getQueueItems(self, core):
        qdef = await core.getCoreQueueByName('model_3_2_0:nodes')
        return [(offs, item) async for (offs, item) in core.coreQueueGets(qdef['iden'], 0, cull=False, wait=False)]

    async def test_modelrev_3_2_0(self):

        with self.getRegrDir('cortexes', 'model-3.2.0') as dirn:

            async with self._getUrlCore(dirn, maxvers=(3, 1, 0)) as core:

                forkopts, roopts = await self._getUrlViews(core)

                for layr in core.layers.values():
                    self.eq((3, 1, 0), await layr.getModelVers())

                # every value the migration touches, plus the existing node one of them merges into
                count = len(URL_MOVED) + len(URL_FIXPROPS) + len(URL_QUEUED) + len(URL_UNTOUCHED) + 1
                self.len(count, await core.nodes('inet:url'))

                # the bad values no longer normalize, so they are found by scanning
                async def getUrl(valu, opts=None):
                    for node in await core.nodes('inet:url', opts=opts):
                        if node.ndef[1] == valu:
                            return node

                self.nn(await getUrl('https:////fork.com/x', opts=forkopts))
                self.nn(await getUrl('https:////ro.com/x', opts=roopts))

                node = await getUrl('file://host@ssl@0.0.1.187/x')
                self.propeq(node, 'username', 'host@SSL')
                self.propeq(node, 'host', (4, 443))

                node = await getUrl('http://foo.com/r?u=https:////evil.com/x')
                self.propeq(node, 'proto', 'http://foo.com/r?u=https')

                created = (await getUrl('http:////foo.com/x')).getMeta('created')
                dstcreated = (await getUrl('http://exists.com/y')).getMeta('created')

                rolayr = core.getView(roopts['view']).layers[0]
                self.true(rolayr.readonly)

                self.none(await core.getCoreQueueByName('model_3_2_0:nodes'))

            async with self._getUrlCore(dirn) as core:

                forkopts, roopts = await self._getUrlViews(core)

                for layr in core.layers.values():
                    self.ge(await layr.getModelVers(), (3, 2, 0))

                # every stored value normalizes to itself, with the computed props it derives
                inettype = core.model.type('inet:url')
                for opts in (None, forkopts, roopts):
                    for node in await core.nodes('inet:url', opts=opts):

                        (norm, info) = await inettype.norm(node.ndef[1])
                        self.eq(norm, node.ndef[1])

                        self.nn(s_modelrev.s_inet.schemere.fullmatch(node.get('proto')[1]))

                        username = node.get('username')
                        self.true(username is None or '#' not in username[1])

                expected = set(URL_MOVED.values()) | set(URL_FIXPROPS) | set(URL_UNTOUCHED)
                self.eq(expected, {n.ndef[1] for n in await core.nodes('inet:url')})
                self.eq(expected | {'https://fork.com/x'}, {n.ndef[1] for n in await core.nodes('inet:url', opts=forkopts)})
                self.eq({'https://ro.com/x'}, {n.ndef[1] for n in await core.nodes('inet:url', opts=roopts)})

                # a removed node is gone from every layer, including ones holding only its tags
                for valu in URL_QUEUED + tuple(URL_MOVED.keys()):
                    nid = core.getNidByNdef(('inet:url', valu))
                    for layr in core.layers.values():
                        self.none(layr.getStorNode(nid).get('form'))

                # a moved node keeps its tags, tag props, node data, edges and creation time
                nodes = await core.nodes('inet:url=http://foo.com/x')
                self.len(1, nodes)
                node = nodes[0]
                self.eq(created, node.getMeta('created'))
                self.propeq(node, 'host', 'foo.com')
                self.propeq(node, 'port', 80)
                self.nn(node.getTag('rep.test'))
                self.eq(10, node.getTagProp('rep.test', '_score'))
                self.eq('hehe', await node.getData('woot'))
                self.none(await node.getData('forkdata'))

                self.eq({('meta:source', URL_SOURCE)}, {n.ndef for n in await core.nodes('inet:url=http://foo.com/x <(seen)- *')})
                self.len(1, await core.nodes('inet:url=http://foo.com/x <(has)- it:dev:repo'))
                self.eq([('inet:fqdn', 'vertex.link')], [n.ndef for n in await core.nodes('inet:url=http://foo.com/x -(refs)> *')])

                # the fork keeps its own tags and node data, and its tombstone of a base tag
                nodes = await core.nodes('inet:url=http://foo.com/x', opts=forkopts)
                self.len(1, nodes)
                self.nn(nodes[0].getTag('fork.only'))
                self.none(nodes[0].getTag('rep.test'))
                self.eq('yep', await nodes[0].getData('forkdata'))

                # the read only layer was repaired and is still read only
                nodes = await core.nodes('inet:url=https://ro.com/x', opts=roopts)
                self.len(1, nodes)
                self.nn(nodes[0].getTag('ro.tag'))
                self.true(core.getView(roopts['view']).layers[0].readonly)

                # scalar, array and poly references follow the node
                self.len(1, await core.nodes('doc:report:title="scalar ref" +:url=http://foo.com/x'))
                nodes = await core.nodes('entity:contact:name="array ref"')
                self.eq(('http://foo.com/x', 'https://good.com/x'), tuple(v[1] for v in nodes[0].get('websites')))
                nodes = await core.nodes('it:av:scan:result:signame="poly ref"')
                self.eq(('inet:url', 'http://foo.com/x'), nodes[0].get('target'))

                # comps are renamed, including ones embedding the node twice or two moved nodes
                self.len(1, await core.nodes('inet:url:redir=(http://foo.com/x, https://good.com/x) +#redir.one'))
                self.len(1, await core.nodes('inet:url:redir=(http://foo.com/x, http://foo.com/x)'))
                nodes = await core.nodes('inet:url:redir=(http://foo.com/x, smb://s)')
                self.len(1, nodes)
                self.propeq(nodes[0], 'target', 'smb://s')
                self.len(1, await core.nodes('inet:urlfile:url=http://foo.com/x'))
                self.len(1, await core.nodes('it:host:hosted:url:url=http://foo.com/x'))
                self.len(3, await core.nodes('inet:url:redir'))
                self.len(0, await core.nodes('inet:url:mirror'))

                # a move into an existing node merges, and records what it could not keep
                nodes = await core.nodes('inet:url=http://exists.com/y')
                self.len(1, nodes)
                self.eq(dstcreated, nodes[0].getMeta('created'))
                self.eq(7, nodes[0].getTagProp('rep.test', '_score'))
                self.eq('good', await nodes[0].getData('woot'))
                self.nn(nodes[0].getTag('existing'))
                self.eq({'http:////exists.com/y': {'tagprops': {'rep.test': {'_score': 5}}, 'nodedata': {'woot': 'bad'}}},
                        await nodes[0].getData('model_3_2_0'))

                # computed props derived from the wrong part of the URL are re-normalized
                nodes = await core.nodes('inet:url="http://foo.com/r?u=https:////evil.com/x"')
                self.propeq(nodes[0], 'proto', 'http')
                self.propeq(nodes[0], 'host', 'foo.com')

                nodes = await core.nodes('inet:url="http://foo.com/r?u=https://u@evil.com/x"')
                self.none(nodes[0].get('username'))

                nodes = await core.nodes('inet:url="https://login.example.net#first.last@example.com"')
                self.propeq(nodes[0], 'host', 'login.example.net')
                self.none(nodes[0].get('username'))
                self.len(1, await core.nodes('inet:fqdn=login.example.net'))

                nodes = await core.nodes('inet:url="https://a.example#u:p@b.example"')
                self.propeq(nodes[0], 'host', 'a.example')
                self.none(nodes[0].get('passwd'))

                # WebDAV ports stored as an IPv4 host are restored
                nodes = await core.nodes('inet:url="file://1.2.3.4@80/t.htm"')
                self.propeq(nodes[0], 'host', (4, 0x01020304))
                self.propeq(nodes[0], 'port', 80)
                self.none(nodes[0].get('username'))
                self.len(1, await core.nodes('inet:ip=1.2.3.4'))

                nodes = await core.nodes('inet:url="file://host@SSL@443/x"')
                self.propeq(nodes[0], 'host', 'host')
                self.propeq(nodes[0], 'port', 443)

                nodes = await core.nodes('inet:url="file://u@host@80/x"')
                self.propeq(nodes[0], 'username', 'u')
                self.propeq(nodes[0], 'port', 80)

                # references to removed nodes are cleared
                nodes = await core.nodes('doc:report:title="queued ref"')
                self.none(nodes[0].get('url'))
                nodes = await core.nodes('doc:report:title="noscheme ref"')
                self.none(nodes[0].get('url'))
                nodes = await core.nodes('entity:contact:name="queued array ref"')
                self.eq((('inet:url', 'https://good.com/x'),), nodes[0].get('websites'))

                for layr in core.layers.values():
                    self.len(0, [e async for e in layr.verifyAllProps()])

                # the removed nodes are recorded in the queue
                items = await self._getQueueItems(core)
                self.len(len(URL_QUEUED) + 3, items)

                byvalu = {item['valu']: (offs, item) for (offs, item) in items}
                self.eq(set(URL_QUEUED) | {'dvdnav:////ro/sr1'},
                        {item['valu'] for (offs, item) in items if item['form'] == 'inet:url'})

                comps = [item for (offs, item) in items if item['form'] != 'inet:url']
                self.sorteq(['inet:url:mirror', 'inet:url:redir'], [item['form'] for item in comps])
                self.true(all(item['reason'] == 'comp' for item in comps))

                (offs, item) = byvalu['c:////spam////eggs']
                self.eq('remove', item['reason'])
                self.eq("Unknown scheme 'c' with an empty authority.", item['mesg'])
                self.eq((URL_SOURCE,), tuple(item['sources']))
                self.len(2, item['layers'])
                self.sorteq(['doc:report:url', 'entity:contact:websites', 'inet:url:mirror:at', 'inet:url:redir:source'],
                            [ref[2] for ref in item['refs']])
                self.sorteq([True, True], [ref[4] for ref in item['refs'] if ref[2].startswith('inet:url:')])

                (_, roitem) = byvalu['dvdnav:////ro/sr1']
                self.eq([core.getView(roopts['view']).layers[0].iden], list(roitem['layers'].keys()))

                (_, nsitem) = byvalu['//www.example.com/submit?url=https://example.org/x']
                self.eq('Invalid/Missing protocol', nsitem['mesg'])

                # the queue helpers
                lib = '$lib.model.migration.s.model_3_2_0'

                rows = await core.callStorm(f'''
                    $rows = ([])
                    for $row in {lib}.listNodes(source={URL_SOURCE}) {{ $rows.append($row) }}
                    return($rows)
                ''')
                self.eq([(offs, 'inet:url', 'c:////spam////eggs', (URL_SOURCE,))], rows)

                rows = await core.callStorm(f'''
                    $rows = ([])
                    for $row in {lib}.listNodes(form=inet:url:redir) {{ $rows.append($row) }}
                    return($rows)
                ''')
                self.len(1, rows)

                rows = await core.callStorm(f'''
                    $rows = ([])
                    for $row in {lib}.listNodes(offset=(1), size=(2)) {{ $rows.append($row) }}
                    return($rows)
                ''')
                self.eq([1, 2], [row[0] for row in rows])

                msgs = await core.stormlist(f'{lib}.printNode($offs)', opts={'vars': {'offs': offs}})
                self.stormIsInPrint("inet:url='c:////spam////eggs'", msgs)
                self.stormIsInPrint("reason: remove: Unknown scheme 'c' with an empty authority.", msgs)
                self.stormIsInPrint('#fork.queued', msgs)
                self.stormIsInPrint(f"<(seen)- meta:source='{URL_SOURCE}'", msgs)
                self.stormIsInPrint(f'sources: {URL_SOURCE}', msgs)
                self.stormIsInPrint('ref: doc:report:url on doc:report=', msgs)
                self.stormIsInPrint('inet:url:redir:source on inet:url:redir=', msgs)
                self.stormIsInPrint('(comp key, repair separately)', msgs)

                msgs = await core.stormlist(f'{lib}.printNode((9999))')
                self.stormIsInPrint('No item at offset 9999 in queue model_3_2_0:nodes.', msgs)

                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'return({lib}.repairNode($offs, newp))', opts={'vars': {'offs': offs}})

                opts = {'vars': {'offs': offs}}
                self.true(await core.callStorm(f'return({lib}.repairNode($offs, https://spam.example/eggs))', opts=opts))

                nodes = await core.nodes('inet:url=https://spam.example/eggs')
                self.len(1, nodes)
                self.propeq(nodes[0], 'host', 'spam.example')
                self.len(1, await core.nodes('inet:url=https://spam.example/eggs <(seen)- meta:source'))
                self.len(1, await core.nodes('doc:report:title="queued ref" +:url=https://spam.example/eggs'))
                nodes = await core.nodes('entity:contact:name="queued array ref"')
                self.eq(('https://good.com/x', 'https://spam.example/eggs'), tuple(v[1] for v in nodes[0].get('websites')))

                nodes = await core.nodes('inet:url=https://spam.example/eggs', opts=forkopts)
                self.nn(nodes[0].getTag('fork.queued'))

                # repairing again is idempotent, and remove pops the item
                self.len(len(URL_QUEUED) + 3, await self._getQueueItems(core))
                self.true(await core.callStorm(f'return({lib}.repairNode($offs, https://spam.example/eggs, remove=(true)))', opts=opts))
                self.len(len(URL_QUEUED) + 2, await self._getQueueItems(core))
                nodes = await core.nodes('entity:contact:name="queued array ref"')
                self.len(2, nodes[0].get('websites'))

                self.false(await core.callStorm(f'return({lib}.repairNode($offs, https://spam.example/eggs))', opts=opts))

                # a node held only by a read only layer is skipped there
                (rooffs, _) = byvalu['dvdnav:////ro/sr1']
                msgs = await core.stormlist(f'{lib}.repairNode($offs, https://ro.example/sr1)', opts={'vars': {'offs': rooffs}})
                self.stormIsInWarn('is read only, skipping it.', msgs)
                self.len(0, await core.nodes('inet:url=https://ro.example/sr1', opts=roopts))

                # the helpers require global admin
                visi = await core.auth.addUser('visi')
                with self.raises(s_exc.AuthDeny):
                    await core.callStorm(f'for $row in {lib}.listNodes() {{}}', opts={'user': visi.iden})

                for meth in ('printNode((0))', 'repairNode((0), https://newp.example)'):
                    with self.raises(s_exc.AuthDeny):
                        await core.callStorm(f'return({lib}.{meth})', opts={'user': visi.iden})

                with self.raises(s_exc.IsReadOnly):
                    await core.callStorm(f'return({lib}.repairNode((0), https://newp.example))', opts={'readonly': True})

                editoffs = core.getLayer().getEditIndx()

            # running again changes nothing
            async with self._getUrlCore(dirn) as core:
                self.eq(editoffs, core.getLayer().getEditIndx())

    async def test_modelrev_3_2_0_spooled(self):

        # Spilled working sets hold tuples and visit nodes in a different order, but must
        # migrate the same nodes. MAX_SPOOL_SIZE is bound as a default argument when the
        # class is defined, and neither the migration nor NodeFuser pass a size, so the
        # anit is patched rather than the module constant.
        orig = s_spooled.Spooled.__anit__

        async def __anit__(self, dirn=None, size=s_spooled.MAX_SPOOL_SIZE, cell=None):
            await orig(self, dirn=dirn, size=1, cell=cell)

        with mock.patch('synapse.lib.spooled.Spooled.__anit__', __anit__):

            with self.getRegrDir('cortexes', 'model-3.2.0') as dirn:

                async with self._getUrlCore(dirn) as core:

                    forkopts, roopts = await self._getUrlViews(core)

                    async with await s_modelrev.ModelMigration_3_2_0.anit(core, []) as migr:
                        self.eq(1, migr.verdicts.size)
                        self.eq(1, migr.removing.size)
                        self.eq(1, migr.queued.size)

                    items = await self._chkUrlMigrated(core)

                    self.sorteq([
                        (('inet:url', 'http://foo.com/x'), ('inet:url', 'https://good.com/x')),
                        (('inet:url', 'http://foo.com/x'), ('inet:url', 'http://foo.com/x')),
                        (('inet:url', 'http://foo.com/x'), ('inet:url', 'smb://s')),
                    ], [n.ndef[1] for n in await core.nodes('inet:url:redir')])

                    nodes = await core.nodes('doc:report:title="scalar ref"')
                    self.eq(('inet:url', 'http://foo.com/x'), nodes[0].get('url'))

                    nodes = await core.nodes('inet:url=http://exists.com/y')
                    self.eq({'http:////exists.com/y': {'tagprops': {'rep.test': {'_score': 5}}, 'nodedata': {'woot': 'bad'}}},
                            await nodes[0].getData('model_3_2_0'))

                    nodes = await core.nodes('inet:url=http://foo.com/x', opts=forkopts)
                    self.nn(nodes[0].getTag('fork.only'))
                    self.none(nodes[0].getTag('rep.test'))

                    self.eq(set(URL_QUEUED) | {'dvdnav:////ro/sr1'},
                            {item['valu'] for (offs, item) in items if item['form'] == 'inet:url'})

    async def _chkUrlMigrated(self, core):
        '''
        Check the state a complete run of the 3.2.0 migration leaves the regression cortex in.

        Returns:
            list: The (offs, item) of every queue item.
        '''
        forkopts, roopts = await self._getUrlViews(core)

        for layr in core.layers.values():
            self.ge(await layr.getModelVers(), (3, 2, 0))
            self.len(0, [e async for e in layr.verifyAllProps()])

        expected = set(URL_MOVED.values()) | set(URL_FIXPROPS) | set(URL_UNTOUCHED)
        self.eq(expected, {n.ndef[1] for n in await core.nodes('inet:url')})
        self.eq(expected | {'https://fork.com/x'}, {n.ndef[1] for n in await core.nodes('inet:url', opts=forkopts)})
        self.eq({'https://ro.com/x'}, {n.ndef[1] for n in await core.nodes('inet:url', opts=roopts)})

        # nothing was recorded twice, nothing recorded is left, and the record of each
        # inet:url names the comps removed with it
        items = await self._getQueueItems(core)
        self.len(len(URL_QUEUED) + 3, items)
        self.false(any(self._isStored(core, (item['form'], item['valu'])) for (offs, item) in items))

        comps = {(item['form'], item['valu']) for (offs, item) in items if item['form'] != 'inet:url'}
        self.sorteq(['inet:url:mirror', 'inet:url:redir'], [comp[0] for comp in comps])
        self.eq(comps, {s_common.tuplify(ref[1]) for (offs, item) in items if item['form'] == 'inet:url'
                        for ref in item['refs'] if ref[4]})

        return items

    async def test_modelrev_3_2_0_rerun(self):

        # A migration interrupted while renaming or removing nodes finishes on the next boot.
        # A rerun finds the comps to remove through the inet:url they embed, so each comp is
        # removed before it.
        def failOn(cls, name, fail):
            orig = getattr(cls, name)

            async def wrap(self, *args):
                if fail(*args):
                    raise s_exc.SynErr(mesg='boom')
                return await orig(self, *args)

            return mock.patch.object(cls, name, wrap)

        renames = []
        def thirdRename(meta):
            renames.append(meta)
            return len(renames) == 3

        for patch in (failOn(s_modelrev.UrlFuser, 'applyLayerEdits', thirdRename),
                      failOn(s_modelrev.ModelMigrationBase, 'removeNode', lambda ndef, *args: ndef[0] == 'inet:url')):

            with self.getRegrDir('cortexes', 'model-3.2.0') as dirn:

                with patch:
                    async with self._getUrlCore(dirn) as core:

                        for layr in core.layers.values():
                            self.eq((3, 1, 0), await layr.getModelVers())

                        # every node was recorded, and every comp removed
                        items = await self._getQueueItems(core)
                        self.len(len(URL_QUEUED) + 3, items)
                        self.false(any(self._isStored(core, (item['form'], item['valu']))
                                       for (offs, item) in items if item['form'] != 'inet:url'))

                async with self._getUrlCore(dirn) as core:
                    await self._chkUrlMigrated(core)

    async def test_modelrev_3_2_0_nested(self):

        # A comp which embeds another comp is removed before it, and one reached at more
        # than one depth is removed before everything below its deepest path.
        async with self.getTestCore() as core:

            layr = core.getLayer()

            await core.addForm('_test:nest', 'comp', {'fields': (('_url', 'inet:url'), ('_redir', 'inet:url:redir'))}, {})
            await core.addFormProp('_test:nest', '_url', ('inet:url', {}), {'computed': True})
            await core.addFormProp('_test:nest', '_redir', ('inet:url:redir', {}), {'computed': True})

            urlndef = ('inet:url', 'c:////x')
            redirndef = ('inet:url:redir', (urlndef, ('inet:url', 'https://vertex.link')))
            nestndef = ('_test:nest', (urlndef, redirndef))

            await self._addRawNode(core, layr, *urlndef)
            await self._addRawNode(core, layr, 'inet:url', 'https://vertex.link')
            await self._addRawNode(core, layr, *redirndef, (('source', urlndef), ('target', ('inet:url', 'https://vertex.link'))))
            await self._addRawNode(core, layr, *nestndef, (('_url', urlndef), ('_redir', redirndef)))

            async with await s_modelrev.ModelMigration_3_2_0.anit(core, [layr]) as migr:
                self.sorteq([(urlndef, 0), (redirndef, 1), (nestndef, 2)], await migr._addRemoving(urlndef))
                self.eq([], await migr._addRemoving(urlndef))

            removed = []
            orig = s_modelrev.ModelMigrationBase.removeNode

            async def removeNode(self, ndef, reason, mesg, removing):
                removed.append(ndef)
                return await orig(self, ndef, reason, mesg, removing)

            with mock.patch.object(s_modelrev.ModelMigrationBase, 'removeNode', removeNode):
                async with core.enterMigrationMode():
                    await s_modelrev.ModelRev(core).revModel_3_2_0([layr])

            self.eq([nestndef, redirndef, urlndef], removed)
            self.false(any(self._isStored(core, ndef) for ndef in removed))

            # the inet:url was recorded while both comps still embedded it
            (_, item) = await self._getQueueItem(core, urlndef[1])
            self.sorteq([redirndef, nestndef], [s_common.tuplify(ref[1]) for ref in item['refs'] if ref[4]])

    async def test_modelrev_3_2_0_tombstones(self):

        # Removing a node deletes the tombstones a fork holds for it, so they are recorded
        # and restored with it, and the fork does not see what it deleted again.
        async with self.getTestCore() as core:

            lib = '$lib.model.migration.s.model_3_2_0'
            layr = core.getLayer()

            await core.addTagProp('_score', ('int', {}), {})

            await core.nodes('''
                [ test:str=other test:str=other2 inet:url=https://c.example/x ]
                [( test:str=tomb :hehe=haha +#tag +#foo:_score=3
                   +(refs)> { test:str=other test:str=other2 } <(refs)+ { test:str=other test:str=other2 } )]
                $node.data.set(woot, hehe)
                [( test:str=gone )]
            ''')

            forkopts = {'view': await core.callStorm('return($lib.view.get().fork().iden)')}
            forklayr = core.getView(forkopts['view']).layers[0]

            await core.nodes('''
                test:str=tomb
                [ -:hehe -#tag -#foo:_score
                  -(refs)> { test:str=other test:str=other2 } <(refs)- { test:str=other test:str=other2 } ]
                $node.data.pop(woot)
            ''', opts=forkopts)
            await core.nodes('test:str=gone | delnode', opts=forkopts)

            # a tombstone of a computed prop is not recorded, since the value derives it
            meta = {'time': s_common.now(), 'user': core.auth.rootuser.iden}
            urlnid = core.getNidByNdef(('inet:url', 'https://c.example/x'))
            await forklayr.saveNodeEdits([(s_common.int64un(urlnid), 'inet:url', ((s_layer.EDIT_PROP_TOMB, ('proto',)),))], meta)

            edges = [('refs', ('test:str', 'other')), ('refs', ('test:str', 'other2'))]

            async with await s_modelrev.ModelMigration_3_2_0.anit(core, [layr, forklayr]) as migr:

                item = await migr.captureNode(('inet:url', 'https://c.example/x'), 'remove', None)
                self.eq([], item['layers'][forklayr.iden]['tombs']['props'])

                item = await migr.captureNode(('test:str', 'tomb'), 'remove', 'test mesg')

                notombs = {'valu': False, 'props': [], 'tags': [], 'tagprops': {}, 'nodedata': [], 'n1edges': [], 'n2edges': []}
                self.eq(notombs, item['layers'][layr.iden]['tombs'])

                tombs = item['layers'][forklayr.iden]['tombs']
                self.eq({'valu': False, 'props': ['hehe'], 'tags': ['tag'], 'tagprops': {'foo': ['_score']},
                         'nodedata': ['woot'], 'n1edges': edges, 'n2edges': edges},
                        {**tombs, 'n1edges': sorted(tombs['n1edges']), 'n2edges': sorted(tombs['n2edges'])})

                # a prop which is gone by the time it is repaired is skipped
                tombs['props'].append('newp')

                await core.coreQueuePuts(await migr._reqQueue(), (item,))
                await migr.queued.add(('test:str', 'tomb'))

                for valu in ('tomb', 'gone'):
                    await migr.removeNode(('test:str', valu), 'remove', None, migr.removing)

            (tomboffs, _) = await self._getQueueItem(core, 'tomb')
            (goneoffs, item) = await self._getQueueItem(core, 'gone')
            self.true(item['layers'][forklayr.iden]['tombs']['valu'])

            msgs = await core.stormlist(f'{lib}.printNode($offs)', opts={'vars': {'offs': tomboffs}})
            for line in ('tombstone: :hehe', 'tombstone: #tag', 'tombstone: #foo:_score', 'tombstone: data: woot',
                         "tombstone: -(refs)> test:str='other'", "tombstone: <(refs)- test:str='other'"):
                self.stormIsInPrint(line, msgs)

            msgs = await core.stormlist(f'{lib}.printNode($offs)', opts={'vars': {'offs': goneoffs}})
            self.stormIsInPrint('tombstone: node', msgs)

            # a tombstone of an edge to a node which no longer exists has nothing to hide
            await core.nodes('test:str=other2 | delnode --force')

            for (offs, valu) in ((tomboffs, 'tomb2'), (goneoffs, 'gone2')):
                self.true(await core.callStorm(f'return({lib}.repairNode($offs, {valu}))', opts={'vars': {'offs': offs}}))

            # the base view sees everything the node held, and the fork still does not see
            # what it deleted
            async def getState(opts=None):
                node = (await core.nodes('test:str=tomb2', opts=opts))[0]
                return (node.get('hehe'), node.getTag('tag') is not None, node.getTagProp('foo', '_score'),
                        await node.getData('woot'),
                        len(await core.nodes('test:str=tomb2 -(refs)> *', opts=opts)),
                        len(await core.nodes('test:str=tomb2 <(refs)- *', opts=opts)))

            self.eq((('str', 'haha'), True, 3, 'hehe', 1, 1), await getState())
            self.eq((None, False, None, None, 0, 0), await getState(forkopts))

            self.len(1, await core.nodes('test:str=gone2'))
            self.len(0, await core.nodes('test:str=gone2', opts=forkopts))

            for othr in (layr, forklayr):
                self.len(0, [e async for e in othr.verifyAllProps()])

    def _isStored(self, core, ndef):
        '''
        Return whether any layer holds a node, without normalizing a value which may no
        longer be valid.
        '''
        if (nid := core.getNidByNdef(s_common.tuplify(ndef))) is None:
            return False

        return any(layr.getStorNode(nid).get('valu') is not None for layr in core.layers.values())

    async def _addRawNode(self, core, layr, form, valu, props=()):
        '''
        Store a node without normalizing its value, the way the pre-fix normalizer did.
        '''
        meta = {'time': s_common.now(), 'user': core.auth.rootuser.iden}

        (stortype, virts) = core.model.form(form).type.getStorInfo(valu)
        edits = [(s_layer.EDIT_NODE_ADD, (valu, stortype, virts))]

        for name, pvalu in props:
            prop = core.model.prop(f'{form}:{name}')
            (pstortype, pvirts) = prop.type.getStorInfo(pvalu)
            edits.append((s_layer.EDIT_PROP_SET, (name, pvalu, pstortype, pvirts)))

        await layr.saveNodeEdits([(None, form, edits)], meta)

    async def _getQueueItem(self, core, valu):
        for (offs, item) in await self._getQueueItems(core):
            if item['valu'] == valu:
                return offs, item

    async def test_modelrev_3_2_0_synthetic(self):

        async with self.getTestCore() as core:

            lib = '$lib.model.migration.s.model_3_2_0'
            layr = core.getLayer()

            await core.addTagProp('_score', ('int', {}), {})

            # --- the helpers, and a migration with nothing to repair ---

            msgs = await core.stormlist(f'for $item in {lib}.listNodes() {{ $lib.print($item) }}')
            self.stormIsInPrint('Queue model_3_2_0:nodes not found, no nodes to list.', msgs)

            msgs = await core.stormlist(f'{lib}.printNode((0))')
            self.stormIsInPrint('Queue model_3_2_0:nodes not found, no nodes to print.', msgs)

            msgs = await core.stormlist(f'{lib}.repairNode((0), https://vertex.link)')
            self.stormIsInPrint('Queue model_3_2_0:nodes not found, no nodes to repair.', msgs)

            async with core.enterMigrationMode():
                await s_modelrev.ModelRev(core).revModel_3_2_0(list(core.layers.values()))

            self.none(await core.getCoreQueueByName('model_3_2_0:nodes'))

            # --- verdicts ---

            async with await s_modelrev.ModelMigration_3_2_0.anit(core, list(core.layers.values())) as migr:

                async def verdict(valu, **props):
                    props = {name: (('str', v), 0, None) for (name, v) in props.items()}
                    return await migr._getVerdict(valu, props)

                self.eq(('move', 'http://foo.com/x', None), await verdict('http:////foo.com/x'))
                self.eq('remove', (await verdict('c:////foo.com/x'))[0])

                # the first :// is not preceded by a valid scheme, so it belongs to a URL
                # embedded in the path or query rather than marking an empty authority
                self.eq(('move', 'file:///x?u=http:////y', None), await verdict('file:/x?u=http:////y'))
                self.eq(('remove', None, 'Invalid/Missing protocol'), await verdict('foo?u=http:////y'))

                # a UNC file URL is valid
                self.none(await verdict('file:////host/share/x'))

                self.eq(('fixprops', None, None), await verdict('http://a.com/?u=b://c', proto='http://a.com/?u=b'))
                self.eq('remove', (await verdict('1http://example.com'))[0])
                self.eq(('fixprops', None, None), await verdict('https://a.example', username=''))
                self.eq(('fixprops', None, None), await verdict('https://a.example', passwd='a#b'))

                # WebDAV ports stored as IPv4 hosts
                self.eq(('move', 'file://host@SSL@443/x', None), await verdict('file://host@ssl@0.0.1.187/x'))
                self.eq(('move', 'file://host@80/x', None), await verdict('file://host@0.0.0.80/x'))
                self.eq('remove', (await verdict('file://host@0.0.256.0/x'))[0])
                self.eq('remove', (await verdict('file://host@0.0.999.999/x'))[0])

                # userinfo and a host is valid, and the props are re-derived from the value
                self.eq(('fixprops', None, None), await verdict('file://user@host/x'))
                self.none(await verdict('https://good.com/x'))
                self.none(await verdict('file:///c:/foo'))

                self.eq(0, await migr.fixComputedProps('inet:url', 'https://newp.example'))

            # --- comps embedding more than one bad URL ---

            for valu in ('http:////a.com/x', 'http:////b.com/x', 'c:////x', 'd:////y'):
                await self._addRawNode(core, layr, 'inet:url', valu)

            def redirvalu(src, dst):
                return (('inet:url', src), ('inet:url', dst))

            # both slots move, one moves and one is removed, and both are removed
            for (src, dst) in (('http:////a.com/x', 'http:////b.com/x'),
                               ('http:////a.com/x', 'c:////x'),
                               ('c:////x', 'd:////y')):
                await self._addRawNode(core, layr, 'inet:url:redir', redirvalu(src, dst),
                                       (('source', ('inet:url', src)), ('target', ('inet:url', dst))))

            self.len(3, await core.nodes('inet:url:redir'))

            async with core.enterMigrationMode():
                await s_modelrev.ModelRev(core).revModel_3_2_0([layr])

            nodes = await core.nodes('inet:url:redir')
            self.eq([('inet:url:redir', redirvalu('http://a.com/x', 'http://b.com/x'))], [n.ndef for n in nodes])
            self.propeq(nodes[0], 'source', 'http://a.com/x')
            self.propeq(nodes[0], 'target', 'http://b.com/x')

            items = await self._getQueueItems(core)
            self.sorteq(['inet:url', 'inet:url', 'inet:url:redir', 'inet:url:redir'], [item['form'] for (_, item) in items])

            self.len(0, [e async for e in layr.verifyAllProps()])

            # with nothing left to repair, a second run changes nothing
            async with core.enterMigrationMode():
                await s_modelrev.ModelRev(core).revModel_3_2_0([layr])

            self.len(4, await self._getQueueItems(core))

            # --- what a queue item records, and repairing it ---

            await self._addRawNode(core, layr, 'inet:url', 'zz:////x')

            # a layer which is not the write layer of any view
            nvlayr = await core.addLayer()
            nvlayr = core.getLayer(nvlayr['iden'])

            await self._addRawNode(core, nvlayr, 'inet:url', 'zz:////x')
            await self._addRawNode(core, nvlayr, 'inet:url', 'http:////nv.example/x')

            # a merge whose node data agrees is not a conflict
            await self._addRawNode(core, layr, 'inet:url', 'http:////m.example/x')
            await core.nodes('[ inet:url=http://m.example/x ]')

            # the bad values no longer normalize, so they are edited by lifting every inet:url
            await core.nodes('''
                [ test:str=n1 test:str=n2 test:str=keep ]
                inet:url
                [ +#foo:_score=5 +(refs)> { test:str=n2 } <(refs)+ { test:str=n1 } +(refs)> { test:str=keep } ]
                $node.data.set(woot, hehe)
                $node.data.set(same, yes)
            ''')

            async with core.enterMigrationMode():
                await s_modelrev.ModelRev(core).revModel_3_2_0(list(core.layers.values()))

            nodes = await core.nodes('inet:url=http://m.example/x')
            self.eq('yes', await nodes[0].getData('same'))
            self.none(await nodes[0].getData('model_3_2_0'))

            nvnid = core.getNidByNdef(('inet:url', 'http://nv.example/x'))
            self.nn(nvlayr.getStorNode(nvnid).get('valu'))

            # the nodes a moved value adds are created in a layer no view writes to
            self.nn(nvlayr.getStorNode(core.getNidByNdef(('inet:fqdn', 'nv.example'))).get('valu'))

            self.len(5, await self._getQueueItems(core))
            (offs, item) = await self._getQueueItem(core, 'zz:////x')

            info = item['layers'][layr.iden]
            self.eq({'foo': {'_score': 5}}, info['tagprops'])
            self.sorteq([('woot', 'hehe'), ('same', 'yes')], info['nodedata'])
            self.sorteq([('refs', ('test:str', 'n2')), ('refs', ('test:str', 'keep'))], info['n1edges'])
            self.eq([('refs', ('test:str', 'n1'))], info['n2edges'])
            self.eq([nvlayr.iden], [iden for iden in item['layers'].keys() if iden != layr.iden])

            opts = {'vars': {'offs': offs}}

            msgs = await core.stormlist(f'{lib}.printNode($offs)', opts=opts)
            self.stormIsInPrint('#foo:_score = 5', msgs)
            self.stormIsInPrint('data: woot', msgs)
            self.stormIsInPrint("-(refs)> test:str='n2'", msgs)
            self.stormIsInPrint("<(refs)- test:str='n1'", msgs)

            await core.nodes('test:str=n1 test:str=n2 | delnode --force')
            await core.delLayer(nvlayr.iden)

            msgs = await core.stormlist(f'{lib}.repairNode($offs, https://zz.example/x)', opts=opts)
            self.stormIsInWarn(f'Layer {nvlayr.iden} no longer exists, skipping it.', msgs)
            self.stormIsInWarn("Node test:str='n2' no longer exists, skipping its -(refs)> edge.", msgs)
            self.stormIsInWarn("Node test:str='n1' no longer exists, skipping its -(refs)> edge.", msgs)

            nodes = await core.nodes('inet:url=https://zz.example/x')
            self.len(1, nodes)
            self.eq(5, nodes[0].getTagProp('foo', '_score'))
            self.eq('hehe', await nodes[0].getData('woot'))
            self.eq([('test:str', 'keep')], [n.ndef for n in await core.nodes('inet:url=https://zz.example/x -(refs)> *')])

            for othr in core.layers.values():
                self.len(0, [e async for e in othr.verifyAllProps()])

            # --- capturing and repairing a node with props, tombstones and stale references ---

            await core.nodes('''
                [ test:str=other ]
                [( test:str=cap :hehe=haha +#tag=(2020, 2021) +#foo:_score=3
                   +(refs)> { test:str=other } <(refs)+ { test:str=other } )]
                $node.data.set(woot, hehe)
                $n=$node
                [( test:str=ref :bar=$n )]
            ''')

            forkiden = await core.callStorm('return($lib.view.get().fork().iden)')
            forkopts = {'view': forkiden}
            await core.nodes('test:str=cap [ -#tag -(refs)> { test:str=other } <(refs)- { test:str=other } ]', opts=forkopts)

            forklayr = core.getView(forkiden).layers[0]

            async with await s_modelrev.ModelMigration_3_2_0.anit(core, [layr, forklayr]) as migr:

                item = await migr.captureNode(('test:str', 'cap'), 'remove', 'test mesg')

                self.eq({'hehe': ('str', 'haha')}, item['layers'][layr.iden]['props'])
                self.eq({'foo': {'_score': 3}}, item['layers'][layr.iden]['tagprops'])
                self.eq([('test:str:bar', False, False)], [ref[2:] for ref in item['refs']])
                self.eq([('refs', ('test:str', 'other'))], item['layers'][layr.iden]['n1edges'])
                self.eq([('refs', ('test:str', 'other'))], item['layers'][layr.iden]['n2edges'])

                # tombstones are recorded apart from the state the node held
                forkinfo = item['layers'][forklayr.iden]
                self.false(forkinfo['valu'])
                self.eq([], forkinfo['n1edges'])
                self.eq([], forkinfo['n2edges'])
                self.eq(['tag'], forkinfo['tombs']['tags'])
                self.eq([('refs', ('test:str', 'other'))], forkinfo['tombs']['n1edges'])
                self.eq([('refs', ('test:str', 'other'))], forkinfo['tombs']['n2edges'])

                # a tag prop or a layer which is gone by the time it is repaired is skipped
                item['layers'][layr.iden]['tagprops']['foo']['_newp'] = 1
                item['layers'][layr.iden]['props']['newp'] = 'newp'
                item['layers']['0' * 32] = item['layers'][forklayr.iden]
                item['refs'].append(('0' * 32, ('test:str', 'ref'), 'test:str:bar', False, False))
                item['refs'].append((layr.iden, ('test:str', 'newp'), 'test:str:bar', False, False))
                item['refs'].append((forklayr.iden, ('test:str', 'ref'), 'test:str:bar', False, False))

                await core.coreQueuePuts(await migr._reqQueue(), (item,))

            (offs, _) = await self._getQueueItem(core, 'cap')
            opts = {'vars': {'offs': offs}}

            # a removal clears the references to the node, which delnode does not
            await core.nodes('test:str=cap | delnode --force')
            await core.nodes('test:str=ref [ -:bar ]')

            msgs = await core.stormlist(f'{lib}.printNode($offs)', opts=opts)
            self.stormIsInPrint('test:str=\'cap\'', msgs)
            self.stormIsInPrint('reason: remove: test mesg', msgs)
            self.stormIsInPrint(':hehe = haha', msgs)
            self.stormIsInPrint('#tag = 2020-01-01T00:00:00Z - 2021-01-01T00:00:00Z', msgs)

            await forklayr.setLayerInfo('readonly', True)

            msgs = await core.stormlist(f'{lib}.repairNode($offs, cap2)', opts=opts)
            self.stormIsInWarn('Tag property _newp no longer exists, skipping it.', msgs)
            self.stormIsInWarn(f'Layer {"0" * 32} no longer exists, skipping it.', msgs)
            self.stormIsInWarn(f'Layer {forklayr.iden} is read only, skipping it.', msgs)

            nodes = await core.nodes('test:str=cap2')
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 'haha')
            self.nn(nodes[0].getTag('tag'))
            self.eq(3, nodes[0].getTagProp('foo', '_score'))

            # a scalar reference which has been set again since is left alone
            nodes = await core.nodes('test:str=ref')
            self.eq(('test:str', 'cap2'), nodes[0].get('bar'))
            await core.nodes('test:str=ref test:str=other $o=$node -> { test:str=ref [ :bar=$o ] }')

            await forklayr.setLayerInfo('readonly', False)
            await core.nodes('test:str=ref [ -:bar ]', opts=forkopts)
            await forklayr.setLayerInfo('readonly', True)

            await core.stormlist(f'{lib}.repairNode($offs, cap2)', opts=opts)
            nodes = await core.nodes('test:str=ref')
            self.eq(('test:str', 'other'), nodes[0].get('bar'))

    async def test_modelrev_3_2_0_failures(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()

            await self._addRawNode(core, layr, 'inet:url', 'http:////a.example/x')

            # a layer which could not be written leaves the model version unset
            def getResult(self):
                return {'failed': [(layr.iden, 'boom')], 'warnings': []}

            with mock.patch.object(s_modelrev.UrlFuser, 'getResult', getResult):
                async with core.enterMigrationMode():
                    with self.raises(s_exc.SynErr) as cm:
                        await s_modelrev.ModelRev(core).revModel_3_2_0([layr])

            self.isin('could not apply its edits to every layer', cm.exception.get('mesg'))

            await self._addRawNode(core, layr, 'inet:url', 'http:////c.example/x')
            await self._addRawNode(core, layr, 'inet:url:redir', (('inet:url', 'http:////c.example/x'), ('inet:url', 'https://d.example')),
                                   (('source', ('inet:url', 'http:////c.example/x')), ('target', ('inet:url', 'https://d.example'))))

            # a node which cannot be renamed is recorded instead, along with the comps embedding it
            async def getLayerEdits(self, srcndef, dstndef):
                raise s_exc.BadTypeValu(mesg='rename boom')

            with mock.patch.object(s_modelrev.UrlFuser, 'getLayerEdits', getLayerEdits):
                async with core.enterMigrationMode():
                    await s_modelrev.ModelRev(core).revModel_3_2_0([layr])

            items = await self._getQueueItems(core)
            self.sorteq([('inet:url', 'remove'), ('inet:url:redir', 'comp')], [(item['form'], item['reason']) for (_, item) in items])
            self.true(all(item['mesg'] == 'rename boom' for (_, item) in items))

            self.len(0, await core.nodes('inet:url:redir'))
            self.eq(['http://a.example/x'], [n.ndef[1] for n in await core.nodes('inet:url')])
