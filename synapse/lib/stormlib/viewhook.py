import copy

import synapse.lib.stormtypes as s_stormtypes

hooktypedesc = 'The hook type (`created`, `merging`, or `deleted`).'

@s_stormtypes.registry.registerType
class ViewHook(s_stormtypes.Prim):
    '''
    A view hook which runs a Storm query on a view lifecycle event.
    '''
    _storm_typename = 'view:hook'
    _storm_locals = (
        {'name': 'iden', 'desc': 'The iden of the view hook.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorIden', 'returns': {'type': 'str'}}},
        {'name': 'name', 'desc': 'The name of the view hook.',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_gtorName', '_storfunc': '_storName',
                  'returns': {'type': 'str'}}},
        {'name': 'type', 'desc': hooktypedesc,
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_gtorType', '_storfunc': '_storType',
                  'returns': {'type': 'str'}}},
        {'name': 'storm', 'desc': 'The Storm query the view hook runs.',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_gtorStorm', '_storfunc': '_storStorm',
                  'returns': {'type': 'str'}}},
        {'name': 'enabled', 'desc': 'Set to true if the view hook is enabled.',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_gtorEnabled', '_storfunc': '_storEnabled',
                  'returns': {'type': 'boolean'}}},
        {'name': 'creator', 'desc': 'The iden of the user the view hook runs as.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorCreator', 'returns': {'type': 'str'}}},
        {'name': 'created', 'desc': 'The time the view hook was created.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorCreated', 'returns': {'type': 'time'}}},
        {'name': 'updated', 'desc': 'The time the view hook was last modified.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorUpdated', 'returns': {'type': 'time'}}},
        {'name': 'pack', 'desc': 'Get the view hook definition.',
         'type': {'type': 'function', '_funcname': '_methPack', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'The view hook definition.'}}},
    )

    def __init__(self, runt, hdef):
        s_stormtypes.Prim.__init__(self, hdef)
        self.runt = runt
        self.iden = hdef.get('iden')

        self.stors.update({
            'name': self._storName,
            'type': self._storType,
            'storm': self._storStorm,
            'enabled': self._storEnabled,
        })

        self.gtors.update({
            'iden': self._gtorIden,
            'name': self._gtorName,
            'type': self._gtorType,
            'storm': self._gtorStorm,
            'enabled': self._gtorEnabled,
            'creator': self._gtorCreator,
            'created': self._gtorCreated,
            'updated': self._gtorUpdated,
        })

        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'pack': self._methPack,
        }

    async def stormrepr(self):
        return f'{self._storm_typename}: {self.valu.get("name")} ({self.iden})'

    def value(self):
        return copy.deepcopy(self.valu)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPack(self):
        return copy.deepcopy(self.valu)

    async def _setHookValu(self, name, valu):
        self.runt.reqAdmin(mesg='Modifying a view hook requires admin privileges.')
        self.valu = await self.runt.snap.core.modViewHook(self.iden, name, valu)

    async def _storName(self, name):
        await self._setHookValu('name', await s_stormtypes.tostr(name))

    async def _storType(self, htype):
        await self._setHookValu('type', await s_stormtypes.tostr(htype))

    async def _storStorm(self, storm):
        await self._setHookValu('storm', await s_stormtypes.tostr(storm))

    async def _storEnabled(self, enabled):
        await self._setHookValu('enabled', await s_stormtypes.tobool(enabled))

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorIden(self):
        return self.iden

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorName(self):
        return self.valu.get('name')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorType(self):
        return self.valu.get('type')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorStorm(self):
        return self.valu.get('storm')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorEnabled(self):
        return self.valu.get('enabled')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorCreator(self):
        return self.valu.get('creator')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorCreated(self):
        return self.valu.get('created')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorUpdated(self):
        return self.valu.get('updated')

@s_stormtypes.registry.registerLib
class LibViewHook(s_stormtypes.Lib):
    '''
    A Storm Library for managing view hooks.

    A view hook runs a Storm query as its creator, in the view, when a view is created,
    about to be merged, or about to be deleted. An exception raised by a `merging` or
    `deleted` hook aborts the merge or delete. Managing view hooks requires admin privileges.
    '''
    _storm_lib_path = ('view', 'hook')
    _storm_locals = (
        {'name': 'add', 'desc': '''
            Add a view hook.

            Example:
                Add a hook which sets the description of every new view::

                    $lib.view.hook.add(viewdesc, created, ${ $lib.view.get().set(desc, "A new view.") })
            ''',
         'type': {'type': 'function', '_funcname': '_methHookAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the view hook.'},
                      {'name': 'type', 'type': 'str', 'desc': hooktypedesc},
                      {'name': 'storm', 'type': 'str', 'desc': 'The Storm query to run.'},
                      {'name': 'enabled', 'type': 'boolean', 'default': True,
                       'desc': 'Set to false to add the view hook disabled.'},
                  ),
                  'returns': {'type': 'view:hook', 'desc': 'The new view hook.'}}},
        {'name': 'del', 'desc': 'Delete a view hook.',
         'type': {'type': 'function', '_funcname': '_methHookDel',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the view hook.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'get', 'desc': 'Get a view hook. Raises `NoSuchIden` if the view hook does not exist.',
         'type': {'type': 'function', '_funcname': '_methHookGet',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The iden of the view hook.'},
                  ),
                  'returns': {'type': 'view:hook', 'desc': 'The view hook.'}}},
        {'name': 'list', 'desc': 'List the view hooks.',
         'type': {'type': 'function', '_funcname': '_methHookList', 'args': (),
                  'returns': {'type': 'list', 'desc': 'A list of `view:hook` objects.'}}},
    )

    def getObjLocals(self):
        return {
            'add': self._methHookAdd,
            'del': self._methHookDel,
            'get': self._methHookGet,
            'list': self._methHookList,
        }

    async def _methHookAdd(self, name, type, storm, enabled=True):
        self.runt.reqAdmin(mesg='Adding a view hook requires admin privileges.')

        hdef = {
            'name': await s_stormtypes.tostr(name),
            'type': await s_stormtypes.tostr(type),
            'storm': await s_stormtypes.tostr(storm),
            'enabled': await s_stormtypes.tobool(enabled),
            'creator': self.runt.user.iden,
        }

        hdef = await self.runt.snap.core.addViewHook(hdef)
        return ViewHook(self.runt, hdef)

    async def _methHookDel(self, iden):
        self.runt.reqAdmin(mesg='Deleting a view hook requires admin privileges.')
        iden = await s_stormtypes.tostr(iden)
        await self.runt.snap.core.delViewHook(iden)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methHookGet(self, iden):
        self.runt.reqAdmin(mesg='Getting a view hook requires admin privileges.')
        iden = await s_stormtypes.tostr(iden)
        hdef = await self.runt.snap.core.getViewHook(iden)
        return ViewHook(self.runt, hdef)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methHookList(self):
        self.runt.reqAdmin(mesg='Listing view hooks requires admin privileges.')
        hdefs = await self.runt.snap.core.getViewHooks()
        hdefs.sort(key=lambda hdef: hdef.get('created'))
        return [ViewHook(self.runt, hdef) for hdef in hdefs]
