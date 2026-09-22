import textwrap

import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class AhaLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with AHA.
    '''

    _storm_locals = (
        {'name': 'del', 'desc': '''Delete a service from AHA.

        Examples:
            Deleting a service with its relative name::

                $lib.aha.del(00.mysvc...)

            Deleting a service with its full name::

                $lib.aha.del(00.mysvc.loop.vertex.link)
        ''',
         'type': {'type': 'function', '_funcname': '_methAhaDel',
                  'args': (
                      {'name': 'svcname', 'type': 'str',
                       'desc': 'The name of the service to delete. It is easiest to use the relative name of a service, ending with "...".', },
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'get', 'desc': '''Get information about an AHA service.

        Examples:
            Getting service information with a relative name::

                $lib.aha.get(000.cortex...)

            Getting service information with its full name::

                $lib.aha.get(000.cortex.loop.vertex.link)
        ''',
         'type': {'type': 'function', '_funcname': '_methAhaGet',
                  'args': (
                      {'name': 'svcname', 'type': 'str',
                       'desc': 'The name of the AHA service to look up. It is easiest to use the relative name of a service, ending with "...".', },
                      {'name': 'filters', 'type': 'dict', 'default': None,
                       'desc': 'An optional dictionary of filters to use when resolving the AHA service.'}
                  ),
                  'returns': {'type': ('null', 'dict'),
                              'desc': 'The AHA service information dictionary, or `(null))`.', }}},
        {'name': 'list', 'desc': 'Enumerate all of the AHA services.',
         'type': {'type': 'function', '_funcname': '_methAhaList', 'args': (),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'The AHA service dictionaries.', }}},
        {'name': 'callPeerApi', 'desc': '''Call an API on all peers (leader and mirrors) of an AHA service and yield the responses from each.

        Examples:
            Call getCellInfo on an AHA service::

                $todo = $lib.utils.todo('getCellInfo')
                for $info in $lib.aha.callPeerApi(cortex..., $todo) {
                    $lib.print($info)
                }

            Call getCellInfo on an AHA service, skipping the invoking service::

                $todo = $lib.utils.todo('getCellInfo')
                for $info in $lib.aha.callPeerApi(cortex..., $todo, skiprun=$lib.cell.getCellInfo().cell.run) {
                    $lib.print($info)
                }

            Call method with arguments::

                $todo = $lib.utils.todo(('method', ([1, 2]), ({'foo': 'bar'})))
                for $info in $lib.aha.callPeerApi(cortex..., $todo) {
                    $lib.print($info)
                }

        ''',
         'type': {'type': 'function', '_funcname': '_methCallPeerApi',
                  'args': (
                      {'name': 'svcname', 'type': 'str',
                       'desc': 'The name of the AHA service to call. It is easiest to use the relative name of a service, ending with "...".', },
                      {'name': 'todo', 'type': 'list',
                       'desc': 'The todo tuple (name, args, kwargs).'},
                      {'name': 'timeout', 'type': 'int', 'default': None,
                       'desc': 'Optional timeout in seconds.'},
                      {'name': 'skiprun', 'type': 'str', 'default': None,
                       'desc': '''Optional run ID argument that allows skipping results from a specific service run ID.
                                  This is most often used to omit the invoking service from the results, ensuring that only responses from other services are included.
                        '''},
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'Yields the results of the API calls as tuples of (svcname, (ok, info)).', }}},
        {'name': 'callPeerGenr', 'desc': '''Call a generator API on all peers (leader and mirrors) of an AHA service and yield the responses from each.

        Examples:
            Call getNexusChanges on an AHA service::

                $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                for $info in $lib.aha.callPeerGenr(cortex..., $todo) {
                    $lib.print($info)
                }

            Call getNexusChanges on an AHA service, skipping the invoking service::

                $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                for $info in $lib.aha.callPeerGenr(cortex..., $todo, skiprun=$lib.cell.getCellInfo().cell.run) {
                    $lib.print($info)
                }

        ''',
         'type': {'type': 'function', '_funcname': '_methCallPeerGenr',
                  'args': (
                      {'name': 'svcname', 'type': 'str',
                       'desc': 'The name of the AHA service to call. It is easiest to use the relative name of a service, ending with "...".', },
                      {'name': 'todo', 'type': 'list',
                       'desc': 'The todo tuple (name, args, kwargs).'},
                      {'name': 'timeout', 'type': 'int', 'default': None,
                       'desc': 'Optional timeout in seconds.'},
                      {'name': 'skiprun', 'type': 'str', 'default': None,
                       'desc': '''Optional run ID argument that allows skipping results from a specific service run ID.
                                  This is most often used to omit the invoking service from the results, ensuring that only responses from other services are included.
                       '''},
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'Yields the results of the API calls as tuples containing (svcname, (ok, info)).', }}}

    )
    _storm_lib_path = ('aha',)
    def getObjLocals(self):
        return {
            'del': self._methAhaDel,
            'get': self._methAhaGet,
            'list': self._methAhaList,
            'callPeerApi': self._methCallPeerApi,
            'callPeerGenr': self._methCallPeerGenr,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methAhaList(self):
        self.runt.reqAdmin()
        proxy = await self.runt.view.core.reqAhaProxy()
        async for info in proxy.getAhaSvcs():
            yield info

    async def _methAhaDel(self, svcname):
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)
        proxy = await self.runt.view.core.reqAhaProxy()
        svc = await proxy.getAhaSvc(svcname)
        if svc is None:
            raise s_exc.NoSuchName(mesg=f'No AHA service for {svcname=}')

        return await proxy.delAhaSvc(svc.get('name'))

    @s_stormtypes.stormfunc(readonly=True)
    async def _methAhaGet(self, svcname, filters=None):
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)
        filters = await s_stormtypes.toprim(filters)
        proxy = await self.runt.view.core.reqAhaProxy()
        return await proxy.getAhaSvc(svcname, filters=filters)

    async def _methCallPeerApi(self, svcname, todo, timeout=None, skiprun=None):
        '''
        Call an API on an AHA service.

        Args:
            svcname (str): The name of the AHA service to call.
            todo (list): The todo tuple from $lib.utils.todo().
            timeout (int): Optional timeout in seconds.
            skiprun (str): Optional run ID argument allows skipping self-enumeration.
        '''
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)
        todo = await s_stormtypes.toprim(todo)
        timeout = await s_stormtypes.toint(timeout, noneok=True)
        skiprun = await s_stormtypes.tostr(skiprun, noneok=True)

        proxy = await self.runt.view.core.reqAhaProxy()
        svc = await proxy.getAhaSvc(svcname)
        if svc is None:
            raise s_exc.NoSuchName(mesg=f'No AHA service found for {svcname}')

        svcinfo = svc.get('info')
        svciden = svcinfo.get('iden')
        if svciden is None:
            raise s_exc.NoSuchName(mesg=f'Service {svcname} has no iden')

        async for svcname, (ok, info) in proxy.callAhaPeerApi(svciden, todo, timeout=timeout, skiprun=skiprun):
            yield (svcname, (ok, info))

    async def _methCallPeerGenr(self, svcname, todo, timeout=None, skiprun=None):
        '''
        Call a generator API on an AHA service.

        Args:
            svcname (str): The name of the AHA service to call.
            todo (list): The todo tuple from $lib.utils.todo().
            timeout (int): Optional timeout in seconds.
            skiprun (str): Optional run ID argument allows skipping self-enumeration.
        '''
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)
        todo = await s_stormtypes.toprim(todo)
        timeout = await s_stormtypes.toint(timeout, noneok=True)
        skiprun = await s_stormtypes.tostr(skiprun, noneok=True)

        proxy = await self.runt.view.core.reqAhaProxy()
        svc = await proxy.getAhaSvc(svcname)
        if svc is None:
            raise s_exc.NoSuchName(mesg=f'No AHA service found for {svcname}')

        svcinfo = svc.get('info')
        svciden = svcinfo.get('iden')
        if svciden is None:
            raise s_exc.NoSuchName(mesg=f'Service {svcname} has no iden')

        async for svcname, (ok, info) in proxy.callAhaPeerGenr(svciden, todo, timeout=timeout, skiprun=skiprun):
            yield (svcname, (ok, info))

stormcmds = (
    {
        'name': 'aha.svc.stat',
        'desc': '''Show all information for a specific AHA service.

