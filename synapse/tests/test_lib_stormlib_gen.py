import synapse.tests.utils as s_test

class StormLibGenTest(s_test.SynTest):

    async def test_stormlib_gen(self):

        async with self.getTestCore() as core:
            nodes00 = await core.nodes('yield $lib.gen.orgByName(vertex)')
            nodes01 = await core.nodes('gen.ou.org vertex')
            self.eq('vertex', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('gen.ou.org.hq vertex')
            self.eq('vertex', nodes00[0].get('orgname'))

            nodes00 = await core.nodes('yield $lib.gen.orgByFqdn(vertex.link)')
            nodes01 = await core.nodes('yield $lib.gen.orgByFqdn(vertex.link)')
            self.eq('vertex.link', nodes00[0].get('dns:mx')[0])
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.industryByName(intelsoftware)')
            nodes01 = await core.nodes('gen.ou.industry intelsoftware')
            self.eq('intelsoftware', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.newsByUrl(https://vertex.link)')
            nodes01 = await core.nodes('yield $lib.gen.newsByUrl(https://vertex.link)')
            self.eq('https://vertex.link', nodes00[0].get('url'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.softByName(synapse)')
            nodes01 = await core.nodes('gen.it.prod.soft synapse')
            self.eq('synapse', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.riskThreat(apt1, mandiant)')
            nodes01 = await core.nodes('gen.risk.threat apt1 mandiant')
            self.eq('apt1', nodes00[0].get('org:name'))
            self.eq('mandiant', nodes00[0].get('reporter:name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.riskToolSoftware(redcat, vertex)')
            nodes01 = await core.nodes('gen.risk.tool.software redcat vertex')
            self.eq('redcat', nodes00[0].get('soft:name'))
            self.eq('vertex', nodes00[0].get('reporter:name'))
            self.nn(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.vulnByCve(CVE-2022-00001)')
            nodes01 = await core.nodes('gen.risk.vuln CVE-2022-00001')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.vulnByCve(CVE-2022-00001)')
            nodes01 = await core.nodes('gen.risk.vuln CVE-2022-00001')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.polCountryByIso2(UA)')
            nodes01 = await core.nodes('gen.pol.country ua')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            self.len(1, await core.nodes('''
                gen.pol.country.government ua |
                +ou:org +:name="ua government"
                -> pol:country +:iso2=ua
            '''))

            nodes00 = await core.nodes('gen.ps.contact.email vertex.employee visi@vertex.link')
            nodes01 = await core.nodes('yield $lib.gen.psContactByEmail(vertex.employee, visi@vertex.link)')
            self.eq('vertex.employee.', nodes00[0].get('type'))
            self.eq('visi@vertex.link', nodes00[0].get('email'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
