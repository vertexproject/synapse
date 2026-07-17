import synapse.exc as s_exc

import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.urlhelp as s_urlhelp

descr = '''
Promote a mirror to the leader.

By default this performs a graceful handoff coordinated with the current
leader. Use --failure only when the current leader is confirmed offline;
if it is actually still alive, this will very likely render it unusable.

Example (being run from a Cortex mirror docker container):
    python -m synapse.tools.service.promote
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.service.promote', outp=outp, description=descr)

    pars.add_argument('--url', default='cell:///vertex/storage',
                      help='The telepath URL of the Synapse service.')

    pars.add_argument('--failure', default=False, action='store_true',
                      help='Force promotion because the leader is offline and a graceful handoff is not '
                           'possible. This does NOT stop the old leader from believing it is still the '
                           'leader: if it is actually still alive and reachable, it will very likely '
                           'detect a leadership schism and require a restore from backup. Only use this '
                           'once the old leader is confirmed unreachable/offline.')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as cell:

            outp.printf(f'Promoting to leader: {opts.url}')
            try:
                await cell.promote(force=opts.failure)
            except s_exc.BadState as e:
                mesg = f'Failed to promote service to being a leader; {e.get("mesg")}'
                outp.printf(mesg)
                return 1
            except s_exc.SynErr as e:
                outp.printf(f'Failed to promote service {s_urlhelp.sanitizeUrl(opts.url)}: {e}')
                return 1

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
