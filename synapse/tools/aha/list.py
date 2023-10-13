import sys
import asyncio
import logging
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

reqver = '>=2.11.0,<3.0.0'

async def _main(argv, outp):

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

        try:
            network = argv[1]
        except IndexError:
            network = None

        mesg = f"{'Service':<20s} {'network':<30s} {'leader':<6} {'online':<6} {'scheme':<6} {'host':<20} {'port':<5}  connection opts"
        outp.printf(mesg)

        svcs = []
        ldrs = set()
        async for svc in prox.getAhaSvcs(network):
            svcinfo = svc.get('svcinfo')
            if svcinfo and svc.get('svcname') == svcinfo.get('leader'):
                ldrs.add(svcinfo.get('run'))
            svcs.append(svc)

        for svc in svcs:
            svcname = svc.pop('svcname')
            svcnetw = svc.pop('svcnetw')

            svcinfo = svc.pop('svcinfo')
            urlinfo = svcinfo.pop('urlinfo')
            online = str(bool(svcinfo.pop('online', False)))
            host = urlinfo.pop('host')
            port = str(urlinfo.pop('port'))
            scheme = urlinfo.pop('scheme')

            leader = 'None'
            if svcinfo.get('leader') is not None:
                if svcinfo.get('run') in ldrs:
                    leader = 'True'
                else:
                    leader = 'False'

            mesg = f'{svcname:<20s} {svcnetw:<30s} {leader:<6} {online:<6} {scheme:<6} {host:<20} {port:<5}'
            if svc:
                mesg = f'{mesg}  {svc}'

            outp.printf(mesg)
        return 0

async def main(argv, outp=None):  # pragma: no cover

    if outp is None:
        outp = s_output.stdout

    if len(argv) not in (1, 2):
        outp.printf('usage: python -m synapse.tools.aha.list <url> [network name]')
        return 1

    s_common.setlogging(logger, 'WARNING')

    async with s_telepath.withTeleEnv():
        await _main(argv, outp)

    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
