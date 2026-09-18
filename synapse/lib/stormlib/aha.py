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

                $lib.aha.get(00.cortex...)

            Getting service information with its full name::

                $lib.aha.get(00.cortex.loop.vertex.link)
        ''',
         'type': {'type': 'function', '_funcname': '_methAhaGet',
                  'args': (
                      {'name': 'svcname', 'type': 'str',
                       'desc': 'The name of the AHA service to look up. It is easiest to use the relative name of a service, ending with "...".', },
                      {'name': 'filters', 'type': 'dict', 'default': None,
                       'desc': 'An optional dictionary of filters to use when resolving the AHA service.'}
                  ),
                  'returns': {'type': ('null', 'dict'),
                              'desc': 'The AHA service information dictionary, or ``(null))``.', }}},
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
        proxy = await self.runt.snap.core.reqAhaProxy()
        async for info in proxy.getAhaSvcs():
            yield info

    async def _methAhaDel(self, svcname):
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)
        proxy = await self.runt.snap.core.reqAhaProxy()
        svc = await proxy.getAhaSvc(svcname)
        if svc is None:
            raise s_exc.NoSuchName(mesg=f'No AHA service for {svcname=}')
        if svc.get('services'):  # It is an AHA Pool!
            mesg = f'Cannot use $lib.aha.del() to remove an AHA Pool. Use $lib.aha.pool.del(); {svcname=}'
            raise s_exc.BadArg(mesg=mesg)
        return await proxy.delAhaSvc(svc.get('svcname'), network=svc.get('svcnetw'))

    @s_stormtypes.stormfunc(readonly=True)
    async def _methAhaGet(self, svcname, filters=None):
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)
        filters = await s_stormtypes.toprim(filters)
        proxy = await self.runt.snap.core.reqAhaProxy()
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

        proxy = await self.runt.snap.core.reqAhaProxy()
        svc = await proxy.getAhaSvc(svcname)
        if svc is None:
            raise s_exc.NoSuchName(mesg=f'No AHA service found for {svcname}')

        svcinfo = svc.get('svcinfo')
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

        proxy = await self.runt.snap.core.reqAhaProxy()
        svc = await proxy.getAhaSvc(svcname)
        if svc is None:
            raise s_exc.NoSuchName(mesg=f'No AHA service found for {svcname}')

        svcinfo = svc.get('svcinfo')
        svciden = svcinfo.get('iden')
        if svciden is None:
            raise s_exc.NoSuchName(mesg=f'Service {svcname} has no iden')

        async for svcname, (ok, info) in proxy.callAhaPeerGenr(svciden, todo, timeout=timeout, skiprun=skiprun):
            yield (svcname, (ok, info))

@s_stormtypes.registry.registerLib
class AhaPoolLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with AHA service pools.
    '''

    _storm_locals = (
        {'name': 'add', 'desc': '''Add a new AHA service pool.

        Examples:
            Add a pool via its relative name::

                $lib.aha.pool.add(pool00.cortex...)
        ''',
         'type': {'type': 'function', '_funcname': '_methPoolAdd',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the pool to add. It is easiest to use the relative name of a pool, ending with "...".', },
                  ),
                  'returns': {'type': 'aha:pool'}}},
        {'name': 'del', 'desc': '''Delete an existing AHA service pool.

        Examples:
            Delete a pool via its relative name::

                $lib.aha.pool.del(pool00.cortex...)
        ''',
         'type': {'type': 'function', '_funcname': '_methPoolDel',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the pool to delete. It is easiest to use the relative name of a pool, ending with "...".', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The AHA pool definition that was deleted.'}}},
        {'name': 'get', 'desc': 'Get an existing AHA service pool.',
         'type': {'type': 'function', '_funcname': '_methPoolGet',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'The name of the pool to get. It is easiest to use the relative name of a pool, ending with "...".', },
                  ),
                  'returns': {'type': ['null', 'aha:pool'], 'desc': 'The pool if it exists, or ``(null)``.'}}},
        {'name': 'list', 'desc': 'Enumerate all of the AHA service pools.',
         'type': {'type': 'function', '_funcname': '_methPoolList',
                  'returns': {'name': 'yields', 'type': 'aha:pool'}}},
    )
    _storm_lib_path = ('aha', 'pool')

    def getObjLocals(self):
        return {
            'add': self._methPoolAdd,
            'del': self._methPoolDel,
            'get': self._methPoolGet,
            'list': self._methPoolList,
        }

    async def _methPoolAdd(self, name):
        self.runt.reqAdmin()
        name = await s_stormtypes.tostr(name)
        proxy = await self.runt.snap.core.reqAhaProxy()
        poolinfo = {'creator': self.runt.user.iden}
        poolinfo = await proxy.addAhaPool(name, poolinfo)
        return AhaPool(self.runt, poolinfo)

    async def _methPoolDel(self, name):
        self.runt.reqAdmin()
        name = await s_stormtypes.tostr(name)
        proxy = await self.runt.snap.core.reqAhaProxy()
        return await proxy.delAhaPool(name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPoolGet(self, name):
        self.runt.reqAdmin()
        name = await s_stormtypes.tostr(name)
        proxy = await self.runt.snap.core.reqAhaProxy()
        poolinfo = await proxy.getAhaPool(name)
        if poolinfo is not None:
            return AhaPool(self.runt, poolinfo)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPoolList(self):
        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()

        async for poolinfo in proxy.getAhaPools():
            yield AhaPool(self.runt, poolinfo)

@s_stormtypes.registry.registerType
class AhaPool(s_stormtypes.StormType):
    '''
    Implements the Storm API for an AHA pool.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': '''Add a service to the AHA pool

        Examples:
            Add a service to a pool with its relative name::

                $pool = $lib.aha.pool.get(pool00.cortex...)
                $pool.add(00.cortex...)
        ''',
         'type': {'type': 'function', '_funcname': '_methPoolSvcAdd',
                  'args': (
                      {'name': 'svcname', 'type': 'str',
                       'desc': 'The name of the AHA service to add. It is easiest to use the relative name of a service, ending with "...".', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'del', 'desc': '''Remove a service from the AHA pool.

        Examples:
            Remove a service from a pool with its relative name::

                $pool = $lib.aha.pool.get(pool00.cortex...)
                $pool.del(00.cortex...)
        ''',
         'type': {'type': 'function', '_funcname': '_methPoolSvcDel',
                  'args': (
                      {'name': 'svcname', 'type': 'str',
                       'desc': 'The name of the AHA service to remove. It is easiest to use the relative name of a service, ending with "...".', },
                  ),
                  'returns': {'type': ['null', 'str'], 'desc': 'The service removed from the pool or null if a service was not removed.'}}},
    )
    _storm_typename = 'aha:pool'

    def __init__(self, runt, poolinfo):
        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self.poolinfo = poolinfo

        self.locls.update({
            'add': self._methPoolSvcAdd,
            'del': self._methPoolSvcDel,
        })

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.poolinfo.get("name")}'

    async def _derefGet(self, name):
        return self.poolinfo.get(name)

    async def _methPoolSvcAdd(self, svcname):
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)

        proxy = await self.runt.snap.core.reqAhaProxy()

        poolname = self.poolinfo.get('name')

        poolinfo = {'creator': self.runt.user.iden}
        poolinfo = await proxy.addAhaPoolSvc(poolname, svcname, poolinfo)

        self.poolinfo.update(poolinfo)

    async def _methPoolSvcDel(self, svcname):
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)

        proxy = await self.runt.snap.core.reqAhaProxy()

        poolname = self.poolinfo.get('name')
        newinfo = await proxy.delAhaPoolSvc(poolname, svcname)

        tname = svcname
        if tname.endswith('...'):
            tname = tname[:-2]
        deleted_service = None
        deleted_services = [svc for svc in self.poolinfo.get('services').keys()
                            if svc not in newinfo.get('services') and svc.startswith(tname)]
        if deleted_services:
            deleted_service = deleted_services[0]

        self.poolinfo = newinfo

        return deleted_service

stormcmds = (
    {
        'name': 'aha.pool.list',
        'descr': 'Display a list of AHA service pools and their services.',
        'storm': '''

        $count = (0)
        for $pool in $lib.aha.pool.list() {
            $count = ($count + 1)
            $lib.print(`Pool: {$pool.name}`)
            for ($svcname, $svcinfo) in $pool.services {
                $lib.print(`    {$svcname}`)
            }
        }
        $lib.print(`{$count} pools.`)
        ''',
    },
    {
        'name': 'aha.pool.add',
        'descr': 'Create an AHA service pool configuration.',
        'cmdargs': (
            ('name', {'help': 'The name of the new AHA service pool.'}),
        ),
        'storm': '''
            $pool = $lib.aha.pool.add($cmdopts.name)
            $lib.print(`Created AHA service pool: {$pool.name}`)
        '''
    },
    {
        'name': 'aha.pool.del',
        'descr': 'Delete an AHA service pool configuration.',
        'cmdargs': (
            ('name', {'help': 'The name of the AHA pool to delete.'}),
        ),
        'storm': '''
            $pool = $lib.aha.pool.del($cmdopts.name)
            if $pool { $lib.print(`Removed AHA service pool: {$pool.name}`) }
        ''',
    },
    {
        'name': 'aha.pool.svc.add',
        'descr': '''
            Add an AHA service to a service pool.

            Examples:

                // add 00.cortex... to the existing pool named pool.cortex
                aha.pool.svc.add pool.cortex... 00.cortex...
        ''',
        'cmdargs': (
            ('poolname', {'help': 'The name of the AHA pool.'}),
            ('svcname', {'help': 'The name of the AHA service.'}),
        ),
        'storm': '''
            $pool = $lib.aha.pool.get($cmdopts.poolname)
            if (not $pool) { $lib.exit(`No AHA service pool named: {$cmdopts.poolname}`) }

            $pool.add($cmdopts.svcname)
            $lib.print(`AHA service ({$cmdopts.svcname}) added to service pool ({$pool.name})`)
        ''',
    },
    {
        'name': 'aha.pool.svc.del',
        'descr': 'Remove an AHA service from a service pool.',
        'cmdargs': (
            ('poolname', {'help': 'The name of the AHA pool.'}),
            ('svcname', {'help': 'The name of the AHA service.'}),
        ),
        'storm': '''
            $pool = $lib.aha.pool.get($cmdopts.poolname)
            if (not $pool) { $lib.exit(`No AHA service pool named: {$cmdopts.poolname}`) }

            $svc = $pool.del($cmdopts.svcname)
            if $svc {
                $lib.print(`AHA service ({$svc}) removed from service pool ({$pool.name})`)
            } else {
                $lib.print(`Did not remove ({$cmdopts.svcname}) from the service pool.`)
            }
        ''',
    },
    {
        'name': 'aha.svc.stat',
        'descr': '''Show all information for a specific AHA service.

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
                return ( $_info.cell.nexsindx )
            } catch * as _err {
                $_emsg = $_err.mesg
                if ($_emsg = null ) {
                    $_emsg = `{$_err}`
                }
                return ( $_emsg )
            }
        }

        $svc = $lib.aha.get($cmdopts.svc)
        if ($svc = null) {
            $lib.print(`No service found for: "{$cmdopts.svc}"`)
        } else {
            $services = $svc.services
            if $services {
                $lib.print(`Resolved {$cmdopts.svc} to an AHA Pool.\n`)
                $lib.print(`The pool currently has {$lib.len($services)} members.`)

                $lib.print(`AHA Pool:   {$svc.name}`)
                for ($_svcname, $_svcinfo) in $services {
                    $lib.print(`Member:     {$_svcname}`)
                }
            } else {
                $lib.print(`Resolved {$cmdopts.svc} to an AHA Service.\n`)
                $svcinfo = $svc.svcinfo
                $leader = $svcinfo.leader
                if ($leader = null) {
                    $leader = 'Service did not register itself with a leader name.'
                }
                $online = false
                if $svcinfo.online {
                    $online = true
                }
                $ready = 'null'
                if $lib.dict.has($svcinfo, ready) {
                    $ready = `{$svcinfo.ready}`
                }
                $lib.print(`Name:       {$svc.name}`)
                $lib.print(`Online:     {$online}`)
                $lib.print(`Ready:      {$ready}`)
                $lib.print(`Run iden:   {$svcinfo.run}`)
                $lib.print(`Cell iden:  {$svcinfo.iden}`)
                $lib.print(`Leader:     {$leader}`)

                if $cmdopts.nexus {
                    if $svcinfo.online {
                        $nexusOffset = $_getNexus($svc.name)
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
        }
        '''
    },
    {
        'name': 'aha.svc.list',
        'descr': '''List AHA services.

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
                return ( $_info.cell.nexsindx )
            } catch * as _err {
                $_emsg = $_err.mesg
                if ($_emsg = null ) {
                    $_emsg = `{$_err}`
                }
                return ( $_emsg )
            }
        }

        $svcs = ()
        for $svc in $lib.aha.list() {
            $svcs.append($svc)
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
            for $info in $svcs {
                $svcinfo = $info.svcinfo
                if $svcinfo {
                    if ($info.svcname = $svcinfo.leader) {
                        $leaders.add($svcinfo.run)
                    }
                }
            }

            $lib.print($columns)

            for $info in $svcs {
                $name = $info.name
                $nexusOffset = (null)
                $svcinfo = $info.svcinfo

                if $cmdopts.nexus {
                    if $svcinfo.online {
                        $nexusOffset = $_getNexus($name)
                    } else {
                        $nexusOffset = '<offline>'
                    }
                }
                $name=$name.ljust(45)

                $online = false
                if $svcinfo.online {
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

                $leader = null
                if ( $svcinfo.leader != null ) {
                    if $leaders.has($svcinfo.run) {
                        $leader = true
                    } else {
                        $leader = false
                    }
                }
                $leader = $leader.ljust(6)

                if $info {
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
        'descr': textwrap.dedent('''\
            Query the AHA services and their mirror relationships.

            Mirror group members are identified by the service iden which they share, so a
            group is displayed even when no service has claimed the group leader name.

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

        // AHA de-duplicates peer responses by run iden and labels each with whichever
        // service entry it resolved first, which may be the leader alias rather than the
        // member entry. Key responses by run iden and fall back to the name for peers
        // which did not report one.
        function get_cell_infos(svcname, timeout) {
            $byrun = ({})
            $byname = ({})
            $todo = $lib.utils.todo('getCellInfo')
            try {
                for $item in $lib.aha.callPeerApi($svcname, $todo, timeout=$timeout) {
                    $peername = $item.0
                    ($ok, $info) = $item.1
                    if (not $ok) { continue }

                    $byname.$peername = $info

                    $run = $info.cell.run
                    if ($run != null) {
                        $byrun.$run = $info
                    }
                }
            } catch * as err {
                $lib.warn(`Failed to query mirror group members for {$svcname}: {$err.mesg}`)
            }

            return(({"byrun": $byrun, "byname": $byname}))
        }

        function build_status_list(members, cell_infos) {
            $group_status = ()
            for $svc in $members {
                $svcinfo = $svc.svcinfo
                $svcname = $svc.name
                $status = ({
                    'name': $svcname,
                    'responded': (false),
                    'role': '<unknown>',
                    'online': $lib.dict.has($svcinfo, 'online'),
                    'ready': $svcinfo.ready,
                    'host': $svcinfo.urlinfo.host,
                    'port': $svcinfo.urlinfo.port,
                    'version': '<unknown>',
                    'synapse_version': '<unknown>',
                    'nexs_indx': (null),
                    'follows': '<unknown>'
                })
                $info = (null)

                $byrun = $cell_infos.byrun
                $run = $svcinfo.run
                if ($run != null) {
                    $info = $byrun.$run
                }

                if ($info = null) {
                    $byname = $cell_infos.byname
                    $info = $byname.$svcname
                }

                if ($info != null) {
                    $status.responded = (true)
                    $cell_info = $info.cell
                    $status.nexs_indx = $cell_info.nexsindx
                    if ($cell_info.active) {
                        $status.role = 'leader'
                    } else {
                        $status.role = 'follower'
                    }
                    $status.version = $info.cell.verstring
                    $status.synapse_version = $info.synapse.verstring

                    // The URL is sanitized by the service before it is returned to us.
                    if $lib.dict.has($cell_info, 'mirror') {
                        $mirror = $cell_info.mirror
                        if ($mirror = null) {
                            $status.follows = '<none - write root>'
                        } else {
                            $status.follows = $mirror
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

        // Leadership is reported by the service itself, so it stays accurate when the
        // leader alias is missing or stale.
        function get_group_leaders(group_status) {
            $leaders = ()
            for $status in $group_status {
                if ($status.role = 'leader') {
                    $leaders.append($status.name)
                }
            }
            return($leaders)
        }

        function output_group_leaders(leaders) {
            if ($lib.len($leaders) = 0) {
                $lib.print('Group Leader: <none>')
            } elif ($lib.len($leaders) = 1) {
                $lib.print(`Group Leader: {$leaders.0}`)
            } else {
                $lib.print(`Group Leader: <multiple: {(', ').join($leaders)}>`)
            }
        }

        function get_group_name(iden, alias, members) {

            if ($alias != null) {
                return($alias.name)
            }

            for $svc in $members {
                $leader = $svc.svcinfo.leader
                if ($leader != null) {
                    return(`{$leader}.{$svc.svcnetw} (leader alias not registered)`)
                }
            }

            return(`<no leader alias> (service iden: {$iden})`)
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
        }

        // The leader alias is only registered by an active service, so a group with no
        // claimed leader has no alias entry to group on. Every member of a mirror group
        // shares the service iden, so group on that instead.
        $leader_aliases = ({})
        $svcs_by_run = ({})

        for $svc in $lib.aha.list() {

            $svcinfo = $svc.svcinfo

            $iden = $svcinfo.iden
            $run = $svcinfo.run
            if (($iden = null) or ($run = null)) {
                continue
            }

            // A service registers its alias with addAhaSvc($leader, $info), so the alias
            // entry is the one whose service name matches the leader name it carries.
            $leader = $svcinfo.leader
            if (($leader != null) and ($svc.svcname = $leader)) {
                if (not $lib.dict.has($leader_aliases, $iden)) {
                    $leader_aliases.$iden = $svc
                }
                continue
            }

            // Several entries may share a run iden. Prefer the one which names itself.
            $runkey = `{$iden}|{$run}`
            $seen = $svcs_by_run.$runkey
            if (($seen != null) and ($seen.name = $seen.svcinfo.urlinfo.hostname)) {
                continue
            }

            $svcs_by_run.$runkey = $svc
        }

        $members_by_iden = ({})
        for ($runkey, $svc) in $svcs_by_run {
            $iden = $svc.svcinfo.iden
            $members = $members_by_iden.$iden
            if ($members = null) {
                $members = ({})
            }
            $name = $svc.name
            $members.$name = $svc
            $members_by_iden.$iden = $members
        }

        $mirror_groups = ()
        for ($iden, $membermap) in $members_by_iden {

            $names = $lib.dict.keys($membermap)
            if ($lib.len($names) <= 1) {
                continue
            }
            $names.sort()

            $members = ()
            $anyonline = (false)
            for $name in $names {
                $svc = $membermap.$name
                $members.append($svc)
                if $lib.dict.has($svc.svcinfo, 'online') {
                    $anyonline = (true)
                }
            }

            // AHA never reaps service entries, so a decommissioned cluster lingers in the
            // registry forever. Only report groups which still have a service online.
            if (not $anyonline) {
                continue
            }

            $mirror_groups.append(($iden, $members))
        }

        if ($lib.len($mirror_groups) = 0) {
            $lib.print('No mirror groups found.')
        } else {
            $lib.print('Service Mirror Groups:')
        }

        for ($iden, $members) in $mirror_groups {

            $alias = $leader_aliases.$iden
            $vname = $get_group_name($iden, $alias, $members)

            // callPeerApi() resolves any group member to the shared service iden, so a member
            // name works when no alias is registered.
            $svcname = $members.0.name
            if ($alias != null) {
                $svcname = $alias.name
            }

            $cell_infos = $get_cell_infos($svcname, $timeout)
            $group_status = $build_status_list($members, $cell_infos)
            $output_status($vname, $group_status, $printer)

            $leaders = $get_group_leaders($group_status)
            $output_group_leaders($leaders)

            $syncstatus = $get_sync_status($group_status)
            $lib.print(`Group Status: {$syncstatus}`)

            if ($syncstatus != 'In Sync') {
                if $wait {

                    $allresp = (true)
                    for $status in $group_status {
                        if (not $status.responded) {
                            $allresp = (false)
                        }
                    }

                    $leader_nexs = (null)
                    for $status in $group_status {
                        if (($status.role = 'leader') and ($status.nexs_indx != null)) {
                            $leader_nexs = $status.nexs_indx
                        }
                    }

                    // Without a single leader there is no replication to wait on, and
                    // an unresponsive member can never satisfy the wait loop.
                    if ($lib.len($leaders) != 1) {
                        $lib.warn('Skipping --wait: the group has no active leader.')
                    } elif (not $allresp) {
                        $lib.warn('Skipping --wait: one or more group members did not respond.')
                    } elif ($leader_nexs = null) {
                        $lib.warn('Skipping --wait: the leader did not report a nexus index.')
                    } else {
                        while (true) {
                            $responses = ()
                            $todo = $lib.utils.todo(waitNexsOffs, ($leader_nexs - 1), timeout=$timeout)
                            for $info in $lib.aha.callPeerApi($svcname, $todo, timeout=$timeout) {
                                $peername = $info.0
                                ($ok, $info) = $info.1
                                if ($ok and $info) {
                                    $responses.append(($peername, $info))
                                }
                            }

                            if ($lib.len($responses) = $lib.len($members)) {
                                $cell_infos = $get_cell_infos($svcname, $timeout)
                                $group_status = $build_status_list($members, $cell_infos)

                                $lib.print('')
                                $lib.print('Updated status:')
                                $output_status($vname, $group_status, $printer)

                                $syncstatus = $get_sync_status($group_status)
                                if ($syncstatus = 'In Sync') {
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
