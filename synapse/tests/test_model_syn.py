import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.time as s_time
import synapse.lib.version as s_version
import synapse.lib.stormsvc as s_stormsvc

import synapse.tests.utils as s_t_utils

class TestService(s_stormsvc.StormSvc):
    _storm_svc_name = 'test'
    _storm_svc_pkgs = (
        {
            'name': 'foo',
            'version': (0, 0, 1),
            'synapse_version': '>=3.0.0b2,<4.0.0',
            'commands': (
                {
                    'name': 'foobar',
                    'descr': 'foobar is a great service',
                    'storm': '',
                },
                {
                    'name': 'ohhai',
                    'storm': '',
                },
                {
                    'name': 'deprvers',
                    'storm': '',
                    'deprecated': {'eolvers': 'v3.0.0'},
                },
                {
                    'name': 'deprdate',
                    'storm': '',
                    'deprecated': {'eoldate': '2099-01-01'},
                },
                {
                    'name': 'deprmesg',
                    'storm': '',
                    'deprecated': {'eoldate': '2099-01-01', 'mesg': 'Please use ``ohhai``.'},
                },
            )
        },
    )

class SynModelTest(s_t_utils.SynTest):

    async def test_syn_userrole(self):

        async with self.getTestCore() as core:

            (ok, iden) = await core.callStorm('return($lib.trycast(syn:user, root))')
            self.true(ok)
            self.eq(iden, core.auth.rootuser.iden)

            # coverage for iden taking precedence
            (ok, iden) = await core.callStorm(f'return($lib.trycast(syn:user, {iden}))')
            self.true(ok)
            self.eq(iden, core.auth.rootuser.iden)

            self.eq('root', await core.callStorm(f'return($lib.repr(syn:user, {iden}))'))

            with self.raises(s_exc.BadTypeValu) as exc:
                await core.callStorm('return($lib.cast(syn:user, newp))')
            self.eq(exc.exception.get('mesg'), 'No user named newp and value is not a guid.')
            self.eq(exc.exception.get('valu'), 'newp')
            self.eq(exc.exception.get('name'), 'syn:user')

            with self.raises(s_exc.BadTypeValu) as exc:
                await core.callStorm('$lib.cast(syn:user, *)')

            self.isin('syn:user values must be a valid username or a guid.', exc.exception.get('mesg'))
            self.eq(exc.exception.get('valu'), '*')
            self.eq(exc.exception.get('name'), 'syn:user')

            (ok, iden) = await core.callStorm('return($lib.trycast(syn:role, all))')
            self.true(ok)
            self.eq(iden, core.auth.allrole.iden)

            # coverage for iden taking precedence
            (ok, iden) = await core.callStorm(f'return($lib.trycast(syn:role, {iden}))')
            self.true(ok)
            self.eq(iden, core.auth.allrole.iden)

            self.eq('all', await core.callStorm(f'return($lib.repr(syn:role, {iden}))'))

            with self.raises(s_exc.BadTypeValu) as exc:
                await core.callStorm('return($lib.cast(syn:role, newp))')
            self.eq(exc.exception.get('mesg'), 'No role named newp and value is not a guid.')
            self.eq(exc.exception.get('valu'), 'newp')
            self.eq(exc.exception.get('name'), 'syn:role')

            with self.raises(s_exc.BadTypeValu) as exc:
                await core.callStorm('$lib.cast(syn:role, *)')
            self.eq(exc.exception.get('mesg'), 'syn:role values must be a valid rolename or a guid.')
            self.eq(exc.exception.get('valu'), '*')
            self.eq(exc.exception.get('name'), 'syn:role')

            # coverage for DataModel without a cortex reference
            iden = s_common.guid()

            model = core.model
            model.core = None

            synuser = model.type('syn:user')
            synrole = model.type('syn:user')

            self.eq(iden, synuser.repr(iden))
            self.eq(iden, synrole.repr(iden))

            self.eq(iden, (await synuser.norm(iden))[0])
            self.eq(iden, (await synrole.norm(iden))[0])

    async def test_synuser_merge_failure(self):
        async with self.getTestCore() as core:

            visi = await core.addUser('visi')

            async def populate(viewiden):
                q = '[proj:project=(p1,) :creator={[ syn:user=visi ]} ]'
                msgs = await core.stormlist(q, opts={'view': viewiden})
                self.stormHasNoWarnErr(msgs)

                q = 'proj:project=(p1,)'
                msgs = await core.stormlist(q, opts={'view': viewiden, 'repr': True})
                self.stormHasNoWarnErr(msgs)

            # populate two forks up-front so both have the syn:user reference
            # captured while visi still exists.
            forkiden = await core.callStorm('return($lib.view.get().fork().iden)')
            await populate(forkiden)

            forkiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            await populate(forkiden2)

            await core.delUser(visi.get('iden'))

            q = 'proj:project=(p1,)'
            msgs = await core.stormlist(q, opts={'view': forkiden, 'repr': True})
            self.stormHasNoWarnErr(msgs)

            # $lib.view.get().merge() schedules a background merge that
            # ends by removing the view; wait for it to finish.
            forkview = core.getView(forkiden)
            q = '$lib.view.get($view).merge()'
            msgs = await core.stormlist(q, opts={'vars': {'view': forkiden}})
            self.stormHasNoWarnErr(msgs)
            self.true(await forkview.waitfini(timeout=5))
            self.none(core.getView(forkiden))

            self.len(1, await core.nodes('proj:project=(p1,)'))

            # MergeCmd (merge --apply) is a separate, synchronous, pipeline
            # driven merge; verify it also handles the deleted-user case.
            q = 'proj:project | merge --apply'
            msgs = await core.stormlist(q, opts={'view': forkiden2, 'repr': True})
            self.stormHasNoWarnErr(msgs)

            self.len(1, await core.nodes('proj:project=(p1,)'))

    async def test_syn_tag(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[syn:tag=foo.bar.baz]')
            self.len(1, nodes)
            node = nodes[0]

            self.propeq(node, 'up', 'foo.bar')
            self.propeq(node, 'depth', 2)
            self.propeq(node, 'base', 'baz')

            nodes = await core.nodes('syn:tag=foo.bar')
            self.len(1, nodes)

            nodes = await core.nodes('syn:tag=foo')
            self.len(1, nodes)

    async def test_syn_model_runts(self):

        async def addExtModelConfigs(cortex):
            await cortex.addTagProp('_beep', ('int', {}), {'doc': 'words'})
            await cortex.addFormProp('test:str', '_twiddle', ('bool', {}), {'doc': 'hehe', 'computed': True})

        async def delExtModelConfigs(cortex):
            await cortex.delTagProp('_beep')
            await cortex.delFormProp('test:str', '_twiddle')

        async with self.getTestCore() as core:

            await addExtModelConfigs(core)

            # Ensure that we can lift by syn:type + prop + valu,
            # and expected props are present.
            nodes = await core.nodes('syn:type')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:type:ctor')
            self.gt(len(nodes), 1)

            self.len(0, await core.nodes('.created'))

            nodes = await core.nodes('syn:type=comp')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:type', 'comp'), node.ndef)
            self.none(node.get('parent'))
            self.propeq(node, 'opts', {'sepr': None, 'fields': ()})
            self.propeq(node, 'ctor', 'synapse.lib.types.Comp')
            self.propeq(node, 'doc', 'The base type for compound node fields.')

            nodes = await core.nodes('syn:type=test:comp')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:type', 'test:comp'), node.ndef)
            self.propeq(node, 'opts', {'fields': (('hehe', 'test:int'), ('haha', 'test:lower')), 'sepr': None})
            self.propeq(node, 'parent', 'comp')
            self.propeq(node, 'ctor', 'synapse.lib.types.Comp')
            self.propeq(node, 'doc', 'A fake comp type.')

            nodes = await core.nodes('syn:type:ctor="synapse.lib.types.Int"')
            self.gt(len(nodes), 1)

            # Ensure that we can lift by syn:form + prop + valu,
            # and expected props are present.
            nodes = await core.nodes('syn:form')
            self.none(nodes[0].get('.created'))
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:form:type')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:form=test:comp')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:form', 'test:comp'), node.ndef)
            self.nn(node.get('runt'))
            self.propeq(node, 'runt', False)
            self.propeq(node, 'type', 'test:comp')
            self.propeq(node, 'doc', 'A fake comp type.')
            # A form which implements no interfaces has no :interfaces value
            self.none(node.get('interfaces'))

            nodes = await core.nodes('syn:form=syn:form')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:form', 'syn:form'), node.ndef)
            self.true(node.get('runt'))
            self.propeq(node, 'type', 'syn:form')
            self.propeq(node, 'doc', 'A Synapse form used for representing nodes in the graph.')

            # A form exposes the fully resolved (direct + inherited) set of
            # interfaces it implements, deduplicated. meta:causal is inherited
            # by inet:flow via the base:activity interface.
            nodes = await core.nodes('syn:form=inet:flow')
            self.len(1, nodes)
            node = nodes[0]
            ifaces = [valu for (form, valu) in node.get('interfaces')]
            self.isin('meta:causal', ifaces)

            # We can lift / filter forms by an implemented interface
            nodes = await core.nodes('syn:form:interfaces*[=meta:causal]')
            self.isin('inet:flow', {n.ndef[1] for n in nodes})

            # We can even inspect which forms are runtime-online forms
            nodes = await core.nodes('syn:form:runt=1')
            self.ge(len(nodes), 3)
            pprops = {n.ndef[1] for n in nodes}
            self.true(pprops.issuperset({'syn:form', 'syn:prop', 'syn:type'}))

            # Ensure that we can lift by syn:prop + prop + valu
            # and expected props are present.
            nodes = await core.nodes('syn:prop')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:prop:computed')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:prop="test:type10:intprop"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:type10:intprop'), node.ndef)
            self.nn(node.get('computed'))
            self.propeq(node, 'computed', 0)
            self.propeq(node, 'type', ['test:int2030'])
            self.propeq(node, 'array', False)
            self.propeq(node, 'form', 'test:type10')
            self.propeq(node, 'doc', '')
            self.propeq(node, 'relname', 'intprop')
            self.propeq(node, 'base', 'intprop')
            self.propeq(node, 'extmodel', False)

            # Ensure that extmodel formprops are seen
            nodes = await core.nodes('syn:prop="test:str:_twiddle"')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'extmodel', True)

            # Array props expose array=True and list their element types.
            nodes = await core.nodes('syn:prop="meta:cluster:ids"')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'array', True)
            self.propeq(node, 'type', ['base:id'])

            # Interface-backed Poly array props expand to the implementing forms.
            nodes = await core.nodes('syn:prop="edu:class:assistants"')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'array', True)
            self.propeq(node, 'type', ['entity:contact', 'inet:service:account', 'ps:person'])

            # A deeper nested prop will have different base and relname values
            nodes = await core.nodes('syn:prop="inet:flow:server:host"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'inet:flow:server:host'), node.ndef)
            self.propeq(node, 'base', 'host')
            self.propeq(node, 'relname', 'server:host')

            # forms are also props but have some slightly different keys populated
            nodes = await core.nodes('syn:prop="test:type10"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:type10'), node.ndef)
            self.propeq(node, 'form', 'test:type10')

            self.none(node.get('computed'))
            self.none(node.get('base'))
            self.none(node.get('relname'))

            # Tag prop data is also represented
            nodes = await core.nodes('syn:tagprop=_beep')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:tagprop', '_beep'), node.ndef)
            self.propeq(node, 'doc', 'words')
            self.propeq(node, 'type', 'int')

            # Interfaces are represented as runt nodes
            nodes = await core.nodes('syn:interface')
            self.gt(len(nodes), 1)

            # An interface with no parent interfaces
            nodes = await core.nodes('syn:interface=meta:taxonomy')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:interface', 'meta:taxonomy'), node.ndef)
            self.propeq(node, 'doc', 'Properties common to taxonomies.')
            self.none(node.get('interfaces'))

            # An interface which inherits from another interface
            nodes = await core.nodes('syn:interface=base:event')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:interface', 'base:event'), node.ndef)
            self.propeq(node, 'doc', 'Properties common to an event.')
            self.propeq(node, 'interfaces', ('meta:causal',))

            # We can lift / filter by the interfaces array prop
            nodes = await core.nodes('syn:interface:interfaces')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:interface:interfaces*[=meta:causal]')
            self.eq({'base:activity', 'base:event'}, {n.ndef[1] for n in nodes})

            # A cmpr that isn't '='
            nodes = await core.nodes('syn:interface~="^meta:"')
            self.gt(len(nodes), 1)
            self.true(all(n.ndef[1].startswith('meta:') for n in nodes))

            # A nonexistent interface lifts nothing
            self.len(0, await core.nodes('syn:interface=newp:newp'))

            # Ensure that we can filter / pivot across the model nodes
            nodes = await core.nodes('syn:form=test:comp -> syn:prop:form')
            self.ge(len(nodes), 4)

            # implicit pivot works as well
            nodes = await core.nodes('syn:prop:form=test:comp -> syn:form | uniq')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('syn:form', 'test:comp'))

            # Go from a syn:type to a syn:form to a syn:prop with a filter
            q = 'syn:type:parent=comp +syn:type:doc~=".*fake.*" -> syn:form:type -> syn:prop:form'
            nodes = await core.nodes(q)
            self.ge(len(nodes), 4)

            # Wildcard pivot out from a prop and ensure we got the form
            q = 'syn:prop=test:comp -> * '
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq({('syn:form', 'test:comp'), ('syn:type', 'test:comp')},
                    {n.ndef for n in nodes})

            # Some forms inherit from a single type
            nodes = await core.nodes('syn:type="inet:sockaddr" -> syn:type:parent')
            self.ge(len(nodes), 2)
            pprops = {n.ndef[1] for n in nodes}
            self.isin('inet:server', pprops)
            self.isin('inet:client', pprops)

            # syn:form:parent is set when a form extends a parent form
            nodes = await core.nodes('syn:form=it:physical:host')
            self.len(1, nodes)
            self.propeq(nodes[0], 'parent', 'it:host')

            # forms which do not extend another form have no :parent
            nodes = await core.nodes('syn:form=test:str')
            self.len(1, nodes)
            self.none(nodes[0].get('parent'))

            # and we can pivot from a parent form to its children
            nodes = await core.nodes('syn:form=it:host -> syn:form:parent')
            self.isin('it:physical:host', {n.ndef[1] for n in nodes})

            # Test a cmpr that isn't '='
            nodes = await core.nodes('syn:form~="^test:type"')
            self.len(2, nodes)

            # More pivot coverage
            self.len(1, await core.nodes('syn:type=test:guid --> *'))

            nodes = await core.nodes('syn:type=test:guid')
            self.len(1, nodes)
            runt = nodes[0]
            self.len(0, [item async for item in runt.iterEdgesN1()])
            self.len(0, [item async for item in runt.iterEdgesN2()])
            self.len(0, [item async for item in runt.iterEdgeVerbs('newp')])
            self.none(runt.valuvirts())

            self.len(9, await core.nodes('syn:type=test:guid <- *'))
            self.len(9, await core.nodes('syn:type=test:guid <-- *'))

            self.len(8, await core.nodes('syn:prop=test:str:poly :type -> syn:type'))
            self.len(1, await core.nodes('syn:form=test:str :type -> syn:type'))

            # We can uniq runt nodes
            self.len(9, await core.nodes('syn:type=test:guid <-- * | uniq'))

            # Can't add an edge to a runt node
            await self.asyncraises(s_exc.IsRuntForm, nodes[0].addEdge('newp', 'newp'))

            q = core.nodes('syn:form [ +(newp)> { inet:ip } ]')
            await self.asyncraises(s_exc.IsRuntForm, q)

            q = core.nodes('[ test:str=foo +(newp)> { syn:form } ]')
            await self.asyncraises(s_exc.IsRuntForm, q)

            self.eq((), await core.callStorm('syn:form=inet:fqdn return($node.tags())'))

            # Ensure that delete a read-only runt prop fails, whether or not it exists.
            with self.raises(s_exc.IsRuntForm):
                await core.nodes('syn:form:doc [-:doc]')

            with self.raises(s_exc.IsRuntForm):
                await core.nodes('syn:type -:parent [-:ctor]')

            # # Ensure that adding tags on runt nodes fails
            with self.raises(s_exc.IsRuntForm):
                await core.nodes('syn:form [+#hehe]')

            with self.raises(s_exc.IsRuntForm):
                await core.nodes('syn:form [-#hehe]')

            # Ensure that adding / deleting runt nodes fails
            with self.raises(s_exc.IsRuntForm):
                await core.nodes('[syn:form=newp]')

            with self.raises(s_exc.IsRuntForm):
                await core.nodes('syn:form | delnode')

        # Ensure that the model runts are re-populated after a model load has occurred.
        with self.getTestDir() as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:

                # Lift nodes
                nodes = await core.nodes('syn:form=syn:tag')
                self.len(1, nodes)

                await core._addModelDefs(s_t_utils.testmodel)

                nodes = await core.nodes('syn:prop:form="test:str" +:extmodel=True')
                self.len(0, nodes)
                # 2 built-in tagprops (tlp, confidence) are always present
                nodes = await core.nodes('syn:tagprop')
                self.len(2, nodes)

                await addExtModelConfigs(core)

                nodes = await core.nodes('syn:prop:form="test:str" +:extmodel=True')
                self.len(1, nodes)
                # 2 built-in + 1 ext (_beep)
                nodes = await core.nodes('syn:tagprop')
                self.len(3, nodes)

                await delExtModelConfigs(core)

                nodes = await core.nodes('syn:prop:form="test:str" +:extmodel=True')
                self.len(0, nodes)
                # Back to 2 built-in only
                nodes = await core.nodes('syn:tagprop')
                self.len(2, nodes)

        async with self.getTestCore() as core:
                # Check we can iterate runt nodes while changing the underlying dictionary

                numforms = len(core.model.forms)

                q = '''
                init {
                    $forms = ()
                    $count = (0)
                }

                syn:form

                $forms.append(({'name': $node.repr(), 'doc': :doc }))

                $count = ($count + 1)

                if ($count = (2)) {
                    $info = ({"doc": "test taxonomy", "interfaces": [["meta:taxonomy", {}]]})
                    $lib.model.ext.addForm(_test:taxonomy, taxonomy, ({}), $info)
                }

                spin |

                fini { return($forms) }
                '''

                forms = await core.callStorm(q)
                self.len(numforms, forms)
                self.len(numforms + 1, core.model.forms)

                numtypes = len(core.model.types)
                q = '''
                init {
                    $types = ()
                    $count = (0)
                }

                syn:type

                $types.append(({'name': $node.repr(), 'doc': :doc }))

                $count = ($count + 1)

                if ($count = (2)) {
                    $typeopts = ({"lower": true, "onespace": true})
                    $typeinfo = ({"doc": "A test type doc."})
                    $lib.model.ext.addType(_test:type, str, $typeopts, $typeinfo)
                }

                spin |

                fini { return($types) }
                '''

                types = await core.callStorm(q)
                self.len(numtypes, types)
                self.len(numtypes + 1, core.model.types)

                q = '''
                init {
                    $tagprops = ()
                    $count = (0)
                    $lib.model.ext.addTagProp(_cypher, (str, ({})), ({}))
                    $lib.model.ext.addTagProp(_trinity, (str, ({})), ({}))
                    $lib.model.ext.addTagProp(_morpheus, (str, ({})), ({}))
                }

                syn:tagprop

                $tagprops.append(({'name': $node.repr(), 'doc': :doc }))

                $count = ($count + 1)

                if ($count = (2)) {
                    $lib.model.ext.addTagProp(_neo, (str, ({})), ({}))
                }

                spin |

                fini { return($tagprops) }
                '''

                tagprops = await core.callStorm(q)
                self.len(5, tagprops)
                self.len(6, core.model.tagprops)

    async def test_syn_cmd_runts(self):

        async with self.getTestDmon() as dmon:

            dmon.share('test', TestService())
            host, port = dmon.addr
            url = f'tcp://127.0.0.1:{port}/test'

            async with self.getTestCore() as core:
                nodes = await core.nodes('syn:cmd=help')
                self.len(1, nodes)

                self.eq(nodes[0].ndef, ('syn:cmd', 'help'))
                self.propeq(nodes[0], 'doc', 'List available information about Storm and'
                                             ' brief descriptions of different items.')

                self.none(nodes[0].get('package'))
                self.none(nodes[0].get('svciden'))

                nodes = await core.nodes('syn:cmd +:package')
                self.len(0, nodes)

                await core.nodes(f'service.add test {url}')
                iden = core.getStormSvcs()[0].iden

                await core.nodes('$lib.service.wait(test)')

                # check that runt nodes for new commands are created
                nodes = await core.nodes('syn:cmd +:package')
                self.len(5, nodes)

                self.eq(nodes[0].ndef, ('syn:cmd', 'foobar'))
                self.propeq(nodes[0], 'doc', 'foobar is a great service')
                self.propeq(nodes[0], 'package', 'foo')
                self.propeq(nodes[0], 'svciden', iden)
                self.none(nodes[0].get('deprecated'))

                self.eq(nodes[1].ndef, ('syn:cmd', 'ohhai'))
                self.propeq(nodes[1], 'doc', 'No description')
                self.propeq(nodes[1], 'package', 'foo')
                self.propeq(nodes[1], 'svciden', iden)
                self.none(nodes[1].get('deprecated'))

                self.eq(nodes[2].ndef, ('syn:cmd', 'deprvers'))
                self.true(nodes[2].get('deprecated'))
                self.propeq(nodes[2], 'deprecated:version', s_version.packVersion(3, 0, 0))
                self.none(nodes[2].get('deprecated:date'))
                self.none(nodes[2].get('deprecated:mesg'))

                self.eq(nodes[3].ndef, ('syn:cmd', 'deprdate'))
                self.true(nodes[3].get('deprecated'))
                self.none(nodes[3].get('deprecated:version'))
                self.propeq(nodes[3], 'deprecated:date', s_time.parse('2099-01-01'))
                self.none(nodes[3].get('deprecated:mesg'))

                self.eq(nodes[4].ndef, ('syn:cmd', 'deprmesg'))
                self.true(nodes[4].get('deprecated'))
                self.none(nodes[4].get('deprecated:version'))
                self.propeq(nodes[4], 'deprecated:date', s_time.parse('2099-01-01'))
                self.propeq(nodes[4], 'deprecated:mesg', 'Please use ``ohhai``.')

                nodes = await core.nodes('syn:cmd:deprecated')
                self.len(3, nodes)
                self.sorteq(['deprvers', 'deprdate', 'deprmesg'], [k.ndef[1] for k in nodes])

                nodes = await core.nodes('syn:cmd:deprecated:version')
                self.len(1, nodes)
                self.sorteq(['deprvers'], [k.ndef[1] for k in nodes])

                nodes = await core.nodes('syn:cmd:deprecated:date')
                self.len(2, nodes)
                self.sorteq(['deprdate', 'deprmesg'], [k.ndef[1] for k in nodes])

                nodes = await core.nodes('syn:cmd:deprecated:mesg')
                self.len(1, nodes)
                self.sorteq(['deprmesg'], [k.ndef[1] for k in nodes])

                # Test a cmpr that isn't '='
                nodes = await core.nodes('syn:cmd~="foo"')
                self.len(1, nodes)

                await core.nodes(f'service.del {iden}')

                # Check that runt nodes for the commands are gone
                nodes = await core.nodes('syn:cmd +:package')
                self.len(0, nodes)

        async with self.getTestCore() as core:
                # Check we can iterate runt nodes while changing the underlying dictionary

                numcmds = len(core.stormcmds)

                stormpkg = {
                    'name': 'stormpkg',
                    'version': '1.2.3',
                    'synapse_version': '>=3.0.0b2,<4.0.0',
                    'commands': (
                        {
                         'name': 'pkgcmd.old',
                         'storm': '$lib.print(hi)',
                        },
                    ),
                }

                q = '''
                init {
                    $cmds = ()
                    $count = (0)
                }

                syn:cmd

                $cmds.append(({'name': $node.repr(), 'doc': :doc }))

                $count = ($count + 1)

                if ($count = (2)) {
                    $lib.pkg.add($pkgdef)
                }

                spin |

                fini { return($cmds) }
                '''

                opts = {'vars': {'pkgdef': stormpkg}}
                cmds = await core.callStorm(q, opts=opts)
                self.len(numcmds, cmds)
                self.len(numcmds + 1, core.stormcmds)

    async def test_syn_deleted(self):

        async with self.getTestCore() as core:

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            await core.nodes('[ test:str=foo :seen=2020 (inet:ip=1.2.3.4 :asn=10) ]')
            await core.nodes('test:str=foo inet:ip=1.2.3.4 delnode', opts=viewopts2)

            nodes = await core.nodes('diff', opts=viewopts2)
            self.len(2, nodes)
            for node in nodes:
                self.eq('syn:deleted', node.ndef[0])

            nodes = await core.nodes('diff | +syn:deleted:form=inet:ip', opts=viewopts2)
            self.len(1, nodes)
            for node in nodes:
                self.eq('syn:deleted', node.ndef[0])
                self.eq('inet:ip', node.ndef[1][0])
                self.eq(('inet:ip', (4, 16909060)), node.valu())
                self.gt(node.intnid(), 0)
                self.propeq(node, 'nid', node.intnid())
                sodes = node.get('sodes')[1]
                self.len(2, sodes)
                self.true(sodes[0]['antivalu'])
                self.eq('inet:ip', sodes[0]['form'])
                self.nn(sodes[0]['meta']['updated'])
                self.eq((('inet:asn', 10), 16393, None), sodes[1]['props']['asn'])

            q = 'diff | +syn:deleted:form=inet:ip return($node.getStorNodes())'
            self.eq((), await core.callStorm(q, opts=viewopts2))

            q = 'diff | +syn:deleted:form=inet:ip return($node.getByLayer())'
            self.eq({}, await core.callStorm(q, opts=viewopts2))

            await core.nodes('diff | merge --apply', opts=viewopts2)

            self.len(0, await core.nodes('test:str=foo inet:ip=1.2.3.4'))
            self.len(0, await core.nodes('diff', opts=viewopts2))

            with self.raises(s_exc.BadArg):
                await view2.getDeletedRuntNode(s_common.int64en(9001))

            await core.nodes('[ test:str=bar ]')
            await core.nodes('test:str=bar delnode', opts=viewopts2)

            q1 = '''
            $q1=$lib.queue.gen(q1)
            $q2=$lib.queue.gen(q2)
            diff |
            $q1.put(1)
            $q2.get()
            merge
            '''
            task = core.schedCoro(core.nodes(q1, opts=viewopts2))

            q2 = '''
            $q1=$lib.queue.gen(q1)
            $q2=$lib.queue.gen(q2)
            $q1.get()
            diff | merge --apply |
            $q2.put(2)
            '''
            await core.nodes(q2, opts=viewopts2)
            await task
