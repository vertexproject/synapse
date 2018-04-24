import regex

import synapse.lib.cmdr as s_cmdr

from synapse.tests.common import *

class SynCmdCoreTest(SynTest, TstMixin):
    def test_cmds_auth(self):
        with self.getSslCore() as proxies:
            uprox, rprox = proxies  # type: s_cores_common.CoreApi, s_cores_common.CoreApi

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            cmdr.runCmdLine('auth --type user --act get')
            self.true(outp.expect('root@localhost'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            cmdr.runCmdLine('auth --type role --act get')
            outp.expect("'roles': ()")

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --name creator --type role')
            self.istufo(retn)
            rolefo = retn[1].get('role')
            self.eq(rolefo[0], 'creator')

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --name creator --type role --rule node:add --form *')
            self.istufo(retn)
            self.true(outp.expect("('node:add', {'form': '*'})"))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            cmdr.runCmdLine('ask [strform="giggles"]')
            self.true(outp.expect('AuthDeny'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --name root@localhost --role creator')
            self.true(outp.expect("'roles': ('creator',)"))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            cmdr.runCmdLine('ask [strform="giggles"]')
            self.true(outp.expect('strform = giggles'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --name user@localhost --act add')
            self.true(outp.expect('user@localhost'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --name user@localhost --role creator')
            self.true(outp.expect('user@localhost'))
            self.true(outp.expect("'roles': ('creator',)"))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role --name creator --rule node:tag:add --tag *')
            self.true(outp.expect("('node:tag:add', {'tag': '*'})"))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(uprox, outp=outp)
            retn = cmdr.runCmdLine('ask [strform=hehe] addtag(yes.no)')
            self.true(outp.expect('strform = hehe'))
            self.true(outp.expect('#yes.no'))
