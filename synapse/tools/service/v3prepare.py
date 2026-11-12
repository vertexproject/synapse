import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.cell as s_cell
import synapse.lib.output as s_output

descr = '''
Check a Synapse service for readiness to upgrade to Synapse 3.x and, if the check has no errors, prepare it. Run it
against the leader.

Examples:
    python -m synapse.tools.service.v3prepare --dry-run
    python -m synapse.tools.service.v3prepare --url aha://optic...
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.service.v3prepare', outp=outp, description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')
    pars.add_argument('--dry-run', default=False, action='store_true',
                      help='Only check the service, without preparing it.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as cell:

            ok = True
            try:
                async for name, info in cell.prepareV3(dryrun=opts.dry_run):
                    ok = ok and name != 'error'
                    outp.printf(s_cell.getV3MesgLine(name, info))

            except s_exc.SynErr as exc:
                mesg = exc.get('mesg')
                outp.printf(f'ERROR: {exc.__class__.__name__}: {mesg}')
                return 1

            outp.printf(s_cell.getV3Summary('The service', ok, opts.dry_run))
            if opts.dry_run:
                outp.printf(s_cell.V3_DRYRUN_MESG)

            return 0 if ok else 1

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
