import synapse.lib.cmdr as s_cmdr
import synapse.tests.common as s_test


class CmdCoreTest(s_test.SynTest):

    def test_ask(self):
        help_msg = 'Execute a storm query.'
        with self.getTestCore() as core:
            with core.snap() as snap:
                valu = 'abcd'
                node = snap.addNode('teststr', valu, props={'tick': 123})
                node.addTag('cool')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('help ask')
            outp.expect(help_msg)

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask help')
            outp.expect('For detailed help on any command')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask')
            outp.expect(help_msg)

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask --debug teststr=abcd')
            outp.expect("('init',")
            outp.expect("('node',")
            outp.expect("('fini',")
            outp.expect("tick")
            outp.expect("tock")
            outp.expect("took")

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask --debug teststr=zzz')
            outp.expect("('init',")
            self.false(outp.expect("('node',", throw=False))
            outp.expect("('fini',")
            outp.expect("tick")
            outp.expect("tock")
            outp.expect("took")

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask teststr=b')
            outp.expect('complete. 0 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask teststr=abcd')
            outp.expect(':tick = 1970/01/01 00:00:00.123')
            outp.expect('#cool = (None, None)')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask --hide-tags teststr=abcd')
            outp.expect(':tick = 1970/01/01 00:00:00.123')
            self.false(outp.expect('#cool = (None, None)', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask --hide-props teststr=abcd')
            self.false(outp.expect(':tick = 1970/01/01 00:00:00.123', throw=False))
            outp.expect('#cool = (None, None)')
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask --hide-tags --hide-props teststr=abcd')
            self.false(outp.expect(':tick = 1970/01/01 00:00:00.123', throw=False))
            self.false(outp.expect('#cool = (None, None)', throw=False))
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask --raw teststr=abcd')
            outp.expect("'tick': 123")
            outp.expect("{'tags': {'cool': (None, None)}")
            outp.expect('complete. 1 nodes')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask --bad')
            outp.expect('Traceback')
            outp.expect('BadStormSyntax')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask newpz')
            outp.expect('err')
            outp.expect('NoSuchProp')

# FIXME incorporate these into storm tests
'''
class SynCmdCoreTest(s_test.SynTest):

    def test_cmds_ask_showcols(self):
        with self.getDmonCore() as core:
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            core.formTufoByProp('inet:email', 'vertexmc@vertex.link')
            core.formTufoByProp('inet:email', 'z@a.vertex.link')
            core.formTufoByProp('inet:email', 'a@vertex.link')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            line = 'ask inet:email="visi@vertex.link" show:cols(inet:email:fqdn,inet:email:user,node:ndef)'
            resp = cmdr.runCmdLine(line)
            self.len(1, resp['data'])
            self.true(outp.expect('vertex.link visi a20979f71b90cf2ae1c53933675b5c3c'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            line = 'ask inet:email show:cols(inet:email, order=inet:email:fqdn)'
            resp = cmdr.runCmdLine(line)
            self.len(4, resp['data'])
            result = [mesg.strip() for mesg in outp.mesgs]
            self.eq(result, ['z@a.vertex.link', 'a@vertex.link', 'vertexmc@vertex.link', 'visi@vertex.link', '(4 results)'])

    def test_cmds_ask_mesgs(self):
        with self.getDmonCore() as core:
            real_core = s_scope.get('syn:core')
            real_core.setOperFunc('test:mesg', mesg_cmd)

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            resp = cmdr.runCmdLine('ask [inet:ipv4=1.2.3.4] test:mesg()')
            self.len(1, resp['data'])
            self.len(2, resp['mesgs'])

            outp.expect('Storm Status Messages:')
            outp.expect('Log test messages')
            outp.expect('Query has [1] nodes')
            print('cli> ask [inet:ipv4=1.2.3.4] test:mesg()')
            print(outp)

    def test_cmds_ask_tagtime(self):

        with self.getDmonCore() as core:

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)

            resp = cmdr.runCmdLine('ask [ inet:ipv4=1.2.3.4 #foo.bar@2011-2016 #baz.faz ]')
            self.len(1, resp['data'])

            lines = [s.strip() for s in str(outp).split('\n')]

            self.true(any([regex.search('^#baz.faz \(added [0-9/: \.]+\)$', l) for l in lines]))
            self.true(any([regex.search('^#foo.bar \(added [0-9/: \.]+\) 2011/01/01 00:00:00.000  -  2016/01/01 00:00:00.000$', l) for l in lines]))

    def test_cmds_ask_mutual_exclusive(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask --raw --props inet:email="visi@vertex.link"')
            self.none(resp)
            self.true(outp.expect('Cannot specify --raw and --props together.'))

    def test_cmds_ask_null_response(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask inet:email="pennywise@vertex.link"')
            self.none(resp)
            self.true(outp.expect('(0 results)'))

    def test_cmds_ask_exc_response(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask inet:dns:a:ipv4*inet:cidr=192.168.0.0/100')
            self.none(resp)

            outp = str(outp)
            terms = ('\(0 results\)',
                     'oplog:',
                     'options:',
                     'limits:')
            for term in terms:
                self.nn(regex.search(term, outp))

    def test_cmds_ask_multilift(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('strform', 'hehe')
            core.formTufoByProp('inet:ipv4', 0)
            resp = cmdr.runCmdLine('ask strform inet:ipv4')
            self.len(2, resp['data'])

            outp = str(outp)
            terms = ('0.0.0.0', 'hehe')

            for term in terms:
                self.nn(regex.search(term, outp))
'''
