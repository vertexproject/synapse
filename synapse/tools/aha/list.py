import sys
import asyncio
import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.output as s_output
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

reqver = '>=3.0.0,<4.0.0'

async def main(argv, outp=s_output.stdout):

    if len(argv) != 1:
        outp.printf('usage: python -m synapse.tools.aha.list <url>')
        return 1

    async with s_telepath.withTeleEnv():
        async with await s_telepath.openurl(argv[0]) as prox:
            try:
                s_version.reqVersion(prox._getSynVers(), reqver)
            except s_exc.BadVersion as e:  # pragma: no cover
                valu = s_version.fmtVersion(*e.get('valu'))
                outp.printf(f'Proxy version {valu} is outside of the aha supported range ({reqver}).')
                return 1
            classes = prox._getClasses()
            if 'synapse.lib.aha.AhaApi' not in classes:
                outp.printf(f'Service at {argv[0]} is not an Aha server')
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

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    s_common.setlogging(logger, 'WARNING')
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
