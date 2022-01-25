import synapse.exc as s_exc
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
            Return a notification by ID (or $lib.null).

            ''',
            'type': {
                'type': 'function', '_funcname': 'get',
                'args': (
                    {'name': 'indx', 'type': 'int', 'desc': 'The index number of the notification to return.'},
                ),
                'returns': {
                    'name': 'retn', 'type': 'dict',
                    'desc': 'The requested notification or $lib.null.'},
            },
        },
    )

    def getObjLocals(self):
        return {
            'get': self.get,
            'del': self._del,
            'list': self.list,
            # 'bytime':
            # 'bytype':
        }

    async def get(self, indx):
        indx = await s_stormtypes.toint(indx)
        mesg = await self.runt.snap.core.getUserNotif(indx)
        if mesg[0] != self.runt.user.iden and not self.runt.isAdmin():
            mesg = 'You may only get notifications which belong to you.'
            raise s_exc.AuthDeny(mesg=mesg)
        return mesg

    async def _del(self, indx):
        indx = await s_stormtypes.toint(indx)
        mesg = await self.runt.snap.core.getUserNotif(indx)
        if mesg[0] != self.runt.user.iden and not self.runt.isAdmin():
            mesg = 'You may only delete notifications which belong to you.'
            raise s_exc.AuthDeny(mesg=mesg)
        await self.runt.snap.core.delUserNotif(indx)

    async def list(self, size=None):
        size = await s_stormtypes.toint(size, noneok=True)
        async for mesg in self.runt.snap.core.iterUserNotifs(self.runt.user.iden, size=size):
            yield mesg
