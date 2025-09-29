import asyncio

import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

stormcmds = [
    {
        'name': 'pkg.list',
        'descr': 'List the storm packages loaded in the cortex.',
        'cmdargs': (
            ('--verbose', {'default': False, 'action': 'store_true',
                'help': 'Display build time for each package.'}),
        ),
        'storm': '''
            init {
                $conf = ({
                    "columns": [
                        {"name": "name", "width": 40},
                        {"name": "vers", "width": 10},
                    ],
                    "separators": {
                        "row:outline": false,
                        "column:outline": false,
                        "header:row": "#",
                        "data:row": "",
                        "column": "",
                    },
                })
                if $cmdopts.verbose {
                    $conf.columns.append(({"name": "time", "width": 20}))
                }
                $printer = $lib.tabular.printer($conf)
            }

            $pkgs = $lib.pkg.list()

            if $($pkgs.size() > 0) {
                $lib.print('Loaded storm packages:')
                $lib.print($printer.header())
                for $pkg in $pkgs {
                    $row = (
                        $pkg.name, $pkg.version,
                    )
                    if $cmdopts.verbose {
                        try {
                            $row.append($lib.time.format($pkg.build.time, '%Y-%m-%d %H:%M:%S'))
                        } catch StormRuntimeError as _ {
                            $row.append('not available')
                        }
                    }
                    $lib.print($printer.row($row))
                }
            } else {
                $lib.print('No storm packages installed.')
            }
        '''
    },
    {
        'name': 'pkg.perms.list',
        'descr': 'List any permissions declared by the package.',
        'cmdargs': (
            ('name', {'help': 'The name (or name prefix) of the package.', 'type': 'str'}),
        ),
        'storm': '''
            $pdef = $lib.null
            for $pkg in $lib.pkg.list() {
                if $pkg.name.startswith($cmdopts.name) {
                    $pdef = $pkg
                    break
                }
            }

            if (not $pdef) {
                $lib.warn(`Package ({$cmdopts.name}) not found!`)
            } else {
                if $pdef.perms {
                    $lib.print(`Package ({$cmdopts.name}) defines the following permissions:`)
                    for $permdef in $pdef.perms {
                        $defv = $permdef.default
                        if ( $defv = $lib.null ) {
                            $defv = $lib.false
                        }
                        $text = `{('.').join($permdef.perm).ljust(32)} : {$permdef.desc} ( default: {$defv} )`
                        $lib.print($text)
                    }
                } else {
                    $lib.print(`Package ({$cmdopts.name}) contains no permissions definitions.`)
                }
            }
        '''
    },
    {
        'name': 'pkg.del',
        'descr': 'Remove a storm package from the cortex.',
        'cmdargs': (
            ('name', {'help': 'The name (or name prefix) of the package to remove.'}),
        ),
        'storm': '''

            $pkgs = $lib.set()

            for $pkg in $lib.pkg.list() {
                if $pkg.name.startswith($cmdopts.name) {
                    $pkgs.add($pkg.name)
                }
            }

            if $($pkgs.size() = 0) {

                $lib.print('No package names match "{name}". Aborting.', name=$cmdopts.name)

            } elif $($pkgs.size() = 1) {

                $name = $pkgs.list().index(0)
                $lib.print('Removing package: {name}', name=$name)
                $lib.pkg.del($name)

            } else {

                $lib.print('Multiple package names match "{name}". Aborting.', name=$cmdopts.name)

            }
        '''
    },
    {
        'name': 'pkg.docs',
        'descr': 'Display documentation included in a storm package.',
        'cmdargs': (
            ('name', {'help': 'The name (or name prefix) of the package.'}),
        ),
        'storm': '''
            $pdef = $lib.null
            for $pkg in $lib.pkg.list() {
                if $pkg.name.startswith($cmdopts.name) {
                    $pdef = $pkg
                    break
                }
            }

            if (not $pdef) {
                $lib.warn("Package ({name}) not found!", name=$cmdopts.name)
            } else {
                if $pdef.docs {
                    for $doc in $pdef.docs {
                        $lib.print($doc.content)
                    }
                } else {
                    $lib.print("Package ({name}) contains no documentation.", name=$cmdopts.name)
                }
            }
        '''
    },
    {
        'name': 'pkg.load',
        'descr': 'Load a storm package from an HTTP URL.',
        'cmdargs': (
            ('url', {'help': 'The HTTP URL to load the package from.'}),
            ('--raw', {'default': False, 'action': 'store_true',
                'help': 'Response JSON is a raw package definition without an envelope.'}),
            ('--verify', {'default': False, 'action': 'store_true',
                'help': 'Enforce code signature verification on the storm package.'}),
            ('--ssl-noverify', {'default': False, 'action': 'store_true',
                'help': 'Specify to disable SSL verification of the server.'}),
        ),
        'storm': '''
            init {
                $ssl = $lib.true
                if $cmdopts.ssl_noverify { $ssl = $lib.false }

                $headers = ({'X-Synapse-Version': ('.').join($lib.version.synapse())})

                $resp = $lib.inet.http.get($cmdopts.url, ssl_verify=$ssl, headers=$headers)

                if ($resp.code != 200) {
                    $lib.warn("pkg.load got HTTP code: {code} for URL: {url}", code=$resp.code, url=$cmdopts.url)
                    $lib.exit()
                }

                $reply = $resp.json()
                if $cmdopts.raw {
                    $pkg = $reply
                } else {
                    if ($reply.status != "ok") {
                        $lib.warn("pkg.load got JSON error: {code} for URL: {url}", code=$reply.code, url=$cmdopts.url)
                        $lib.exit()
                    }

                    $pkg = $reply.result
                }

                $pkd = $lib.pkg.add($pkg, verify=$cmdopts.verify)

                $lib.print("Loaded Package: {name} @{version}", name=$pkg.name, version=$pkg.version)
            }
        ''',
    },
]

