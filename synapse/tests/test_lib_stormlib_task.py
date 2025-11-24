import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.lib.base as s_base
import synapse.tests.utils as s_test

class TaskLibTest(s_test.SynTest):

    async def test_lib_task_basics(self):

        async with self.getTestAha() as aha:

            conf = {'aha:provision': await aha.addAhaSvcProv('00.cortex')}
            core00 = await aha.enter_context(self.getTestCore(conf=conf))

            conf = {'aha:provision': await aha.addAhaSvcProv('01.cortex', {'mirror': 'cortex'})}
            core01 = await aha.enter_context(self.getTestCore(conf=conf))

            iden0 = 'c7fc6d4ced5759fe6fcc047b6bd3374a'
            task0 = aha.schedCoro(core01.stormlist('$lib.print(root) $lib.time.sleep(10)', opts={'task': iden0}))

            msgs = await core00.stormlist('task.list')
            self.stormIsInPrint('00.cortex.synapse', msgs)
            self.stormIsInPrint('task.list', msgs)
            self.stormIsInPrint('01.cortex.synapse', msgs)
            self.stormIsInPrint('$lib.print(root)', msgs)
            self.stormIsInPrint('2 tasks', msgs)

            msgs = await core01.stormlist('task.list')
            self.stormIsInPrint('00.cortex.synapse', msgs)
            self.stormIsInPrint('task.list', msgs)
            self.stormIsInPrint('01.cortex.synapse', msgs)
            self.stormIsInPrint('$lib.print(root)', msgs)
            self.stormIsInPrint('2 tasks', msgs)

            user = await core01.auth.addUser('someuser')

            async with core00.getLocalProxy(user='someuser') as prox00:
                iden1 = s_common.guid()
                task1 = aha.schedCoro(prox00.callStorm('$lib.print(on00) $lib.time.sleep(10)', opts={'task': iden1}))

                async with core01.getLocalProxy(user='someuser') as prox01:
                    msgs = await s_test.alist(prox01.storm('task.list'))
                    self.stormIsInPrint('00.cortex.synapse', msgs)
                    self.stormIsInPrint('$lib.print(on00)', msgs)
                    self.stormIsInPrint('01.cortex.synapse', msgs)
                    self.stormIsInPrint('task.list', msgs)
                    self.stormIsInPrint('2 tasks', msgs)

                    await user.addRule((True, ('task', 'get')))

                    msgs = await s_test.alist(prox00.storm('task.list'))
                    self.stormIsInPrint('4 tasks', msgs)

                    msgs = await s_test.alist(prox01.storm('task.list'))
                    self.stormIsInPrint('4 tasks', msgs)

                    # We can kill our own  task
                    await prox01.callStorm(f'task.kill {iden1}')
                    with self.raises(s_exc.SynErr):
                        await task1

                    # No task matches
                    with self.raises(s_exc.StormRuntimeError) as exc:
                        await prox01.callStorm('task.kill newp')
                    self.isin('does not match any tasks', exc.exception.get('mesg'))

                    with self.raises(s_exc.StormRuntimeError) as exc:
                        await prox01.callStorm('task.kill ""')
                    self.isin('empty task iden prefix', exc.exception.get('mesg'))

                    iden2 = 'c7fc6d4ced5759fe6fcc047b6bd3374b'
                    task2 = aha.schedCoro(core00.stormlist('$lib.print(root) $lib.time.sleep(10)', opts={'task': iden2}))

                    # Matches exist but we don't have perms to see them
                    with self.raises(s_exc.StormRuntimeError) as exc:
                        await prox01.callStorm('task.kill c7fc')
                    self.isin('does not match any tasks', exc.exception.get('mesg'))

                    await user.addRule((True, ('task', 'del')))

                    # Multiple matches
                    with self.raises(s_exc.StormRuntimeError) as exc:
                        await prox01.callStorm('task.kill c7fc')
                    self.isin('more than one task', exc.exception.get('mesg'))

                    await prox01.callStorm(f'task.kill {iden0}')
                    with self.raises(asyncio.CancelledError):
                        await task0

                    await prox01.callStorm(f'task.kill {iden2}')
                    with self.raises(asyncio.CancelledError):
                        await task2

            msgs = await s_test.alist(core00.storm('task.list'))
            self.stormIsInPrint('1 task', msgs)
