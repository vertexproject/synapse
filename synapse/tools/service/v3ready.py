import argparse

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

descr = '''
Check or prepare a Synapse service for the upgrade to Synapse 3.x. Run it against the leader.

Examples:
    python -m synapse.tools.service.v3ready check
    python -m synapse.tools.service.v3ready --url aha://optic... prepare
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

    pars = s_cmd.Parser(prog='synapse.tools.service.v3ready', outp=outp, description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')

    subpars = pars.add_subparsers(dest='action', required=True)

    subpars.add_parser('check', help='Check the service for readiness to upgrade to Synapse 3.x.')

    prep = subpars.add_parser('prepare', help='Prepare the service to upgrade to Synapse 3.x, then check it.')
    prep.add_argument('--check', default=True, action=argparse.BooleanOptionalAction,
                      help='Check the service after preparing it.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as cell:

            try:
                if opts.action == 'prepare':
                    if not await printMesgs(outp, cell.prepareV3()):
                        outp.printf('The service could not be prepared for Synapse 3.x.')
                        return 1

                    if not opts.check:
                        return 0

                if await printMesgs(outp, cell.checkV3Ready()):
                    outp.printf('The service is ready for Synapse 3.x.')
                    return 0

                outp.printf('The service is not ready for Synapse 3.x.')
                return 1

            except s_exc.SynErr as exc:
                mesg = exc.get('mesg')
                outp.printf(f'ERROR: {exc.__class__.__name__}: {mesg}')
                return 1

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
