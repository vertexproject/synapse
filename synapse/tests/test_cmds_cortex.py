import os
import asyncio

import synapse.common as s_common

import synapse.lib.cmdr as s_cmdr
import synapse.lib.encoding as s_encoding
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils

from synapse.tests.utils import alist


class CmdCoreTest(s_t_utils.SynTest):

    async def test_storm(self):

        help_msg = 'Execute a storm query.'

        async with self.getTestCoreAndProxy() as (realcore, core):

            await realcore.addTagProp('score', ('int', {}), {})

            await self.agenlen(1, core.eval("[ test:str=abcd :tick=2015 +#cool]"))

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
            await cmdr.runCmdLine('storm --show-nodeedits [test:int=42]')
            outp.expect('node:edits')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --editformat count [test:int=43]')
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
            outp.expect('Syntax Error')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm newpz')
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
            await cmdr.runCmdLine('storm --show-prov [ test:str=foo +#bar.baz=(2015,?) ]')
            self.true(outp.expect('prov:new'))
            self.true(outp.expect('....\ntest:str'))
            self.true(outp.expect('#bar.baz = (2015/01/01 00:00:00.000, ?)', throw=False))
            self.false(outp.expect('#bar ', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm [ test:str=foo +#bar:score=22 +#bar.baz:score=0 ]')
            self.true(outp.expect('#bar:score = 22', throw=False))
            self.true(outp.expect('#bar.baz = (2015/01/01 00:00:00.000, ?)', throw=False))
            self.true(outp.expect('#bar.baz:score = 0', throw=False))
            self.false(outp.expect('#bar ', throw=False))
            outp.expect('complete. 1 nodes')

            # Warning test
            guid = s_common.guid()
            await alist(core.eval(f'[test:guid={guid}]'))
            await alist(core.eval(f'[test:edge=(("test:guid", {guid}), ("test:str", abcd))]'))

            q = 'storm test:str=abcd <- test:edge :n1:form -> *'
            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine(q)
            e = 'WARNING: The source property "n1:form" type "str" is not a form. Cannot pivot.'
            self.true(outp.expect(e))

            # Err case
            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm test:str -> test:newp')
            self.true(outp.expect('ERROR'))
            self.true(outp.expect('NoSuchProp'))
            self.true(outp.expect('test:newp'))

            # Cancelled case
            evnt = asyncio.Event()
            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

            def setEvt(event):
                smsg = event[1].get('mesg')
                if smsg[0] == 'node':
                    evnt.set()

            async def runLongStorm():
                with cmdr.onWith('storm:mesg', setEvt):
                    await cmdr.runCmdLine('storm .created | sleep 10')

            task = realcore.schedCoro(runLongStorm())
            self.true(await asyncio.wait_for(evnt.wait(), timeout=6))
            ps = await core.ps()
            self.len(1, ps)
            iden = ps[0].get('iden')
            await core.kill(iden)
            await asyncio.sleep(0)
            self.true(outp.expect('query canceled.'))
            self.true(task.done())

            # Color test
            outp.clear()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine(f'storm test:{"x"*50} -> * -> $')
            outp.expect('-> *')
            outp.expect('Syntax Error')

            outp.clear()
            with self.withCliPromptMock() as patch:
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                cmdr.colorsenabled = True
                await cmdr.runCmdLine('storm [#foo]')
                await cmdr.runCmdLine('storm test:str ->')
            lines = self.getMagicPromptColors(patch)
            clines = []
            for (color, text) in lines:
                if text.startswith('Syntax Error:'):
                    text = 'Syntax Error'
                clines.append((color, text))
            self.isin(('#6faef2', '[#foo]'), clines)
            self.isin(('#6faef2', ' ^'), clines)
            self.isin(('#ff0066', 'Syntax Error'), clines)
            self.isin(('#6faef2', 'test:str ->'), clines)
            self.isin(('#6faef2', '           ^'), clines)

            # Trying to print an \r doesn't assert (prompt_toolkit bug)
            # https://github.com/prompt-toolkit/python-prompt-toolkit/issues/915
            await core.addNode('test:str', 'foo', props={'hehe': 'windows\r\nwindows\r\n'})
            await cmdr.runCmdLine('storm test:str=foo')
            self.true(1)

            await realcore.nodes('[ inet:ipv4=1.2.3.4 +#visi.woot ]')
            await s_lmdbslab.Slab.syncLoopOnce()

            # The storm --spawn option works
            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
            await cmdr.runCmdLine('storm --spawn inet:ipv4=1.2.3.4')
            outp.expect('#visi.woot')

    async def test_log(self):

        def check_locs_cleanup(cobj):
            keys = list(cobj.locs.keys())
            for key in keys:
                if key.startswith('log:'):
                    self.fail(f'Key with "log:" prefix found. [{key}]')

        async with self.getTestCoreAndProxy() as (realcore, core):

            with self.getTestSynDir() as dirn:

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                await cmdr.runCmdLine('log --on --format jsonl')
                fp = cmdr.locs.get('log:fp')
                await cmdr.runCmdLine('storm --editformat splices [test:str=hi :tick=2018 +#haha.hehe]')

                await cmdr.runCmdLine('storm --editformat nodeedits [test:str=hi2 :tick=2018 +#haha.hehe]')
                await cmdr.runCmdLine('storm [test:comp=(42, bar)]')

                # Try calling on a second time - this has no effect on the
                # state of cmdr, but prints a warning
                await cmdr.runCmdLine('log --on --format jsonl')

                await cmdr.runCmdLine('log --off')
                await cmdr.fini()
                check_locs_cleanup(cmdr)

                self.true(outp.expect('Starting logfile'))
                e = 'Must call --off to disable current file before starting a new file.'
                self.true(outp.expect(e))
                self.true(outp.expect('Closing logfile'))
                self.true(os.path.isfile(fp))

                # Ensure that jsonl is how the data was saved
                with s_common.genfile(fp) as fd:
                    genr = s_encoding.iterdata(fd, close_fd=False, format='jsonl')
                    objs = list(genr)
                self.eq(objs[0][0], 'init')

                nodeedits = [m for m in objs if m[0] == 'node:edits']
                self.ge(len(nodeedits), 2)

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                # Our default format is mpk
                fp = os.path.join(dirn, 'loggyMcLogFace.mpk')
                await cmdr.runCmdLine(f'log --on --edits-only --path {fp}')
                fp = cmdr.locs.get('log:fp')
                await cmdr.runCmdLine('storm [test:str="I am a message!" :tick=1999 +#oh.my] ')
                await cmdr.runCmdLine('log --off')
                await cmdr.fini()
                check_locs_cleanup(cmdr)

                self.true(os.path.isfile(fp))
                with s_common.genfile(fp) as fd:
                    genr = s_encoding.iterdata(fd, close_fd=False, format='mpk')
                    objs = list(genr)

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                # Our default format is mpk
                fp = os.path.join(dirn, 'loggyMcNodeFace.mpk')
                await cmdr.runCmdLine(f'log --on --nodes-only --path {fp}')
                fp = cmdr.locs.get('log:fp')
                await cmdr.runCmdLine('storm [test:str="I am a message!" :tick=1999 +#oh.my] ')
                await cmdr.runCmdLine('log --off')
                await cmdr.fini()
                check_locs_cleanup(cmdr)

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
                await cmdr.runCmdLine('log --on --edits-only --nodes-only')
                await cmdr.fini()
                e = 'log: error: argument --nodes-only: not allowed with argument --edits-only'
                self.true(outp.expect(e))

                # Bad internal state
                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)
                await cmdr.runCmdLine('log --on --nodes-only')
                cmdr.locs['log:fmt'] = 'newp'
                with self.getAsyncLoggerStream('synapse.cmds.cortex',
                                               'Unknown encoding format: newp') as stream:
                    await cmdr.runCmdLine('storm test:str')
                    self.true(await stream.wait(2))

                await cmdr.fini()

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
            self.eq({tuple(n[0]) for n in jsdata},
                    {('test:int', 20), ('test:int', 30)})

    async def test_storm_file_optfile(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            test_opts = {'vars': {'hehe': 'woot.com'}}
            dirn = s_common.gendir(core.dirn, 'junk')

            optsfile = os.path.join(dirn, 'woot.json')
            optsfile_yaml = os.path.join(dirn, 'woot.yaml')
            stormfile = os.path.join(dirn, 'woot.storm')

            with s_common.genfile(stormfile) as fd:
                fd.write(b'[ inet:fqdn=$hehe ]')

            s_common.jssave(test_opts, optsfile)
            s_common.yamlsave(test_opts, optsfile_yaml)

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(prox, outp=outp)
            await cmdr.runCmdLine(f'storm --optsfile {optsfile} --file {stormfile}')
            self.true(outp.expect('inet:fqdn=woot.com'))

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(prox, outp=outp)
            await cmdr.runCmdLine(f'storm --optsfile {optsfile_yaml} --file {stormfile}')
            self.true(outp.expect('inet:fqdn=woot.com'))

            # Sad path cases
            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(prox, outp=outp)
            await cmdr.runCmdLine(f'storm --file {stormfile} --optsfile {optsfile} .created')
            self.true(outp.expect('Cannot use a storm file and manual query together.'))
            self.false(outp.expect('inet:fqdn=woot.com', throw=False))

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(prox, outp=outp)
            await cmdr.runCmdLine(f'storm --file {stormfile} --optsfile newp')
            self.true(outp.expect('optsfile not found'))

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(prox, outp=outp)
            await cmdr.runCmdLine(f'storm --file newp --optsfile {optsfile}')
            self.true(outp.expect('file not found'))
