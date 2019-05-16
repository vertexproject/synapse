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

        async with self.getTestCoreAndProxy() as (realcore, core):

            await self.agenlen(1, core.eval("[ test:str=abcd :tick=2015 +#cool ]"))

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
            await cmdr.runCmdLine('storm --debug test:str=abcd')
            outp.expect("('init',")
            outp.expect("('node',")
            outp.expect("('fini',")
            outp.expect("tick")
            outp.expect("tock")
            outp.expect("took")

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --debug test:str=zzz')
            outp.expect("('init',")
            self.false(outp.expect("('node',", throw=False))
            outp.expect("('fini',")
            outp.expect("tick")
            outp.expect("tock")
            outp.expect("took")

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm test:str=b')
            outp.expect('complete. 0 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm test:str=abcd')
            outp.expect(':tick = 2015/01/01 00:00:00.000')
            outp.expect('#cool')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --hide-tags test:str=abcd')
            outp.expect(':tick = 2015/01/01 00:00:00.000')
            self.false(outp.expect('#cool', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --hide-props test:str=abcd')
            self.false(outp.expect(':tick = 2015/01/01 00:00:00.000', throw=False))
            outp.expect('#cool')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --show print,foo:bar test:str=abcd')
            self.false(outp.expect(':tick = 2015/01/01 00:00:00.000', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --hide-tags --hide-props test:str=abcd')
            self.false(outp.expect(':tick = 2015/01/01 00:00:00.000', throw=False))
            self.false(outp.expect('#cool', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --raw test:str=abcd')
            outp.expect("'tick': 1420070400000")
            outp.expect("'tags': {'cool': (None, None)")
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --bad')
            outp.expect('BadSyntax')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm newpz')
            outp.expect('err')
            outp.expect('NoSuchName')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --hide-unknown [test:str=1234]')
            s = str(outp)
            self.notin('node:add', s)
            self.notin('prop:set', s)
            await self.agenlen(1, core.eval('[test:comp=(1234, 5678)]'))

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            q = 'storm --raw --path test:comp -> test:int'
            await cmdr.runCmdLine(q)
            self.true(outp.expect("('test:int', 1234)"))
            self.true(outp.expect("'path'"))

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm [ test:str=foo +#bar.baz=(2015,?) ]')
            self.true(outp.expect('#bar.baz = (2015/01/01 00:00:00.000, ?)', throw=False))
            self.false(outp.expect('#bar ', throw=False))
            outp.expect('complete. 1 nodes')

    async def test_log(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            with self.getTestSynDir() as dirn:

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                await cmdr.runCmdLine('log --on --format jsonl')
                fp = cmdr.locs.get('log:fp')
                await cmdr.runCmdLine('storm [test:str=hi :tick=2018 +#haha.hehe]')
                await cmdr.runCmdLine('log --off')
                await cmdr.fini()

                self.true(outp.expect('Starting logfile'))
                self.true(outp.expect('Closing logfile'))
                self.true(os.path.isfile(fp))

                # Ensure that jsonl is how the data was saved
                with s_common.genfile(fp) as fd:
                    genr = s_encoding.iterdata(fd, close_fd=False, format='jsonl')
                    objs = list(genr)
                self.eq(objs[0][0], 'init')

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                # Our default format is mpk
                fp = os.path.join(dirn, 'loggyMcLogFace.mpk')
                await cmdr.runCmdLine(f'log --on --splices-only --path {fp}')
                fp = cmdr.locs.get('log:fp')
                await cmdr.runCmdLine('storm [test:str="I am a message!" :tick=1999 +#oh.my] ')
                await cmdr.runCmdLine('log --off')
                await cmdr.fini()

                self.true(os.path.isfile(fp))
                with s_common.genfile(fp) as fd:
                    genr = s_encoding.iterdata(fd, close_fd=False, format='mpk')
                    objs = list(genr)
                self.eq(objs[0][0], 'node:add')

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                # Our default format is mpk
                fp = os.path.join(dirn, 'loggyMcNodeFace.mpk')
                await cmdr.runCmdLine(f'log --on --nodes-only --path {fp}')
                fp = cmdr.locs.get('log:fp')
                await cmdr.runCmdLine('storm [test:str="I am a message!" :tick=1999 +#oh.my] ')
                await cmdr.runCmdLine('log --off')
                await cmdr.fini()

                self.true(os.path.isfile(fp))
                with s_common.genfile(fp) as fd:
                    genr = s_encoding.iterdata(fd, close_fd=False, format='mpk')
                    objs = list(genr)
                self.eq(objs[0][0], ('test:str', 'I am a message!'))

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                await cmdr.runCmdLine('log --on --off')
                await cmdr.fini()
                self.true(outp.expect('log: error: argument --off: not allowed with argument --on'))

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                await cmdr.runCmdLine('log')
                await cmdr.fini()
                self.true(outp.expect('log: error: one of the arguments --on --off is required'))

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                await cmdr.runCmdLine('log --on --splices-only --nodes-only')
                await cmdr.fini()
                e = 'log: error: argument --nodes-only: not allowed with argument --splices-only'
                self.true(outp.expect(e))

    async def test_storm_save_nodes(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            dirn = s_common.gendir(core.dirn, 'junk')
            path = os.path.join(dirn, 'nodes.jsonl')

            await core.nodes('[ test:int=20 test:int=30 ]')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(prox, outp=outp)
            await cmdr.runCmdLine(f'storm --save-nodes {path} test:int')
            outp.expect('2 nodes')

            jsdata = [item for item in s_common.jslines(path)]
            self.len(2, jsdata)
            self.eq(jsdata[0][0], ('test:int', 20))

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
