import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes


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
    $lib.print('The following Wiews will be fixed in order:')
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

fixes = (
    ((0, 0, 1), storm_missing_autoadds),
)


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
    )
    _storm_lib_path = ('cell',)

    def getObjLocals(self):
        return {
            'fixApply': self._fixApply,
            'fixCheck': self._fixCheck,
            'getCellInfo': self._getCellInfo,
            'getBackupInfo': self._getBackupInfo,
            'getSystemInfo': self._getSystemInfo,
            'getHealthCheck': self._getHealthCheck,
        }

    async def _fixApply(self):
        pass

    async def _fixCheck(self):
        pass

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
