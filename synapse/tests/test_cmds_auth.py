import regex

import synapse.lib.cmdr as s_cmdr

from synapse.tests.common import *

class SynCmdCoreTest(SynTest, TstMixin):
    def test_cmds_auth_list(self):
        with self.getSslCore() as proxies:
            uprox, rprox = proxies  # type: s_cores_common.CoreApi, s_cores_common.CoreApi

            outp = self.getTestOutp()
            cmdr = s_cmdr.getItemCmdr(rprox, outp=outp)
            cmdr.runCmdLine('auth --list')
            outp.expect('"root@localhost"')
            print(outp)
