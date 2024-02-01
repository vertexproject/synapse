import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormLibGenTest(s_test.SynTest):

    async def test_stormlib_gen(self):

        async with self.getTestCore() as core:
            nodes00 = await core.nodes('yield $lib.gen.orgByName(vertex)')
            nodes01 = await core.nodes('gen.ou.org vertex')
            self.eq('vertex', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            vtxguid = nodes00[0].ndef[1]

            nodes00 = await core.nodes('gen.ou.org.hq vertex')
            self.eq('vertex', nodes00[0].get('orgname'))
            self.eq(vtxguid, nodes00[0].get('org'))

            await core.nodes('ps:contact:orgname=vertex [ -:org ]')
            nodes00 = await core.nodes('gen.ou.org.hq vertex')
            self.eq(vtxguid, nodes00[0].get('org'))

            await core.nodes('ps:contact:orgname=vertex [ :org=$lib.guid() ]')
            nodes00 = await core.nodes('gen.ou.org.hq vertex')
            self.ne(vtxguid, nodes00[0].get('org'))

            nodes00 = await core.nodes('yield $lib.gen.orgByFqdn(vertex.link)')
            nodes01 = await core.nodes('yield $lib.gen.orgByFqdn(vertex.link)')
            self.eq('vertex.link', nodes00[0].get('dns:mx')[0])
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            self.len(0, await core.nodes('yield $lib.gen.orgByFqdn("...", try=$lib.true)'))

            nodes00 = await core.nodes('yield $lib.gen.industryByName(intelsoftware)')
            nodes01 = await core.nodes('gen.ou.industry intelsoftware')
            self.eq('intelsoftware', nodes00[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('yield $lib.gen.newsByUrl(https://vertex.link)')
            nodes01 = await core.nodes('yield $lib.gen.newsByUrl(https://vertex.link)')
            self.eq('https://vertex.link', nodes00[0].get('url'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            self.len(0, await core.nodes('yield $lib.gen.newsByUrl("...", try=$lib.true)'))

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

            nodes00 = await core.nodes('yield $lib.gen.orgIdType(barcode)')
            nodes01 = await core.nodes('gen.ou.id.type barcode')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            barcode = nodes00[0].ndef[1]

            nodes00 = await core.nodes('yield $lib.gen.orgIdNumber(barcode, 12345)')
            nodes01 = await core.nodes('gen.ou.id.number barcode 12345')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.eq(nodes00[0].get('type'), barcode)

            self.len(0, await core.nodes('gen.risk.vuln newp --try'))

            nodes00 = await core.nodes('yield $lib.gen.polCountryByIso2(UA)')
            nodes01 = await core.nodes('gen.pol.country ua')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            self.len(0, await core.nodes('gen.pol.country newp --try'))

            self.len(1, await core.nodes('''
                gen.pol.country.government ua |
                +ou:org +:name="ua government"
                -> pol:country +:iso2=ua
            '''))

            self.len(0, await core.nodes('gen.pol.country.government newp --try'))

            nodes00 = await core.nodes('gen.ps.contact.email vertex.employee visi@vertex.link')
            nodes01 = await core.nodes('yield $lib.gen.psContactByEmail(vertex.employee, visi@vertex.link)')
            self.eq('vertex.employee.', nodes00[0].get('type'))
            self.eq('visi@vertex.link', nodes00[0].get('email'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            self.len(0, await core.nodes('gen.ps.contact.email vertex.employee newp --try'))

            nodes00 = await core.nodes('gen.lang.language "English (US)" | [ :names+="Murican" ]')
            nodes01 = await core.nodes('yield $lib.gen.langByName(Murican)')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes00 = await core.nodes('gen.ou.campaign "operation overlord" vertex | [ :names+="d-day" ]')
            nodes01 = await core.nodes('gen.ou.campaign d-day vertex')
            nodes02 = await core.nodes('gen.ou.campaign d-day otherorg')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)
            self.ne(nodes01[0].ndef, nodes02[0].ndef)

            q = 'gen.it.av.scan.result inet:fqdn vertex.link foosig --scanner-name barscn --time 2022'
            nodes00 = await core.nodes(q)
            self.len(1, nodes00)
            self.eq('vertex.link', nodes00[0].get('target:fqdn'))
            self.eq('foosig', nodes00[0].get('signame'))
            self.eq('barscn', nodes00[0].get('scanner:name'))
            self.eq('2022/01/01 00:00:00.000', nodes00[0].repr('time'))
            nodes01 = await core.nodes(q)
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes02 = await core.nodes('gen.it.av.scan.result inet:fqdn vertex.link foosig --scanner-name barscn')
            self.eq(nodes00[0].ndef, nodes02[0].ndef)
            self.eq('2022/01/01 00:00:00.000', nodes02[0].repr('time'))

            nodes03 = await core.nodes('gen.it.av.scan.result inet:fqdn vertex.link foosig --scanner-name bazscn')
            self.ne(nodes00[0].ndef, nodes03[0].ndef)

            nodes04 = await core.nodes('gen.it.av.scan.result inet:fqdn vertex.link foosig --time 2022')
            self.eq(nodes00[0].ndef, nodes04[0].ndef)

            nodes05 = await core.nodes('gen.it.av.scan.result inet:fqdn vertex.link foosig --time 2023')
            self.ne(nodes00[0].ndef, nodes05[0].ndef)

            opts = {
                'vars': {
                    'guid': '28c5902d115f29f1fcb818c0abeaa491',
                    'ip': '1.2.3.4',
                    'fqdn': 'vtk.lk',
                }
            }

            self.len(1, await core.nodes('gen.it.av.scan.result file:bytes `guid:{$guid}` foosig', opts=opts))
            self.len(1, await core.nodes('gen.it.av.scan.result inet:fqdn $fqdn foosig', opts=opts))
            self.len(1, await core.nodes('gen.it.av.scan.result inet:ipv4 $ip  foosig', opts=opts))
            self.len(1, await core.nodes('gen.it.av.scan.result inet:ipv6 $ip foosig', opts=opts))
            self.len(1, await core.nodes('gen.it.av.scan.result inet:url `http://{$fqdn}` foosig', opts=opts))
            self.len(1, await core.nodes('gen.it.av.scan.result it:exec:proc $guid foosig', opts=opts))
            self.len(1, await core.nodes('gen.it.av.scan.result it:host $guid foosig', opts=opts))

            self.len(7, await core.nodes('''
                file:bytes=`guid:{$guid}`
                inet:fqdn=$fqdn
                it:host=$guid
                inet:ipv4=$ip
                inet:ipv6:ipv4=$ip
                it:exec:proc=$guid
                inet:url=`http://{$fqdn}`
                +{
                    ($form, $valu) = $node.ndef()
                    -> { gen.it.av.scan.result $form $valu foosig }
                }=1
                -> it:av:scan:result
            ''', opts=opts))

            nodes = await core.nodes('''
                [ it:av:filehit=(`guid:{$lib.guid()}`, ($lib.guid(), fsig)) :sig:name=fsig ]
                gen.it.av.scan.result file:bytes :file :sig:name
            ''')
            self.sorteq(['it:av:filehit', 'it:av:scan:result'], [n.ndef[0] for n in nodes])

            with self.raises(s_exc.NoSuchType) as cm:
                await core.nodes('gen.it.av.scan.result newp vertex.link foosig --try')
            self.eq('No type or prop found for name newp.', cm.exception.errinfo['mesg'])

            with self.raises(s_exc.BadArg) as cm:
                await core.nodes('gen.it.av.scan.result ps:name nah foosig --try')
            self.eq('Unsupported target form ps:name', cm.exception.errinfo['mesg'])

            self.len(0, await core.nodes('gen.it.av.scan.result file:bytes newp foosig --try'))

            self.none(await core.callStorm('return($lib.gen.itAvScanResultByTarget(inet:fqdn, vertex.link, $lib.null, try=$lib.true))'))
            self.none(await core.callStorm('return($lib.gen.itAvScanResultByTarget(inet:fqdn, "..", barsig, try=$lib.true))'))
            self.none(await core.callStorm('return($lib.gen.itAvScanResultByTarget(inet:fqdn, vertex.link, barsig, scanner=$lib.set(), try=$lib.true))'))
            self.none(await core.callStorm('return($lib.gen.itAvScanResultByTarget(inet:fqdn, vertex.link, barsig, time=newp, try=$lib.true))'))

            # Stable guid test
            fork = await core.callStorm('return( $lib.view.get().fork().iden )')

            nodes00 = await core.nodes('yield $lib.gen.orgByName(forkOrg)', opts={'view': fork})
            self.len(1, nodes00)
            nodes01 = await core.nodes('yield $lib.gen.orgByName(forkOrg)')
            self.len(1, nodes01)
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes02 = await core.nodes('yield $lib.gen.orgByName(anotherForkOrg)', opts={'view': fork})
            self.len(1, nodes02)
            self.len(0, await core.nodes('ou:org:name=anotherforkorg'))

            # Merge the fork down
            await core.nodes('view.merge --delete $fork', opts={'vars': {'fork': fork}})

            self.len(1, await core.nodes('ou:org:name=forkorg'))
            self.len(1, await core.nodes('ou:org:name=anotherforkorg'))
