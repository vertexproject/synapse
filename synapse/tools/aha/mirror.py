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

# Mirrors the column configuration used by the aha.svc.mirror Storm command so that
# both renderings of this data stay identical. A column with no width is not padded.
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
    Render a row the way $lib.tabular does with no column separator configured, which
    is a leading pad, items joined by a doubled pad, and a trailing pad.
    '''
    items = []
    for (name, width), valu in zip(columns, values):

        valu = '' if valu is None else str(valu)
        if width is not None:
            valu = valu.ljust(width)

        items.append(valu)

    return f'{pad}{(pad * 2).join(items)}{pad}'

async def get_cell_infos(prox, outp, iden, timeout):

    cell_infos = {}
    todo = s_common.todo('getCellInfo')

    try:

        async for svcname, (ok, info) in prox.callAhaPeerApi(iden, todo, timeout=timeout):

            if not ok:
                continue

            cell_infos[svcname] = info

    except Exception as e:
        mesg = repr(e)
        if isinstance(e, s_exc.SynErr):
            mesg = e.errinfo.get('mesg', repr(e))

        outp.printf(f'WARNING: Failed to query mirror group members: {mesg}')

    return cell_infos

def build_status_list(members, cell_infos):

    group_status = []

    for svc in members:

        svcname = svc.get('name')
        if (svcinfo := svc.get('info')) is None: # pragma: no cover
            svcinfo = {}

        ready = svcinfo.get('ready')

        status = {
            'name': svcname,
            'responded': False,
            'role': '<unknown>',
            'online': str(svc.get('online', False)),
            'ready': '' if ready is None else str(ready),
            'host': svcinfo.get('urlinfo', {}).get('host', ''),
            'port': str(svcinfo.get('urlinfo', {}).get('port', '')),
            'version': '<unknown>',
            'synapse': '<unknown>',
            'nexs_indx': None,
            'follows': '<unknown>',
        }

        if svcname in cell_infos:

            info = cell_infos[svcname]
            cell_info = info.get('cell', {})

            status.update({
                'responded': True,
                'nexs_indx': cell_info.get('nexus', {}).get('indx'),
                'role': 'leader' if cell_info.get('active') else 'follower',
                'version': str(cell_info.get('version', '')),
                'synapse': str(info.get('synapse', {}).get('version', '')),
                'online': 'True',
            })

            # The URL is sanitized by the service before it is returned to us.
            if 'parent' in cell_info:
                parent = cell_info.get('parent')
                status['follows'] = '<none - write root>' if parent is None else parent

        group_status.append(status)

    return group_status

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

def output_group_leader(outp, members, group_status):
    '''
    Aha elects a leadership term per service type. The term flag is derived from the
    term name alone, so it stays set on a service which is down. Report the term holder
    and flag any disagreement with the live status.
    '''
    termname = None
    termonline = False

    for svc in members:
        if svc.get('leader'):
            termname = svc.get('name')
            termonline = svc.get('online', False)

    if termname is None:
        outp.printf('Group Leader: <no term>')
        return

    actives = [status['name'] for status in group_status if status['role'] == 'leader']

    termactive = termname in actives
    others = [name for name in actives if name != termname]

    if not termonline:
        outp.printf(f'Group Leader: {termname} (offline)')
        return

    if not termactive:
        if not others:
            outp.printf(f'Group Leader: {termname} (inactive)')
            return

        outp.printf(f'Group Leader: {termname} (inactive; {", ".join(others)} reports active)')
        return

    if others:
        outp.printf(f'Group Leader: {termname} (also active: {", ".join(others)})')
        return

    outp.printf(f'Group Leader: {termname}')

def get_mirror_groups(svcdefs):
    '''
    A leader and its mirrors share an immutable service iden, so group on that.

    Returns a list of (name, members) tuples.
    '''
    svc_groups = {}
    for svc in svcdefs:

        iden = svc.get('info', {}).get('iden')
        if iden is None:
            continue

        svc_groups.setdefault(iden, []).append(svc)

    mirror_groups = []
    for iden, svcs in svc_groups.items():

        if len(svcs) <= 1:
            continue

        # Aha never reaps service entries, so a decommissioned cluster lingers in the
        # registry forever. Only report groups which still have a service online.
        if not any(svc.get('online') for svc in svcs):
            continue

        # Name the group by its current ( term-holding ) leader and list it first.
        leader = next((svc for svc in svcs if svc.get('leader')), svcs[0])
        members = [leader] + [svc for svc in svcs if svc is not leader]

        mirror_groups.append((leader.get('name'), members))

    return mirror_groups

async def output_group(outp, prox, vname, members, opts):

    iden = members[0].get('info', {}).get('iden')

    cell_infos = await get_cell_infos(prox, outp, iden, opts.timeout)
    group_status = build_status_list(members, cell_infos)
    output_status(outp, vname, group_status)
    output_group_leader(outp, members, group_status)

    syncstatus = get_sync_status(group_status)
    outp.printf(f'Group Status: {syncstatus}')

    if syncstatus == 'In Sync' or not opts.wait:
        return

    allresp = all(status['responded'] for status in group_status)
    actives = sum(1 for status in group_status if status['role'] == 'leader')

    leader_nexs = None
    for status in group_status:
        if status['role'] == 'leader' and status['nexs_indx'] is not None:
            leader_nexs = status['nexs_indx']

    # Without a single active leader there is no replication to wait on, and an
    # unresponsive member can never satisfy the wait loop.
    if actives != 1:
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

            cell_infos = await get_cell_infos(prox, outp, iden, opts.timeout)
            group_status = build_status_list(members, cell_infos)

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
                classes = prox._getClasses()
                if 'synapse.lib.aha.AhaApi' not in classes:
                    outp.printf(f'Service at {opts.url} is not an Aha server')
                    return 1

                svcdefs = [svc async for svc in prox.getAhaSvcs()]

                mirror_groups = get_mirror_groups(svcdefs)

                if not mirror_groups:
                    outp.printf('No mirror groups found.')
                    return 0

                outp.printf('Service Mirror Groups:')
                for vname, members in mirror_groups:
                    await output_group(outp, prox, vname, members, opts)
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
