import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

descr = '''
Query the Aha server for the service cluster status of mirrors.

Examples:

    python -m synapse.tools.aha.mirror --timeout 30

'''

async def get_cell_infos(prox, outp, iden, timeout):
    '''
    Aha de-duplicates peer responses by run iden and labels each response with whichever
    service entry it resolved first, which may be the leader alias rather than the member
    entry. Key the responses by run iden and fall back to the name for any peer which did
    not report one.
    '''
    byrun = {}
    byname = {}

    todo = s_common.todo('getCellInfo')

    try:

        async for svcname, (ok, info) in prox.callAhaPeerApi(iden, todo, timeout=timeout):

            if not ok:
                continue

            byname[svcname] = info

            run = info.get('cell', {}).get('run')
            if run is not None:
                byrun[run] = info

    except Exception as e:
        mesg = repr(e)
        if isinstance(e, s_exc.SynErr):
            mesg = e.errinfo.get('mesg', repr(e))

        outp.printf(f'WARNING: Failed to query mirror group members: {mesg}')

    return byrun, byname

def build_status_list(members, byrun, byname):

    group_status = []

    for svc in members:

        svcname = svc.get('name')
        svcinfo = svc.get('svcinfo', {})

        ready = svcinfo.get('ready')

        status = {
            'name': svcname,
            'responded': False,
            'role': '<unknown>',
            'online': str('online' in svcinfo),
            'ready': '' if ready is None else str(ready),
            'host': svcinfo.get('urlinfo', {}).get('host', ''),
            'port': str(svcinfo.get('urlinfo', {}).get('port', '')),
            'version': '<unknown>',
            'synapse': '<unknown>',
            'nexs_indx': None,
            'follows': '<unknown>',
        }

        info = byrun.get(svcinfo.get('run'))
        if info is None:
            info = byname.get(svcname)

        if info is not None:

            cell_info = info.get('cell', {})

            status.update({
                'responded': True,
                'nexs_indx': cell_info.get('nexsindx'),
                'role': 'leader' if cell_info.get('active') else 'follower',
                'version': str(cell_info.get('verstring', '')),
                'synapse': str(info.get('synapse', {}).get('verstring', '')),
                'online': 'True',
            })

            # The URL is sanitized by the service before it is returned to us.
            if 'mirror' in cell_info:
                mirror = cell_info.get('mirror')
                status['follows'] = '<none - write root>' if mirror is None else mirror

        group_status.append(status)

    return group_status

# Mirrors the column configuration used by the aha.svc.mirror Storm command so that both
# renderings of this data stay identical. A column with no width is not padded.
columns = (
    ('name', 40),
    ('role', 9),
    ('online', 7),
    ('ready', 6),
    ('host', 16),
    ('port', 8),
    ('version', 12),
    ('synapse', 12),
    ('nexus idx', 10),
    ('follows', None),
)

def format_row(values, pad=' '):
    '''
    Render a row the way $lib.tabular does with no column separator configured, which is
    a leading pad, items joined by a doubled pad, and a trailing pad.
    '''
    items = []
    for (name, width), valu in zip(columns, values):

        valu = '' if valu is None else str(valu)
        if width is not None:
            valu = valu.ljust(width)

        items.append(valu)

    return f'{pad}{(pad * 2).join(items)}{pad}'

def output_status(outp, vname, group_status):

    outp.printf(format_row([name for name, width in columns]))
    outp.printf(format_row([(width or len(name)) * '#' for name, width in columns], pad='#'))
    outp.printf(vname)

    for status in group_status:

        nexs = status.get('nexs_indx')
        if nexs is None:
            nexs = '<unknown>'

        outp.printf(format_row((
            status['name'],
            status['role'],
            status['online'],
            status['ready'],
            status['host'],
            status['port'],
            status['version'],
            status['synapse'],
            nexs,
            status['follows'],
        )))

def get_sync_status(group_status):

    indices = {status['nexs_indx'] for status in group_status if status['nexs_indx'] is not None}
    known = sum(1 for status in group_status if status['nexs_indx'] is not None)

    # No member reported an index, so we can say nothing about replication.
    if known == 0:
        return 'Unknown'

    if known == len(group_status) and len(indices) == 1:
        return 'In Sync'

    return 'Out of Sync'

def get_group_leaders(group_status):
    # Leadership is reported by the service itself, so it stays accurate when the leader
    # alias is missing or stale.
    return [status['name'] for status in group_status if status['role'] == 'leader']

def output_group_leaders(outp, leaders):

    if not leaders:
        outp.printf('Group Leader: <none>')
        return

    if len(leaders) == 1:
        outp.printf(f'Group Leader: {leaders[0]}')
        return

    outp.printf(f'Group Leader: <multiple: {", ".join(leaders)}>')

