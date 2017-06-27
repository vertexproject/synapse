import synapse.lib.cli as s_cli

from synapse.common import *

class GuidCmd(s_cli.Cmd):
    '''
    Generate a new guid

    Examples:

        guid

    '''

    _cmd_name = 'guid'
    _cmd_syntax = ()

    def runCmdOpts(self, opts):
        self.printf('new guid: %r' % (guid(),))

class PyCmd(s_cli.Cmd):
    '''
    Evaluate a line of python code with the cmd item.

    Examples:

        py item.getFooThingByBar('baz')

    '''

    _cmd_name = 'py'
    _cmd_syntax = (
        ('expr',{'type':'glob'}),
    )

    def runCmdOpts(self, opts):
        expr = opts.get('expr')
        item = self.getCmdItem()

        retn = eval(expr,{'item':item,'cmd':self})
        self.printf('returned: %r' % (retn,))
