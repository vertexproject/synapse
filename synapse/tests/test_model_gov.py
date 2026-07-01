import synapse.tests.utils as s_test

class GovModelTest(s_test.SynTest):

    async def test_model_gov_iso_oid(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ iso:oid=1.2.3
                    :name="Foo Bar"
                    :desc="A test OID."
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('iso:oid', '1.2.3'))
            self.propeq(node, 'name', 'Foo Bar')
            self.propeq(node, 'desc', 'A test OID.')
            # title type lifts case-insensitively
            self.len(1, await core.nodes('iso:oid:name="foo bar"'))
