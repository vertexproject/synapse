import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

desc = '''
Initiate a graceful shutdown of a service.

This tool is designed to put the service into a state where
any non-background tasks will be allowed to complete while ensuring
no new tasks are created. Without a timeout, it can block forever if
tasks do not exit.

The command exits with code 0 if the graceful shutdown was successful and
exit code 1 if a timeout was specified and was hit. Upon hitting the timeout
the system resumes normal operation.

NOTE: This will also demote the service if run on a leader with mirrors.
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.shutdown', outp=outp, description=desc)

    pars.add_argument('--url', default='cell:///vertex/storage',
                        help='The telepath URL to connect to the service.')

    pars.add_argument('--timeout', default=None, type=int,
                        help='An optional timeout in seconds. If timeout is reached, the shutdown is aborted.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        try:

            async with await s_telepath.openurl(opts.url) as proxy:

                if await proxy.shutdown(timeout=opts.timeout):
                    return 0

                return 1

        except Exception as e: # pragma: no cover
            text = s_exc.reprexc(e)
            outp.printf(f'Error while attempting graceful shutdown: {text}')
            return 1

if __name__ == '__main__': # pragma: no cover
    s_cmd.exitmain(main)
