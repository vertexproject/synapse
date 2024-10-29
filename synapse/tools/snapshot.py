import sys
import asyncio
import logging
import argparse

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

desc = '''
Command line tool to freeze/resume service operations to allow
system admins to generate a transactionally consistent volume
snapshot using 3rd party tools.

The use pattern should be::

    python -m synapse.tools.snapshot freeze

    <generate volume snapshot using 3rd party tools>

    python -m synapse.tools.snapshot resume

The tool will set the process exit code to 0 on success.
'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser('synapse.tools.snapshot',
                        description=desc,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    subs = pars.add_subparsers(required=True, title='commands', dest='cmd')

    freeze = subs.add_parser('freeze', help='Suspend edits and sync changes to disk.')
    freeze.add_argument('--timeout', type=int, default=120,
                        help='Maximum time to wait for the nexus lock.')

    freeze.add_argument('--svcurl', default='cell:///vertex/storage',
                        help='The telepath URL of the Synapse service.')

    resume = subs.add_parser('resume', help='Resume edits and continue normal operation.')
    resume.add_argument('--svcurl', default='cell:///vertex/storage',
                        help='The telepath URL of the Synapse service.')

    opts = pars.parse_args(argv)

    try:
        async with s_telepath.withTeleEnv():

            async with await s_telepath.openurl(opts.svcurl) as proxy:

                if opts.cmd == 'freeze':
                    await proxy.freeze(timeout=opts.timeout)
                    return 0

                if opts.cmd == 'resume':
                    await proxy.resume()
                    return 0

    except s_exc.SynErr as e:
        mesg = e.errinfo.get('mesg')
        outp.printf(f'ERROR {e.__class__.__name__}: {mesg}')
        return 1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
