import textwrap

import synapse.exc as s_exc
import synapse.common as s_common
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
                  'returns': {'name': 'Yields', 'type': 'list',
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

            Note: non-mirror services are not displayed.
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
            for $info in $lib.aha.callPeerApi($vname, $todo, timeout=$timeout) {
                $svcname = $info.0
                ($ok, $info) = $info.1
                if $ok {
                    $cell_infos.$svcname = $info
                }
            }
            return($cell_infos)
        }

        function build_status_list(members, cell_infos) {
            $group_status = ()
            for $svc in $members {
                $svcinfo = $svc.svcinfo
                $svcname = $svc.name
                $status = ({
                    'name': $svcname,
                    'role': '<unknown>',
                    'online': $lib.dict.has($svcinfo, 'online'),
                    'ready': $svcinfo.ready,
                    'host': $svcinfo.urlinfo.host,
                    'port': $svcinfo.urlinfo.port,
                    'version': '<unknown>',
                    'synapse_version': '<unknown>',
                    'nexs_indx': (0)
                })
                if ($cell_infos.$svcname) {
                    $info = $cell_infos.$svcname
                    $cell_info = $info.cell
                    $status.nexs_indx = $cell_info.nexsindx
                    if ($cell_info.uplink) {
                        $status.role = 'follower'
                    } else {
                        $status.role = 'leader'
                    }
                    $status.version = $info.cell.verstring
                    $status.synapse_version = $info.synapse.verstring
                }
                $group_status.append($status)
            }
            return($group_status)
        }

        function check_sync_status(group_status) {
            $indices = $lib.set()
            $known_count = (0)
            for $status in $group_status {
                $indices.add($status.nexs_indx)
                $known_count = ($known_count + (1))
            }
            if ($lib.len($indices) = 1) {
                if ($known_count = $lib.len($group_status)) {
                    return(true)
                }
            }
        }

        function output_status(vname, group_status, printer) {
            $lib.print($printer.header())
            $lib.print($vname)
            for $status in $group_status {
                if ($status.nexs_indx = 0) {
                    $status.nexs_indx = '<unknown>'
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
                    $status.nexs_indx
                )
                $lib.print($printer.row($row))
            }
        }

        $virtual_services = ({})
        $member_servers = ({})

        for $svc in $lib.aha.list() {
            $name = $svc.name
            $svcinfo = $svc.svcinfo
            $urlinfo = $svcinfo.urlinfo
            $hostname = $urlinfo.hostname

            if ($name != $hostname) {
                $virtual_services.$name = $svc
            } else {
                $member_servers.$name = $svc
            }
        }

        $mirror_groups = ({})
        for ($vname, $vsvc) in $virtual_services {
            $vsvc_info = $vsvc.svcinfo
            $vsvc_iden = $vsvc_info.iden
            $vsvc_leader = $vsvc_info.leader
            $vsvc_hostname = $vsvc_info.urlinfo.hostname

            if (not $vsvc_iden or not $vsvc_hostname or not $vsvc_leader) {
                continue
            }

            $primary_member = $member_servers.$vsvc_hostname
            if (not $primary_member) {
                continue
            }

            $members = ([$primary_member])
            for ($mname, $msvc) in $member_servers {
                if ($mname != $vsvc_hostname) {
                    $msvc_info = $msvc.svcinfo
                    if ($msvc_info.iden = $vsvc_iden and $msvc_info.leader = $vsvc_leader) {
                        $members.append($msvc)
                    }
                }
            }

            if ($lib.len($members) > 1) {
                $mirror_groups.$vname = $members
            }
        }

        for ($vname, $members) in $mirror_groups {
            $cell_infos = $get_cell_infos($vname, $timeout)
            $group_status = $build_status_list($members, $cell_infos)
            $lib.print('Service Mirror Groups:')
            $output_status($vname, $group_status, $printer)

            if $check_sync_status($group_status) {
                $lib.print('Group Status: In Sync')
            } else {
                $lib.print(`Group Status: Out of Sync`)
                if $wait {
                    $leader_nexs = (0)
                    for $status in $group_status {
                        if (($status.role = 'leader') and ($status.nexs_indx > 0)) {
                            $leader_nexs = $status.nexs_indx
                        }
                    }
                    if ($leader_nexs > 0) {
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

                                if $check_sync_status($group_status) {
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
