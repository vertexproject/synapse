import os
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

class BackupTest(s_test.SynTest):

    async def test_stormlib_backup(self):

        with self.getTestDir() as dirn:

            backdirn = s_common.gendir(dirn, 'backup')
            coredirn = s_common.gendir(dirn, 'cortex')

            s_common.yamlsave({'backup:dir': backdirn}, coredirn, 'cell.yaml')

            async with self.getTestCore(dirn=coredirn) as core:

                self.eq((), await core.callStorm('return($lib.backup.list())'))

                name = await core.callStorm('return($lib.backup.run())')
                self.true(os.path.isdir(os.path.join(backdirn, name)))

                self.eq((name,), await core.callStorm('return($lib.backup.list())'))

                await core.callStorm('$lib.backup.del($name)', opts={'vars': {'name': name}})
                self.false(os.path.isdir(os.path.join(backdirn, name)))

                await core.callStorm('$lib.backup.run(name=foo)', opts={'vars': {'name': name}})
                self.true(os.path.isdir(os.path.join(backdirn, 'foo')))

                await core.callStorm('$lib.backup.del(foo)')
                self.false(os.path.isdir(os.path.join(backdirn, 'foo')))

                async def mockBackupTask(dirn):
                    await asyncio.sleep(5)

                core._execBackupTask = mockBackupTask

                with self.raises(s_exc.BackupAlreadyRunning):
                    q = 'return(($lib.backup.run(wait=(false)) + $lib.backup.run(wait=(false))))'
                    name = await core.callStorm(q)
