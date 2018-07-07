import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.common as s_test

class BaseTest(s_test.SynTest):

    def test_model_base_node(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                iden = s_common.guid()

                props = {
                    'type': 'hehe haha',
                    'data': ('some', 'data', 'here'),
                }

                node = snap.addNode('graph:node', iden, props=props)
                self.eq(node.ndef, ('graph:node', iden))
                self.eq(node.get('type'), 'hehe haha')
                self.eq(node.get('data'), ('some', 'data', 'here'))

    def test_model_base_link(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                node1 = snap.addNode('testint', 20)
                node2 = snap.addNode('teststr', 'foo')

                link = snap.addNode('graph:link', (node1.ndef, node2.ndef))

                self.eq(link.ndef[1], (('testint', 20), ('teststr', 'foo')))
                self.eq(link.get('n1'), ('testint', 20))
                self.eq(link.get('n1:form'), 'testint')

                self.eq(link.get('n2'), ('teststr', 'foo'))
                self.eq(link.get('n2:form'), 'teststr')

                timelink = snap.addNode('graph:timelink', (node1.ndef, node2.ndef, '2015'))

                self.eq(timelink.ndef[1], (('testint', 20), ('teststr', 'foo'), 1420070400000))

                self.eq(timelink.get('time'), 1420070400000)

                self.eq(timelink.get('n1'), ('testint', 20))
                self.eq(timelink.get('n1:form'), 'testint')

                self.eq(timelink.get('n2'), ('teststr', 'foo'))
                self.eq(timelink.get('n2:form'), 'teststr')

    def test_model_base_event(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                iden = s_common.guid()

                props = {
                    'type': 'HeHe HaHa',
                    'time': '2015',
                    'data': ('some', 'data', 'here'),
                }

                node = snap.addNode('event', iden, props=props)

                self.eq(node.ndef, ('event', iden))

                self.eq(node.get('type'), 'HeHe HaHa')
                self.eq(node.get('time'), 1420070400000)
                self.eq(node.get('data'), ('some', 'data', 'here'))

    def test_model_base_edge(self):

        with self.getTestCore() as core:

            pers = s_common.guid()
            plac = s_common.guid()

            n1def = ('ps:person', pers)
            n2def = ('geo:place', plac)

            with core.snap() as snap:

                node = snap.addNode('has', (n1def, n2def))

                self.eq(node.get('n1'), n1def)
                self.eq(node.get('n1:form'), 'ps:person')

                self.eq(node.get('n2'), n2def)
                self.eq(node.get('n2:form'), 'geo:place')

                node = snap.addNode('wentto', (n1def, n2def, '2016'))

                self.eq(node.get('time'), 1451606400000)

                self.eq(node.get('n1'), n1def)
                self.eq(node.get('n1:form'), 'ps:person')

                self.eq(node.get('n2'), n2def)
                self.eq(node.get('n2:form'), 'geo:place')

            opts = {'vars': {'pers': pers}}

            self.len(1, core.eval('ps:person=$pers -> has -> *', opts=opts))
            self.len(1, core.eval('ps:person=$pers -> has -> geo:place', opts=opts))
            self.len(0, core.eval('ps:person=$pers -> has -> inet:ipv4', opts=opts))

            self.len(1, core.eval('ps:person=$pers -> wentto -> *', opts=opts))
            self.len(1, core.eval('ps:person=$pers -> wentto +:time@=(2014,2017) -> geo:place', opts=opts))
            self.len(0, core.eval('ps:person=$pers -> wentto -> inet:ipv4', opts=opts))

            opts = {'vars': {'place': plac}}

            self.len(1, core.eval('geo:place=$place <- has <- *', opts=opts))
            self.len(1, core.eval('geo:place=$place <- has <- ps:person', opts=opts))
            self.len(0, core.eval('geo:place=$place <- has <- inet:ipv4', opts=opts))

            # Make a restricted edge and validate that you can only form certain relationships
            copts = {'n1:forms': ('ps:person',), 'n2:forms': ('geo:place',)}
            t = core.model.type('edge').clone(copts)
            norm, info = t.norm((n1def, n2def))
            self.eq(norm, (n1def, n2def))
            self.raises(s_exc.BadTypeValu, t.norm, (n1def, ('testint', 1)))
            self.raises(s_exc.BadTypeValu, t.norm, (('testint', 1), n2def))

    def test_model_base_source(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                props = {
                    'name': 'FOO BAR',
                    'type': 'osint',
                }

                sorc = snap.addNode('source', '*', props=props)

                self.eq(sorc.get('type'), 'osint')
                self.eq(sorc.get('name'), 'foo bar')

                valu = (sorc.ndef[1], ('inet:fqdn', 'woot.com'))

                seen = snap.addNode('seen', valu)

                self.eq(seen.get('source'), sorc.ndef[1])
                self.eq(seen.get('node'), ('inet:fqdn', 'woot.com'))
