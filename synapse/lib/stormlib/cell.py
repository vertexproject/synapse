import asyncio
import logging

import synapse.exc as s_exc
import synapse.lib.autodoc as s_autodoc
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

def prepHotfixDesc(txt):
    lines = txt.split('\n')
    lines = s_autodoc.scrubLines(lines)
    lines = s_autodoc.ljuster(lines)
    return lines

storm_missing_autoadds = '''
$absoluteOrder = $lib.view.list(deporder=$lib.true)

if $lib.debug {
    $lib.print('The following Views will be fixed in order:')
    for $view in $absoluteOrder {
        $lib.print($view.iden)
    }
}

$queries = ( ${ inet:dns:request:query:name:fqdn [inet:fqdn=:query:name:fqdn] },
${ inet:dns:request:query:name:ipv4 [inet:ipv4=:query:name:ipv4] },
${ inet:dns:request:query:name:ipv6 [inet:ipv6=:query:name:ipv6] },
${ inet:dns:query:name:fqdn [inet:fqdn=:name:fqdn] },
${ inet:dns:query:name:ipv4 [inet:ipv4=:name:ipv4] },
${ inet:dns:query:name:ipv6 [inet:ipv6=:name:ipv6] },
${ inet:asnet4:net4:min [inet:ipv4=:net4:min] },
${ inet:asnet4:net4:max [inet:ipv4=:net4:max] },
${ inet:asnet6:net6:min [inet:ipv6=:net6:min] },
${ inet:asnet6:net6:max [inet:ipv6=:net6:max] },
${ inet:whois:iprec:net4:min [inet:ipv4=:net4:min] },
${ inet:whois:iprec:net4:max [inet:ipv4=:net4:max] },
${ inet:whois:iprec:net6:min [inet:ipv6=:net6:min] },
${ inet:whois:iprec:net6:max [inet:ipv6=:net6:max] },
${ it:app:snort:hit:src:ipv4 [inet:ipv4=:src:ipv4] },
${ it:app:snort:hit:src:ipv6 [inet:ipv6=:src:ipv6] },
${ it:app:snort:hit:dst:ipv4 [inet:ipv4=:dst:ipv4] },
${ it:app:snort:hit:dst:ipv6 [inet:ipv6=:dst:ipv6] },)

for $view in $absoluteOrder {
    if $lib.debug { $lib.print('Fixing autoadd data in view {v}', v=$view) }
    for $query in $queries {
        if $lib.debug { $lib.print('Executing { {q} }', q=$query) }
        view.exec $view.iden $query
    }
}
'''

storm_missing_coins = '''
    for $view in $lib.view.list(deporder=$lib.true) {
        view.exec $view.iden {
            $coins = $lib.set()
            crypto:currency:address
            $coins.add(:coin) | spin |
            for $coin in $coins {[ crypto:currency:coin=$coin ]}
        }
    }
'''

storm_missing_cpe22 = '''
$views = $lib.view.list(deporder=$lib.true)
for $view in $views {
    view.exec $view.iden { it:sec:cpe -:v2_2 [ :v2_2=$node.value() ] }
}
'''

storm_migrate_riskhasvuln = '''
for $view in $lib.view.list(deporder=$lib.true) {
    view.exec $view.iden {
        $layer = $lib.layer.get()
        for ($buid, $sode) in $layer.getStorNodesByForm(risk:hasvuln) {
            yield $buid
            $lib.model.migration.s.riskHasVulnToVulnerable($node)
        }
    }
}
'''

hotfixes = (
    ((1, 0, 0), {
        'desc': 'Create nodes for known missing autoadds.',
        'query': storm_missing_autoadds,
    }),
    ((2, 0, 0), {
        'desc': 'Populate crypto:currency:coin nodes from existing addresses.',
        'query': storm_missing_coins,
    }),
    ((3, 0, 0), {
        'desc': 'Populate it:sec:cpe:v2_2 properties from existing CPE where the property is not set.',
        'query': storm_missing_cpe22,
    }),
    ((4, 0, 0), {
        'desc': '''
            Create risk:vulnerable nodes from existing risk:hasvuln nodes.

            This hotfix should only be applied after all logic that would create
            risk:hasvuln nodes has been updated. The hotfix uses the
            $lib.model.migration.s.riskHasVulnToVulnerable() function,
            which can be used directly for testing.

            Tags, tag properties, edges, and node data will all be copied
            to the risk:vulnerable nodes.
        ''',
        'query': storm_migrate_riskhasvuln,
    }),
)
runtime_fixes_key = 'cortex:runtime:stormfixes'

