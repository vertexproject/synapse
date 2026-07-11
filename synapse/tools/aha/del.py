import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

descr = '''
Remove an AHA service entry from the AHA registry.

This deletes the named service's registration from the AHA server. It does not
stop or uninstall the running service; it only removes the entry so the name
( and its service type ) is freed -- for example before registering a different
service instance in its place. Use synapse.tools.aha.list to find the service
name.

Examples:

    # remove a service entry named 000.cortex from within the AHA container
    python -m synapse.tools.aha.del 000.cortex...

    # remove a service entry from a remote AHA server
    python -m synapse.tools.aha.del --url <telepath-url> 000.cortex...
'''

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.aha.del', outp=outp, description=descr)

    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('svcname', help='The name of the service to remove, relative to the AHA network ( e.g. 000.cortex... ).')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        try:
            async with await s_telepath.openurl(opts.url) as aha:
                await aha.delAhaSvc(opts.svcname)
                outp.printf(f'Removed AHA service entry: {opts.svcname}')
                return 0
        except s_exc.SynErr as e:
            mesg = e.errinfo.get('mesg', repr(e))
            outp.printf(f'ERROR: {mesg}')
            return 1

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