If the --nexus argument is given, the Cortex will attempt to connect the service and report the Nexus offset of the service.

The ready value indicates that a service has entered into the realtime change window for synchronizing changes from its leader.
        ''',
        'cmdargs': (
            ('svc', {'help': 'The service to inspect.'}),
            ('--nexus', {'help': 'Try to connect to online services and report their nexus offset.',
                         'default': False, 'action': 'store_true'}),
        ),
        'storm': '''
        function _getNexus(svcname) {
            $_url = `aha://{$svcname}/`
            try {
                $_prox = $lib.telepath.open($_url)
                $_info = $_prox.getCellInfo()
                return ( $_info.cell.nexus.indx )
            } catch * as _err {
                $_emsg = $_err.mesg
                if ($_emsg = null ) {
                    $_emsg = `{$_err}`
                }
                return ( $_emsg )
            }
        }

        $svcentry = $lib.aha.get($cmdopts.svc)
        if ($svcentry = null) {
            $lib.print(`No service found for: "{$cmdopts.svc}"`)
        } else {
            $lib.print(`Resolved {$cmdopts.svc} to an AHA Service.\n`)
            $svcinfo = $svcentry.info
            // the leader is the current term-elected instance of this service type
            $leader = 'No leadership term for this service type.'
            if $svcinfo.type {
                $leadersvc = $lib.aha.get(`{$svcinfo.type}...`)
                if ($leadersvc != null) {
                    $leader = $leadersvc.name
                }
            }
            $online = false
            if $svcentry.online {
                $online = true
            }
            $ready = 'null'
            if $lib.dict.has($svcinfo, ready) {
                $ready = `{$svcinfo.ready}`
            }
            $lib.print(`Name:       {$svcentry.name}`)
            $lib.print(`Online:     {$online}`)
            $lib.print(`Ready:      {$ready}`)
            $lib.print(`Run iden:   {$svcinfo.run}`)
            $lib.print(`Cell iden:  {$svcinfo.iden}`)
            $lib.print(`Leader:     {$leader}`)

            if $cmdopts.nexus {
                if $svcentry.online {
                    $nexusOffset = $_getNexus($svcentry.name)
                } else {
                    $nexusOffset = 'Service is not online. Will not attempt to retrieve its nexus offset.'
                }
                $lib.print(`Nexus:      {$nexusOffset}`)
            }

            $lib.print('Connection information:')
            $urlinfo = $svcinfo.urlinfo
            $keys = $lib.dict.keys($urlinfo)
            $keys.sort()
            for $k in $keys {
                $dk = `{$k}:`
                $dk = $dk.ljust(12)
                $lib.print(`    {$dk}{$urlinfo.$k}`)
            }
        }
        '''
    },
    {
        'name': 'aha.svc.list',
        'desc': '''List AHA services.

