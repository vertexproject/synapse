import synapse.exc as s_exc
import synapse.cortex as s_cortex

import synapse.tests.utils as s_t_utils

class SynModelTest(s_t_utils.SynTest):

    async def test_model_syn_tag(self):

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

    async def test_model_syn_runts(self):

        async with self.getTestCore() as core:

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

            nodes = await core.eval('syn:prop="test:comp.created"').list()
            self.len(1, nodes)
            node = nodes[0]
            self.eq(('syn:prop', 'test:comp.created'), node.ndef)
            self.nn(node.get('univ'))
            self.false(node.get('univ'))

            nodes = await core.eval('syn:prop:univ=1').list()
            self.ge(len(nodes), 2)

            # Ensure that we can filter / pivot across the model nodes
            nodes = await core.eval('syn:form=test:comp -> syn:prop:form').list()
            # form is a prop, two universal properties (+1 test univ) and two model secondary properties.
            self.len(1 + 2 + 1 + 2, nodes)

            # Go from a syn:type to a syn:form to a syn:prop with a filter
            q = 'syn:type:subof=comp +syn:type:doc~=".*fake.*" -> syn:form:type -> syn:prop:form'
            nodes = await core.eval(q).list()
            self.len(1 + 2 + 1 + 2, nodes)

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
