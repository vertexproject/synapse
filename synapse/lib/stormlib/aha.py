import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class AhaLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with AHA.
    '''

    _storm_locals = (
        {'name': 'del', 'desc': 'Delete a service from AHA.',
         'type': {'type': 'function', '_funcname': '_methSvcDel',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the service to delete.', },
                      {'name': 'network', 'type': 'str', 'desc': 'An optional network to use when looking up the service name.',
                       'default': None},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'get', 'desc': 'Get information about an AHA service.',
         'type': {'type': 'function', '_funcname': '_methSvcGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the AHA service to look up.', },
                      {'name': 'filters', 'type': 'dict', 'desc': 'An optional dictionary of filters to use when resolving the AHA service.',
                       'default': None}
                  ),
                  'returns': {'type': ('null', 'dict'), 'desc': 'The AHA service information dictionary, or $lib.null.', }}},
        {'name': 'list', 'desc': 'List the services registered with AHA.',
         'type': {'type': 'function', '_funcname': '_methSvcList', 'args': (),
                  'returns': {'type': 'list', 'desc': 'A list of the AHA service dictionaries for all registered services.', }}},
    )
    _storm_lib_path = ('aha',)
    def getObjLocals(self):
        return {
            'del': self._methSvcDel,
            'get': self._methSvcGet,
            'list': self._methSvcList,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSvcList(self):
        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()
        # DISCUSS: Do we want this to be a generator or list?
        svcs = []
        async for info in proxy.getAhaSvcs():
            svcs.append(info)
        return svcs

    async def _methSvcDel(self, name, network=None):
        self.runt.reqAdmin()
        name = await s_stormtypes.tostr(name)
        network = await s_stormtypes.tostr(network, noneok=True)
        proxy = await self.runt.snap.core.reqAhaProxy()
        return await proxy.delAhaSvc(name, network=network)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSvcGet(self, name, filters=None):
        self.runt.reqAdmin()
        name = await s_stormtypes.tostr(name)
        filters = await s_stormtypes.toprim(filters)
        proxy = await self.runt.snap.core.reqAhaProxy()
        return await proxy.getAhaSvc(name, filters=filters)

@s_stormtypes.registry.registerLib
class AhaPoolLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with AHA service pools.
    '''

    _storm_locals = (
        {'name': 'add', 'desc': 'Add a new AHA service pool.',
         'type': {'type': 'function', '_funcname': '_add',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the pool to add.', },
                  ),
                  'returns': {'type': 'aha:pool'}}},
        {'name': 'del', 'desc': 'Delete an existing AHA service pool.',
         'type': {'type': 'function', '_funcname': '_del',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the pool to delete.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The AHA pool definition that was deleted.'}}},
        {'name': 'get', 'desc': 'Get an existing AHA service pool.',
         'type': {'type': 'function', '_funcname': '_get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the pool to get.', },
                  ),
                  'returns': {'type': ['null', 'aha:pool'], 'desc': 'The pool if it exists, or $lib.null.'}}},
        {'name': 'list', 'desc': 'Enumerate all of the AHA service pools.',
         'type': {'type': 'function', '_funcname': '_list',
                  'returns': {'name': 'yields', 'type': 'aha:pool'}}},
    )
    _storm_lib_path = ('aha', 'pool')

    def getObjLocals(self):
        return {
            'add': self._add,
            'del': self._del,
            'get': self._get,
            'list': self._list,
        }

    async def _add(self, name):
        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()
        poolinfo = {'creator': self.runt.user.iden}
        poolinfo = await proxy.addAhaPool(name, poolinfo)
        return AhaPool(self.runt, poolinfo)

    async def _del(self, name):
        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()
        return await proxy.delAhaPool(name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _get(self, name):
        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()
        poolinfo = await proxy.getAhaPool(name)
        if poolinfo is not None:
            return AhaPool(self.runt, poolinfo)

    @s_stormtypes.stormfunc(readonly=True)
    async def _list(self):
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
        {'name': 'add', 'desc': 'Add a service to the AHA pool.',
         'type': {'type': 'function', '_funcname': '_add',
                  'args': (
                      {'name': 'svcname', 'type': 'str', 'desc': 'The name of the AHA service to add.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'add', 'desc': 'Remove a service from the AHA pool.',
         'type': {'type': 'function', '_funcname': '_del',
                  'args': (
                      {'name': 'svcname', 'type': 'str', 'desc': 'The name of the AHA service to remove.', },
                  ),
                  'returns': {'type': 'null', }}},
    )
    _storm_typename = 'aha:pool'

    def __init__(self, runt, poolinfo):
        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self.poolinfo = poolinfo

        self.locls.update({
            'add': self._add,
            'del': self._del,
        })

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.poolinfo.get("name")}'

    async def _derefGet(self, name):
        return self.poolinfo.get(name)

    async def _add(self, svcname):
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)

        proxy = await self.runt.snap.core.reqAhaProxy()

        poolname = self.poolinfo.get('name')

        poolinfo = {'creator': self.runt.user.iden}
        poolinfo = await proxy.addAhaPoolSvc(poolname, svcname, poolinfo)

        self.poolinfo.update(poolinfo)

    async def _del(self, svcname):
        self.runt.reqAdmin()
        svcname = await s_stormtypes.tostr(svcname)

        proxy = await self.runt.snap.core.reqAhaProxy()

        poolname = self.poolinfo.get('name')
        await proxy.delAhaPoolSvc(poolname, svcname)

        self.poolinfo = await proxy.getAhaPool(poolname)

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

            $pool.del($cmdopts.svcname)
            $lib.print(`AHA service ({$cmdopts.svcname}) removed from service pool ({$pool.name})`)
        ''',
    },
    {
        'name': 'aha.svc.stat',
        'descr': 'Show all information for a specific aha service.',
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
                if ($_emsg = $lib.null ) {
                    $_emsg = `{$_err}`
                }
                return ( $_emsg )
            }
        }

        function _getBoolKey(dict, key, default) {
            $_valu = $dict.$key
            if ( $_valu != $lib.null ) {
                if $_valu {
                    return ( true )
                } else {
                    return ( false )
                }
            }
            return ( $default )
        }

        $svc = $lib.aha.get($cmdopts.svc)
        if ($svc = (null)) {
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
                if ($leader = (null)) {
                    $leader = 'Service did not register itself with a leader name.'
                }
                $lib.print(`Name:       {$svc.name}`)
                $lib.print(`Online:     {$_getBoolKey($svcinfo, online, null)}`)
                $lib.print(`Ready:      {$_getBoolKey($svcinfo, ready, null)}`)
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
        'descr': 'List AHA services.',
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
                if ($_emsg = $lib.null ) {
                    $_emsg = `{$_err}`
                }
                return ( $_emsg )
            }
        }

        function _getBoolKey(dict, key, default) {
            $_valu = $dict.$key
            if ( $_valu != $lib.null ) {
                if $_valu {
                    return ( true )
                } else {
                    return ( false )
                }
            }
            return ( $default )
        }

        $leaders = $lib.set()
        $svcs = $lib.aha.list()
        if ($lib.len($svcs) = 0) {
            $lib.print('No AHA services registered.')
        }
        else {
            $columns = 'Name                           Leader Online Ready Host            Port '
            if $cmdopts.nexus {
                $columns = `{$columns} Nexus`
            }

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
                        $nexusOffset = 'Service is not online. Will not attempt to retrieve its nexus offset.'
                    }
                }
                $name=$name.ljust(30)

                $online = $_getBoolKey($svcinfo, online, null)
                $online = $online.ljust(6)

                $urlinfo = $svcinfo.urlinfo

                $host = $urlinfo.host
                $host = $host.ljust(15)

                $port = $lib.cast(str, $urlinfo.port)  // Cast to str
                $port = $port.ljust(5)

                $ready = $_getBoolKey($svcinfo, ready, null)
                $ready = $ready.ljust(5)

                $leader = null
                if ( $svcinfo.leader != $lib.null ) {
                    if $leaders.has($svcinfo.run) {
                        $leader = true
                    } else {
                        $leader = false
                    }
                }
                $leader = $leader.ljust(6)

                if $info {
                    $s = `{$name} {$leader} {$online} {$ready} {$host} {$port}`
                    if ($nexusOffset != (null)) {
                        $s = `{$s} {$nexusOffset}`
                    }
                    $lib.print($s)
                }
            }
        }
        '''
    }
)