If the --nexus argument is given, the Cortex will attempt to connect to each service and report the Nexus offset of the service.

The ready column indicates that a service has entered into the realtime change window for synchronizing changes from its leader.''',
        'cmdargs': (
            ('--nexus', {'help': 'Try to connect to online services and report their nexus offset.',
                         'default': False, 'action': 'store_true'}),
        ),
        'storm': '''
        function _getNexus(svcname) {
            $_url = `aha://{$svcname}/`
            try {
                $_prox = $lib.telepath.open($_url)
                $_info = $_prox.getCellInfo()
                return ( $_info.cell.nexus.indx )
            } catch * as _err {
                $_emsg = $_err.mesg
                if ($_emsg = null ) {
                    $_emsg = `{$_err}`
                }
                return ( $_emsg )
            }
        }

        $svcs = ()
        for $svcentry in $lib.aha.list() {
            $svcs.append($svcentry)
        }

        if ($lib.len($svcs) = 0) {
            $lib.print('No AHA services registered.')
        }
        else {
            $columns = 'Name                                          Leader Online Ready Host            Port '
            if $cmdopts.nexus {
                $columns = `{$columns} Nexus`
            }

            $leaders = $lib.set()
            for $svcentry in $svcs {
                $svcinfo = $svcentry.info
                if $svcentry.leader {
                    $leaders.add($svcinfo.run)
                }
            }

            $lib.print($columns)

            for $svcentry in $svcs {
                $name = $svcentry.name
                $nexusOffset = (null)
                $svcinfo = $svcentry.info

                if $cmdopts.nexus {
                    if $svcentry.online {
                        $nexusOffset = $_getNexus($name)
                    } else {
                        $nexusOffset = '<offline>'
                    }
                }
                $name=$name.ljust(45)

                $online = false
                if $svcentry.online {
                    $online = true
                }
                $online = $online.ljust(6)

                $urlinfo = $svcinfo.urlinfo

                $host = $urlinfo.host
                $host = $host.ljust(15)

                $port = $lib.cast(str, $urlinfo.port)  // Cast to str
                $port = $port.ljust(5)

                $ready = 'null'
                if $lib.dict.has($svcinfo, ready) {
                    $ready = `{$svcinfo.ready}`
                }
                $ready = $ready.ljust(5)

                // the leader flag is managed by the leadership term for the type;
                // offline stubs without run info cannot be resolved and show null
                $leader = null
                if ( $svcinfo.run != null ) {
                    $leader = false
                    if $leaders.has($svcinfo.run) {
                        $leader = true
                    }
                }
                $leader = $leader.ljust(6)

                if $svcentry {
                    $s = `{$name} {$leader} {$online} {$ready} {$host} {$port}`
                    if ($nexusOffset != null) {
                        $s = `{$s} {$nexusOffset}`
                    }
                    $lib.print($s)
                }
            }
        }
        '''
    },
    {
        'name': 'aha.svc.mirror',
        'desc': textwrap.dedent('''\
            Query the AHA services and their mirror relationships.

            Mirror group members are identified by the service iden which they share. The
            group is named for the holder of the current AHA leadership term, which is
            reported separately from the live status of each service so that a stale or
            unreachable term holder is visible.

            The role and follows columns reflect the status reported by each service,
            where follows is the service which that member mirrors from.

            Notes:
                - Non-mirror services are not displayed, nor are groups which have no
                  online service.
                - A service restored from another service's backup shares its service iden
                  and is displayed as a member of that group.
        '''),
        'cmdargs': (
            ('--timeout', {'help': 'The timeout in seconds for individual service API calls.',
                           'default': 10, 'type': 'int'}),
            ('--wait', {'help': 'Whether to wait for the mirrors to sync.',
                        'action': 'store_true'}),
        ),
        'storm': '''
        init {
            $conf = ({
                "columns": [
                    {"name": "name", "width": 40},
                    {"name": "role", "width": 9},
                    {"name": "online", "width": 7},
                    {"name": "ready", "width": 6},
                    {"name": "host", "width": 16},
                    {"name": "port", "width": 8},
                    {"name": "version", "width": 12},
                    {"name": "synapse", "width": 12},
                    {"name": "nexus idx", "width": 10},
                    {"name": "follows"},
                ],
                "separators": {
                    "row:outline": false,
                    "column:outline": false,
                    "header:row": "#",
                    "data:row": "",
                    "column": "",
                },
            })
            $printer = $lib.tabular.printer($conf)
            $timeout = $cmdopts.timeout
            $wait = $cmdopts.wait
        }

        function get_cell_infos(vname, timeout) {
            $cell_infos = ({})
            $todo = $lib.utils.todo('getCellInfo')
            try {
                for $info in $lib.aha.callPeerApi($vname, $todo, timeout=$timeout) {
                    $svcname = $info.0
                    ($ok, $info) = $info.1
                    if $ok {
                        $cell_infos.$svcname = $info
                    }
                }
            } catch * as err {
                $lib.warn(`Failed to query mirror group members for {$vname}: {$err.mesg}`)
            }

            return($cell_infos)
        }

        function build_status_list(members, cell_infos) {
            $group_status = ()
            for $svcentry in $members {
                $svcinfo = $svcentry.info
                $svcname = $svcentry.name
                $status = ({
                    'name': $svcname,
                    'responded': (false),
                    'role': '<unknown>',
                    'online': $svcentry.online,
                    'ready': $svcinfo.ready,
                    'host': $svcinfo.urlinfo.host,
                    'port': $svcinfo.urlinfo.port,
                    'version': '<unknown>',
                    'synapse_version': '<unknown>',
                    'nexs_indx': (null),
                    'follows': '<unknown>'
                })
                if ($cell_infos.$svcname) {
                    $info = $cell_infos.$svcname
                    $cell_info = $info.cell
                    $status.responded = (true)
                    $status.nexs_indx = $cell_info.nexus.indx
                    if ($cell_info.active) {
                        $status.role = 'leader'
                    } else {
                        $status.role = 'follower'
                    }
                    $status.version = $info.cell.version
                    $status.synapse_version = $info.synapse.version

                    // The URL is sanitized by the service before it is returned to us.
                    if $lib.dict.has($cell_info, 'parent') {
                        $parent = $cell_info.parent
                        if ($parent = null) {
                            $status.follows = '<none - write root>'
                        } else {
                            $status.follows = $parent
                        }
                    }
                }
                $group_status.append($status)
            }
            return($group_status)
        }

        function get_sync_status(group_status) {

            $indices = $lib.set()
            $known = (0)

            for $status in $group_status {
                $indx = $status.nexs_indx
                if ($indx = null) {
                    continue
                }
                $indices.add($indx)
                $known = ($known + (1))
            }

            // No member reported an index, so we can say nothing about replication.
            if ($known = 0) {
                return('Unknown')
            }

            if (($known = $lib.len($group_status)) and ($lib.len($indices) = 1)) {
                return('In Sync')
            }

            return('Out of Sync')
        }

        // AHA elects a leadership term per service type. The term flag is derived from
        // the term name alone, so it stays set on a service which is down. Report the
        // term holder and flag any disagreement with the live status.
        function output_group_leader(members, group_status) {

            $termname = (null)
            $termonline = (false)
            for $svcentry in $members {
                if $svcentry.leader {
                    $termname = $svcentry.name
                    $termonline = $svcentry.online
                }
            }

            if ($termname = null) {
                $lib.print('Group Leader: <no term>')
                return()
            }

            $actives = ()
            for $status in $group_status {
                if ($status.role = 'leader') {
                    $actives.append($status.name)
                }
            }

            $others = ()
            $termactive = (false)
            for $name in $actives {
                if ($name = $termname) {
                    $termactive = (true)
                } else {
                    $others.append($name)
                }
            }

            if (not $termonline) {
                $lib.print(`Group Leader: {$termname} (offline)`)
                return()
            }

            if (not $termactive) {
                if ($lib.len($others) = 0) {
                    $lib.print(`Group Leader: {$termname} (inactive)`)
                } else {
                    $lib.print(`Group Leader: {$termname} (inactive; {(', ').join($others)} reports active)`)
                }
                return()
            }

            if ($lib.len($others) > 0) {
                $lib.print(`Group Leader: {$termname} (also active: {(', ').join($others)})`)
                return()
            }

            $lib.print(`Group Leader: {$termname}`)
            return()
        }

        function output_status(vname, group_status, printer) {
            $lib.print($printer.header())
            $lib.print($vname)
            for $status in $group_status {
                $nexs = $status.nexs_indx
                if ($nexs = null) {
                    $nexs = '<unknown>'
                }
                $row = (
                    $status.name,
                    $status.role,
                    $status.online,
                    $status.ready,
                    $status.host,
                    $status.port,
                    $status.version,
                    $status.synapse_version,
                    $nexs,
                    $status.follows
                )
                $lib.print($printer.row($row))
            }
            return()
        }

        // group services by their shared service iden ( a leader and its mirrors ).
        $svc_groups = ({})
        for $svcentry in $lib.aha.list() {
            $iden = $svcentry.info.iden
            if (not $iden) {
                continue
            }
            $grp = $svc_groups.$iden
            if (not $grp) {
                $grp = ()
            }
            $grp.append($svcentry)
            $svc_groups.$iden = $grp
        }

        // a group is a leader plus at least one mirror; name it by the current
        // ( term-elected ) leader.
        $mirror_groups = ({})
        for ($iden, $svcs) in $svc_groups {
            if ($lib.len($svcs) <= 1) {
                continue
            }
            $leadername = (null)
            $firstname = (null)
            $anyonline = (false)
            for $svcentry in $svcs {
                if (not $firstname) {
                    $firstname = $svcentry.name
                }
                if $svcentry.leader {
                    $leadername = $svcentry.name
                }
                if $svcentry.online {
                    $anyonline = (true)
                }
            }

            // AHA never reaps service entries, so a decommissioned cluster lingers in
            // the registry forever. Only report groups which still have a service online.
            if (not $anyonline) {
                continue
            }

            if (not $leadername) {
                $leadername = $firstname
            }
            $mirror_groups.$leadername = $svcs
        }

        if ($lib.len($mirror_groups) = 0) {
            $lib.print('No mirror groups found.')
        } else {
            $lib.print('Service Mirror Groups:')
        }
        for ($vname, $members) in $mirror_groups {
            $cell_infos = $get_cell_infos($vname, $timeout)
            $group_status = $build_status_list($members, $cell_infos)
            $output_status($vname, $group_status, $printer)
            $output_group_leader($members, $group_status)

            $syncstatus = $get_sync_status($group_status)
            $lib.print(`Group Status: {$syncstatus}`)

            if ($syncstatus != 'In Sync') {
                if $wait {

                    $allresp = (true)
                    $actives = (0)
                    for $status in $group_status {
                        if (not $status.responded) {
                            $allresp = (false)
                        }
                        if ($status.role = 'leader') {
                            $actives = ($actives + (1))
                        }
                    }

                    $leader_nexs = (null)
                    for $status in $group_status {
                        if (($status.role = 'leader') and ($status.nexs_indx != null)) {
                            $leader_nexs = $status.nexs_indx
                        }
                    }

                    // Without a single active leader there is no replication to wait on,
                    // and an unresponsive member can never satisfy the wait loop.
                    if ($actives != 1) {
                        $lib.warn('Skipping --wait: the group has no active leader.')
                    } elif (not $allresp) {
                        $lib.warn('Skipping --wait: one or more group members did not respond.')
                    } elif ($leader_nexs = null) {
                        $lib.warn('Skipping --wait: the leader did not report a nexus index.')
                    } else {
                        while (true) {
                            $responses = ()
                            $todo = $lib.utils.todo(waitNexsOffs, ($leader_nexs - 1), timeout=$timeout)
                            for $info in $lib.aha.callPeerApi($vname, $todo, timeout=$timeout) {
                                $svcname = $info.0
                                ($ok, $info) = $info.1
                                if ($ok and $info) {
                                    $responses.append(($svcname, $info))
                                }
                            }

                            if ($lib.len($responses) = $lib.len($members)) {
                                $cell_infos = $get_cell_infos($vname, $timeout)
                                $group_status = $build_status_list($members, $cell_infos)

                                $lib.print('')
                                $lib.print('Updated status:')
                                $output_status($vname, $group_status, $printer)

                                if ($get_sync_status($group_status) = 'In Sync') {
                                    $lib.print('Group Status: In Sync')
                                    break
                                }
                            }
                        }
                    }
                }
            }
            $lib.print('')
        }
        '''
    },
)
