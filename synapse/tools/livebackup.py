import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

descr = '''
Generate a new backup of a running Synapse service.

Examples:

    # Generate a backup from inside a Synapse service container
    python -m synapse.tools.livebackup

'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.livebackup', outp=outp, description=descr)

    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')
    pars.add_argument('--name', default=None, help='Specify a name for the backup.  Defaults to an automatically generated timestamp.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as cell:
            outp.printf(f'Running backup of: {opts.url}')
            name = await cell.runBackup(name=opts.name)
            outp.printf(f'...backup created: {name}')
    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
