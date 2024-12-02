import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.version as s_version

reqver = '>=2.2.0,<3.0.0' # TODO: update version with gatherApis

descr = '''
Query the Aha server for the service cluster status of mirrors.

Examples:

    python -m synapse.tools.aha.mirror --timeout 30

'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.aha.mirror', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('--timeout', type=int, default=60, help='The number of seconds to wait before timing out.')
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        try:

            async with await s_telepath.openurl(opts.url) as prox:

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

                mirror_idens = set()
                async for svcinfo in prox.getAhaSvcs():
                    svcconf = svcinfo.get('svcinfo', {})

                    mirrors = await prox.getAhaSvcMirrors(None, iden=svcconf.get('iden'))
                    if not mirrors:
                        continue

                    for mirror in mirrors:
                        mirror_svcinfo = mirror.get('svcinfo', {})
                        mirror_iden = mirror_svcinfo.get('iden')
                        if mirror_iden is not None:
                            mirror_idens.add(mirror_iden)

                todo = s_common.todo('getCellInfo')
                for mirror_iden in mirror_idens:
                    async for svcname, (ok, info) in prox.callAhaPeerApi(mirror_iden, todo, timeout=opts.timeout):
                        if not ok:
                            outp.printf(f'Error getting status from {svcname}: {info}')
                            continue

                        cell_info = info.get('cell', {})
                        is_ready = cell_info.get('ready', False)
                        nexs_indx = cell_info.get('nexsindx', 0)
                        uplink = cell_info.get('uplink', False)
                        leader = 'False' if uplink else 'True'
                        version = cell_info.get('verstring', '')

                        status = 'ready' if is_ready else 'not ready'
                        outp.printf(f'Mirror: {svcname}')
                        outp.printf(f'  Leader: {leader}')
                        outp.printf(f'  Status: {status}')
                        outp.printf(f'  Nexus Index: {nexs_indx}')
                        outp.printf(f'  Version: {version}')
                        outp.printf('')

                return 0

        except Exception as e:
            mesg = repr(e)
            if isinstance(e, s_exc.SynErr):
                mesg = e.errinfo.get('mesg', repr(e))

            outp.printf(f'ERROR: {mesg}')
            return 1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
