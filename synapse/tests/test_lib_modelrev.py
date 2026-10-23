
import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.layer as s_layer
import synapse.lib.modelrev as s_modelrev

import synapse.tests.utils as s_tests


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
                self.eq((3, 1, 0), await layr.getModelVers())
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
