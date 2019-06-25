import regex
import asyncio

import synapse.exc as s_exc
import synapse.lib.cmdr as s_cmdr

import synapse.tests.utils as s_t_utils


class CmdBossTest(s_t_utils.SynTest):

    async def test_ps_kill(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            evnt = asyncio.Event()

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

            await cmdr.runCmdLine('ps')

            self.true(outp.expect('0 tasks found.'))

            async def runLongStorm():
                async for _ in core.storm('[ test:str=foo test:str=bar ] | sleep 10'):
                    evnt.set()

            task = realcore.schedCoro(runLongStorm())

            self.true(await asyncio.wait_for(evnt.wait(), timeout=6))

            outp.clear()
            await cmdr.runCmdLine('ps')
            self.true(outp.expect('1 tasks found.'))
            self.true(outp.expect('start time: 2'))

            regx = regex.compile('task iden: ([a-f0-9]{32})')
            match = regx.match(str(outp))

            iden = match.groups()[0]

            outp.clear()
            await cmdr.runCmdLine('kill')
            outp.expect('no iden given to kill')

            outp.clear()
            await cmdr.runCmdLine('kill %s' % (iden,))

            outp.expect('kill status: True')
            self.true(task.done())

            outp.clear()
            await cmdr.runCmdLine('ps')
            self.true(outp.expect('0 tasks found.'))

        async with self.getTestCoreAndProxy() as (realcore, core):

            await realcore.auth.addUser('test')

            async with realcore.getLocalProxy(user='test') as tcore:

                evnt = asyncio.Event()

                async def runLongStorm():
                    async for mesg in core.storm('[ test:str=foo test:str=bar ] | sleep 10'):
                        evnt.set()

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

                toutp = self.getTestOutp()
                tcmdr = await s_cmdr.getItemCmdr(tcore, outp=toutp)

                task = realcore.schedCoro(runLongStorm())
                self.true(await asyncio.wait_for(evnt.wait(), timeout=6))

                outp.clear()
                await cmdr.runCmdLine('ps')
                self.true(outp.expect('1 tasks found.'))

                regx = regex.compile('task iden: ([a-f0-9]{32})')
                match = regx.match(str(outp))
                iden = match.groups()[0]

                toutp.clear()
                await tcmdr.runCmdLine('ps')
                self.true(toutp.expect('0 tasks found.'))

                # Try killing from the unprivileged user
                await self.asyncraises(s_exc.AuthDeny, tcore.kill(iden))
                toutp.clear()
                await tcmdr.runCmdLine('kill %s' % (iden,))
                self.true(toutp.expect('no matching process found. aborting.'))

                # Tear down the task as a real user
                outp.clear()
                await cmdr.runCmdLine('kill %s' % (iden,))
                outp.expect('kill status: True')
                self.true(task.done())