def get_group_name(iden, alias, members):

    if alias is not None:
        return alias.get('name')

    for svc in members:
        leader = svc.get('svcinfo', {}).get('leader')
        if leader is not None:
            return f'{leader}.{svc.get("svcnetw")} (leader alias not registered)'

    return f'<no leader alias> (service iden: {iden})'

def get_mirror_groups(svcdefs):
    '''
    The leader alias is only registered by an active service, so a group with no claimed
    leader has no alias entry to group on. Every member of a mirror group shares the cell
    iden, so group on that instead.

    Returns a tuple of (leader_aliases, mirror_groups).
    '''
    leader_aliases = {}
    svcs_by_run = {}

    for svc in svcdefs:

        svcinfo = svc.get('svcinfo', {})

        iden = svcinfo.get('iden')
        run = svcinfo.get('run')
        if iden is None or run is None:
            continue

        # A service registers its alias with addAhaSvc(leader, info), so the alias entry
        # is the one whose service name matches the leader name it carries.
        leader = svcinfo.get('leader')
        if leader is not None and svc.get('svcname') == leader:
            leader_aliases.setdefault(iden, svc)
            continue

        # Several entries may share a run iden. Prefer the one which names itself.
        seen = svcs_by_run.get((iden, run))
        if seen is not None:
            seeninfo = seen.get('svcinfo', {})
            if seen.get('name') == seeninfo.get('urlinfo', {}).get('hostname'):
                continue

        svcs_by_run[(iden, run)] = svc

    members_by_iden = {}
    for (iden, run), svc in svcs_by_run.items():
        members_by_iden.setdefault(iden, {})[svc.get('name')] = svc

    mirror_groups = []
    for iden, membermap in members_by_iden.items():

        if len(membermap) <= 1:
            continue

        members = [membermap[name] for name in sorted(membermap)]

        # Aha never reaps service entries, so a decommissioned cluster lingers in the
        # registry forever. Only report groups which still have a service online.
        if not any('online' in svc.get('svcinfo', {}) for svc in members):
            continue

        mirror_groups.append((iden, members))

    return leader_aliases, mirror_groups

async def output_group(outp, prox, iden, alias, members, opts):

    vname = get_group_name(iden, alias, members)

    byrun, byname = await get_cell_infos(prox, outp, iden, opts.timeout)
    group_status = build_status_list(members, byrun, byname)
    output_status(outp, vname, group_status)

    leaders = get_group_leaders(group_status)
    output_group_leaders(outp, leaders)

    syncstatus = get_sync_status(group_status)
    outp.printf(f'Group Status: {syncstatus}')

    if syncstatus == 'In Sync' or not opts.wait:
        return

    allresp = all(status['responded'] for status in group_status)

    leader_nexs = None
    for status in group_status:
        if status['role'] == 'leader' and status['nexs_indx'] is not None:
            leader_nexs = status['nexs_indx']

    # Without a single leader there is no replication to wait on, and an unresponsive
    # member can never satisfy the wait loop.
    if len(leaders) != 1:
        outp.printf('WARNING: Skipping --wait: the group has no active leader.')
        return

    if not allresp:
        outp.printf('WARNING: Skipping --wait: one or more group members did not respond.')
        return

    if leader_nexs is None:
        outp.printf('WARNING: Skipping --wait: the leader did not report a nexus index.')
        return

    while True:

        responses = []
        todo = s_common.todo('waitNexsOffs', leader_nexs - 1, timeout=opts.timeout)
        async for svcname, (ok, info) in prox.callAhaPeerApi(iden, todo, timeout=opts.timeout):
            if ok and info:
                responses.append((svcname, info))

        if len(responses) == len(members):

            byrun, byname = await get_cell_infos(prox, outp, iden, opts.timeout)
            group_status = build_status_list(members, byrun, byname)

            outp.printf('')
            outp.printf('Updated status:')
            output_status(outp, vname, group_status)

            if get_sync_status(group_status) == 'In Sync':
                outp.printf('Group Status: In Sync')
                return

def timeout_type(valu):
    try:
        ivalu = int(valu)
        if ivalu < 0:
            raise ValueError
    except ValueError:
        raise s_exc.BadArg(mesg=f"{valu} is not a valid non-negative integer")
    return ivalu

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.aha.mirror', outp=outp, description=descr)

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

                svcdefs = [svc async for svc in prox.getAhaSvcs()]

                leader_aliases, mirror_groups = get_mirror_groups(svcdefs)

                if not mirror_groups:
                    outp.printf('No mirror groups found.')
                    return 0

                outp.printf('Service Mirror Groups:')
                for iden, members in mirror_groups:
                    await output_group(outp, prox, iden, leader_aliases.get(iden), members, opts)
                    outp.printf('')

                return 0

        except Exception as e:
            mesg = repr(e)
            if isinstance(e, s_exc.SynErr):
                mesg = e.errinfo.get('mesg', repr(e))
            outp.printf(f'ERROR: {mesg}')
            return 1

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
