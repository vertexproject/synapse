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

                    await core01.nodes('[ inet:ip=1.2.3.4 ]')
                    self.len(1, await core00.nodes('inet:ip=1.2.3.4'))

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
