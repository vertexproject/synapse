import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class CellLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with the Cortex.
    '''
    _storm_locals = (
        {'name': 'iden', 'desc': 'The Cortex service identifier.',
         'type': {'type': 'gtor', '_gtorfunc': '_getCellIden',
                  'returns': {'type': 'str', 'desc': 'The Cortex service identifier.'}}},
        {'name': 'getCellInfo', 'desc': 'Return metadata specific for the Cortex.',
         'type': {'type': 'function', '_funcname': '_getCellInfo', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing metadata.', }}},
        {'name': 'getSystemInfo', 'desc': 'Get info about the system in which the Cortex is running.',
         'type': {'type': 'function', '_funcname': '_getSystemInfo', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing system information.', }}},
        {'name': 'getHealthCheck', 'desc': 'Get healthcheck information about the Cortex.',
         'type': {'type': 'function', '_funcname': '_getHealthCheck', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing healthcheck information.', }}},
        {'name': 'getMirrorUrls', 'desc': 'Get mirror Telepath URLs for an AHA configured service.',
         'type': {'type': 'function', '_funcname': '_getMirrorUrls',
                  'args': (
                      {'name': 'name', 'type': 'str', 'default': None,
                       'desc': 'The name, or iden, of the service to get mirror URLs for '
                               '(defaults to the Cortex if not provided).'},
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of Telepath URLs.', }}},
        {'name': 'trimNexsLog', 'desc': '''
            Rotate and cull the Nexus log (and any consumers) at the current offset.

            If the consumers argument is provided they will first be checked
            if online before rotating and raise otherwise.
            After rotation, all consumers provided must catch-up to the offset to cull at
            within the specified timeout before executing the cull, and will raise otherwise.
         ''',
         'type': {'type': 'function', '_funcname': '_trimNexsLog',
                  'args': (
                      {'name': 'consumers', 'type': 'list', 'default': None,
                       'desc': 'List of Telepath URLs for consumers of the Nexus log.'},
                      {'name': 'timeout', 'type': 'int', 'default': 30,
                       'desc': 'Time (in seconds) to wait for consumers to catch-up before culling.'}
                  ),
                  'returns': {'type': 'int', 'desc': 'The offset that was culled (up to and including).'}}},
        {'name': 'uptime', 'desc': 'Get update data for the Cortex or a connected Service.',
         'type': {'type': 'function', '_funcname': '_uptime',
                  'args': (
                      {'name': 'name', 'type': 'str', 'default': None,
                       'desc': 'The name, or iden, of the service to get uptime data for '
                               '(defaults to the Cortex if not provided).'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing uptime data.', }}},
    )
    _storm_lib_path = ('cell',)

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name=name)
        self.gtors['iden'] = self._getCellIden

    def getObjLocals(self):
        return {
            'getCellInfo': self._getCellInfo,
            'getSystemInfo': self._getSystemInfo,
            'getHealthCheck': self._getHealthCheck,
            'getMirrorUrls': self._getMirrorUrls,
            'trimNexsLog': self._trimNexsLog,
            'uptime': self._uptime,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _getCellIden(self):
        return self.runt.view.core.getCellIden()

    @s_stormtypes.stormfunc(readonly=True)
    async def _getCellInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getCellInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return await self.runt.view.core.getCellInfo()

    @s_stormtypes.stormfunc(readonly=True)
    async def _getSystemInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getSystemInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return await self.runt.view.core.getSystemInfo()

    @s_stormtypes.stormfunc(readonly=True)
    async def _getHealthCheck(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getHealthCheck() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return await self.runt.view.core.getHealthCheck()

    @s_stormtypes.stormfunc(readonly=True)
    async def _getMirrorUrls(self, name=None):

        if not self.runt.isAdmin():
            mesg = '$lib.cell.getMirrorUrls() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)

        name = await s_stormtypes.tostr(name, noneok=True)

        if name is None:
            return await self.runt.view.core.getMirrorUrls()

        ssvc = self.runt.view.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name: {name}'
            raise s_exc.NoSuchName(mesg=mesg)

        proxy = await ssvc.proxy()
        return await proxy.getMirrorUrls()

    async def _trimNexsLog(self, consumers=None, timeout=30):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.trimNexsLog() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)

        timeout = await s_stormtypes.toint(timeout, noneok=True)

        if consumers is not None:
            consumers = [await s_stormtypes.tostr(turl) async for turl in s_stormtypes.toiter(consumers)]

        return await self.runt.view.core.trimNexsLog(consumers=consumers, timeout=timeout)

    @s_stormtypes.stormfunc(readonly=True)
    async def _uptime(self, name=None):

        name = await s_stormtypes.tostr(name, noneok=True)

        if name is None:
            info = await self.runt.view.core.getSystemInfo()
        else:
            ssvc = self.runt.view.core.getStormSvc(name)
            if ssvc is None:
                mesg = f'No service with name: {name}'
                raise s_exc.NoSuchName(mesg=mesg)
            proxy = await ssvc.proxy()
            info = await proxy.getSystemInfo()

        return {
            'starttime': info['cellstarttime'],
            'uptime': info['celluptime'],
        }
