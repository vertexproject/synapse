import sys
import asyncio
import argparse

import synapse.exc as s_exc

import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.urlhelp as s_urlhelp

descr = '''
Promote a mirror to the leader.

Example (being run from a Cortex mirror docker container):
    python -m synapse.tools.promote
'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.promote', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('--svcurl', default='cell:///vertex/storage',
                      help='The telepath URL of the Synapse service.')

    pars.add_argument('--failure', default=False, action='store_true',
                      help='Promotion is due to leader being offline. Graceful handoff is not possible.')

    # TODO pars.add_argument('--timeout', type=float, default=30.0, help='The maximum timeout to wait for the mirror to catch up.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.svcurl) as cell:

            graceful = not opts.failure

            outp.printf(f'Promoting to leader: {opts.svcurl}')
            try:
                await cell.promote(graceful=graceful)
            except s_exc.BadState as e:
                mesg = f'Failed to promote service to being a leader; {e.get("mesg")}'
                outp.printf(mesg)
                return 1
            except s_exc.SynErr as e:
                outp.printf(f'Failed to promote service {s_urlhelp.sanitizeUrl(opts.svcurl)}: {e}')
                return 1

    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