@s_stormtypes.registry.registerLib
class LibPkg(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Storm Packages.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a Storm Package to the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgAdd',
                  'args': (
                      {'name': 'pkgdef', 'type': 'dict', 'desc': 'A Storm Package definition.', },
                      {'name': 'verify', 'type': 'boolean', 'default': False,
                       'desc': 'Verify storm package signature.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get a Storm Package from the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'A Storm Package name.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'The Storm package definition.', }}},
        {'name': 'has', 'desc': 'Check if a Storm Package is available in the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgHas',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'A Storm Package name to check for the existence of.', },
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the package exists in the Cortex, False if it does not.', }}},
        {'name': 'del', 'desc': 'Delete a Storm Package from the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgDel',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the package to delete.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'list', 'desc': 'Get a list of Storm Packages loaded in the Cortex.',
         'type': {'type': 'function', '_funcname': '_libPkgList',
                  'returns': {'type': 'list', 'desc': 'A list of Storm Package definitions.', }}},
        {'name': 'deps', 'desc': 'Verify the dependencies for a Storm Package.',
         'type': {'type': 'function', '_funcname': '_libPkgDeps',
                  'args': (
                      {'name': 'pkgdef', 'type': 'dict', 'desc': 'A Storm Package definition.', },
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary listing dependencies and if they are met.', }}},
        {'name': 'vars',
         'desc': "Get a dictionary representing the package's persistent variables.",
         'type': {'type': 'function', '_funcname': '_libPkgVars',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'A Storm Package name to get vars for.', },
                  ),
                  'returns': {'type': 'pkg:vars', 'desc': 'A dictionary representing the package variables.', }}},
        {'name': 'queues',
         'desc': "Access namespaced Queues for a package.",
         'type': {'type': 'function', '_funcname': '_libPkgQueues',
                  'args': (
                      {'name': 'name', 'type': 'str',
                       'desc': 'A Storm Package name to access Queues for.', },
                  ),
                  'returns': {'type': 'pkg:queues', 'desc': 'An object for accessing the package Queues.', }}},
    )
    _storm_lib_perms = (
        {'perm': ('power-ups', '<name>', 'admin'), 'gate': 'cortex',
         'desc': 'Controls the ability to interact with the vars or Queues for a Storm Package by name.'},
    )
    _storm_lib_path = ('pkg',)

    def getObjLocals(self):
        return {
            'add': self._libPkgAdd,
            'get': self._libPkgGet,
            'has': self._libPkgHas,
            'del': self._libPkgDel,
            'list': self._libPkgList,
            'deps': self._libPkgDeps,
            'vars': self._libPkgVars,
            'queues': self._libPkgQueues,
        }

    async def _libPkgAdd(self, pkgdef, verify=False):
        self.runt.confirm(('pkg', 'add'), None)
        pkgdef = await s_stormtypes.toprim(pkgdef)
        verify = await s_stormtypes.tobool(verify)
        await self.runt.snap.core.addStormPkg(pkgdef, verify=verify)

    @s_stormtypes.stormfunc(readonly=True)
    async def _libPkgGet(self, name):
        name = await s_stormtypes.tostr(name)
        pkgdef = await self.runt.snap.core.getStormPkg(name)
        if pkgdef is None:
            return None

        return s_stormtypes.Dict(pkgdef)

    @s_stormtypes.stormfunc(readonly=True)
    async def _libPkgHas(self, name):
        name = await s_stormtypes.tostr(name)
        pkgdef = await self.runt.snap.core.getStormPkg(name)
        if pkgdef is None:
            return False
        return True

    async def _libPkgDel(self, name):
        self.runt.confirm(('pkg', 'del'), None)
        await self.runt.snap.core.delStormPkg(name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _libPkgList(self):
        pkgs = await self.runt.snap.core.getStormPkgs()
        return list(sorted(pkgs, key=lambda x: x.get('name')))

    @s_stormtypes.stormfunc(readonly=True)
    async def _libPkgDeps(self, pkgdef):
        pkgdef = await s_stormtypes.toprim(pkgdef)
        return await self.runt.snap.core.verifyStormPkgDeps(pkgdef)

    async def _libPkgVars(self, name):
        name = await s_stormtypes.tostr(name)
        s_stormtypes.confirm(('power-ups', name, 'admin'))
        return PkgVars(self.runt, name)

    async def _libPkgQueues(self, name):
        name = await s_stormtypes.tostr(name)
        s_stormtypes.confirm(('power-ups', name, 'admin'))
        return PkgQueues(self.runt, name)

@s_stormtypes.registry.registerType
class PkgVars(s_stormtypes.Prim):
    '''
    The Storm deref/setitem/iter convention on top of pkg vars information.
    '''
    _storm_typename = 'pkg:vars'
    _ismutable = True

    def __init__(self, runt, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt

    def _reqPkgAdmin(self):
        s_stormtypes.confirm(('power-ups', self.valu, 'admin'))

    @s_stormtypes.stormfunc(readonly=True)
    async def deref(self, name):
        self._reqPkgAdmin()
        name = await s_stormtypes.tostr(name)
        return await self.runt.snap.core.getStormPkgVar(self.valu, name)

    async def setitem(self, name, valu):
        self._reqPkgAdmin()
        name = await s_stormtypes.tostr(name)

        if valu is s_stormtypes.undef:
            await self.runt.snap.core.popStormPkgVar(self.valu, name)
            return

        valu = await s_stormtypes.toprim(valu)
        await self.runt.snap.core.setStormPkgVar(self.valu, name, valu)

    @s_stormtypes.stormfunc(readonly=True)
    async def iter(self):
        self._reqPkgAdmin()
        async for name, valu in self.runt.snap.core.iterStormPkgVars(self.valu):
            yield name, valu
            await asyncio.sleep(0)

@s_stormtypes.registry.registerType
class PkgQueues(s_stormtypes.Prim):
    '''
    A StormLib API instance for interacting with persistent Queues for a package in the Cortex.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': 'Add a Queue for the package with a given name.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Queue to add.'},
                  ),
                  'returns': {'type': 'pkg:queue'}}},
        {'name': 'gen', 'desc': 'Add or get a Queue in a single operation.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueGen',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Queue to add or get.'},
                  ),
                  'returns': {'type': 'pkg:queue'}}},
        {'name': 'del', 'desc': 'Delete a given Queue.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueDel',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Queue to delete.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'get', 'desc': 'Get an existing Queue.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Queue to get.'},
                  ),
                  'returns': {'type': 'pkg:queue', 'desc': 'A ``pkg:queue`` object.'}}},
        {'name': 'list', 'desc': 'Get a list of the Queues for the package in the Cortex.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueList',
                  'returns': {'name': 'yields', 'type': 'dict', 'desc': 'Queue definitions for the package.'}}},
    )
    _storm_typename = 'pkg:queues'
    _ismutable = False

    def __init__(self, runt, valu, path=None):
        s_stormtypes.Prim.__init__(self, valu, path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'add': self._methPkgQueueAdd,
            'gen': self._methPkgQueueGen,
            'del': self._methPkgQueueDel,
            'get': self._methPkgQueueGet,
            'list': self._methPkgQueueList,
        }

    def _reqPkgAdmin(self):
        s_stormtypes.confirm(('power-ups', self.valu, 'admin'))

    async def _methPkgQueueAdd(self, name):
        self._reqPkgAdmin()
        name = await s_stormtypes.tostr(name)

        await self.runt.snap.core.addStormPkgQueue(self.valu, name)
        return StormPkgQueue(self.runt, self.valu, name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPkgQueueGet(self, name):
        self._reqPkgAdmin()
        name = await s_stormtypes.tostr(name)

        await self.runt.snap.core.getStormPkgQueue(self.valu, name)
        return StormPkgQueue(self.runt, self.valu, name)

    async def _methPkgQueueGen(self, name):
        try:
            return await self._methPkgQueueGet(name)
        except s_exc.NoSuchName:
            return await self._methPkgQueueAdd(name)

    async def _methPkgQueueDel(self, name):
        self._reqPkgAdmin()
        name = await s_stormtypes.tostr(name)

        await self.runt.snap.core.delStormPkgQueue(self.valu, name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPkgQueueList(self):
        self._reqPkgAdmin()
        async for pkginfo in self.runt.snap.core.listStormPkgQueues(pkgname=self.valu):
            yield pkginfo

@s_stormtypes.registry.registerType
class StormPkgQueue(s_stormtypes.StormType):
    '''
    A StormLib API instance for a package Queue.
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the Queue.', 'type': 'str'},
        {'name': 'pkgname', 'desc': 'The name of the package the Queue belongs to.', 'type': 'str'},
        {'name': 'get', 'desc': 'Get a particular item from the Queue.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueGet',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'desc': 'The offset to retrieve an item from.', 'default': 0},
                      {'name': 'wait', 'type': 'boolean', 'default': True,
                       'desc': 'Wait for the offset to be available before returning the item.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'A tuple of the offset and the item from the Queue. If wait is false and '
                                      'the offset is not present, null is returned.'}}},
        {'name': 'pop', 'desc': 'Pop an item from the Queue at a specific offset.',
         'type': {'type': 'function', '_funcname': '_methPkgQueuePop',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'default': None,
                        'desc': 'Offset to pop the item from. If not specified, the first item in the Queue will be'
                                ' popped.', },
                      {'name': 'wait', 'type': 'boolean', 'default': False,
                        'desc': 'Wait for an item to be available to pop.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'The offset and item popped from the Queue. If there is no item at the '
                                      'offset or the Queue is empty and wait is false, it returns null.'}}},
        {'name': 'put', 'desc': 'Put an item into the Queue.',
         'type': {'type': 'function', '_funcname': '_methPkgQueuePut',
                  'args': (
                      {'name': 'item', 'type': 'prim', 'desc': 'The item being put into the Queue.'},
                  ),
                  'returns': {'type': 'int', 'desc': 'The Queue offset of the item.'}}},
        {'name': 'puts', 'desc': 'Put multiple items into the Queue.',
         'type': {'type': 'function', '_funcname': '_methPkgQueuePuts',
                  'args': (
                      {'name': 'items', 'type': 'list', 'desc': 'The items to put into the Queue.'},
                  ),
                  'returns': {'type': 'int', 'desc': 'The Queue offset of the first item.'}}},
        {'name': 'gets', 'desc': 'Get multiple items from the Queue as a iterator.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueGets',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'desc': 'The offset to retrieve an items from.', 'default': 0},
                      {'name': 'wait', 'type': 'boolean', 'default': True,
                       'desc': 'Wait for the offset to be available before returning the item.'},
                      {'name': 'size', 'type': 'int', 'desc': 'The maximum number of items to yield',
                       'default': None},
                  ),
                  'returns': {'name': 'Yields', 'type': 'list', 'desc': 'Yields tuples of the offset and item.'}}},
        {'name': 'cull', 'desc': 'Remove items from the Queue up to, and including, the offset.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueCull',
                  'args': (
                      {'name': 'offs', 'type': 'int', 'desc': 'The offset which to cull records from the Queue.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'size', 'desc': 'Get the number of items in the Queue.',
         'type': {'type': 'function', '_funcname': '_methPkgQueueSize',
                  'returns': {'type': 'int', 'desc': 'The number of items in the Queue.'}}},
    )
    _storm_typename = 'pkg:queue'
    _ismutable = False

    def __init__(self, runt, pkgname, name):

        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self.name = name
        self.pkgname = pkgname

        self.locls.update(self.getObjLocals())
        self.locls['name'] = self.name
        self.locls['pkgname'] = self.pkgname

    def __hash__(self):
        return hash((self._storm_typename, self.pkgname, self.name))

    def __eq__(self, othr):
        if not isinstance(othr, type(self)):
            return False
        return self.pkgname == othr.pkgname and self.name == othr.name

    def getObjLocals(self):
        return {
            'get': self._methPkgQueueGet,
            'pop': self._methPkgQueuePop,
            'put': self._methPkgQueuePut,
            'puts': self._methPkgQueuePuts,
            'gets': self._methPkgQueueGets,
            'cull': self._methPkgQueueCull,
            'size': self._methPkgQueueSize,
        }

    def _reqPkgAdmin(self):
        s_stormtypes.confirm(('power-ups', self.pkgname, 'admin'))

    async def _methPkgQueueCull(self, offs):
        self._reqPkgAdmin()
        offs = await s_stormtypes.toint(offs)
        await self.runt.snap.core.stormPkgQueueCull(self.pkgname, self.name, offs)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPkgQueueSize(self):
        self._reqPkgAdmin()
        return await self.runt.snap.core.stormPkgQueueSize(self.pkgname, self.name)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPkgQueueGets(self, offs=0, wait=True, size=None):
        self._reqPkgAdmin()
        offs = await s_stormtypes.toint(offs)
        wait = await s_stormtypes.tobool(wait)
        size = await s_stormtypes.toint(size, noneok=True)

        async for item in self.runt.snap.core.stormPkgQueueGets(self.pkgname, self.name, offs, wait=wait, size=size):
            yield item

    async def _methPkgQueuePuts(self, items):
        self._reqPkgAdmin()
        items = await s_stormtypes.toprim(items)
        return await self.runt.snap.core.stormPkgQueuePuts(self.pkgname, self.name, items)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPkgQueueGet(self, offs=0, wait=True):
        self._reqPkgAdmin()
        offs = await s_stormtypes.toint(offs)
        wait = await s_stormtypes.tobool(wait)
        return await self.runt.snap.core.stormPkgQueueGet(self.pkgname, self.name, offs, wait=wait)

    async def _methPkgQueuePop(self, offs=None, wait=False):
        self._reqPkgAdmin()
        offs = await s_stormtypes.toint(offs, noneok=True)
        wait = await s_stormtypes.tobool(wait)

        core = self.runt.snap.core
        if offs is None:
            async for item in core.stormPkgQueueGets(self.pkgname, self.name, 0, wait=wait):
                return await core.stormPkgQueuePop(self.pkgname, self.name, item[0])
            return

        return await core.stormPkgQueuePop(self.pkgname, self.name, offs)

    async def _methPkgQueuePut(self, item):
        return await self._methPkgQueuePuts((item,))

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.pkgname} - {self.name}'
