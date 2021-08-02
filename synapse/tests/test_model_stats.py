import synapse.tests.utils as s_test

class StatsModelTest(s_test.SynTest):

    async def test_model_stats(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ stats:sampleset=* :name=foo :desc=bar ]')
            self.len(1, nodes)
            self.eq('foo', nodes[0].get('name'))
            self.eq('bar', nodes[0].get('desc'))

            iden = await core.callStorm('stats:sampleset return($node.repr())')
            opts = {'vars': {'iden': iden}}

            nodes = await core.nodes('[ (stats:sample=* :seqn=($iden, 2021)) (stats:sample=* :seqn=($iden, 2022)) ]', opts=opts)
            self.len(2, nodes)
            self.eq((iden, 1609459200000), nodes[0].get('seqn'))
            self.eq(iden, nodes[0].get('seqn:set'))
            self.eq(1609459200000, nodes[0].get('seqn:time'))

            nodes = await core.nodes('stats:sample:seqn')
            self.len(2, nodes)
            self.eq((iden, 1609459200000), nodes[0].get('seqn'))
            self.eq(iden, nodes[0].get('seqn:set'))
            self.eq(1609459200000, nodes[0].get('seqn:time'))

            nodes = await core.nodes('stats:sample:seqn > ($iden, 2023)', opts=opts)
            self.len(0, nodes)
            nodes = await core.nodes('stats:sample:seqn < ($iden, 2020)', opts=opts)
            self.len(0, nodes)
            nodes = await core.nodes('stats:sample:seqn >= ($iden, 2023)', opts=opts)
            self.len(0, nodes)
            nodes = await core.nodes('stats:sample:seqn <= ($iden, 2020)', opts=opts)
            self.len(0, nodes)

            nodes = await core.nodes('stats:sample:seqn > ($iden, 2020)', opts=opts)
            self.len(2, nodes)
            self.eq((iden, 1609459200000), nodes[0].get('seqn'))

            nodes = await core.nodes('stats:sample:seqn >= ($iden, 2020)', opts=opts)
            self.len(2, nodes)
            self.eq((iden, 1609459200000), nodes[0].get('seqn'))

            nodes = await core.nodes('stats:sample:seqn < ($iden, 2099)', opts=opts)
            self.len(2, nodes)
            self.eq((iden, 1609459200000), nodes[0].get('seqn'))

            nodes = await core.nodes('stats:sample:seqn <= ($iden, 2099)', opts=opts)
            self.len(2, nodes)
            self.eq((iden, 1609459200000), nodes[0].get('seqn'))
