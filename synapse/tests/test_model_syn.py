import synapse.exc as s_exc
import synapse.cortex as s_cortex

import synapse.lib.stormsvc as s_stormsvc

import synapse.tests.utils as s_t_utils

class TestService(s_stormsvc.StormSvc):
    _storm_svc_name = 'test'
    _storm_svc_pkgs = (
        {
            'name': 'foo',
            'version': (0, 0, 1),
            'synapse_minversion': (2, 8, 0),
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

    async def test_syn_tag(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('syn:tag', 'foo.bar.baz')

                self.eq(node.get('up'), 'foo.bar')
                self.eq(node.get('depth'), 2)
                self.eq(node.get('base'), 'baz')

                node = await snap.getNodeByNdef(('syn:tag', 'foo.bar'))
                self.nn(node)

                node = await snap.getNodeByNdef(('syn:tag', 'foo'))
                self.nn(node)

            # We can safely do a pivot in from a syn:tag node
            # which will attempt a syn:splice lift which will
            # yield no nodes.
            self.len(0, await core.nodes('syn:tag=foo.bar.baz <- *'))
            nodes = await core.nodes('syn:tag=foo.bar.baz [ :doc:url="http://vertex.link" ]')
            self.eq('http://vertex.link', nodes[0].get('doc:url'))

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
            async with await core.snap() as snap:
                node = await snap.addNode('test:edge', (('test:int', 1234), ('test:str', '1234')))

            nodes = await core.nodes('syn:form=test:int -> test:edge:n1:form')
            self.len(1, nodes)
            self.eq('test:edge', nodes[0].ndef[0])

            # Test a cmpr that isn't '='
            nodes = await core.nodes('syn:form~="test:type"')
            self.len(2, nodes)

            # Syn:splice uses a null lift handler
            self.len(1, await core.nodes('[test:str=test]'))
            self.len(0, await core.nodes('syn:splice'))
            self.len(0, await core.nodes('syn:splice:tag'))

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

            # set the trigger doc
            nodes = await core.nodes(f'syn:trigger={iden} [ :doc=hehe ]')
            self.len(1, nodes)
            self.eq('hehe', nodes[0].get('doc'))

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

    async def test_syn_cmd_runts(self):

        async with self.getTestDmon() as dmon:

            dmon.share('test', TestService())
            host, port = dmon.addr
            url = f'tcp://127.0.0.1:{port}/test'

            async with self.getTestCore() as core:
                nodes = await core.nodes('syn:cmd=help')
                self.len(1, nodes)

                self.eq(nodes[0].ndef, ('syn:cmd', 'help'))
                self.eq(nodes[0].get('doc'), 'List available commands and '
                                             'a brief description for each.')

                self.none(nodes[0].get('input'))
                self.none(nodes[0].get('output'))
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

    async def test_syn_cron_runts(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('cron', 'add')))

            async with core.getLocalProxy(user='visi') as proxy:
                cdef = {'storm': 'inet:ipv4', 'reqs': {'hour': 2}}
                adef = await proxy.addCronJob(cdef)
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
