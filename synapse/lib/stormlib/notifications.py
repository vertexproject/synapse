import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class NotifyLib(s_stormtypes.Lib):
    '''A Storm library for a user interacting with their notifications.'''
    _storm_lib_path = ('notifications', )
    _storm_locals = (
        {
            'name': 'list',
            'desc': '''
            Yield (<indx>, <mesg>) tuples for a user's notifications.

            ''',
            'deprecated': {'eolvers': 'v3.0.0'},
            'type': {
                'type': 'function', '_funcname': 'list',
                'args': (
                    {'name': 'size', 'type': 'int', 'desc': 'The max number of notifications to yield.', 'default': None},
                ),
                'returns': {
                    'name': 'Yields', 'type': 'list',
                    'desc': 'Yields (useriden, time, mesgtype, msgdata) tuples.'},
            },
        },
        {
            'name': 'del',
            'desc': '''
            Delete a previously delivered notification.

            ''',
            'deprecated': {'eolvers': 'v3.0.0'},
            'type': {
                'type': 'function', '_funcname': '_del',
                'args': (
                    {'name': 'indx', 'type': 'int', 'desc': 'The index number of the notification to delete.'},
                ),
                'returns': {
                    'name': 'retn', 'type': 'list',
                    'desc': 'Returns an ($ok, $valu) tuple.'},
            },
        },
        {
            'name': 'get',
            'desc': '''
            Return a notification by ID (or ``(null)`` ).

            ''',
            'deprecated': {'eolvers': 'v3.0.0'},
            'type': {
                'type': 'function', '_funcname': 'get',
                'args': (
                    {'name': 'indx', 'type': 'int', 'desc': 'The index number of the notification to return.'},
                ),
                'returns': {
                    'name': 'retn', 'type': 'dict',
                    'desc': 'The requested notification or ``(null)``.'},
            },
        },
    )
    _storm_lib_deprecation = {'eolvers': 'v3.0.0'}

    def getObjLocals(self):
        return {
            'get': self.get,
            'del': self._del,
            'list': self.list,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def get(self, indx):
        indx = await s_stormtypes.toint(indx)
        mesg = await self.runt.snap.core.getUserNotif(indx)
        s_common.deprecated('$lib.notifications.get()', '2.210.0', '3.0.0')
        await self.runt.snap.warnonce('$lib.notifications.get() is deprecated.')
        if mesg[0] != self.runt.user.iden and not self.runt.isAdmin():
            mesg = 'You may only get notifications which belong to you.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return mesg

    async def _del(self, indx):
        indx = await s_stormtypes.toint(indx)
        mesg = await self.runt.snap.core.getUserNotif(indx)
        s_common.deprecated('$lib.notifications.del()', '2.210.0', '3.0.0')
        await self.runt.snap.warnonce('$lib.notifications.del() is deprecated.')
        if mesg[0] != self.runt.user.iden and not self.runt.isAdmin():
            mesg = 'You may only delete notifications which belong to you.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        await self.runt.snap.core.delUserNotif(indx)

    @s_stormtypes.stormfunc(readonly=True)
    async def list(self, size=None):
        size = await s_stormtypes.toint(size, noneok=True)
        s_common.deprecated('$lib.notifications.list()', '2.210.0', '3.0.0')
        await self.runt.snap.warnonce('$lib.notifications.list() is deprecated.')
        async for mesg in self.runt.snap.core.iterUserNotifs(self.runt.user.iden, size=size):
            yield mesg
