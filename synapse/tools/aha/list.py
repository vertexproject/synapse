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

    async with await s_telepath.openurl(argv[0]) as prox:
        try:
            s_version.reqVersion(prox._getSynVers(), reqver)
        except s_exc.BadVersion as e:  # pragma: no cover
            valu = s_version.fmtVersion(*e.get('valu'))
            outp.printf(f'Proxy version {valu} is outside of the aha supported range ({reqver}).')
            return 1

        mesg = f"{'Service':<20s} {'network':<30s} {'leader':<6} {'online':<6} {'scheme':<6} {'host':<20} {'port':<5}  connection opts"
        outp.printf(mesg)

        svcs = []
        ldrs = set()
        async for svcdef in prox.getAhaSvcs():
            if svcdef.get('name') == svcdef.get('leader'):
                ldrs.add(svcdef.get('run'))
            svcs.append(svcdef)

        for svcdef in svcs:

            name = svcdef.get('name')
            ready = svcdef.get('ready')

            online = 'false'
            if svcdef.get('online'):
                online = 'true'

            urlinfo = svcdef.get('urlinfo')

            host = urlinfo.get('host', '<none>')
            port = urlinfo.get('port', '<none>')
            scheme = urlinfo.get('scheme', '<none>')

            leader = '<none>'
            if svcdef.get('leader') is not None:
                if svcdef.get('run') in ldrs:
                    leader = 'true'
                else:
                    leader = 'false'

            mesg = f'{name:<20s} {leader:<6} {online:<6} {scheme:<6} {host:<20} {str(port):<5}'
            outp.printf(mesg)

        return 0

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    s_common.setlogging(logger, 'WARNING')
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
