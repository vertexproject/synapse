import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.version as s_version

descr = '''
Query the Aha server for the service cluster status of mirrors.

Examples:

    python -m synapse.tools.aha.mirror --timeout 30

'''

async def get_cell_infos(prox, iden, members, timeout):
    cell_infos = {}
    if iden is not None:
        todo = s_common.todo('getCellInfo')
        async for svcname, (ok, info) in prox.callAhaPeerApi(iden, todo, timeout=timeout):
            if not ok:
                continue
            cell_infos[svcname] = info
    return cell_infos

def build_status_list(members, cell_infos):
    group_status = []
    for svc in members:
        svcname = svc.get('name')
        svcinfo = svc.get('svcinfo', {})
        status = {
            'name': svcname,
            'role': '<unknown>',
            'online': str('online' in svcinfo),
            'ready': 'True',
            'host': svcinfo.get('urlinfo', {}).get('host', ''),
            'port': str(svcinfo.get('urlinfo', {}).get('port', '')),
            'version': '<unknown>',
            'synapse': '<unknown>',
            'nexs_indx': 0
        }
        if svcname in cell_infos:
            info = cell_infos[svcname]
            cell_info = info.get('cell', {})
            status.update({
                'nexs_indx': cell_info.get('nexsindx', 0),
                'role': 'follower' if cell_info.get('uplink') else 'leader',
                'version': str(info.get('cell', {}).get('verstring', '')),
                'synapse': str(info.get('synapse', {}).get('verstring', '')),
                'online': 'True',
                'ready': str(cell_info.get('ready', False))
            })
        group_status.append(status)
    return group_status

def output_status(outp, vname, group_status):
    header = ' {:<40} {:<10} {:<8} {:<7} {:<16} {:<9} {:<12} {:<12} {:<10}'.format(
        'name', 'role', 'online', 'ready', 'host', 'port', 'version', 'synapse', 'nexus idx')
    outp.printf(header)
    outp.printf('#' * 120)
    outp.printf(vname)
    for status in group_status:
        if status['nexs_indx'] == 0:
            status['nexs_indx'] = '<unknown>'
        line = ' {name:<40} {role:<10} {online:<8} {ready:<7} {host:<16} {port:<9} {version:<12} {synapse:<12} {nexs_indx:<10}'.format(**status)
        outp.printf(line)

def check_sync_status(group_status):
    indices = {status['nexs_indx'] for status in group_status}
    known_count = sum(1 for status in group_status)
    return len(indices) == 1 and known_count == len(group_status)

def timeout_type(valu):
    try:
        ivalu = int(valu)
        if ivalu < 0:
            raise ValueError
    except ValueError:
        raise s_exc.BadArg(mesg=f"{valu} is not a valid non-negative integer")
    return ivalu

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.aha.mirror', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('--timeout', type=timeout_type, default=10, help='The timeout in seconds for individual service API calls')
    pars.add_argument('--wait', action='store_true', help='Whether to wait for the mirrors to sync.')
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():
        try:
            async with await s_telepath.openurl(opts.url) as prox:
                try:
                    if not prox._hasTeleFeat('callpeers', vers=1):
                        outp.printf(f'Service at {opts.url} does not support the required callpeers feature.')
                        return 1
                except s_exc.NoSuchMeth:
                    outp.printf(f'Service at {opts.url} does not support the required callpeers feature.')
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
                    iden = members[0].get('svcinfo', {}).get('iden')

                    cell_infos = await get_cell_infos(prox, iden, members, opts.timeout)
                    group_status = build_status_list(members, cell_infos)
                    output_status(outp, vname, group_status)

                    if check_sync_status(group_status):
                        outp.printf('Group Status: In Sync')
                    else:
                        outp.printf(f'Group Status: Out of Sync')
                        if opts.wait:
                            leader_nexs = None
                            for status in group_status:
                                if status['role'] == 'leader' and isinstance(status['nexs_indx'], int):
                                    leader_nexs = status['nexs_indx']

                            if leader_nexs is not None:
                                while True:
                                    responses = []
                                    todo = s_common.todo('waitNexsOffs', leader_nexs - 1, timeout=opts.timeout)
                                    async for svcname, (ok, info) in prox.callAhaPeerApi(iden, todo, timeout=opts.timeout):
                                        if ok and info:
                                            responses.append((svcname, info))

                                    if len(responses) == len(members):
                                        cell_infos = await get_cell_infos(prox, iden, members, opts.timeout)
                                        group_status = build_status_list(members, cell_infos)

                                        outp.printf('\nUpdated status:')
                                        output_status(outp, vname, group_status)

                                        if check_sync_status(group_status):
                                            outp.printf('Group Status: In Sync')
                                            break

                return 0

        except Exception as e:
            mesg = repr(e)
            if isinstance(e, s_exc.SynErr):
                mesg = e.errinfo.get('mesg', repr(e))
            outp.printf(f'ERROR: {mesg}')
            return 1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
