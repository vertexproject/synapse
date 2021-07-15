import synapse.exc as s_exc

import synapse.tests.utils as s_test

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
