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
                outp.printf(f'AHA server version {valu} is outside of the supported range ({reqver}).')
                return 1

            classes = prox._getClasses()
            if 'synapse.lib.aha.AhaApi' not in classes:
                outp.printf(f'Service at {argv[0]} is not an AHA server')
                return 1

            mesg = f"{'Service':<50s} {'Leader':<6} {'Online':<6} {'Scheme':<6} {'Host':<20} {'Port':<5}"
            outp.printf(mesg)

            svcs = []
            ldrs = set()
            async for svcdef in prox.getAhaSvcs():
                if svcdef.get('name') == svcdef.get('leader'):
                    ldrs.add(svcdef.get('run'))
                svcs.append(svcdef)

            for svcdef in svcs:
                name = svcdef.get('name')
                online = str(bool(svcdef.get('online', False))).lower()

                host = svcdef.get('urlinfo', {}).get('host', '????')
                port = svcdef.get('urlinfo', {}).get('port', '????')
                scheme = svcdef.get('urlinfo', {}).get('scheme', '????')

                islead = 'false'
                leader = svcdef.get('leader')
                if leader is not None and svcdef.get('run') in ldrs:
                    islead = 'true'

                outp.printf(f'{name:<50s} {islead:<6} {online:<6} {scheme:<6} {host:<20} {port:<5}')

            return 0

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    s_common.setlogging(logger, 'WARNING')
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
