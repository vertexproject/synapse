import sys

import synapse.exc as s_exc

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.parser as s_parser

desc = 'Validate Storm query syntax.'

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.validate', outp=outp, description=desc)
    pars.add_argument('file', help='Path to a .storm file to validate (use - for stdin).')
    pars.add_argument('--mode', '-m', default='storm', choices=('storm', 'lookup'),
                      help='Parse mode (default: storm).')

    opts = pars.parse_args(argv)

    if opts.file == '-':
        text = sys.stdin.read()
    else:
        with open(opts.file, 'r') as fd:
            text = fd.read()

    if text is None or text.strip() == '':
        outp.printf('No Storm query text provided.')
        return 1

    try:
        s_parser.parseQuery(text, mode=opts.mode)
    except s_exc.BadSyntax as e:
        mesg = e.get('mesg', 'Unknown syntax error')
        line = e.get('line')
        column = e.get('column')
        parts = [f'BadSyntax: {mesg}']
        if line is not None:
            parts.append(f'  line: {line}')

        if column is not None:
            parts.append(f'  column: {column}')

        outp.printf('\n'.join(parts))
        return 1

    outp.printf('ok')
    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
