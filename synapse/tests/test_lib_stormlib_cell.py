import synapse.exc as s_exc

import synapse.lib.aha as s_aha
import synapse.lib.coro as s_coro
import synapse.lib.const as s_const
import synapse.lib.stormlib.cell as s_stormlib_cell

import synapse.tests.utils as s_test
import synapse.tests.test_lib_stormsvc as s_t_stormsvc

class StormCellTest(s_test.SynTest):

    async def test_stormlib_cell(self):

        async with self.getTestCore() as core:

            ret = await core.callStorm('return ( $lib.cell.iden )')
            self.eq(ret, core.getCellIden())

            ret = await core.callStorm('return ( $lib.cell.getCellInfo() )')
            self.eq(ret, await core.getCellInfo())

            ret = await core.callStorm('return ( $lib.cell.getBackupInfo() )')
            self.eq(ret, await core.getBackupInfo())

            ret = await core.callStorm('return ( $lib.cell.getSystemInfo() )')
            tst = await core.getSystemInfo()
            self.eq(set(ret.keys()), set(tst.keys()))

            ret = await core.callStorm('return ( $lib.cell.getHealthCheck() )')
            self.eq(ret, await core.getHealthCheck())

            # New cores have stormvar set to the current max version fix
            vers = await core.callStorm('return ( $lib.globals.get($key) )',
                                        {'vars': {'key': s_stormlib_cell.runtime_fixes_key}})
            self.nn(vers)
            self.eq(vers, s_stormlib_cell.getMaxHotFixes())

            user = await core.addUser('bob')
            opts = {'user': user.get('iden')}

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.getCellInfo() )', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.getBackupInfo() )', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.getSystemInfo() )', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.getHealthCheck() )', opts=opts)

    async def test_stormlib_cell_uptime(self):

        async with self.getTestCoreProxSvc(s_t_stormsvc.StormvarServiceCell) as (core, prox, svc):

            day = await core.callStorm('return($lib.time.format($lib.time.now(), "%Y-%m-%d"))')

            msgs = await core.stormlist('uptime')
            self.stormIsInPrint('up 00:00:', msgs)
            self.stormIsInPrint(f'since {day}', msgs)

            msgs = await core.stormlist('uptime stormvar')
            self.stormIsInPrint('up 00:00:', msgs)
            self.stormIsInPrint(f'since {day}', msgs)

            msgs = await core.stormlist('uptime newp')
            self.stormIsInErr('No service with name/iden: newp', msgs)

            svc.starttime = svc.starttime - (1 * s_const.day + 2 * s_const.hour) / 1000
            msgs = await core.stormlist('uptime stormvar')
            self.stormIsInPrint('up 1D 02:00:', msgs)
            self.stormIsInPrint(day, msgs)

            resp = await core.callStorm('return($lib.cell.uptime())')
            self.eq(core.startms, resp['starttime'])
            self.lt(resp['uptime'], s_const.minute)

    async def test_stormlib_cell_getmirrors(self):

        async with self.getTestAha() as aha:

            provurl = await aha.addAhaSvcProv('00.cortex')
            coreconf = {'aha:provision': provurl}
            ahawait = aha.waiter(1, 'aha:svcadd')

            async with self.getTestCore(conf=coreconf) as core00:

                self.gt(len(await ahawait.wait(timeout=6)), 0)  # nexus replay fires 2 events

                user = await core00.addUser('low')
                with self.raises(s_exc.AuthDeny):
                    await core00.callStorm('return($lib.cell.getMirrorUrls())', opts={'user': user.get('iden')})

                self.eq([], await core00.callStorm('return($lib.cell.getMirrorUrls())'))

                provinfo = {'mirror': '00.cortex'}
                provurl = await aha.addAhaSvcProv('01.cortex', provinfo=provinfo)
                ahawait = aha.waiter(1, 'aha:svcadd')

                coreconf = {'aha:provision': provurl}
                async with self.getTestCore(conf=coreconf) as core01:

                    self.gt(len(await ahawait.wait(timeout=6)), 0)  # nexus replay fires 2 events
                    self.true(await s_coro.event_wait(core01.nexsroot._mirready, timeout=6))

                    await core01.nodes('[ inet:ipv4=1.2.3.4 ]')
                    self.len(1, await core00.nodes('inet:ipv4=1.2.3.4'))

                    expurls = ['aha://01.cortex.synapse']

                    self.eq(expurls, await core00.callStorm('return($lib.cell.getMirrorUrls())'))
                    self.eq(expurls, await core01.callStorm('return($lib.cell.getMirrorUrls())'))

                provurl = await aha.addAhaSvcProv('00.testsvc')
                svcconf = {'aha:provision': provurl}
                ahawait = aha.waiter(1, 'aha:svcadd')

                async with self.getTestCell(s_t_stormsvc.StormvarServiceCell, conf=svcconf) as svc00:

                    self.gt(len(await ahawait.wait(timeout=6)), 0)  # nexus replay fires 2 events

                    await self.addSvcToCore(svc00, core00, svcname='testsvc')

                    with self.raises(s_exc.NoSuchName):
                        await core00.callStorm('return($lib.cell.getMirrorUrls(name=newp))')

                    self.eq([], await core00.callStorm('return($lib.cell.getMirrorUrls(name=testsvc))'))

                    provinfo = {'mirror': '00.testsvc'}
                    provurl = await aha.addAhaSvcProv('01.testsvc', provinfo=provinfo)
                    ahawait = aha.waiter(1, 'aha:svcadd')

                    svcconf = {'aha:provision': provurl}
                    async with self.getTestCell(s_t_stormsvc.StormvarServiceCell, conf=svcconf) as svc01:

                        self.gt(len(await ahawait.wait(timeout=6)), 0)  # nexus replay fires 2 events
                        self.true(await s_coro.event_wait(svc01.nexsroot._mirready, timeout=6))

                        await svc01.sync()

                        expurls = ('aha://01.testsvc.synapse',)

                        self.eq(expurls, await core00.callStorm('return($lib.cell.getMirrorUrls(name=testsvc))'))

                    await aha.delAhaSvc('00.testsvc.synapse')

                    with self.raises(s_exc.NoSuchName):
                        await core00.callStorm('return($lib.cell.getMirrorUrls(name=testsvc))')

        # No AHA case

        async with self.getTestCore() as core:

            emesg = 'Enumerating mirror URLs is only supported when AHA is configured'

            with self.raises(s_exc.BadConfValu) as cm:
                await core.callStorm('return($lib.cell.getMirrorUrls())')
                self.eq(emesg, cm.exception.get('mesg'))

            async with self.getTestCell(s_t_stormsvc.StormvarServiceCell) as svc:

                await self.addSvcToCore(svc, core, svcname='testsvc')

                with self.raises(s_exc.BadConfValu) as cm:
                    await core.callStorm('return($lib.cell.getMirrorUrls(name=testsvc))')
                    self.eq(emesg, cm.exception.get('mesg'))

    async def test_stormfix_autoadds(self):

        async def get_regression_views(cortex):
            q = '''function get_view(name) {
                        for $view in $lib.view.list() {
                            $p = $view.pack()
                            if ($p.name = $name) {
                                return ( $view.iden )
                            }
                        }
                        $lib.exit('No view found for name={name}', name=$name)
                    }
                    $ret = ({})
                    $ret.baseview=$get_view(default)
                    $ret.fork1a=$get_view(base1a)
                    $ret.fork2a=$get_view(base2a)
                    $ret.fork1b=$get_view(base1b)
                    $ret.stackview=$get_view(stackview)
                    $ret.stackview1a=$get_view(stackview1a)
                    return ($ret)'''
            ret = await cortex.callStorm(q)
            return ret

        async with self.getRegrCore('2.47.0-autoadds-fix') as core:  # type: s_cortex.Cortex

            user = await core.auth.addUser('user', passwd='user')

            self.len(6, core.views)
            for view in core.views:
                self.len(0, await core.nodes('inet:ipv4 -inet:ipv4=1.2.3.4 -inet:ipv4=1.2.3.5',
                                             opts={'view': view}))
                self.len(0, await core.nodes('inet:ipv6', opts={'view': view}))
                self.len(0, await core.nodes('inet:fqdn', opts={'view': view}))

            msgs = await core.stormlist('$r = $lib.cell.hotFixesCheck() $lib.print("r={r}", r=$r)')
            self.stormIsInPrint('Would apply fix (1, 0, 0) for [Create nodes for known missing autoadds.]', msgs)
            self.stormIsInPrint('r=true', msgs)

            q = '$lib.debug=$lib.true $r = $lib.cell.hotFixesApply() $lib.print("r={r}", r=$r)'
            mesg = '\n'.join(['The following Views will be fixed in order:', '68695c660aa6981192d70e954af0c8e3',
                              '3a3f351ea0704fc310772096c0291405', '18520682d60c09857a12a262c4e2b1ec',
                              '9568f8706b4ce26652dd189b77892e1f', 'd427e8e7f2cd9b92123a80669216e763',
                              'f2edfe4a9da70308dcffd744a9a50bef'])
            msgs = await core.stormlist(q)
            self.stormIsInPrint(mesg, msgs)
            self.stormIsInPrint('fix (1, 0, 0)', msgs)
            self.stormIsInPrint('fix (2, 0, 0)', msgs)

            msgs = await core.stormlist('$r = $lib.cell.hotFixesCheck() $lib.print("r={r}", r=$r)')
            self.stormIsInPrint('r=false', msgs)

            name2view = await get_regression_views(core)

            nodes = await core.nodes('inet:ipv4', opts={'view': name2view.get('baseview')})
            self.eq({n.ndef[1] for n in nodes},
                    {16777217, 16777220, 16842753, 16842756, 16908801, 16908802, 16909060, 1347440720, 1347440721})
            nodes = await core.nodes('inet:ipv6', opts={'view': name2view.get('fork1a')})
            self.eq({n.ndef[1] for n in nodes},
                    {'::ffff:1.1.0.1', '::ffff:1.1.0.4', '::ffff:1.2.2.2', '::ffff:1.2.3.4', '::ffff:80.80.80.81', })

            nodes = await core.nodes('inet:ipv6', opts={'view': name2view.get('fork1b')})
            self.eq({n.ndef[1] for n in nodes},
                    {'::ffff:1.1.0.1', '::ffff:1.1.0.4', '::ffff:1.2.2.2', '::ffff:3.0.9.1', '::ffff:80.80.80.81', })

            nodes = await core.nodes('inet:fqdn', opts={'view': name2view.get('fork2a')})
            self.eq({n.ndef[1] for n in nodes},
                    {'com', 'woot.com', 'stuff.com'})

            nodes = await core.nodes('inet:ipv4', opts={'view': name2view.get('stackview1a')})
            self.eq({n.ndef[1] for n in nodes},
                    {16777217, 16777220, 16842753, 16842756, 167837953, 167904004, 16908801, 16908802, 16909060,
                     1347440720, 1347440721, 3232235777, 3232236031})

            nodes = await core.nodes('inet:ipv6', opts={'view': name2view.get('stackview1a')})
            self.eq({n.ndef[1] for n in nodes},
                    {'::ffff:1.1.0.1', '::ffff:1.1.0.4', '::ffff:1.2.2.2', '::ffff:80.80.80.81', '::ffff:192.168.1.1',
                     '::ffff:192.168.1.255', })

            # Sad path
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return( $lib.cell.hotFixesApply() )', opts={'user': user.iden})

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.cell.hotFixesCheck()) ', opts={'user': user.iden})

    async def test_stormfix_cryptocoin(self):

        async with self.getRegrCore('2.68.0-cryptocoin-fix') as core:  # type: s_cortex.Cortex

            self.len(0, await core.nodes('crypto:currency:coin'))

            msgs = await core.stormlist('$r = $lib.cell.hotFixesCheck() $lib.print("r={r}", r=$r)')
            m = 'Would apply fix (2, 0, 0) for [Populate crypto:currency:coin nodes from existing addresses.]'
            self.stormIsInPrint(m, msgs)
            self.stormIsInPrint('r=true', msgs)

            q = '$lib.debug=$lib.true $r = $lib.cell.hotFixesApply() $lib.print("r={r}", r=$r)'

            msgs = await core.stormlist(q)
            self.stormIsInPrint('Applied hotfix (2, 0, 0)', msgs)

            self.len(2, await core.nodes('crypto:currency:coin'))

    async def test_stormfix_cpe2_2(self):

        async with self.getTestCore() as core:
            view0 = core.getView().iden
            view1 = await core.callStorm('return ( $lib.view.get().fork().iden )')
            view2 = await core.callStorm('return($lib.view.add(($lib.layer.add().iden,)).iden)')
            # Create it:sec:cpe nodes and strip off the :v2_2 property
            nodes = await core.nodes('[it:sec:cpe=cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:*] [-:v2_2]',
                                      opts={'view': view0})
            self.none(nodes[0].get('v2_2'))
            nodes = await core.nodes('[it:sec:cpe=cpe:2.3:a:vertex:testsss:*:*:*:*:*:*:*:*] [-:v2_2]',
                                     opts={'view': view1})
            self.none(nodes[0].get('v2_2'))
            nodes = await core.nodes('[it:sec:cpe=cpe:2.3:a:vertex:stuffff:*:*:*:*:*:*:*:*] [-:v2_2]',
                                     opts={'view': view2})
            self.none(nodes[0].get('v2_2'))

            self.len(0, await core.nodes('it:sec:cpe:v2_2', opts={'view': view0}))
            self.len(0, await core.nodes('it:sec:cpe:v2_2', opts={'view': view1}))
            self.len(0, await core.nodes('it:sec:cpe:v2_2', opts={'view': view2}))

            # Set the hotfix valu
            opts = {'vars': {'key': s_stormlib_cell.runtime_fixes_key, 'valu': (2, 0, 0)}}
            await core.callStorm('$lib.globals.set($key, $valu)', opts)

            # Run all hotfixes.
            msgs = await core.stormlist('$lib.cell.hotFixesApply()')

            self.stormIsInPrint('Applying hotfix (3, 0, 0) for [Populate it:sec:cpe:v2_2', msgs)
            self.stormIsInPrint('Applied hotfix (3, 0, 0)', msgs)

            self.len(1, await core.nodes('it:sec:cpe:v2_2', opts={'view': view0}))
            self.len(2, await core.nodes('it:sec:cpe:v2_2', opts={'view': view1}))
            self.len(1, await core.nodes('it:sec:cpe:v2_2', opts={'view': view2}))

    async def test_stormfix_riskhasvuln(self):

        async with self.getTestCore() as core:

            view0 = core.getView().iden
            view1 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = await core.callStorm('return($lib.view.add(($lib.layer.add().iden,)).iden)')

            self.len(1, await core.nodes('''
                [ risk:hasvuln=*
                    :vuln={[ risk:vuln=* ]}
                    :software={[ it:prod:softver=* :name=view0 ]}
                ]
            ''', opts={'view': view0}))

            self.len(1, await core.nodes('''
                risk:hasvuln
                [ :software={[ it:prod:softver=* :name=view1 ]} ]
            ''', opts={'view': view1}))

            self.len(1, await core.nodes('''
                [ risk:hasvuln=*
                    :vuln={[ risk:vuln=* ]}
                    :host={[ it:host=* :name=view2 ]}
                ]
            ''', opts={'view': view2}))

            opts = {'vars': {'key': s_stormlib_cell.runtime_fixes_key, 'valu': (2, 0, 0)}}
            await core.callStorm('$lib.globals.set($key, $valu)', opts)

            msgs = await core.stormlist('$lib.cell.hotFixesCheck()')
            printmesgs = [m[1]['mesg'] for m in msgs if m[0] == 'print']
            self.isin('Would apply fix (3, 0, 0)', printmesgs[0])
            self.eq('', printmesgs[1])
            self.isin('Would apply fix (4, 0, 0)', printmesgs[2])
            self.eq('', printmesgs[3])
            self.isin('This hotfix should', printmesgs[4])
            self.eq('', printmesgs[-1])

            msgs = await core.stormlist('$lib.cell.hotFixesApply()')
            self.stormIsInPrint('Applying hotfix (4, 0, 0) for [Create risk:vulnerable nodes', msgs)
            self.stormIsInPrint('Applied hotfix (4, 0, 0)', msgs)

            self.len(1, await core.nodes('risk:vulnerable -> it:prod:softver +:name=view0', opts={'view': view0}))
            self.len(1, await core.nodes('risk:vulnerable -> it:prod:softver +:name=view1', opts={'view': view1}))
            self.len(1, await core.nodes('risk:vulnerable -> it:host', opts={'view': view2}))
