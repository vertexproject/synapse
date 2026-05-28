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

When --drain is provided, the service may drain itself of tasks that it is
running, allowing the operator to bound shutdown wall time. Demote is still
attempted within the timeout; only the task-wait phase changes.

The --timeout value bounds the entire operation. Demote discovery, demote,
and task reaping share the single timeout value; no sub-phase may exceed
the time remaining when it starts.

Exit codes:
  0 - graceful shutdown was initiated successfully
  1 - the shutdown was aborted because the timeout was reached; the
      service may be in a partially shutdown state as a result of this
      timeout.
  2 - an unexpected error occurred

NOTE: This will also demote the service if run on a leader with mirrors.
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.service.shutdown', outp=outp, description=desc)

    pars.add_argument('--url', default='cell:///vertex/storage',
                        help='The telepath URL to connect to the service.')

    pars.add_argument('--timeout', default=None, type=int,
                        help='An optional timeout in seconds. If timeout is reached, the shutdown is aborted.')

    pars.add_argument('--drain', default=False, action='store_true',
                        help='Drain the service of running tasks instead of awaiting them.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        try:

            async with await s_telepath.openurl(opts.url) as proxy:

                kwargs = {'timeout': opts.timeout}

                if opts.drain:
                    supported = proxy._hasTeleFeat('shutdowndrain', vers=1)
                    if not supported:
                        outp.printf(f'Service at {opts.url} does not support the --drain feature.')
                        return 2

                    kwargs['drain'] = True

                if await proxy.shutdown(**kwargs):
                    return 0

                return 1

        except Exception as e:
            text = s_exc.reprexc(e)
            outp.printf(f'Error while attempting graceful shutdown: {text}')
            return 2

if __name__ == '__main__': # pragma: no cover
    s_cmd.exitmain(main)
