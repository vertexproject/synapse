# stdlib
# third party code
# custom code
import synapse.lib.cli as s_cli
import synapse.common as s_common

class GuidCmd(s_cli.Cmd):
    '''
    Generate a new guid

    Examples:

        guid

    '''

    _cmd_name = 'guid'
    _cmd_syntax = ()

    def runCmdOpts(self, opts):
        self.printf('new guid: %r' % (s_common.guid(),))
