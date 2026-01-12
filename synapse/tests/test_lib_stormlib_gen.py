import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

class StormLibGenTest(s_test.SynTest):

    async def test_stormlib_gen(self):

        async with self.getTestCore() as core:

            view2 = await core.callStorm('return($lib.view.add(layers=($lib.layer.add().iden,)).iden)')
            onview2 = {'view': view2}

            self.len(1, nodes := await core.nodes('[ ou:org=({"name": "vtx"}) :names=(vertex,) ]'))
            vtxguid = nodes[0].ndef[1]

            # gen.entity.campaign

            self.len(0, await core.nodes('gen.entity.campaign overlord (null) --try'))
            self.len(0, await core.nodes('gen.entity.campaign (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.entity.campaign (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.entity.campaign overload (null)'))

            self.len(1, nodes00 := await core.nodes('gen.entity.campaign "operation overlord" vertex | [ :names+=overlord ]'))
            self.len(1, nodes01 := await core.nodes('gen.entity.campaign overlord vertex'))
            self.eq('operation overlord', nodes00[0].get('name'))
            self.eq(['overlord'], nodes00[0].get('names'))
            self.eq('vertex', nodes00[0].get('reporter:name'))
            self.nn(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('entity:campaign:name="operation overlord" :reporter -> ou:org'))
            self.eq(vtxguid, nodes[0].ndef[1])
            self.eq(['vertex'], nodes[0].get('names'))

            self.len(1, nodes := await core.nodes('gen.entity.campaign overlord otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.eq('overlord', nodes[0].get('name'))
            self.none(nodes[0].get('names'))
            self.eq('otherorg', nodes[0].get('reporter:name'))
            self.nn(nodes[0].get('reporter'))

            self.len(1, nodes := await core.nodes('gen.entity.campaign "operation overlord" vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.geo.place

            self.len(0, await core.nodes('gen.geo.place (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.geo.place (null)'))

            self.len(1, nodes00 := await core.nodes('gen.geo.place zimbabwe | [ :names+=rhodesia ]'))
            self.len(1, nodes01 := await core.nodes('gen.geo.place rhodesia'))
            self.eq('zimbabwe', nodes00[0].get('name'))
            self.eq(['rhodesia'], nodes00[0].get('names'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.geo.place zimbabwe', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.it.software

            self.len(0, await core.nodes('gen.it.software (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.it.software (null)'))

            self.len(1, nodes00 := await core.nodes('gen.it.software rar | [ :names+=rarrr ]'))
            self.len(1, nodes01 := await core.nodes('gen.it.software rarrr'))
            self.eq('rar', nodes00[0].get('name'))
            self.eq(['rarrr'], nodes00[0].get('names'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.it.software rar', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.lang.language

            self.len(0, await core.nodes('gen.lang.language (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.lang.language (null)'))

            self.len(1, nodes00 := await core.nodes('gen.lang.language german | [ :names+=deutsch ]'))
            self.len(1, nodes01 := await core.nodes('gen.lang.language deutsch'))
            self.eq('german', nodes00[0].get('name'))
            self.eq(['deutsch'], nodes00[0].get('names'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.lang.language german', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.ou.industry

            self.len(0, await core.nodes('gen.ou.industry ngo (null) --try'))
            self.len(0, await core.nodes('gen.ou.industry (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.ou.industry (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.ou.industry ngo (null)'))

            self.len(1, nodes00 := await core.nodes('gen.ou.industry ngo vertex | [ :names+=ngos ]'))
            self.len(1, nodes01 := await core.nodes('gen.ou.industry ngos vertex'))
            self.eq('ngo', nodes00[0].get('name'))
            self.eq(['ngos'], nodes00[0].get('names'))
            self.eq('vertex', nodes00[0].get('reporter:name'))
            self.nn(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('ou:industry:name=ngo :reporter -> ou:org'))
            self.eq(vtxguid, nodes[0].ndef[1])

            self.len(1, nodes := await core.nodes('gen.ou.industry ngo otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.eq('ngo', nodes[0].get('name'))
            self.none(nodes[0].get('names'))
            self.eq('otherorg', nodes[0].get('reporter:name'))
            self.nn(nodes[0].get('reporter'))

            self.len(1, nodes := await core.nodes('gen.ou.industry ngo vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.ou.org

            self.len(0, await core.nodes('gen.ou.org (null) --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.ou.org (null)'))

            self.len(1, nodes00 := await core.nodes('gen.ou.org intel | [ :names+=intelsoft ]'))
            self.len(1, nodes01 := await core.nodes('gen.ou.org intelsoft'))
            self.eq('intel', nodes00[0].get('name'))
            self.eq(['intelsoft'], nodes00[0].get('names'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.ou.org intel', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.pol.country

            self.len(0, await core.nodes('gen.pol.country newp --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.pol.country newp'))

            self.len(1, nodes00 := await core.nodes('gen.pol.country us'))
            self.len(1, nodes01 := await core.nodes('gen.pol.country us'))
            self.eq('us', nodes00[0].get('code'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('gen.pol.country us', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.pol.country.government

            self.len(0, await core.nodes('gen.pol.country.government newp --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.pol.country.government newp'))

            self.len(1, nodes00 := await core.nodes('gen.pol.country.government us'))
            self.len(1, nodes01 := await core.nodes('gen.pol.country.government us'))
            self.eq('ou:org', nodes00[0].ndef[0])
            self.eq('us government', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, pols00 := await core.nodes('ou:org:name="us government" -> pol:country'))
            self.eq('us', pols00[0].get('code'))

            self.len(1, nodes := await core.nodes('gen.pol.country.government us', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)
            self.len(1, nodes := await core.nodes('ou:org:name="us government" -> pol:country', opts=onview2))
            self.eq(pols00[0].ndef, nodes[0].ndef)

            # gen.risk.threat

            self.len(0, await core.nodes('gen.risk.threat apt1 (null) --try'))
            self.len(0, await core.nodes('gen.risk.threat (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.risk.threat (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.risk.threat apt1 (null)'))

            self.len(1, nodes00 := await core.nodes('gen.risk.threat apt1 vertex | [ :names+=apt-1 ]'))
            self.len(1, nodes01 := await core.nodes('gen.risk.threat apt-1 vertex'))
            self.eq('apt1', nodes00[0].get('name'))
            self.eq(['apt-1'], nodes00[0].get('names'))
            self.eq('vertex', nodes00[0].get('reporter:name'))
            self.nn(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('risk:threat:name=apt1 :reporter -> ou:org'))
            self.eq(vtxguid, nodes[0].ndef[1])

            self.len(1, nodes := await core.nodes('gen.risk.threat apt1 otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.eq('apt1', nodes[0].get('name'))
            self.none(nodes[0].get('names'))
            self.eq('otherorg', nodes[0].get('reporter:name'))
            self.nn(nodes[0].get('reporter'))

            self.len(1, nodes := await core.nodes('gen.risk.threat apt1 vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.risk.tool.software

            self.len(0, await core.nodes('gen.risk.tool.software blackcat (null) --try'))
            self.len(0, await core.nodes('gen.risk.tool.software (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.risk.tool.software (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.risk.tool.software blackcat (null)'))

            self.len(1, nodes00 := await core.nodes('gen.risk.tool.software blackcat vertex | [ :names+=alphv ]'))
            self.len(1, nodes01 := await core.nodes('gen.risk.tool.software alphv vertex'))
            self.eq('blackcat', nodes00[0].get('name'))
            self.eq(['alphv'], nodes00[0].get('names'))
            self.eq('vertex', nodes00[0].get('reporter:name'))
            self.nn(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('risk:tool:software:name=blackcat :reporter -> ou:org'))
            self.eq(vtxguid, nodes[0].ndef[1])

            self.len(1, nodes := await core.nodes('gen.risk.tool.software blackcat otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.eq('blackcat', nodes[0].get('name'))
            self.none(nodes[0].get('names'))
            self.eq('otherorg', nodes[0].get('reporter:name'))
            self.nn(nodes[0].get('reporter'))

            self.len(1, nodes := await core.nodes('gen.risk.tool.software blackcat vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)

            # gen.risk.vuln

            self.len(0, await core.nodes('gen.risk.vuln newp (null) --try'))
            self.len(0, await core.nodes('gen.risk.vuln (null) vertex --try'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.risk.vuln (null) vertex'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('gen.risk.vuln newp (null)'))

            self.len(1, nodes00 := await core.nodes('gen.risk.vuln cve-2024-0123 vertex'))
            self.len(1, nodes01 := await core.nodes('gen.risk.vuln cve-2024-0123 vertex'))
            self.eq('CVE-2024-0123', nodes00[0].get('id'))
            self.eq('vertex', nodes00[0].get('reporter:name'))
            self.nn(nodes00[0].get('reporter'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].getProps(), nodes01[0].getProps())

            self.len(1, nodes := await core.nodes('it:sec:cve=cve-2024-0123 -> risk:vuln:id :reporter -> ou:org'))
            self.eq(vtxguid, nodes[0].ndef[1])

            self.len(1, nodes := await core.nodes('gen.risk.vuln cve-2024-0123 otherorg'))
            self.ne(nodes00[0].ndef[1], nodes[0].ndef[1])
            self.eq('CVE-2024-0123', nodes[0].get('id'))
            self.eq('otherorg', nodes[0].get('reporter:name'))
            self.nn(nodes[0].get('reporter'))

            self.len(1, nodes := await core.nodes('gen.risk.vuln cve-2024-0123 vertex', opts=onview2))
            self.eq(nodes00[0].ndef, nodes[0].ndef)
