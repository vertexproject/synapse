import regex

import synapse.lib.cmdr as s_cmdr
import synapse.cmds.cortex as s_cmds_cortex

from synapse.tests.common import *

class SynCmdCoreTest(SynTest):

    def test_cmds_ask(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask inet:email="visi@vertex.link"')
            self.len(1, resp['data'])
            self.true(outp.expect('visi@vertex.link'))

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

    def test_cmds_ask_debug(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask --debug inet:email="visi@vertex.link"')
            self.len(1, resp['data'])

            outp = str(outp)
            terms = ('oplog', 'took', 'options', 'limits')

            for term in terms:
                self.nn(regex.search(term, outp))

    def test_cmds_ask_props(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask --props inet:email="visi@vertex.link"')
            self.len(1, resp['data'])

            outp = str(outp)
            terms = ('fqdn = vertex.link', 'user = visi')

            for term in terms:
                self.nn(regex.search(term, outp))

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

    def test_cmds_ask_raw(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask --raw inet:email="visi@vertex.link"')
            self.len(1, resp['data'])

            outp = str(outp)
            terms = ('"tufo:form": "inet:email"', '"inet:email:user": "visi"')
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

    def test_cmds_ask_noopts(self):
        with self.getDmonCore() as core:
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask')
            self.nn(regex.search('Examples:', str(outp)))
