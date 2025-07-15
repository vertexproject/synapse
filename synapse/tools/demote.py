import synapse.exc as s_exc

import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.urlhelp as s_urlhelp

descr = '''
Automatically select a new leader and demote this service.

Example:
    python -m synapse.tools.demote
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.demote', outp=outp, description=descr)

    pars.add_argument('--url', default='cell:///vertex/storage',
                      help='The telepath URL of the Synapse service.')

    pars.add_argument('--timeout', type=int, default=60,
                      help='The timeout to use awaiting network connections.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        try:

            async with await s_telepath.openurl(opts.url) as cell:

                outp.printf(f'Demoting leader: {opts.url}')

                if await cell.demote(timeout=opts.timeout):
                    return 0

        except s_exc.SynErr as e:
            outp.printf(f'Error while demoting service {s_urlhelp.sanitizeUrl(opts.url)}: {e}')
            return 1

        outp.printf(f'Failed to demote service {s_urlhelp.sanitizeUrl(opts.url)}')
        return 1

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
