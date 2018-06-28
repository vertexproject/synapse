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

                node = snap.addNode('node', iden, props=props)
                self.eq(node.ndef, ('node', iden))
                self.eq(node.get('type'), 'hehe haha')
                self.eq(node.get('data'), ('some', 'data', 'here'))

    def test_model_base_event(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                iden = s_common.guid()

                props = {
                    'type': 'hehe haha',
                    'time': '2015',
                    'data': ('some', 'data', 'here'),
                }

                node = snap.addNode('event', iden, props=props)

                self.eq(node.ndef, ('event', iden))

                self.eq(node.get('type'), 'hehe haha')
                self.eq(node.get('time'), 'hehe haha')
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
