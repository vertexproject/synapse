import synapse.tests.utils as s_test

class StormLibGenTest(s_test.SynTest):

    async def test_stormlib_gen(self):

        async with self.getTestCore() as core:
            nodes00 = await core.nodes('yield $lib.gen.orgByName(vertex)')
            nodes01 = await core.nodes('yield $lib.gen.orgByName(vertex)')
            self.eq('vertex', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.orgByFqdn(vertex.link)')
            nodes01 = await core.nodes('yield $lib.gen.orgByFqdn(vertex.link)')
            self.eq('vertex.link', nodes00[0].get('dns:mx')[0])
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.industryByName(intelsoftware)')
            nodes01 = await core.nodes('yield $lib.gen.industryByName(intelsoftware)')
            self.eq('intelsoftware', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.newsByUrl(https://vertex.link)')
            nodes01 = await core.nodes('yield $lib.gen.newsByUrl(https://vertex.link)')
            self.eq('https://vertex.link', nodes00[0].get('url'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.softByName(synapse)')
            nodes01 = await core.nodes('yield $lib.gen.softByName(synapse)')
            self.eq('synapse', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
