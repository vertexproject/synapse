import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

descr = '''
Check a Synapse service for readiness to upgrade to Synapse 3.x and, if the check has no errors, prepare it. Run it
against the leader.

Examples:
    python -m synapse.tools.service.v3prepare --dry-run
    python -m synapse.tools.service.v3prepare --url aha://optic...
'''

async def printMesgs(outp, genr):
    ok = True
    async for name, info in genr:
        if name == 'print':
            outp.printf(info)

        elif name == 'error':
            ok = False
            outp.printf(f'ERROR: {info}')

        elif name == 'warning':
            outp.printf(f'WARNING: {info}')

    return ok

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.service.v3prepare', outp=outp, description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')
    pars.add_argument('--dry-run', default=False, action='store_true',
                      help='Only check the service, without preparing it or recording anything.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as cell:

            try:
                ok = await printMesgs(outp, cell.prepareV3(dryrun=opts.dry_run))

            except s_exc.SynErr as exc:
                mesg = exc.get('mesg')
                outp.printf(f'ERROR: {exc.__class__.__name__}: {mesg}')
                return 1

            if opts.dry_run:
                if ok:
                    outp.printf('The service has no errors blocking Synapse 3.x.')
                else:
                    outp.printf('The service has errors blocking Synapse 3.x.')

                outp.printf('This was a dry run, so nothing was prepared or recorded.')

            elif ok:
                outp.printf('The service is ready for Synapse 3.x.')

            else:
                outp.printf('The service is not ready for Synapse 3.x.')

            return 0 if ok else 1

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
