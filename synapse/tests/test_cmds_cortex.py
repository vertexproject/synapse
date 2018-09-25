import os
import synapse.common as s_common

import synapse.lib.cmdr as s_cmdr
import synapse.lib.scope as s_scope
import synapse.lib.msgpack as s_msgpack
import synapse.lib.encoding as s_encoding

import synapse.tests.utils as s_t_utils


class CmdCoreTest(s_t_utils.SynTest):

    async def test_storm(self):
        help_msg = 'Execute a storm query.'
        async with self.getTestCore() as core:
            with await core.snap() as snap:
                valu = 'abcd'
                node = await snap.addNode('teststr', valu, props={'tick': 123})
                node.addTag('cool')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('help storm')
            outp.expect(help_msg)

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm help')
            outp.expect('For detailed help on any command')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm')
            outp.expect(help_msg)

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm --debug teststr=abcd')
            outp.expect("('init',")
            outp.expect("('node',")
            outp.expect("('fini',")
            outp.expect("tick")
            outp.expect("tock")
            outp.expect("took")

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm --debug teststr=zzz')
            outp.expect("('init',")
            self.false(outp.expect("('node',", throw=False))
            outp.expect("('fini',")
            outp.expect("tick")
            outp.expect("tock")
            outp.expect("took")

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm teststr=b')
            outp.expect('complete. 0 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm teststr=abcd')
            outp.expect(':tick = 1970/01/01 00:00:00.123')
            outp.expect('#cool = (None, None)')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm --hide-tags teststr=abcd')
            outp.expect(':tick = 1970/01/01 00:00:00.123')
            self.false(outp.expect('#cool = (None, None)', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm --hide-props teststr=abcd')
            self.false(outp.expect(':tick = 1970/01/01 00:00:00.123', throw=False))
            outp.expect('#cool = (None, None)')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm --hide-tags --hide-props teststr=abcd')
            self.false(outp.expect(':tick = 1970/01/01 00:00:00.123', throw=False))
            self.false(outp.expect('#cool = (None, None)', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm --raw teststr=abcd')
            outp.expect("'tick': 123")
            outp.expect("'tags': {'cool': (None, None)")
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm --bad')
            outp.expect('Traceback')
            outp.expect('BadStormSyntax')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm newpz')
            outp.expect('err')
            outp.expect('NoSuchProp')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('storm --hide-unknown [teststr=1234]')
            s = str(outp)
            self.notin('node:add', s)
            self.notin('prop:set', s)

            self.len(1, core.eval('[testcomp=(1234, 5678)]'))
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            q = 'storm --raw --path testcomp -> testint'
            cmdr.runCmdLine(q)
            self.true(outp.expect("('testint', 1234)"))
            self.true(outp.expect("'path'"))

    def test_log(self):
        async with self.getTestDmon('dmoncore') as dmon:
            dirn = s_scope.get('dirn')
            with self.setSynDir(dirn):
                with self.getTestProxy(dmon, 'core') as core:
                    breakpoint()
                    outp = self.getTestOutp()
                    cmdr = s_cmdr.getItemCmdr(core, outp=outp)
                    cmdr.runCmdLine('log --on --format jsonl')
                    fp = cmdr.locs.get('log:fp')
                    cmdr.runCmdLine('storm [teststr=hi :tick=2018 +#haha.hehe]')
                    cmdr.runCmdLine('log --off')
                    cmdr.fini()

                    self.true(outp.expect('Starting logfile'))
                    self.true(outp.expect('Closing logfile'))
                    self.true(os.path.isfile(fp))

                    # Ensure that jsonl is how the data was saved
                    with s_common.genfile(fp) as fd:
                        genr = s_encoding.iterdata(fd, close_fd=False, format='jsonl')
                        objs = list(genr)
                    self.eq(objs[0][0], 'init')

                with self.getTestProxy(dmon, 'core') as core:
                    outp = self.getTestOutp()
                    cmdr = s_cmdr.getItemCmdr(core, outp=outp)
                    # Our default format is mpk
                    fp = os.path.join(dirn, 'loggyMcLogFace.mpk')
                    cmdr.runCmdLine(f'log --on --splices-only --path {fp}')
                    fp = cmdr.locs.get('log:fp')
                    cmdr.runCmdLine('storm [teststr="I am a message!" :tick=1999 +#oh.my] ')
                    cmdr.runCmdLine('log --off')
                    cmdr.fini()

                    self.true(os.path.isfile(fp))
                    with s_common.genfile(fp) as fd:
                        genr = s_encoding.iterdata(fd, close_fd=False, format='mpk')
                        objs = list(genr)
                    self.eq(objs[0][0], 'node:add')

                with self.getTestProxy(dmon, 'core') as core:
                    outp = self.getTestOutp()
                    cmdr = s_cmdr.getItemCmdr(core, outp=outp)
                    cmdr.runCmdLine('log --on --off')
                    cmdr.fini()
                    self.true(outp.expect('Pick one'))

                    outp = self.getTestOutp()
                    cmdr = s_cmdr.getItemCmdr(core, outp=outp)
                    cmdr.runCmdLine('log')
                    cmdr.fini()
                    self.true(outp.expect('Pick one'))

# FIXME incorporate these into storm tests
'''
class SynCmdCoreTest(s_t_utils.SynTest):

    def test_cmds_storm_showcols(self):
        with self.getDmonCore() as core:
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            core.formTufoByProp('inet:email', 'vertexmc@vertex.link')
            core.formTufoByProp('inet:email', 'z@a.vertex.link')
            core.formTufoByProp('inet:email', 'a@vertex.link')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            line = 'storm inet:email="visi@vertex.link" show:cols(inet:email:fqdn,inet:email:user,node:ndef)'
            resp = cmdr.runCmdLine(line)
            self.len(1, resp['data'])
            self.true(outp.expect('vertex.link visi a20979f71b90cf2ae1c53933675b5c3c'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            line = 'storm inet:email show:cols(inet:email, order=inet:email:fqdn)'
            resp = cmdr.runCmdLine(line)
            self.len(4, resp['data'])
            result = [mesg.strip() for mesg in outp.mesgs]
            self.eq(result, ['z@a.vertex.link', 'a@vertex.link', 'vertexmc@vertex.link', 'visi@vertex.link', '(4 results)'])
'''
