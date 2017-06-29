from __future__ import absolute_import, unicode_literals

import re
from contextlib import contextmanager

import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr
import synapse.cmds.cortex as s_cmds_cortex

from synapse.tests.common import *

class SynCmdCoreTest(SynTest):

    @contextmanager
    def getDmonCore(self):

        dmon = s_daemon.Daemon()
        core = s_cortex.openurl('ram:///')

        link = dmon.listen('tcp://127.0.0.1:0/')
        dmon.share('core00', core)
        port = link[1].get('port')
        prox = s_telepath.openurl('tcp://127.0.0.1/core00', port=port)

        s_scope.set('syn:test:link', link)
        #s_scope.set('syn:test:dmon',dmon)

        s_scope.set('syn:cmd:core', prox)

        yield prox

        prox.fini()
        core.fini()
        dmon.fini()

    def getCoreCmdr(self, core):
        outp = s_output.OutPutStr()
        return s_cmdr.getItemCmdr(core, outp=outp)

    def test_cmds_help(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('help')
            self.true(str(outp).find('List commands and display help output.') != -1)

    def test_cmds_quit(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('quit')
            self.true(str(outp).find('o/') != -1)

    def test_cmds_ask(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask inet:email="visi@vertex.link"')
            self.eq(len(resp['data']), 1)
            self.ne(str(outp).strip().find('visi@vertex.link'), -1)

    def test_cmds_ask_debug(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask --debug inet:email="visi@vertex.link"')
            self.eq(len(resp['data']), 1)

            outp = str(outp)
            terms = ('oplog', 'took', 'options', 'limits')

            for term in terms:
                self.nn(re.search(term, outp))

    def test_cmds_ask_props(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask --props inet:email="visi@vertex.link"')
            self.eq(len(resp['data']), 1)

            outp = str(outp)
            terms = ('fqdn = vertex.link', 'user = visi')

            for term in terms:
                self.nn(re.search(term, outp))

    def test_cmds_ask_tagtime(self):

        with self.getDmonCore() as core:

            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)

            resp = cmdr.runCmdLine('ask [ inet:ipv4=1.2.3.4 #foo.bar@2011-2016 #baz.faz ]')
            self.eq(len(resp['data']), 1)

            lines = [s.strip() for s in str(outp).split('\n')]

            self.true(any([re.search('^#baz.faz \(added [0-9/: \.]+\)$', l) for l in lines]))
            self.true(any([re.search('^#foo.bar \(added [0-9/: \.]+\) 2011/01/01 00:00:00.000  -  2016/01/01 00:00:00.000$', l) for l in lines]))

    def test_cmds_ask_mutual_exclusive(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask --raw --props inet:email="visi@vertex.link"')
            self.none(resp)
            outp = str(outp)
            self.true('Cannot specify --raw and --props together.' in outp)

    def test_cmds_ask_null_response(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask inet:email="pennywise@vertex.link"')
            self.none(resp)
            outp = str(outp)
            self.true('(0 results)' in outp)

    def test_cmds_ask_exc_response(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
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
                self.nn(re.search(term, outp))

    def test_cmds_ask_raw(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('inet:email', 'visi@vertex.link')
            resp = cmdr.runCmdLine('ask --raw inet:email="visi@vertex.link"')
            self.eq(len(resp['data']), 1)

            outp = str(outp)
            terms = ('"tufo:form": "inet:email"', '"inet:email:user": "visi"')
            for term in terms:
                self.nn(re.search(term, outp))

    def test_cmds_ask_multilift(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            core.formTufoByProp('str', 'hehe')
            core.formTufoByProp('inet:ipv4', 0)
            resp = cmdr.runCmdLine('ask str inet:ipv4')
            self.eq(len(resp['data']), 2)

            outp = str(outp)
            terms = ('0.0.0.0', 'hehe')

            for term in terms:
                self.nn(re.search(term, outp))

    def test_cmds_ask_noopts(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('ask')
            self.nn(re.search('Examples:', str(outp)))

    def test_cmds_guid(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('guid')
            self.ne(str(outp).find('new guid:'), -1)

    def test_cmds_py(self):
        with self.getDmonCore() as core:
            outp = s_output.OutPutStr()
            cmdr = s_cmdr.getItemCmdr(core, outp=outp)
            cmdr.runCmdLine('py 20 + 20')
            self.ne(str(outp).find('40'), -1)
