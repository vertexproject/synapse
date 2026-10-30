import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerType
class ViewHook(s_stormtypes.Prim):
    '''
    A view hook which runs a Storm query on a view lifecycle event.
    '''
    _storm_typename = 'view:hook'
    _storm_locals = (
        {'name': 'iden', 'desc': 'The iden of the view hook.', 'type': 'str'},
        {'name': 'name', 'desc': 'The name of the view hook.',
         'type': {'type': 'stor', '_storfunc': '_storName', 'returns': {'type': 'str'}}},
        {'name': 'type', 'desc': 'The hook type (`created`, `merging`, or `deleted`).',
         'type': {'type': 'stor', '_storfunc': '_storType', 'returns': {'type': 'str'}}},
        {'name': 'storm', 'desc': 'The Storm query the view hook runs.',
         'type': {'type': 'stor', '_storfunc': '_storStorm', 'returns': {'type': 'str'}}},
        {'name': 'enabled', 'desc': 'Set to true if the view hook is enabled.',
         'type': {'type': 'stor', '_storfunc': '_storEnabled', 'returns': {'type': 'boolean'}}},
        {'name': 'creator', 'desc': 'The iden of the user who added the view hook.', 'type': 'str'},
        {'name': 'created', 'desc': 'The time the view hook was created.', 'type': 'time'},
        {'name': 'updated', 'desc': 'The time the view hook was last modified.', 'type': 'time'},
    )

    def __init__(self, runt, iden):
        s_stormtypes.Prim.__init__(self, iden)
        self.runt = runt
        self.iden = iden

        self.locls['iden'] = iden

        self.stors.update({
            'name': self._storName,
            'type': self._storType,
            'storm': self._storStorm,
            'enabled': self._storEnabled,
        })

    async def stormrepr(self):
        hdef = await self.value()
        return f'{self._storm_typename}: {hdef.get("name")} ({self.iden})'

    async def value(self):
        return await self.runt.snap.core.getViewHook(self.iden)

    async def _derefGet(self, name):
        hdef = await self.value()
        return hdef.get(name, s_common.novalu)

    async def _setHookValu(self, name, valu):
        self.runt.reqAdmin(mesg='Modifying a view hook requires admin privileges.')
        await self.runt.snap.core.modViewHook(self.iden, {name: valu})

    async def _storName(self, name):
        await self._setHookValu('name', await s_stormtypes.tostr(name))

    async def _storType(self, htype):
        await self._setHookValu('type', await s_stormtypes.tostr(htype))

    async def _storStorm(self, storm):
        await self._setHookValu('storm', await s_stormtypes.tostr(storm))

    async def _storEnabled(self, enabled):
        await self._setHookValu('enabled', await s_stormtypes.tobool(enabled))

@s_stormtypes.registry.registerLib
class LibViewHook(s_stormtypes.Lib):
    '''
    A Storm Library for managing view hooks.

    A view hook runs a Storm query as root, in the view, when a view is created,
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
                      {'name': 'type', 'type': 'str', 'desc': 'The hook type (`created`, `merging`, or `deleted`).'},
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
        return ViewHook(self.runt, hdef.get('iden'))

    async def _methHookDel(self, iden):
        self.runt.reqAdmin(mesg='Deleting a view hook requires admin privileges.')
        iden = await s_stormtypes.tostr(iden)
        await self.runt.snap.core.delViewHook(iden)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methHookGet(self, iden):
        self.runt.reqAdmin(mesg='Getting a view hook requires admin privileges.')
        iden = await s_stormtypes.tostr(iden)
        await self.runt.snap.core.getViewHook(iden)
        return ViewHook(self.runt, iden)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methHookList(self):
        self.runt.reqAdmin(mesg='Listing view hooks requires admin privileges.')
        hdefs = await self.runt.snap.core.getViewHooks()
        hdefs.sort(key=lambda hdef: hdef.get('created'))
        return [ViewHook(self.runt, hdef.get('iden')) for hdef in hdefs]
