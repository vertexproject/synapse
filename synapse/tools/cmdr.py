import synapse.cortex as s_cortex
import synapse.cmds.cortex as s_cmds_cortex

import synapse.lib.cli as s_cli
import synapse.lib.tufo as s_tufo
import synapse.lib.scope as s_scope

def main(argv):

    if len(argv) > 1:
        core = s_cortex.openurl(argv[1])
        s_scope.set('syn:cmd:core',core)

    cli = s_cmds_cortex.initCoreCli()
    cli.cmdprompt = 'core> '
    cli.runCmdLoop()

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
