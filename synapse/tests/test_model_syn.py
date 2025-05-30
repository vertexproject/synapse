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
            'synapse_version': '>=2.8.0,<3.0.0',
            'commands': (
                {
                    'name': 'foobar',
                    'descr': 'foobar is a great service',
                    'forms': {
                        'input': [
                            'inet:ipv4',
                            'inet:ipv6',
                        ],
                        'output': [
                            'inet:fqdn',
                        ],
                        'nodedata': [
                            ('foo', 'inet:ipv4'),
                            ('bar', 'inet:fqdn'),
                        ],
                    },
                    'storm': '',
                },
                {
                    'name': 'ohhai',
                    'forms': {
                        'output': [
                            'inet:ipv4',
                        ],
                    },
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

            with self.raises(s_exc.BadTypeValu) as exc:
                await core.callStorm('return($lib.cast(syn:user, newp))')
            self.eq(exc.exception.get('mesg'), 'No user named newp and value is not a guid.')
            self.eq(exc.exception.get('valu'), 'newp')
            self.eq(exc.exception.get('name'), 'syn:user')

            with self.raises(s_exc.BadTypeValu) as exc:
                await core.callStorm('[ it:exec:query=* :synuser=* ]')
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

            self.eq(iden, synuser.norm(iden)[0])
            self.eq(iden, synrole.norm(iden)[0])

    async def test_synuser_merge_failure(self):
        async with self.getTestCore() as core:

            visi = await core.addUser('visi')
            view = await core.callStorm('return($lib.view.get().fork().iden)')

            q = '[proj:project=(p1,) :creator=visi ]'
            msgs = await core.stormlist(q, opts={'view': view})
            self.stormHasNoWarnErr(msgs)

            q = 'proj:project=(p1,)'
            msgs = await core.stormlist(q, opts={'view': view, 'repr': True})
            self.stormHasNoWarnErr(msgs)

            await core.delUser(visi.get('iden'))

            q = 'proj:project=(p1,)'
            msgs = await core.stormlist(q, opts={'view': view, 'repr': True})
            self.stormHasNoWarnErr(msgs)

            # this works
            q = '$lib.view.get($view).merge()'
            msgs = await core.stormlist(q, opts={'vars': {'view': view}})
            self.stormHasNoWarnErr(msgs)

            # this fails
            q = 'proj:project | merge --apply'
            msgs = await core.stormlist(q, opts={'view': view, 'repr': True})
            self.stormHasNoWarnErr(msgs)

            q = 'proj:project=(p1,)'
            msgs = await core.stormlist(q, opts={'vars': {'view': view}})
            self.stormHasNoWarnErr(msgs)

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
            nodes = await core.nodes('syn:prop="test:edge:n1:form"')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:edge:n1:form'), node.ndef)
            self.eq('form', node.get('base'))
            self.eq('n1:form', node.get('relname'))

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
            nodes = await core.nodes('syn:type="inet:addr" -> syn:type:subof')
            self.ge(len(nodes), 2)
            pprops = {n.ndef[1] for n in nodes}
            self.isin('inet:server', pprops)
            self.isin('inet:client', pprops)

            # Pivot from a model node to a Edge node
            await core.nodes('[(test:edge=( ("test:int", (1234)), ("test:str", 1234) ))]')

            nodes = await core.nodes('syn:form=test:int -> test:edge:n1:form')
            self.len(1, nodes)
            self.eq('test:edge', nodes[0].ndef[0])

            # Test a cmpr that isn't '='
            nodes = await core.nodes('syn:form~="test:type"')
            self.len(2, nodes)

            # Can't add an edge to a runt node
            await self.asyncraises(s_exc.IsRuntForm, nodes[0].addEdge('newp', 'newp'))

            q = core.nodes('syn:form [ +(newp)> { inet:ipv4 } ]')
            await self.asyncraises(s_exc.IsRuntForm, q)

            q = core.nodes('test:str [ +(newp)> { syn:form } ]')
            await self.asyncraises(s_exc.IsRuntForm, q)

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

    async def test_syn_trigger_runts(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('syn:trigger')
            self.len(0, nodes)

            tdef = {'cond': 'node:add', 'form': 'inet:ipv4', 'storm': '[inet:user=1] | testcmd'}
            await core.view.addTrigger(tdef)

            triggers = core.view.triggers.list()
            iden = triggers[0][0]
            self.len(1, triggers)

            nodes = await core.nodes('syn:trigger')
            self.len(1, nodes)
            pode = nodes[0].pack()
            self.eq(pode[0][1], iden)

            # lift by iden
            nodes = await core.nodes(f'syn:trigger={iden}')
            self.len(1, nodes)

            indx = await core.getNexsIndx()

            # set the trigger doc
            nodes = await core.nodes(f'syn:trigger={iden} [ :doc=hehe ]')
            self.len(1, nodes)
            self.eq('hehe', nodes[0].get('doc'))

            self.eq(await core.getNexsIndx(), indx + 1)

            # set the trigger name
            nodes = await core.nodes(f'syn:trigger={iden} [ :name=trigname ]')
            self.len(1, nodes)
            self.eq('trigname', nodes[0].get('name'))

            self.eq(await core.getNexsIndx(), indx + 2)

            # Trigger reloads and make some more triggers to play with
            tdef = {'cond': 'prop:set', 'prop': 'inet:ipv4:asn', 'storm': '[inet:user=1] | testcmd'}
            await core.view.addTrigger(tdef)
            tdef = {'cond': 'tag:add', 'tag': 'hehe.haha', 'storm': '[inet:user=1] | testcmd'}
            await core.view.addTrigger(tdef)

            # lift by all props and valus
            nodes = await core.nodes('syn:trigger')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:doc')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:vers')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:cond')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:user')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:storm')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:enabled')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:form')
            self.len(1, nodes)
            nodes = await core.nodes('syn:trigger:prop')
            self.len(1, nodes)
            nodes = await core.nodes('syn:trigger:tag')
            self.len(1, nodes)

            nodes = await core.nodes('syn:trigger:vers=1')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:cond=node:add')
            self.len(1, nodes)

            root = await core.auth.getUserByName('root')

            nodes = await core.nodes(f'syn:trigger:user={root.iden}')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:storm="[inet:user=1] | testcmd"')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:enabled=True')
            self.len(3, nodes)
            nodes = await core.nodes('syn:trigger:form=inet:ipv4')
            self.len(1, nodes)
            nodes = await core.nodes('syn:trigger:prop=inet:ipv4:asn')
            self.len(1, nodes)
            nodes = await core.nodes('syn:trigger:tag=hehe.haha')
            self.len(1, nodes)
            nodes = await core.nodes('syn:trigger:storm~="inet:user"')
            self.len(3, nodes)

            # lift triggers for a different view
            forkview = await core.callStorm('return($lib.view.get().fork().iden)')

            tdef = {'cond': 'node:add', 'form': 'inet:ipv4', 'storm': '[inet:user=1] | testcmd'}
            view = core.getView(forkview)
            await view.addTrigger(tdef)

            triggers = view.triggers.list()
            iden = triggers[0][0]
            self.len(1, triggers)

            nodes = await core.nodes('syn:trigger', opts={'view': forkview})
            self.len(1, nodes)
            pode = nodes[0].pack()
            self.eq(pode[0][1], iden)

        async with self.getTestCore() as core:
                # Check we can iterate runt nodes while changing the underlying dictionary

                tdef = {'cond': 'node:add', 'form': 'it:dev:str', 'storm': '[inet:user=1] | testcmd'}
                await core.view.addTrigger(tdef)

                tdef = {'cond': 'node:add', 'form': 'it:dev:str', 'storm': '[inet:user=2] | testcmd'}
                await core.view.addTrigger(tdef)

                q = '''
                init {
                    $trigs = ()
                    $count = (0)
                }

                syn:trigger

                $trigs.append(({'name': $node.repr(), 'doc': :doc }))

                $count = ($count + 1)

                if ($count = (2)) {
                    $lib.trigger.add($tdef)
                }

                spin |

                fini { return($trigs) }
                '''

                tdef = {'cond': 'node:add', 'form': 'it:dev:str', 'storm': '[inet:user=3] | testcmd'}
                opts = {'vars': {'tdef': tdef}}
                triggers = await core.callStorm(q, opts=opts)
                self.len(2, triggers)
                self.len(3, core.view.triggers.triggers)

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

                self.none(nodes[0].get('input'))
                self.none(nodes[0].get('output'))
                self.none(nodes[0].get('package'))
                self.none(nodes[0].get('svciden'))

                nodes = await core.nodes('syn:cmd +:package')
                self.len(0, nodes)

                with self.getLoggerStream('synapse.cortex') as stream:
                    await core.nodes(f'service.add test {url}')
                    iden = core.getStormSvcs()[0].iden

                    await core.nodes('$lib.service.wait(test)')

                stream.seek(0)
                warn = "Storm command definition 'forms' key is deprecated and will be removed " \
                       "in 3.0.0 (command foobar in package foo)"
                self.isin(warn, stream.read())

                # check that runt nodes for new commands are created
                nodes = await core.nodes('syn:cmd +:package')
                self.len(2, nodes)

                self.eq(nodes[0].ndef, ('syn:cmd', 'foobar'))
                self.eq(nodes[0].get('doc'), 'foobar is a great service')
                self.eq(nodes[0].get('input'), ('inet:ipv4', 'inet:ipv6'))
                self.eq(nodes[0].get('output'), ('inet:fqdn',))
                self.eq(nodes[0].get('nodedata'), (('foo', 'inet:ipv4'), ('bar', 'inet:fqdn')))
                self.eq(nodes[0].get('package'), 'foo')
                self.eq(nodes[0].get('svciden'), iden)

                self.eq(nodes[1].ndef, ('syn:cmd', 'ohhai'))
                self.eq(nodes[1].get('doc'), 'No description')
                self.none(nodes[1].get('input'))
                self.eq(nodes[1].get('output'), ('inet:ipv4',))
                self.none(nodes[1].get('nodedata'))
                self.eq(nodes[1].get('package'), 'foo')
                self.eq(nodes[1].get('svciden'), iden)

                # Pivot from cmds to their forms
                nodes = await core.nodes('syn:cmd=foobar -> *')
                self.len(3, nodes)
                self.eq({('syn:form', 'inet:ipv4'), ('syn:form', 'inet:ipv6'), ('syn:form', 'inet:fqdn')},
                        {n.ndef for n in nodes})
                nodes = await core.nodes('syn:cmd=foobar :input -> *')
                self.len(2, nodes)
                self.eq({('syn:form', 'inet:ipv4'), ('syn:form', 'inet:ipv6')},
                        {n.ndef for n in nodes})
                nodes = await core.nodes('syn:cmd=foobar :output -> *')
                self.len(1, nodes)
                self.eq(('syn:form', 'inet:fqdn'), nodes[0].ndef)

                nodes = await core.nodes('syn:cmd=foobar :input -+> *')
                self.len(3, nodes)
                self.eq({('syn:form', 'inet:ipv4'), ('syn:form', 'inet:ipv6'), ('syn:cmd', 'foobar')},
                        {n.ndef for n in nodes})

                nodes = await core.nodes('syn:cmd +:input*[=inet:ipv4]')
                self.len(1, nodes)

                # Test a cmpr that isn't '='
                nodes = await core.nodes('syn:cmd~="foo"')
                self.len(1, nodes)

                await core.nodes(f'service.del {iden}')

                # Check that runt nodes for the commands are gone
                nodes = await core.nodes('syn:cmd +:package')
                self.len(0, nodes)

                # Check that testcmd sets form props
                nodes = await core.nodes('syn:cmd=testcmd')
                self.len(1, nodes)

                self.eq(nodes[0].ndef, ('syn:cmd', 'testcmd'))
                self.eq(nodes[0].get('input'), ('test:str', 'inet:ipv6'))
                self.eq(nodes[0].get('output'), ('inet:fqdn',))
                self.eq(nodes[0].get('nodedata'), (('foo', 'inet:ipv4'), ('bar', 'inet:fqdn')))

        async with self.getTestCore() as core:
                # Check we can iterate runt nodes while changing the underlying dictionary

                numcmds = len(core.stormcmds)

                stormpkg = {
                    'name': 'stormpkg',
                    'version': '1.2.3',
                    'synapse_version': '>=2.8.0,<3.0.0',
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

    async def test_syn_cron_runts(self):

        async with self.getTestCore() as core:

            visi = await core.addUser('visi')

            cdef = {'storm': 'inet:ipv4', 'reqs': {'hour': 2}, 'creator': visi.get('iden')}
            adef = await core.addCronJob(cdef)
            iden = adef.get('iden')

            nodes = await core.nodes('syn:cron')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('syn:cron', iden))
            self.eq(nodes[0].get('doc'), '')
            self.eq(nodes[0].get('name'), '')
            self.eq(nodes[0].get('storm'), 'inet:ipv4')

            nodes = await core.nodes(f'syn:cron={iden} [ :doc=hehe :name=haha ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('syn:cron', iden))
            self.eq(nodes[0].get('doc'), 'hehe')
            self.eq(nodes[0].get('name'), 'haha')

            nodes = await core.nodes(f'syn:cron={iden}')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('syn:cron', iden))
            self.eq(nodes[0].get('doc'), 'hehe')
            self.eq(nodes[0].get('name'), 'haha')

        async with self.getTestCore() as core:
                # Check we can iterate runt nodes while changing the underlying dictionary

                q = '''
                init {
                    $appts = ()
                    $count = (0)

                    cron.add --hour 1 --day 1 {#foo} |
                    cron.add --hour 2 --day 1 {#foo} |
                    cron.add --hour 3 --day 1 {#foo}
                }

                syn:cron

                $appts.append(({'name': $node.repr(), 'doc': :doc }))

                $count = ($count + 1)

                if ($count = (2)) {
                    cron.add  --hour 4 --day 1 {#foo}
                }

                spin |

                fini { return($appts) }
                '''

                appts = await core.callStorm(q)
                self.len(3, appts)
                self.len(4, core.agenda.appts)
