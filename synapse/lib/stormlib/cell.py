import asyncio
import logging

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)


storm_missing_autoadds = '''
$rootViews = $lib.list()
$view2children = $lib.dict()

for $view in $lib.view.list() {
    $iden=$view.iden
    $parent=$view.parent
    $layers=$lib.list()
    if ( $parent = $lib.null ) {
        $rootViews.append(($lib.len($view.layers), $iden))
    } else {
        if ($view2children.$parent = $lib.null) {
            $_a = $lib.list()
            $_a.append(($lib.len($view.layers), $iden))
            $view2children.$parent = $_a
        } else {
            $_a = $view2children.$parent
            $_a.append(($lib.len($view.layers), $iden))
            $_a.sort()
        }
    }
}

$rootViews.sort()

$absoluteOrder = $lib.list()
for ($_, $view) in $rootViews {
    $absoluteOrder.append($view)
    $children = $view2children.$view
    if $children {
        $todo=$lib.list()
        for ($_, $_child) in $children { $todo.append( $_child) }
        for $child in $todo {
            $absoluteOrder.append($child)
            $_children = $view2children.$child
            if $_children {
                for ($_, $_child) in $_children { $todo.append( $_child) }
            }
        }
    }
}

if $lib.debug {
    $lib.print('The following Views will be fixed in order:')
    for $view in $absoluteOrder {
        $lib.print($view)
    }
}

$queries = ( ${ inet:dns:request:query:name:fqdn $valu=:query:name:fqdn [inet:fqdn=$valu] },
${ inet:dns:request:query:name:ipv4 $valu=:query:name:ipv4 [inet:ipv4=$valu] },
${ inet:dns:request:query:name:ipv6 $valu=:query:name:ipv6 [inet:ipv6=$valu] },
${ inet:dns:query:name:fqdn $valu=:name:fqdn [inet:fqdn=$valu] },
${ inet:dns:query:name:ipv4 $valu=:name:ipv4 [inet:ipv4=$valu] },
${ inet:dns:query:name:ipv6 $valu=:name:ipv6 [inet:ipv6=$valu] },
${ inet:asnet4:net4:min $valu=:net4:min [inet:ipv4=$valu] },
${ inet:asnet4:net4:max $valu=:net4:max [inet:ipv4=$valu] },
${ inet:asnet6:net6:min $valu=:net6:min [inet:ipv6=$valu] },
${ inet:asnet6:net6:max $valu=:net6:max [inet:ipv6=$valu] },
${ inet:whois:iprec:net4:min $valu=:net4:min [inet:ipv4=$valu] },
${ inet:whois:iprec:net4:max $valu=:net4:max [inet:ipv4=$valu] },
${ inet:whois:iprec:net6:min $valu=:net6:min [inet:ipv6=$valu] },
${ inet:whois:iprec:net6:max $valu=:net6:max [inet:ipv6=$valu] },
${ it:app:snort:hit:src:ipv4 $valu=:src:ipv4 [inet:ipv4=$valu] },
${ it:app:snort:hit:src:ipv6 $valu=:src:ipv6 [inet:ipv6=$valu] },
${ it:app:snort:hit:dst:ipv4 $valu=:dst:ipv4 [inet:ipv4=$valu] },
${ it:app:snort:hit:dst:ipv6 $valu=:dst:ipv6 [inet:ipv6=$valu] },)

for $view in $absoluteOrder {
    if $lib.debug { $lib.print('Fixing autoadd data in view {v}', v=$view) }
    for $query in $queries {
        if $lib.debug { $lib.print('Executing { {q} }', q=$query) }
        view.exec $view $query
    }
}
'''


hotfixes = (
    ((1, 0, 0), {
        'desc': 'Create nodes for known missing autoadds.',
        'query': storm_missing_autoadds,
    }),
)
runtime_fixes_key = 'cortex:runtime:stormfixes'

def getMaxHotFixes():
    return max([vers for vers, info in hotfixes])

@s_stormtypes.registry.registerLib
class CellLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Json data.
    '''
    _storm_locals = (
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
        {'name': 'hotFixesApply', 'desc': 'Apply known data migrations and fixes via storm.',
         'type': {'type': 'function', '_funcname': '_hotFixesApply', 'args': (),
                  'returns': {'type': 'list',
                              'desc': 'Tuple containing the current version after applying the fixes.'}}},
        {'name': 'hotFixesCheck', 'desc': 'Check to see if there are known hot fixes to apply.',
         'type': {'type': 'function', '_funcname': '_hotFixesCheck', 'args': (),
                  'returns': {'type': 'bool', 'desc': 'Bool indicating if there are hot fixes to apply or not.'}}},
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
    )
    _storm_lib_path = ('cell',)

    def getObjLocals(self):
        return {
            'getCellInfo': self._getCellInfo,
            'getBackupInfo': self._getBackupInfo,
            'getSystemInfo': self._getSystemInfo,
            'getHealthCheck': self._getHealthCheck,
            'hotFixesApply': self._hotFixesApply,
            'hotFixesCheck': self._hotFixesCheck,
            'trimNexsLog': self._trimNexsLog,
        }

    async def _hotFixesApply(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.stormFixesApply() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)

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

            await self.runt.printf(f'Applying fix {vers} for [{desc}]')
            try:
                query = await self.runt.getStormQuery(text)
                async with self.runt.getSubRuntime(query, opts={'vars': vars}) as runt:
                    async for item in runt.execute():
                        pass
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception(f'Error applying stormfix {vers}')
                raise
            else:
                await self.runt.snap.core.setStormVar(runtime_fixes_key, vers)
                await self.runt.printf(f'Applied fix {vers}')
            curv = vers

        return curv

    async def _hotFixesCheck(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.stormFixesCheck() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)

        curv = await self.runt.snap.core.getStormVar(runtime_fixes_key, default=(0, 0, 0))

        dowork = False
        for vers, info in hotfixes:
            if vers <= curv:
                continue

            dowork = True
            desc = info.get('desc')
            await self.runt.printf(f'Would apply fix {vers} for [{desc}]')

        return dowork

    async def _getCellInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getCellInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.getCellInfo()

    async def _getSystemInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getSystemInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.getSystemInfo()

    async def _getBackupInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getBackupInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.getBackupInfo()

    async def _getHealthCheck(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getHealthCheck() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.getHealthCheck()

    async def _trimNexsLog(self, consumers=None, timeout=30):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.trimNexsLog() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)

        timeout = await s_stormtypes.toint(timeout, noneok=True)

        if consumers is not None:
            consumers = [await s_stormtypes.tostr(turl) async for turl in s_stormtypes.toiter(consumers)]

        return await self.runt.snap.core.trimNexsLog(consumers=consumers, timeout=timeout)
