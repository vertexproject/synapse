import json

import synapse.cores.common as s_cores_commmon


import synapse.lib.cli as s_cli
import synapse.lib.auth as s_auth
import synapse.lib.tufo as s_tufo
import synapse.lib.storm as s_storm

class AuthCmd(s_cli.Cmd):
    '''
    WORDS ARE HARD LETS GO AUTHING
    '''
    _cmd_name = 'auth'
    _cmd_syntax = (
        ('--list', {}),
    )
    def runCmdOpts(self, opts):
        print(opts)

        core = self.getCmdItem()  # type: s_auth.AuthMixin

        if opts.get('list'):
            users = core.authGetUsers()
            s = json.dumps(users, indent=2, sort_keys=True)
            self.printf(s)