def getMaxHotFixes():
    return max([vers for vers, info in hotfixes])

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
        {'name': 'getBackupInfo', 'desc': 'Get information about recent backup activity.',
         'type': {'type': 'function', '_funcname': '_getBackupInfo', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing backup information.', }}},
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
        {'name': 'hotFixesApply', 'desc': 'Apply known data migrations and fixes via storm.',
         'type': {'type': 'function', '_funcname': '_hotFixesApply', 'args': (),
                  'returns': {'type': 'list',
                              'desc': 'Tuple containing the current version after applying the fixes.'}}},
        {'name': 'hotFixesCheck', 'desc': 'Check to see if there are known hot fixes to apply.',
         'type': {'type': 'function', '_funcname': '_hotFixesCheck', 'args': (),
                  'returns': {'type': 'boolean', 'desc': 'Bool indicating if there are hot fixes to apply or not.'}}},
        {'name': 'trimNexsLog', 'desc': '''
            Rotate and cull the Nexus log (and any consumers) at the current offset.

            If the consumers argument is provided they will first be checked
            if online before rotating and raise otherwise.
            After rotation, all consumers provided must catch-up to the offset to cull at
            within the specified timeout before executing the cull, and will raise otherwise.
         ''',
         'type': {'type': 'function', '_funcname': '_trimNexsLog',
                  'args': (
                      {'name': 'consumers', 'type': 'array', 'default': None,
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
            'getBackupInfo': self._getBackupInfo,
            'getSystemInfo': self._getSystemInfo,
            'getHealthCheck': self._getHealthCheck,
            'getMirrorUrls': self._getMirrorUrls,
            'hotFixesApply': self._hotFixesApply,
            'hotFixesCheck': self._hotFixesCheck,
            'trimNexsLog': self._trimNexsLog,
            'uptime': self._uptime,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _getCellIden(self):
        return self.runt.snap.core.getCellIden()

    async def _hotFixesApply(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.stormFixesApply() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)

        curv = await self.runt.snap.core.getStormVar(runtime_fixes_key, default=(0, 0, 0))
        for vers, info in hotfixes:
            if vers <= curv:
                continue

            desc = info.get('desc')
            text = info.get('query')
            vars = info.get('vars', {})
            assert text is not None
            assert desc is not None
            assert vars is not None

            title = prepHotfixDesc(desc)[0]
            await self.runt.printf(f'Applying hotfix {vers} for [{title}]')

            try:
                query = await self.runt.getStormQuery(text)
                async with self.runt.getSubRuntime(query, opts={'vars': vars}) as runt:
                    async for item in runt.execute():
                        pass
            except asyncio.CancelledError: # pragma: no cover
                raise
            except Exception as e: # pragma: no cover
                logger.exception(f'Error applying storm hotfix {vers}')
                raise
            else:
                await self.runt.snap.core.setStormVar(runtime_fixes_key, vers)
                await self.runt.printf(f'Applied hotfix {vers}')
            curv = vers

        return curv

    @s_stormtypes.stormfunc(readonly=True)
    async def _hotFixesCheck(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.stormFixesCheck() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)

        curv = await self.runt.snap.core.getStormVar(runtime_fixes_key, default=(0, 0, 0))

        dowork = False
        for vers, info in hotfixes:
            if vers <= curv:
                continue

            dowork = True

            desclines = prepHotfixDesc(info.get('desc'))
            await self.runt.printf(f'Would apply fix {vers} for [{desclines[0]}]')
            if len(desclines) > 1:
                for line in desclines[1:]:
                    await self.runt.printf(f'    {line}' if line else '')
            else:
                await self.runt.printf('')

        return dowork

    @s_stormtypes.stormfunc(readonly=True)
    async def _getCellInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getCellInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return await self.runt.snap.core.getCellInfo()

    @s_stormtypes.stormfunc(readonly=True)
    async def _getSystemInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getSystemInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return await self.runt.snap.core.getSystemInfo()

    @s_stormtypes.stormfunc(readonly=True)
    async def _getBackupInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getBackupInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return await self.runt.snap.core.getBackupInfo()

    @s_stormtypes.stormfunc(readonly=True)
    async def _getHealthCheck(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getHealthCheck() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)
        return await self.runt.snap.core.getHealthCheck()

    @s_stormtypes.stormfunc(readonly=True)
    async def _getMirrorUrls(self, name=None):

        if not self.runt.isAdmin():
            mesg = '$lib.cell.getMirrorUrls() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)

        name = await s_stormtypes.tostr(name, noneok=True)

        if name is None:
            return await self.runt.snap.core.getMirrorUrls()

        ssvc = self.runt.snap.core.getStormSvc(name)
        if ssvc is None:
            mesg = f'No service with name/iden: {name}'
            raise s_exc.NoSuchName(mesg=mesg)

        await ssvc.proxy.waitready()
        return await ssvc.proxy.getMirrorUrls()

    async def _trimNexsLog(self, consumers=None, timeout=30):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.trimNexsLog() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg, user=self.runt.user.iden, username=self.runt.user.name)

        timeout = await s_stormtypes.toint(timeout, noneok=True)

        if consumers is not None:
            consumers = [await s_stormtypes.tostr(turl) async for turl in s_stormtypes.toiter(consumers)]

        return await self.runt.snap.core.trimNexsLog(consumers=consumers, timeout=timeout)

    @s_stormtypes.stormfunc(readonly=True)
    async def _uptime(self, name=None):

        name = await s_stormtypes.tostr(name, noneok=True)

        if name is None:
            info = await self.runt.snap.core.getSystemInfo()
        else:
            ssvc = self.runt.snap.core.getStormSvc(name)
            if ssvc is None:
                mesg = f'No service with name/iden: {name}'
                raise s_exc.NoSuchName(mesg=mesg)
            await ssvc.proxy.waitready()
            info = await ssvc.proxy.getSystemInfo()

        return {
            'starttime': info['cellstarttime'],
            'uptime': info['celluptime'],
        }
