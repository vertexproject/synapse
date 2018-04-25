import regex

import synapse.lib.cmdr as s_cmdr

from synapse.tests.common import *

class SynCmdCoreTest(SynTest, TstMixin):
    def test_cmds_auth(self):
        with self.getSslCore() as proxies:
            uprox, rprox = proxies  # type: s_cores_common.CoreApi, s_cores_common.CoreApi

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            cmdr.runCmdLine('auth --type user')
            self.true(outp.expect('root@localhost'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            cmdr.runCmdLine('auth --type role')
            outp.expect("'roles': ()")

            # Get our user
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            cmdr.runCmdLine('auth --act get --name root@localhost')
            self.true(outp.expect('root@localhost'))

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
            retn = cmdr.runCmdLine('ask [strform=hehe] addtag(yes.no) addtag(hehe.haha)')
            self.true(outp.expect('strform = hehe'))
            self.true(outp.expect('#yes.no'))
            self.true(outp.expect('#hehe.haha'))

            # uprox is not admin and cannot do auth things
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(uprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role --name creator --rule node:tag:del --tag yes')
            self.none(retn)
            self.true(outp.expect('AuthDeny'))

            # rprox is an admin so he can add the tag deletion rule
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role --name creator --rule node:tag:del --tag yes')
            self.true(outp.expect("('node:tag:del', {'tag': 'yes'})"))

            # Uprox can now delete tags
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(uprox, outp=outp)
            retn = cmdr.runCmdLine('ask strform=hehe deltag(yes.no)')
            self.true(outp.expect('strform = hehe'))
            self.true(outp.expect('#yes'))
            self.false(outp.expect('#yes.no', throw=False))

            # delete a rule
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act del --type role --name creator --rule node:tag:add --tag *')
            self.false(outp.expect("('node:tag:add', {'tag': '*'})", throw=False))

            # Add a node:prop:set rule
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role --name creator --rule node:prop:set --prop '
                                   'foo --form strform')
            self.true(outp.expect("('node:prop:set', {'form': 'strform', 'prop': 'foo'})"))

            # We can elevate user to admin
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --name user@localhost --admin')
            self.true(outp.expect("('user@localhost', {'admin': True"))

            # Uprox can now do admin things like remove his admin bit
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(uprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act del --name user@localhost --admin')
            self.true(outp.expect("('user@localhost', {'admin': False"))

            # We can have json output
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --name root@localhost --json')
            self.true(outp.expect(json.dumps(retn, sort_keys=True, indent=2)))

            # Cannot make rules with invalid combinations
            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role --name creator --rule node:add --tag yes --form '
                                   'intform')
            self.true(outp.expect('Cannot form rulefo with tag and (form OR prop)'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role --name creator --rule node:add --tag yes --prop '
                                   'intform:foo')
            self.true(outp.expect('Cannot form rulefo with tag and (form OR prop)'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role --name creator --rule node:add --prop clown:foo')
            self.true(outp.expect('Unable to form rulefo'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role --name creator --rule node:add')
            self.true(outp.expect('Unable to form rulefo'))

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            retn = cmdr.runCmdLine('auth --act add --type role')
            self.true(outp.expect('Action requires a name'))
