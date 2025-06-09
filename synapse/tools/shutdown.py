import asyncio
import argparse

import synapse.telepath as s_telepath
import synapse.lib.output as s_output

desc = '''
Initiate a graceful shutdown of a service.

This tool is designed to put the service into a state where
any non-background tasks will be allowed to complete while ensuring
no new tasks are created. Without a timeout, it can block forever if
tasks do not exit.

The command exits with code 0 if the graceful shutdown was successful and
exit code 1 if a timeout was specified and was hit. Uppon hitting the timeout
the system resumes normal operation.
'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser('synapse.tools.shutdown', description=desc)

    pars.add_argument('--url', default='cell:///vertex/storage',
                        help='THe telepath URL to connect to the service.')

    pars.add_argument('--timeout', default=None, type=int,
                        help='An optional timeout in seconds. If timeout is reached, the shutdown is aborted.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as proxy:

            if await proxy.shutdown(timeout=opts.timeout):
                return(0)

            return(1)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
