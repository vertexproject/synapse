import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class AhaPoolLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with AHA service pools.
    '''
    _storm_lib_path = ('aha', 'pool')

    def getObjLocals(self):
        return {
            'add': self.add,
            'del': self._del,
            'get': self.get,
            'list': self.list,
        }

    async def add(self, name):
        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()
        poolinfo = {'creator': self.runt.user.iden}
        poolinfo = await proxy.addAhaPool(name, poolinfo)
        return AhaPool(self.runt, poolinfo)

    async def _del(self, name):
        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()
        return await proxy.delAhaPool(name)

    async def get(self, name):
        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()
        poolinfo = await proxy.getAhaPool(name)
        if poolinfo is not None:
            return AhaPool(self.runt, poolinfo)

    async def list(self):

        self.runt.reqAdmin()
        proxy = await self.runt.snap.core.reqAhaProxy()

        async for poolinfo in proxy.getAhaPools():
            yield AhaPool(self.runt, poolinfo)

@s_stormtypes.registry.registerType
class AhaPool(s_stormtypes.StormType):
    _storm_typename = 'aha:pool'

    def __init__(self, runt, poolinfo):
        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self.poolinfo = poolinfo

        self.locls.update({
            'add': self.add,
            'del': self._del,
        })

    async def _derefGet(self, name):
        return self.poolinfo.get(name)

    async def add(self, svcname):
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
            $lib.print($pool)
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
            if (not $pool) { $lib.exit(`No AHA serivce pool named: {$cmdopts.poolname}`) }

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
            if (not $pool) { $lib.exit(`No AHA serivce pool named: {$cmdopts.poolname}`) }

            $pool.del($cmdopts.svcname)
            $lib.print(`AHA service ({$cmdopts.svcname}) removed from service pool ({$pool.name})`)
        ''',
    },
)
