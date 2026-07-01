import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormLibGenTest(s_test.SynTest):

    async def test_stormlib_gen(self):

        async with self.getTestCore() as core:

            view2 = await core.callStorm('return($lib.view.add(layers=($lib.layer.add().iden,)).iden)')
            onview2 = {'view': view2}

            # gen.campaign

            self.len(0, await core.nodes('gen.campaign overlord (null) --try'))
            self.len(0, await core.nodes('gen.campaign (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.campaign (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.campaign overload (null)'))

            self.len(1, nodes00 := await core.nodes('gen.campaign "operation overlord" vertex | [ :names+=overlord ]'))
            self.len(1, nodes01 := await core.nodes('gen.campaign overlord vertex'))
            self.propeq(nodes00[0], 'name', 'operation overlord')
            self.propeq(nodes00[0], 'names', ['overlord'])
            self.propeq(nodes00[0], 'reporter:name', 'vertex')
            self.none(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(0, await core.nodes('ou:org:name=vertex'))

            self.len(1, nodes := await core.nodes('gen.campaign overlord otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.propeq(nodes[0], 'name', 'overlord')
            self.none(nodes[0].get('names'))
            self.propeq(nodes[0], 'reporter:name', 'otherorg')
            self.none(nodes[0].get('reporter'))

            self.len(0, await core.nodes('ou:org:name=otherorg'))

            self.len(1, nodes := await core.nodes('gen.campaign "operation overlord" vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.place

            self.len(0, await core.nodes('gen.place (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.place (null)'))

            self.len(1, nodes00 := await core.nodes('gen.place zimbabwe | [ :names+=rhodesia ]'))
            self.len(1, nodes01 := await core.nodes('gen.place rhodesia'))
            self.propeq(nodes00[0], 'name', 'zimbabwe')
            self.propeq(nodes00[0], 'names', ['rhodesia'])
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.place zimbabwe', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.software

            self.len(0, await core.nodes('gen.software rar (null) --try'))
            self.len(0, await core.nodes('gen.software (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.software (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.software rar (null)'))

            self.len(1, nodes00 := await core.nodes('gen.software rar vertex | [ :names+=rarrr ]'))
            self.len(1, nodes01 := await core.nodes('gen.software rarrr vertex'))
            self.propeq(nodes00[0], 'name', 'rar')
            self.propeq(nodes00[0], 'names', ['rarrr'])
            self.propeq(nodes00[0], 'reporter:name', 'vertex')
            self.none(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(0, await core.nodes('ou:org:name=vertex'))

            self.len(1, nodes := await core.nodes('gen.software rar otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.propeq(nodes[0], 'name', 'rar')
            self.none(nodes[0].get('names'))
            self.propeq(nodes[0], 'reporter:name', 'otherorg')
            self.none(nodes[0].get('reporter'))

            self.len(0, await core.nodes('ou:org:name=otherorg'))

            self.len(1, nodes := await core.nodes('gen.software rar vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.language

            self.len(0, await core.nodes('gen.language (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.language (null)'))

            self.len(1, nodes00 := await core.nodes('gen.language german | [ :names+=deutsch ]'))
            self.len(1, nodes01 := await core.nodes('gen.language deutsch'))
            self.propeq(nodes00[0], 'name', 'german')
            self.propeq(nodes00[0], 'names', ['deutsch'])
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.language german', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.industry

            self.len(0, await core.nodes('gen.industry ngo (null) --try'))
            self.len(0, await core.nodes('gen.industry (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.industry (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.industry ngo (null)'))

            self.len(1, nodes00 := await core.nodes('gen.industry ngo vertex | [ :names+=ngos ]'))
            self.len(1, nodes01 := await core.nodes('gen.industry ngos vertex'))
            self.propeq(nodes00[0], 'name', 'ngo')
            self.propeq(nodes00[0], 'names', ['ngos'])
            self.propeq(nodes00[0], 'reporter:name', 'vertex')
            self.none(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(0, await core.nodes('ou:org:name=vertex'))

            self.len(1, nodes := await core.nodes('gen.industry ngo otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.propeq(nodes[0], 'name', 'ngo')
            self.none(nodes[0].get('names'))
            self.propeq(nodes[0], 'reporter:name', 'otherorg')
            self.none(nodes[0].get('reporter'))

            self.len(0, await core.nodes('ou:org:name=otherorg'))

            self.len(1, nodes := await core.nodes('gen.industry ngo vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.org

            self.len(0, await core.nodes('gen.org (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.org (null)'))

            self.len(1, nodes00 := await core.nodes('gen.org intel | [ :names+=intelsoft ]'))
            self.len(1, nodes01 := await core.nodes('gen.org intelsoft'))
            self.propeq(nodes00[0], 'name', 'intel')
            self.propeq(nodes00[0], 'names', ['intelsoft'])
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.org intel', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.country

            self.len(0, await core.nodes('gen.country (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.country (null)'))

            self.len(1, nodes00 := await core.nodes('gen.country us'))
            self.len(1, nodes01 := await core.nodes('gen.country us'))
            self.propeq(nodes00[0], 'code', 'us')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.country us', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.government

            self.len(0, await core.nodes('gen.government (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.government (null)'))

            self.len(1, nodes00 := await core.nodes('gen.government us'))
            self.len(1, nodes01 := await core.nodes('gen.government us'))
            self.eq('ou:org', nodes00[0].ndef[0])
            self.propeq(nodes00[0], 'name', 'us government')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, pols00 := await core.nodes('ou:org:name="us government" -> pol:country'))
            self.propeq(pols00[0], 'code', 'us')

            self.len(1, nodes := await core.nodes('gen.government us', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)
            self.len(1, nodes := await core.nodes('ou:org:name="us government" -> pol:country', opts=onview2))
            self.eq(pols00[0].ndef, nodes[0].ndef)

            # gen.threat

            self.len(0, await core.nodes('gen.threat apt1 (null) --try'))
            self.len(0, await core.nodes('gen.threat (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.threat (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.threat apt1 (null)'))

            self.len(1, nodes00 := await core.nodes('gen.threat apt1 vertex | [ :names+=apt-1 ]'))
            self.len(1, nodes01 := await core.nodes('gen.threat apt-1 vertex'))
            self.propeq(nodes00[0], 'name', 'apt1')
            self.propeq(nodes00[0], 'names', ['apt-1'])
            self.propeq(nodes00[0], 'reporter:name', 'vertex')
            self.none(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(0, await core.nodes('ou:org:name=vertex'))

            self.len(1, nodes := await core.nodes('gen.threat apt1 otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.propeq(nodes[0], 'name', 'apt1')
            self.none(nodes[0].get('names'))
            self.propeq(nodes[0], 'reporter:name', 'otherorg')
            self.none(nodes[0].get('reporter'))

            self.len(0, await core.nodes('ou:org:name=otherorg'))

            self.len(1, nodes := await core.nodes('gen.threat apt1 vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.vuln

            self.len(0, await core.nodes('gen.vuln newp (null) --try'))
            self.len(0, await core.nodes('gen.vuln (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.vuln (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.vuln newp (null)'))

            self.len(1, nodes00 := await core.nodes('gen.vuln cve-2024-0123 vertex'))
            self.len(1, nodes01 := await core.nodes('gen.vuln cve-2024-0123 vertex'))
            self.propeq(nodes00[0], 'id', 'CVE-2024-0123', type='it:sec:cve')
            self.propeq(nodes00[0], 'reporter:name', 'vertex')
            self.none(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(0, await core.nodes('ou:org:name=vertex'))

            self.len(1, nodes := await core.nodes('gen.vuln cve-2024-0123 otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.propeq(nodes[0], 'id', 'CVE-2024-0123', type='it:sec:cve')
            self.propeq(nodes[0], 'reporter:name', 'otherorg')
            self.none(nodes[0].get('reporter'))

            self.len(0, await core.nodes('ou:org:name=otherorg'))

            self.len(1, nodes := await core.nodes('gen.vuln cve-2024-0123 vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)
