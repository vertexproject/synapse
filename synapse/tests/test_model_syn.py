import synapse.exc as s_exc
import synapse.cortex as s_cortex

import synapse.tests.utils as s_t_utils

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
            nodes = await core.eval('syn:type').list()
            self.gt(len(nodes), 1)

            nodes = await core.eval('syn:type:ctor').list()
            self.gt(len(nodes), 1)

            nodes = await core.eval('syn:type=comp').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:type', 'comp'), node.ndef)
            self.none(node.get('subof'))
            self.none(node.get('opts'))
            self.eq('synapse.lib.types.Comp', node.get('ctor'))
            self.eq('The base type for compound node fields.', node.get('doc'))

            nodes = await core.eval('syn:type=test:comp').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:type', 'test:comp'), node.ndef)
            self.eq({'fields': (('hehe', 'test:int'), ('haha', 'test:lower'))},
                    node.get('opts'))
            self.eq('comp', node.get('subof'))
            self.eq('synapse.lib.types.Comp', node.get('ctor'))
            self.eq('A fake comp type.', node.get('doc'))

            nodes = await core.eval('syn:type:ctor="synapse.lib.types.Int"').list()
            self.gt(len(nodes), 1)

            # Ensure that we can lift by syn:form + prop + valu,
            # and expected props are present.
            nodes = await core.eval('syn:form').list()
            self.gt(len(nodes), 1)

            nodes = await core.eval('syn:form:type').list()
            self.gt(len(nodes), 1)

            nodes = await core.eval('syn:form=test:comp').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:form', 'test:comp'), node.ndef)
            self.nn(node.get('runt'))
            self.false(node.get('runt'))
            self.eq('test:comp', node.get('type'))
            self.eq('A fake comp type.', node.get('doc'))

            nodes = await core.eval('syn:form=syn:form').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:form', 'syn:form'), node.ndef)
            self.true(node.get('runt'))
            self.eq('syn:form', node.get('type'))
            self.eq('A Synapse form used for representing nodes in the graph.',
                    node.get('doc'))

            # We can even inspect which forms are runtime-online forms
            nodes = await core.eval('syn:form:runt=1').list()
            self.ge(len(nodes), 3)
            pprops = {n.ndef[1] for n in nodes}
            self.true(pprops.issuperset({'syn:form', 'syn:prop', 'syn:type'}))

            # Ensure that we can lift by syn:prop + prop + valu
            # and expected props are present.
            nodes = await core.eval('syn:prop').list()
            self.gt(len(nodes), 1)

            nodes = await core.eval('syn:prop:ro').list()
            self.gt(len(nodes), 1)

            nodes = await core.eval('syn:prop="test:type10:intprop"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:type10:intprop'), node.ndef)
            self.nn(node.get('ro'))
            self.false(node.get('ro'))
            self.nn(node.get('univ'))
            self.false(node.get('univ'))
            self.eq('int', node.get('type'))
            self.eq('test:type10', node.get('form'))
            self.eq('no docstring', node.get('doc'))
            self.eq('intprop', node.get('relname'))
            self.eq('20', node.get('defval'))
            self.eq('intprop', node.get('base'))
            self.false(node.get('extmodel'))

            # Ensure that extmodel formprops are seen
            nodes = await core.eval('syn:prop="test:str:_twiddle"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.true(node.get('extmodel'))

            # A deeper nested prop will have different base and relname values
            nodes = await core.eval('syn:prop="test:edge:n1:form"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:edge:n1:form'), node.ndef)
            self.none(node.get('defval'))
            self.eq('form', node.get('base'))
            self.eq('n1:form', node.get('relname'))

            # forms are also props but have some slightly different keys populated
            nodes = await core.eval('syn:prop="test:type10"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:type10'), node.ndef)
            self.eq('test:type10', node.get('form'))

            self.none(node.get('ro'))
            self.none(node.get('base'))
            self.none(node.get('relname'))

            # Including universal props
            nodes = await core.eval('syn:prop=".created"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', '.created'), node.ndef)
            self.true(node.get('univ'))
            self.false(node.get('extmodel'))

            nodes = await core.eval('syn:prop="test:comp.created"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:comp.created'), node.ndef)
            self.true(node.get('univ'))

            nodes = await core.eval('syn:prop:univ=1').list()
            self.ge(len(nodes), 2)

            # extmodel univs are represented
            nodes = await core.eval('syn:prop="._sneaky"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', '._sneaky'), node.ndef)
            self.true(node.get('univ'))
            self.true(node.get('extmodel'))

            nodes = await core.eval('syn:prop="test:comp._sneaky"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:comp._sneaky'), node.ndef)
            self.true(node.get('univ'))
            self.true(node.get('extmodel'))

            # Tag prop data is also represented
            nodes = await core.eval('syn:tagprop=beep').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:tagprop', 'beep'), node.ndef)
            self.eq(node.get('doc'), 'words')
            self.eq(node.get('type'), 'int')

            # Ensure that we can filter / pivot across the model nodes
            nodes = await core.eval('syn:form=test:comp -> syn:prop:form').list()
            # form is a prop, two universal properties (+2 test univ) and two model secondary properties.
            self.true(len(nodes) >= 7)

            # Go from a syn:type to a syn:form to a syn:prop with a filter
            q = 'syn:type:subof=comp +syn:type:doc~=".*fake.*" -> syn:form:type -> syn:prop:form'
            nodes = await core.eval(q).list()
            self.true(len(nodes) >= 7)

            # Some forms inherit from a single type
            nodes = await core.eval('syn:type="inet:addr" -> syn:type:subof').list()
            self.ge(len(nodes), 2)
            pprops = {n.ndef[1] for n in nodes}
            self.isin('inet:server', pprops)
            self.isin('inet:client', pprops)

            # Pivot from a model node to a Edge node
            async with await core.snap() as snap:
                node = await snap.addNode('test:edge', (('test:int', 1234), ('test:str', '1234')))

            nodes = await core.eval('syn:form=test:int -> test:edge:n1:form').list()
            self.len(1, nodes)
            self.eq('test:edge', nodes[0].ndef[0])

            # Sad path lifts
            await self.asyncraises(s_exc.BadCmprValu, core.eval('syn:form~="beep"').list())

        # Ensure that the model runts are re-populated after a model load has occurred.
        with self.getTestDir() as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:

                # Lift nodes
                nodes = await core.eval('syn:form=syn:tag').list()
                self.len(1, nodes)

                nodes = await core.eval('syn:form=test:runt').list()
                self.len(0, nodes)

                await core.loadCoreModule('synapse.tests.utils.TestModule')

                nodes = await core.eval('syn:form=test:runt').list()
                self.len(1, nodes)

                nodes = await core.eval('syn:prop:form="test:str" +:extmodel=True').list()
                self.len(0, nodes)
                nodes = await core.eval('syn:tagprop').list()
                self.len(0, nodes)

                await addExtModelConfigs(core)

                nodes = await core.eval('syn:prop:form="test:str" +:extmodel=True').list()
                self.len(2, nodes)
                nodes = await core.eval('syn:tagprop').list()
                self.len(1, nodes)

                await delExtModelConfigs(core)

                nodes = await core.eval('syn:prop:form="test:str" +:extmodel=True').list()
                self.len(0, nodes)
                nodes = await core.eval('syn:tagprop').list()
                self.len(0, nodes)

    async def test_syn_trigger_runts(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('syn:trigger')
            self.len(0, nodes)

            waiter = core.waiter(1, 'core:trigger:action')
            await core.addTrigger('node:add', '[inet:user=1] | testcmd', info={'form': 'inet:ipv4'})
            evnts = await waiter.wait(3)
            self.len(1, evnts)

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
            waiter = core.waiter(2, 'core:trigger:action')
            await core.addTrigger('prop:set', '[inet:user=1] | testcmd', info={'prop': 'inet:ipv4:asn'})
            await core.addTrigger('tag:add', '[inet:user=1] | testcmd', info={'tag': 'hehe.haha'})
            evnts = await waiter.wait(3)
            self.len(2, evnts)

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
            nodes = await core.nodes('syn:trigger:user=root')
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

            # Sad path lifts
            await self.asyncraises(s_exc.BadCmprValu, core.nodes('syn:trigger:storm~="beep"'))
