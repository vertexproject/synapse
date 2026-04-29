import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.version as s_version

reqver = '>=3.0.0,<4.0.0'

descr = 'List AHA services.'

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.aha.list', outp=outp, description=descr)
    pars.add_argument('url', help='The telepath URL to connect to the AHA service.')
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():
        async with await s_telepath.openurl(opts.url) as prox:
            try:
                s_version.reqVersion(prox._getSynVers(), reqver)
            except s_exc.BadVersion as e:  # pragma: no cover
                valu = s_version.fmtVersion(*e.get('valu'))
                outp.printf(f'Proxy version {valu} is outside of the aha supported range ({reqver}).')
                return 1
            classes = prox._getClasses()
            if 'synapse.lib.aha.AhaApi' not in classes:
                outp.printf(f'Service at {opts.url} is not an Aha server')
                return 1

            mesg = f"{'Service':<40s} {'Leader':<6} {'Online':<6} {'Host':<20} {'Port':<5}"
            outp.printf(mesg)

            svcs = []
            ldrs = set()
            async for svc in prox.getAhaSvcs():
                svcinfo = svc.get('svcinfo')
                if svcinfo and svc.get('svcname') == svcinfo.get('leader'):
                    ldrs.add(svcinfo.get('run'))
                svcs.append(svc)

            for svc in svcs:
                name = svc.get('name')

                svcinfo = svc.get('svcinfo')
                urlinfo = svcinfo.get('urlinfo')

                online = str(bool(svcinfo.get('online', False))).lower()

                host = urlinfo.get('host')
                port = str(urlinfo.get('port'))

                leader = 'None'
                if svcinfo.get('leader') is not None:
                    if svcinfo.get('run') in ldrs:
                        leader = 'True'
                    else:
                        leader = 'False'

                mesg = f'{name:<40s} {leader:<6} {online:<6} {host:<20} {port:<5}'

                outp.printf(mesg)

            return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
