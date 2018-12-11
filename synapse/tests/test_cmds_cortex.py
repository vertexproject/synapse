import os
import regex
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cmdr as s_cmdr
import synapse.lib.encoding as s_encoding

import synapse.tests.utils as s_t_utils


class CmdCoreTest(s_t_utils.SynTest):

    async def test_storm(self):

        help_msg = 'Execute a storm query.'
        async with self.getTestDmon('dmoncore') as dmon, \
                await self.agetTestProxy(dmon, 'core') as core:

            await self.agenlen(1, await core.eval("[ teststr=abcd :tick=2015 +#cool ]"))

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('help storm')
            outp.expect(help_msg)

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm help')
            outp.expect('For detailed help on any command')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm')
            outp.expect(help_msg)

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --debug teststr=abcd')
            outp.expect("('init',")
            outp.expect("('node',")
            outp.expect("('fini',")
            outp.expect("tick")
            outp.expect("tock")
            outp.expect("took")

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --debug teststr=zzz')
            outp.expect("('init',")
            self.false(outp.expect("('node',", throw=False))
            outp.expect("('fini',")
            outp.expect("tick")
            outp.expect("tock")
            outp.expect("took")

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm teststr=b')
            outp.expect('complete. 0 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm teststr=abcd')
            outp.expect(':tick = 2015/01/01 00:00:00.000')
            outp.expect('#cool')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --hide-tags teststr=abcd')
            outp.expect(':tick = 2015/01/01 00:00:00.000')
            self.false(outp.expect('#cool', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --hide-props teststr=abcd')
            self.false(outp.expect(':tick = 2015/01/01 00:00:00.000', throw=False))
            outp.expect('#cool')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --hide-tags --hide-props teststr=abcd')
            self.false(outp.expect(':tick = 2015/01/01 00:00:00.000', throw=False))
            self.false(outp.expect('#cool', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --raw teststr=abcd')
            outp.expect("'tick': 1420070400000")
            outp.expect("'tags': {'cool': (None, None)")
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --bad')
            outp.expect('BadStormSyntax')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm newpz')
            outp.expect('err')
            outp.expect('NoSuchProp')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --hide-unknown [teststr=1234]')
            s = str(outp)
            self.notin('node:add', s)
            self.notin('prop:set', s)
            await self.agenlen(1, await core.eval('[testcomp=(1234, 5678)]'))

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            q = 'storm --raw --path testcomp -> testint'
            await cmdr.runCmdLine(q)
            self.true(outp.expect("('testint', 1234)"))
            self.true(outp.expect("'path'"))

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm [ teststr=foo +#bar.baz=(2015,?) ]')
            self.true(outp.expect('#bar.baz = (2015/01/01 00:00:00.000, ?)', throw=False))
            self.false(outp.expect('#bar ', throw=False))
            outp.expect('complete. 1 nodes')

    async def test_log(self):

        async with self.getTestDmon('dmoncore') as dmon:

            with self.getTestSynDir() as dirn:

                async with await self.agetTestProxy(dmon, 'core') as core:
                    outp = self.getTestOutp()
                    cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                    await cmdr.runCmdLine('log --on --format jsonl')
                    fp = cmdr.locs.get('log:fp')
                    await cmdr.runCmdLine('storm [teststr=hi :tick=2018 +#haha.hehe]')
                    await cmdr.runCmdLine('log --off')
                    cmdr.fini()

                    self.true(outp.expect('Starting logfile'))
                    self.true(outp.expect('Closing logfile'))
                    self.true(os.path.isfile(fp))

                    # Ensure that jsonl is how the data was saved
                    with s_common.genfile(fp) as fd:
                        genr = s_encoding.iterdata(fd, close_fd=False, format='jsonl')
                        objs = list(genr)
                    self.eq(objs[0][0], 'init')

                async with await self.agetTestProxy(dmon, 'core') as core:
                    outp = self.getTestOutp()
                    cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                    # Our default format is mpk
                    fp = os.path.join(dirn, 'loggyMcLogFace.mpk')
                    await cmdr.runCmdLine(f'log --on --splices-only --path {fp}')
                    fp = cmdr.locs.get('log:fp')
                    await cmdr.runCmdLine('storm [teststr="I am a message!" :tick=1999 +#oh.my] ')
                    await cmdr.runCmdLine('log --off')
                    cmdr.fini()

                    self.true(os.path.isfile(fp))
                    with s_common.genfile(fp) as fd:
                        genr = s_encoding.iterdata(fd, close_fd=False, format='mpk')
                        objs = list(genr)
                    self.eq(objs[0][0], 'node:add')

                async with await self.agetTestProxy(dmon, 'core') as core:
                    outp = self.getTestOutp()
                    cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                    await cmdr.runCmdLine('log --on --off')
                    cmdr.fini()
                    self.true(outp.expect('Pick one'))

                    outp = self.getTestOutp()
                    cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                    await cmdr.runCmdLine('log')
                    cmdr.fini()
                    self.true(outp.expect('Pick one'))

    async def test_storm_cmd_ps_kill(self):

        async with self.getTestDmon('dmoncore') as dmon:

            async with await self.agetTestProxy(dmon, 'core') as core:

                evnt = asyncio.Event()

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

                await cmdr.runCmdLine('ps')

                self.true(outp.expect('0 tasks found.'))

                async def runLongStorm():
                    async for _ in await core.storm('[ teststr=foo teststr=bar ] | sleep 10'):
                        evnt.set()

                task = dmon.schedCoro(runLongStorm())

                await evnt.wait()

                outp.clear()
                await cmdr.runCmdLine('ps')
                self.true(outp.expect('1 tasks found.'))
                self.true(outp.expect('start time: 2'))

                regx = regex.compile('task iden: ([a-f0-9]{32})')
                match = regx.match(str(outp))

                iden = match.groups()[0]

                outp.clear()
                await cmdr.runCmdLine('kill %s' % (iden,))

                outp.expect('kill status: True')
                self.true(task.done())

                outp.clear()
                await cmdr.runCmdLine('ps')
                self.true(outp.expect('0 tasks found.'))

        async with self.getTestDmon('dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                await core.addAuthUser('test')
                await core.setUserPasswd('test', 'test')

                tconf = {'user': 'test', 'passwd': 'test'}
                async with await self.agetTestProxy(dmon, 'core', **tconf) as tcore:

                    evnt = asyncio.Event()

                    async def runLongStorm():
                        async for mesg in await core.storm('[ teststr=foo teststr=bar ] | sleep 10 | sudo'):
                            evnt.set()

                    outp = self.getTestOutp()
                    cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

                    toutp = self.getTestOutp()
                    tcmdr = await s_cmdr.getItemCmdr(tcore, outp=toutp)

                    task = dmon.schedCoro(runLongStorm())
                    await evnt.wait()

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
