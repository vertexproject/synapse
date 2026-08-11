import logging
import tempfile

import synapse.common as s_common

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.mdstorm as s_mdstorm

logger = logging.getLogger(__name__)

prog = 'synapse.tools.utils.mdstorm'
descr = 'A Markdown pre-processor that allows you to embed mdstorm directives as fenced code blocks.'

def _formatFlagInvocation(action):
    '''
    Render a single argparse action's flag (and its value placeholder, if
    any) the way it would appear on a fenced directive's flag line, e.g.
    "--vars VARS" or "--hide-query" for a boolean flag. A positional
    argument (e.g. mdinclude's "path") has no option_strings, so it is
    rendered as just its metavar/dest instead of a "--flag" form.

    Args:
        action (argparse.Action): The action to render.

    Returns:
        str: The flag invocation text.
    '''
    if not action.option_strings:
        return action.metavar or action.dest.upper()
    optstr = action.option_strings[0]
    if action.nargs == 0:
        return optstr
    metavar = action.metavar or action.dest.upper()
    return f'{optstr} {metavar}'

async def _getDirectiveHelp():
    '''
    Instantiate MdStorm against a throwaway, empty Markdown file purely to
    inspect its .handlers -- (argparser, callback) tuples -- and render each
    directive's recognized flags for --help, without executing anything.

    Returns:
        str: A --help epilog listing each directive and its flags as Markdown.
    '''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md') as fd:
        async with await s_mdstorm.MdStorm.anit(fd.name) as mdstorm:
            handlers = dict(mdstorm.handlers)

    sections = []
    for name in sorted(handlers):
        parser, _ = handlers[name]
        bullets = '\n'.join(f'- `{_formatFlagInvocation(action)}`: {action.help}' for action in parser._actions)
        sections.append(f'### ```{name}\n\n{bullets}')

    return '## Available mdstorm directives\n\n' + '\n\n'.join(sections)

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog=prog, outp=outp, description=descr, epilog=await _getDirectiveHelp())
    pars.add_argument('mdfile', help='Input Markdown file with fenced storm directives.')
    pars.add_argument('--save', help='Output file to save (default: stdout)')
    pars.add_argument('--mock-http', help='A VCR cassette YAML file to record/replay HTTP calls made by '
                                           'every mdstorm query in the document.')

    opts = pars.parse_args(argv)

    async with await s_mdstorm.MdStorm.anit(opts.mdfile, mockhttp=opts.mock_http) as mdstorm:
        lines = await mdstorm.run()

    if opts.save:
        with open(s_common.genpath(opts.save), 'w') as fd:
            fd.truncate(0)
            [fd.write(line) for line in lines]
    else:
        for line in lines:
            outp.printf(line, addnl=False)

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
