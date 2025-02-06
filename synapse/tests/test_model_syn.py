import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.datamodel as s_datamodel

import synapse.lib.stormsvc as s_stormsvc

import synapse.tests.utils as s_t_utils

class TestService(s_stormsvc.StormSvc):
    _storm_svc_name = 'test'
    _storm_svc_pkgs = (
        {
            'name': 'foo',
            'version': (0, 0, 1),
            'synapse_version': '>=3.0.0,<4.0.0',
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

            (ok, iden) = await core.callStorm('return($lib.trycast(syn:role, all))')
            self.true(ok)
            self.eq(iden, core.auth.allrole.iden)

            # coverage for iden taking precedence
            (ok, iden) = await core.callStorm(f'return($lib.trycast(syn:role, {iden}))')
            self.true(ok)
            self.eq(iden, core.auth.allrole.iden)

            self.eq('all', await core.callStorm(f'return($lib.repr(syn:role, {iden}))'))

            # coverage for DataModel without a cortex reference
            iden = s_common.guid()

            model = core.model
            model.core = None

            synuser = model.type('syn:user')
            synrole = model.type('syn:user')

            self.eq(iden, synuser.repr(iden))
            self.eq(iden, synrole.repr(iden))

            self.eq(iden, synuser.norm(iden)[0])
            self.eq(iden, synrole.norm(iden)[0])

    async def test_syn_tag(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[syn:tag=foo.bar.baz]')
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.get('up'), 'foo.bar')
            self.eq(node.get('depth'), 2)
            self.eq(node.get('base'), 'baz')

            nodes = await core.nodes('syn:tag=foo.bar')
            self.len(1, nodes)

            nodes = await core.nodes('syn:tag=foo')
            self.len(1, nodes)

    async def test_syn_model_runts(self):

        async def addExtModelConfigs(cortex):
            await cortex.addTagProp('beep', ('int', {}), {'doc': 'words'})
            await cortex.addFormProp('test:str', '_twiddle', ('bool', {}), {'doc': 'hehe', 'ro': True})
            await cortex.addUnivProp('_sneaky', ('bool', {}), {'doc': 'Note if a node is sneaky.'})

        async def delExtModelConfigs(cortex):
            await cortex.delTagProp('beep')
            await cortex.delFormProp('test:str', '_twiddle')
            await cortex.delUnivProp('_sneaky')

        async with self.getTestCore() as core:

            await addExtModelConfigs(core)

            # Ensure that we can lift by syn:type + prop + valu,
            # and expected props are present.
            nodes = await core.nodes('syn:type')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:type:ctor')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:type=comp')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:type', 'comp'), node.ndef)
            self.none(node.get('subof'))
            self.none(node.get('opts'))
            self.eq('synapse.lib.types.Comp', node.get('ctor'))
            self.eq('The base type for compound node fields.', node.get('doc'))

            nodes = await core.nodes('syn:type=test:comp')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:type', 'test:comp'), node.ndef)
            self.eq({'fields': (('hehe', 'test:int'), ('haha', 'test:lower'))},
                    node.get('opts'))
            self.eq('comp', node.get('subof'))
            self.eq('synapse.lib.types.Comp', node.get('ctor'))
            self.eq('A fake comp type.', node.get('doc'))

            nodes = await core.nodes('syn:type:ctor="synapse.lib.types.Int"')
            self.gt(len(nodes), 1)

            # Ensure that we can lift by syn:form + prop + valu,
            # and expected props are present.
            nodes = await core.nodes('syn:form')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:form:type')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:form=test:comp')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:form', 'test:comp'), node.ndef)
            self.nn(node.get('runt'))
            self.false(node.get('runt'))
            self.eq('test:comp', node.get('type'))
            self.eq('A fake comp type.', node.get('doc'))

            nodes = await core.nodes('syn:form=syn:form')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:form', 'syn:form'), node.ndef)
            self.true(node.get('runt'))
            self.eq('syn:form', node.get('type'))
            self.eq('A Synapse form used for representing nodes in the graph.',
                    node.get('doc'))

            # We can even inspect which forms are runtime-online forms
            nodes = await core.nodes('syn:form:runt=1')
            self.ge(len(nodes), 3)
            pprops = {n.ndef[1] for n in nodes}
            self.true(pprops.issuperset({'syn:form', 'syn:prop', 'syn:type'}))

            # Ensure that we can lift by syn:prop + prop + valu
            # and expected props are present.
            nodes = await core.nodes('syn:prop')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:prop:ro')
            self.gt(len(nodes), 1)

            nodes = await core.nodes('syn:prop="test:type10:intprop"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:type10:intprop'), node.ndef)
            self.nn(node.get('ro'))
            self.false(node.get('ro'))
            self.nn(node.get('univ'))
            self.false(node.get('univ'))
            self.eq('int', node.get('type'))
            self.eq('test:type10', node.get('form'))
            self.eq('', node.get('doc'))
            self.eq('intprop', node.get('relname'))
            self.eq('intprop', node.get('base'))
            self.false(node.get('extmodel'))

            # Ensure that extmodel formprops are seen
            nodes = await core.nodes('syn:prop="test:str:_twiddle"')
            self.len(1, nodes)
            node = nodes[0]
            self.true(node.get('extmodel'))

            # A deeper nested prop will have different base and relname values
            nodes = await core.nodes('syn:prop="inet:flow:dst:host"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'inet:flow:dst:host'), node.ndef)
            self.eq('host', node.get('base'))
            self.eq('dst:host', node.get('relname'))

            # forms are also props but have some slightly different keys populated
            nodes = await core.nodes('syn:prop="test:type10"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:type10'), node.ndef)
            self.eq('test:type10', node.get('form'))

            self.none(node.get('ro'))
            self.none(node.get('base'))
            self.none(node.get('relname'))

            # Including universal props
            nodes = await core.nodes('syn:prop=".created"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', '.created'), node.ndef)
            self.true(node.get('univ'))
            self.false(node.get('extmodel'))

            nodes = await core.nodes('syn:prop="test:comp.created"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:comp.created'), node.ndef)

            # Bound universal props don't actually show up as univ
            self.false(node.get('univ'))

            nodes = await core.nodes('syn:prop:univ=1')
            self.ge(len(nodes), 2)

            # extmodel univs are represented
            nodes = await core.nodes('syn:prop="._sneaky"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', '._sneaky'), node.ndef)
            self.true(node.get('univ'))
            self.true(node.get('extmodel'))

            nodes = await core.nodes('syn:prop="test:comp._sneaky"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:comp._sneaky'), node.ndef)
            self.true(node.get('extmodel'))

            # Bound universal props don't actually show up as univ
            self.false(node.get('univ'))

            # Tag prop data is also represented
            nodes = await core.nodes('syn:tagprop=beep')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:tagprop', 'beep'), node.ndef)
            self.eq(node.get('doc'), 'words')
            self.eq(node.get('type'), 'int')

            # Ensure that we can filter / pivot across the model nodes
            nodes = await core.nodes('syn:form=test:comp -> syn:prop:form')
            # form is a prop, two universal properties (+2 test univ) and two model secondary properties.
            self.ge(len(nodes), 7)

            # implicit pivot works as well
            nodes = await core.nodes('syn:prop:form=test:comp -> syn:form | uniq')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('syn:form', 'test:comp'))

            # Go from a syn:type to a syn:form to a syn:prop with a filter
            q = 'syn:type:subof=comp +syn:type:doc~=".*fake.*" -> syn:form:type -> syn:prop:form'
            nodes = await core.nodes(q)
            self.ge(len(nodes), 7)

            # Wildcard pivot out from a prop and ensure we got the form
            q = 'syn:prop=test:comp -> * '
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq({('syn:form', 'test:comp'), ('syn:type', 'test:comp')},
                    {n.ndef for n in nodes})

            # Some forms inherit from a single type
            nodes = await core.nodes('syn:type="inet:sockaddr" -> syn:type:subof')
            self.ge(len(nodes), 2)
            pprops = {n.ndef[1] for n in nodes}
            self.isin('inet:server', pprops)
            self.isin('inet:client', pprops)

            # Test a cmpr that isn't '='
            nodes = await core.nodes('syn:form~="^test:type"')
            self.len(2, nodes)

            # Can't add an edge to a runt node
            await self.asyncraises(s_exc.IsRuntForm, nodes[0].addEdge('newp', 'newp'))

            q = core.nodes('syn:form [ +(newp)> { inet:ip } ]')
            await self.asyncraises(s_exc.IsRuntForm, q)

            q = core.nodes('[ test:str=foo +(newp)> { syn:form } ]')
            await self.asyncraises(s_exc.IsRuntForm, q)

            self.eq((), await core.callStorm('syn:form=inet:fqdn return($node.tags())'))

        # Ensure that the model runts are re-populated after a model load has occurred.
        with self.getTestDir() as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:

                # Lift nodes
                nodes = await core.nodes('syn:form=syn:tag')
                self.len(1, nodes)

                nodes = await core.nodes('syn:form=test:runt')
                self.len(0, nodes)

                await core.loadCoreModule('synapse.tests.utils.TestModule')

                nodes = await core.nodes('syn:form=test:runt')
                self.len(1, nodes)

                nodes = await core.nodes('syn:prop:form="test:str" +:extmodel=True')
                self.len(0, nodes)
                nodes = await core.nodes('syn:tagprop')
                self.len(0, nodes)

                await addExtModelConfigs(core)

                nodes = await core.nodes('syn:prop:form="test:str" +:extmodel=True')
                self.len(2, nodes)
                nodes = await core.nodes('syn:tagprop')
                self.len(1, nodes)

                await delExtModelConfigs(core)

                nodes = await core.nodes('syn:prop:form="test:str" +:extmodel=True')
                self.len(0, nodes)
                nodes = await core.nodes('syn:tagprop')
                self.len(0, nodes)

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
                    $info = ({"doc": "test taxonomy", "interfaces": ["meta:taxonomy"]})
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
                    $lib.model.ext.addTagProp(cypher, (str, ({})), ({}))
                    $lib.model.ext.addTagProp(trinity, (str, ({})), ({}))
                    $lib.model.ext.addTagProp(morpheus, (str, ({})), ({}))
                }

                syn:tagprop

                $tagprops.append(({'name': $node.repr(), 'doc': :doc }))

                $count = ($count + 1)

                if ($count = (2)) {
                    $lib.model.ext.addTagProp(neo, (str, ({})), ({}))
                }

                spin |

                fini { return($tagprops) }
                '''

                tagprops = await core.callStorm(q)
                self.len(3, tagprops)
                self.len(4, core.model.tagprops)

    async def test_syn_cmd_runts(self):

        async with self.getTestDmon() as dmon:

            dmon.share('test', TestService())
            host, port = dmon.addr
            url = f'tcp://127.0.0.1:{port}/test'

            async with self.getTestCore() as core:
                nodes = await core.nodes('syn:cmd=help')
                self.len(1, nodes)

                self.eq(nodes[0].ndef, ('syn:cmd', 'help'))
                self.eq(nodes[0].get('doc'), 'List available information about Storm and'
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
                self.len(2, nodes)

                self.eq(nodes[0].ndef, ('syn:cmd', 'foobar'))
                self.eq(nodes[0].get('doc'), 'foobar is a great service')
                self.eq(nodes[0].get('package'), 'foo')
                self.eq(nodes[0].get('svciden'), iden)

                self.eq(nodes[1].ndef, ('syn:cmd', 'ohhai'))
                self.eq(nodes[1].get('doc'), 'No description')
                self.eq(nodes[1].get('package'), 'foo')
                self.eq(nodes[1].get('svciden'), iden)

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
                    'synapse_version': '>=3.0.0,<4.0.0',
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

            await core.nodes('[ it:dev:str=foo .seen=2020 (inet:ip=1.2.3.4 :asn=10) ]')
            await core.nodes('it:dev:str=foo inet:ip=1.2.3.4 delnode', opts=viewopts2)

            nodes = await core.nodes('diff', opts=viewopts2)
            self.len(2, nodes)
            for node in nodes:
                self.eq('syn:deleted', node.ndef[0])

            nodes = await core.nodes('diff | +syn:deleted*form=inet:ip', opts=viewopts2)
            self.len(1, nodes)
            for node in nodes:
                self.eq('syn:deleted', node.ndef[0])
                self.eq('inet:ip', node.ndef[1][0])
                self.eq(('inet:ip', (4, 16909060)), node.valu())
                self.gt(node.intnid(), 0)
                sodes = node.get('sodes')
                self.len(2, sodes)
                self.eq({'antivalu': True, 'form': 'inet:ip'}, sodes[0])
                self.eq((10, 9, None), sodes[1]['props']['asn'])

            q = 'diff | +syn:deleted*form=inet:ip return($node.getStorNodes())'
            self.eq((), await core.callStorm(q, opts=viewopts2))

            q = 'diff | +syn:deleted*form=inet:ip return($node.getByLayer())'
            self.eq({}, await core.callStorm(q, opts=viewopts2))

            await core.nodes('diff | merge --apply', opts=viewopts2)

            self.len(0, await core.nodes('it:dev:str=foo inet:ip=1.2.3.4'))
            self.len(0, await core.nodes('diff', opts=viewopts2))

            with self.raises(s_exc.BadArg):
                await view2.getDeletedRuntNode(s_common.int64en(9001))

            await core.nodes('[ it:dev:str=bar ]')
            await core.nodes('it:dev:str=bar delnode', opts=viewopts2)

            task = core.schedCoro(core.nodes('$q=$lib.queue.gen(wait) diff | $q.put(1) $q.get(1) | merge', opts=viewopts2))
            await core.nodes('$q=$lib.queue.gen(wait) $q.get() diff | merge --apply | $q.put(2)', opts=viewopts2)
            await task
