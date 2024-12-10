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
                    outp.printf(f'Service at {opts.url} is not an Aha server')
                    return 1

                virtual_services, member_servers = {}, {}
                async for svc in prox.getAhaSvcs():
                    name = svc.get('name', '')
                    svcinfo = svc.get('svcinfo', {})
                    urlinfo = svcinfo.get('urlinfo', {})
                    hostname = urlinfo.get('hostname', '')

                    if name != hostname:
                        virtual_services[name] = svc
                    else:
                        member_servers[name] = svc

                mirror_groups = {}
                for vname, vsvc in virtual_services.items():
                    vsvc_info = vsvc.get('svcinfo', {})
                    vsvc_iden = vsvc_info.get('iden')
                    vsvc_leader = vsvc_info.get('leader')
                    vsvc_hostname = vsvc_info.get('urlinfo', {}).get('hostname', '')

                    if not vsvc_iden or not vsvc_hostname or not vsvc_leader:
                        continue

                    primary_member = member_servers.get(vsvc_hostname)
                    if not primary_member:
                        continue

                    members = [primary_member] + [
                        msvc for mname, msvc in member_servers.items()
                        if mname != vsvc_hostname and
                        msvc.get('svcinfo', {}).get('iden') == vsvc_iden and
                        msvc.get('svcinfo', {}).get('leader') == vsvc_leader
                    ]

                    if len(members) > 1:
                        mirror_groups[vname] = members

                outp.printf('Service Mirror Groups:')
                for vname, members in mirror_groups.items():
                    group_status = []
                    cell_infos = {}

                    iden = members[0].get('svcinfo', {}).get('iden')
                    if iden is not None:
                        todo = s_common.todo('getCellInfo')
                        async for svcname, (ok, info) in prox.callAhaPeerApi(iden, todo, timeout=opts.timeout):
                            if not ok:
                                print(f'Error getting cell info from {svcname}: {info}')
                                continue
                            cell_infos[svcname] = info

                    for svc in members:
                        svcinfo = svc.get('svcinfo', {})
                        is_ready = svcinfo.get('ready', False)
                        svcname = svc.get('name')

                        status = {
                            'name': svcname,
                            'role': 'unknown',
                            'online': str(bool(svcinfo.get('online'))),
                            'ready': str(is_ready),
                            'host': svcinfo.get('urlinfo', {}).get('host', ''),
                            'port': str(svcinfo.get('urlinfo', {}).get('port', '')),
                            'version': '',
                            'nexs_indx': '<unknown>'
                        }

                        if is_ready and svcname in cell_infos:
                            info = cell_infos[svcname]
                            cell_info = info.get('cell', {})
                            status['nexs_indx'] = cell_info.get('nexsindx', 0)
                            status['role'] = 'follower' if cell_info.get('uplink') else 'leader'
                            status['version'] = str(info.get('synapse', {}).get('verstring', ''))

                        group_status.append(status)

                    header = ('{:<45}{:<9}{:<7}{:<6}{:<16}{:<8}{:<12}Nexus Index').format(
                        'Name', 'Role', 'Online', 'Ready', 'Host', 'Port', 'Version')
                    outp.printf(header)

                    for status in group_status:
                        line = ('{name:<45}{role:<9}{online:<7}{ready:<6}{host:<16}{port:<8}{version:<12}{nexs_indx}').format(**status)
                        outp.printf(line)

                    indices = {status['nexs_indx'] for status in group_status if isinstance(status['nexs_indx'], int)}
                    known_count = sum(1 for status in group_status if isinstance(status['nexs_indx'], int))
                    in_sync = len(indices) == 1 and known_count == len(group_status)

                    if in_sync:
                        outp.printf('Group Status: In Sync')
                    else:
                        outp.printf('Group Status: Out of Sync')

                return 0

        except Exception as e:
            mesg = repr(e)
            if isinstance(e, s_exc.SynErr):
                mesg = e.errinfo.get('mesg', repr(e))
            outp.printf(f'ERROR: {mesg}')
            return 1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
